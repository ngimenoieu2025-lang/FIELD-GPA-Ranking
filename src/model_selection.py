"""Prediction models for a field's grade deviation, with temporal tuning and test errors.

Instructor's feedback on the Sentence Outline: state which model predicts, its
errors and its tuning. This script makes the temporal validation of progress.py
complete and reproducible.

Target: deviation of a university-field-year mean grade from its university-year
average ("dev", grade points). Test set: 2022-2023 for university-fields seen
before 2022. Every hyperparameter is chosen by expanding-window validation
inside 2015-2021 (train on years < v, validate on year v, v = 2018..2021), so the
test years are never used for tuning.

Models
  baseline          predicts 0 (every field graded like its university average)
  common_field      field mean deviation across universities (no hyperparameter)
  shrunk_profile    common field effect + n/(n+k) x university's own past
                    deviation from it; k (shrinkage) is tuned
  ridge_profile     ridge regression on field and university-by-field indicators;
                    alpha is tuned
  gradient_boosting field, past university-field deviation and its count, dropout
                    and size; depth, learning rate and number of trees tuned

Outputs: results/model_selection_stats.json, results/model_selection_tuning.csv,
figures/model_selection_tuning.pdf/.png.
"""
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from ministry import load as load_spain
from progress import FIG, RES, load_covariates, specific_deviation

SEED = 42
TEST_FROM = 2022
VAL_YEARS = [2018, 2019, 2020, 2021]
K_GRID = [0, 0.25, 0.5, 1, 2, 3, 5, 8, 13, 21, 50, 1e9]
ALPHA_GRID = list(np.logspace(-2, 3, 16))
GBM_GRID = list(itertools.product([2, 3, 5, 8], [0.03, 0.1, 0.3], [100, 300, 600]))


# ---------------------------------------------------------------- features
def history(train: pd.DataFrame) -> pd.DataFrame:
    """Common field effect and each university-field's past deviation from it, from training years only."""
    common = train.groupby("field")["dev"].mean().rename("common")
    t = train.join(common, on="field")
    t["spec"] = t["dev"] - t["common"]
    prof = t.groupby(["univ", "field"])["spec"].agg(spec_mean="mean", n_past="size")
    return common, prof


def add_history(rows: pd.DataFrame, common: pd.Series, prof: pd.DataFrame) -> pd.DataFrame:
    r = rows.join(common, on="field").join(prof, on=["univ", "field"])
    r["common"] = r["common"].fillna(0.0)
    r["spec_mean"] = r["spec_mean"].fillna(0.0)
    r["n_past"] = r["n_past"].fillna(0)
    return r


def expanding_history(train: pd.DataFrame) -> pd.DataFrame:
    """For gradient-boosting training rows: features from years strictly before each row's year."""
    out = []
    for yr in sorted(train["year"].unique())[1:]:
        common, prof = history(train[train["year"] < yr])
        out.append(add_history(train[train["year"] == yr], common, prof))
    return pd.concat(out)


# ---------------------------------------------------------------- models
def fit_predict(name: str, hp, train: pd.DataFrame, target: pd.DataFrame) -> np.ndarray:
    common, prof = history(train)
    tgt = add_history(target, common, prof)
    if name == "baseline":
        return np.zeros(len(target))
    if name == "common_field":
        return tgt["common"].to_numpy()
    if name == "shrunk_profile":
        k = hp
        w = tgt["n_past"] / (tgt["n_past"] + k) if k > 0 else (tgt["n_past"] > 0).astype(float)
        return (tgt["common"] + w * tgt["spec_mean"]).to_numpy()
    if name == "ridge_profile":
        m = make_pipeline(ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), ["field", "uf"])]),
                          Ridge(alpha=hp))
        m.fit(train[["field", "uf"]], train["dev"])
        return m.predict(target[["field", "uf"]])
    if name == "gradient_boosting":
        depth, lr, trees = hp
        num = ["common", "spec_mean", "n_past", "dropout_z", "log_grads_z"]
        tr = expanding_history(train)
        m = make_pipeline(
            ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["field"]),
                               ("n", "passthrough", num)]),
            HistGradientBoostingRegressor(max_depth=depth, learning_rate=lr, max_iter=trees, random_state=SEED))
        m.fit(tr[["field"] + num].fillna(0), tr["dev"])
        return m.predict(tgt[["field"] + num].fillna(0))
    raise ValueError(name)


GRIDS = {"baseline": [None], "common_field": [None], "shrunk_profile": K_GRID,
         "ridge_profile": ALPHA_GRID, "gradient_boosting": GBM_GRID}


def rmse(y, p) -> float:
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def tune(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, grid in GRIDS.items():
        for hp in grid:
            errs = []
            for v in VAL_YEARS:
                tr, va = d[d["year"] < v], d[d["year"] == v]
                va = va[va["uf"].isin(tr["uf"])]
                errs.append(rmse(va["dev"], fit_predict(name, hp, tr, va)))
            rows.append({"model": name, "hyperparameter": str(hp), "hp": hp, "val_rmse": float(np.mean(errs)),
                         **{f"rmse_{v}": e for v, e in zip(VAL_YEARS, errs)}})
    return pd.DataFrame(rows)


def test(d: pd.DataFrame, best: dict) -> dict:
    tr, te = d[d["year"] < TEST_FROM], d[d["year"] >= TEST_FROM]
    te = te[te["uf"].isin(tr["uf"])]
    rng = np.random.default_rng(SEED)
    univs = te["univ"].unique()
    pos = {u: np.flatnonzero(te["univ"].to_numpy() == u) for u in univs}
    boot = [np.concatenate([pos[u] for u in rng.choice(univs, len(univs))]) for _ in range(1000)]
    out = {"n_train": int(len(tr)), "n_test": int(len(te)), "n_test_univ": int(len(univs))}
    preds = {}
    for name, hp in best.items():
        p = fit_predict(name, hp, tr, te)
        preds[name] = p
        e = te["dev"].to_numpy() - p
        b = [np.sqrt(np.mean(e[i] ** 2)) for i in boot]
        out[name] = {"hyperparameter": hp if not isinstance(hp, tuple) else
                     {"max_depth": hp[0], "learning_rate": hp[1], "n_trees": hp[2]},
                     "rmse": float(np.sqrt(np.mean(e ** 2))), "mae": float(np.mean(np.abs(e))),
                     "rmse_ci95_bootstrap_universities": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
                     "r2": float(1 - np.sum(e ** 2) / np.sum((te["dev"] - te["dev"].mean()) ** 2))}
    # paired bootstrap: profile models against the common field effect, and boosting against shrinkage
    e_s = (te["dev"].to_numpy() - preds["shrunk_profile"]) ** 2
    e_g = (te["dev"].to_numpy() - preds["gradient_boosting"]) ** 2
    out["gradient_boosting"]["rmse_minus_shrunk_profile_ci95"] = [float(np.percentile(v, q)) for v in [[np.sqrt(e_g[i].mean()) - np.sqrt(e_s[i].mean()) for i in boot]] for q in (2.5, 97.5)]
    e_c = (te["dev"].to_numpy() - preds["common_field"]) ** 2
    for name in ["shrunk_profile", "ridge_profile", "gradient_boosting"]:
        e_m = (te["dev"].to_numpy() - preds[name]) ** 2
        diff = [np.sqrt(e_m[i].mean()) - np.sqrt(e_c[i].mean()) for i in boot]
        out[name]["rmse_minus_common_field_ci95"] = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
    return out


def fig(tun: pd.DataFrame, best_k: float) -> None:
    fig_, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    common = tun.loc[tun["model"] == "common_field", "val_rmse"].iloc[0]
    s = tun[tun["model"] == "shrunk_profile"].copy()
    s = s[s["hp"] < 1e8]
    axes[0].plot(s["hp"].astype(float) + 0.1, s["val_rmse"], "o-", color="tab:blue")
    axes[0].axhline(common, color="tab:gray", ls="--", label="Common field effect only")
    axes[0].axvline(best_k + 0.1, color="tab:red", lw=0.8, label=f"Chosen k = {best_k:g}")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Shrinkage k (+0.1, log scale)\nweight on own past = n / (n + k)")
    axes[0].set_ylabel("Validation RMSE, 2018-2021\n(grade points)")
    axes[0].legend(frameon=False, fontsize=8)
    r = tun[tun["model"] == "ridge_profile"]
    axes[1].plot(r["hp"].astype(float), r["val_rmse"], "s-", color="tab:green")
    axes[1].axhline(common, color="tab:gray", ls="--")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Ridge penalty alpha (log scale)")
    fig_.tight_layout()
    fig_.savefig(FIG / "model_selection_tuning.pdf")
    fig_.savefig(FIG / "model_selection_tuning.png", dpi=200)
    plt.close(fig_)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    d = specific_deviation(load_spain())[["univ", "field", "year", "dev"]].copy()
    dropout, grads = load_covariates()
    cov = dropout.to_frame().join(np.log(grads.groupby(level=[0, 1]).mean()).rename("log_grads"), how="outer")
    for c in ["dropout", "log_grads"]:
        cov[c + "_z"] = (cov[c] - cov[c].mean()) / cov[c].std()
    d = d.join(cov[["dropout_z", "log_grads_z"]], on=["univ", "field"]).reset_index(drop=True)
    d["uf"] = d["univ"] + "|" + d["field"]

    tun = tune(d)
    tun.drop(columns="hp").round(5).to_csv(RES / "model_selection_tuning.csv", index=False)
    best = {m: g.loc[g["val_rmse"].idxmin(), "hp"] for m, g in tun.groupby("model", sort=False)}
    stats = {"validation_years": VAL_YEARS, "test_years": [TEST_FROM, int(d["year"].max())],
             "validation_rmse_best": {m: float(g["val_rmse"].min()) for m, g in tun.groupby("model", sort=False)},
             "test": test(d, best)}
    fig(tun, float(best["shrunk_profile"]))
    (RES / "model_selection_stats.json").write_text(json.dumps(stats, indent=2, default=float), encoding="utf-8")
    print(json.dumps(stats, indent=2, default=float))


if __name__ == "__main__":
    main()
