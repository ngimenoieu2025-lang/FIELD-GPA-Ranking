"""Preliminary analysis for the project proposal.

1. Exploratory figures: grade distributions by degree.
2. Linear regression: how much of the gap between degrees survives after
   controlling for the students' entry grades and background.
3. Selection simulation: who makes a top-20% cut when students are ranked by
   raw GPA, by within-degree z-score, or by regression-adjusted GPA.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.model_selection import KFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from load_data import ROOT, load_clean, load_raw

FIG = ROOT / "figures"
RES = ROOT / "results"
SEED = 42
TOP_SHARE = 0.20
CONTROLS = ["admission_grade", "prev_grade", "age", "male", "scholarship", "displaced", "international"]

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def degree_summary(raw: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Per-degree grade statistics, including students who passed no unit."""
    raw = raw[raw["course"].isin(df["course"].unique())]
    no_pass = (
        raw.assign(no_pass=(raw["approved_1"] + raw["approved_2"]) == 0)
        .groupby("course")["no_pass"]
        .mean()
    )
    out = df.groupby("course").agg(
        n=("gpa", "size"),
        gpa_mean=("gpa", "mean"),
        gpa_sd=("gpa", "std"),
        gpa_p80=("gpa", lambda s: s.quantile(0.8)),
        admission_mean=("admission_grade", "mean"),
    )
    out["share_no_unit_passed"] = no_pass
    return out.sort_values("gpa_mean")


def fig_boxplot(df: pd.DataFrame, order: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5))
    data = [df.loc[df["course"] == c, "gpa"] for c in order]
    ax.boxplot(data, orientation="horizontal", tick_labels=order, showfliers=False,
               medianprops={"color": "black"})
    ax.axvline(df["gpa"].mean(), color="tab:red", ls="--", lw=1, label="Overall mean")
    ax.set_xlabel("First-year grade average (0-20 scale)")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "gpa_by_degree.pdf")
    fig.savefig(FIG / "gpa_by_degree.png", dpi=200)
    plt.close(fig)


def fit_models(df: pd.DataFrame):
    """OLS with sum-coded degree effects, so each effect is relative to the
    unweighted average degree rather than to an arbitrary baseline."""
    rhs = " + ".join(CONTROLS)
    m_degree = smf.ols("gpa ~ C(course, Sum)", df).fit()
    m_controls = smf.ols(f"gpa ~ {rhs}", df).fit()
    m_full = smf.ols(f"gpa ~ {rhs} + C(course, Sum)", df).fit()
    return m_degree, m_controls, m_full


def degree_effects(model, courses: list[str]) -> pd.DataFrame:
    """Recover all degree effects (the last level is minus the sum of the others)."""
    names = [n for n in model.params.index if n.startswith("C(course, Sum)")]
    est = model.params[names].to_numpy()
    cov = model.cov_params().loc[names, names].to_numpy()
    last_se = np.sqrt(np.ones(len(names)) @ cov @ np.ones(len(names)))
    effects = np.append(est, -est.sum())
    ses = np.append(np.sqrt(np.diag(cov)), last_se)
    return pd.DataFrame({"effect": effects, "se": ses}, index=sorted(courses))


def fig_effects(raw_eff: pd.DataFrame, adj_eff: pd.DataFrame) -> None:
    order = raw_eff.sort_values("effect").index
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.errorbar(raw_eff.loc[order, "effect"], y + 0.15, xerr=1.96 * raw_eff.loc[order, "se"],
                fmt="o", color="tab:gray", label="Raw gap", capsize=2)
    ax.errorbar(adj_eff.loc[order, "effect"], y - 0.15, xerr=1.96 * adj_eff.loc[order, "se"],
                fmt="s", color="tab:blue", label="After controlling for entry grades", capsize=2)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, order)
    ax.set_xlabel("Difference from the average degree (grade points, 95% CI)")
    fig.legend(frameon=False, loc="upper center", ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "degree_effects.pdf")
    fig.savefig(FIG / "degree_effects.png", dpi=200)
    plt.close(fig)


def cross_validated_rmse(df: pd.DataFrame) -> dict:
    """Out-of-sample error with and without the degree as a predictor."""
    cv = KFold(n_splits=10, shuffle=True, random_state=SEED)
    y = df["gpa"]

    def rmse(features, estimator):
        cat = [c for c in features if c == "course"]
        num = [c for c in features if c != "course"]
        pre = ColumnTransformer([("num", StandardScaler(), num),
                                 ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
        scores = cross_val_score(make_pipeline(pre, estimator), df[features], y, cv=cv,
                                 scoring="neg_root_mean_squared_error")
        return float(-scores.mean())

    return {
        "baseline_mean_only": float(y.std()),
        "controls_only": rmse(CONTROLS, LinearRegression()),
        "degree_only": rmse(["course"], LinearRegression()),
        "controls_plus_degree": rmse(CONTROLS + ["course"], LinearRegression()),
        "controls_plus_degree_ridge": rmse(CONTROLS + ["course"], RidgeCV(alphas=np.logspace(-3, 3, 25))),
    }


def selection_simulation(df: pd.DataFrame, adj_eff: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Rank all students for a top-20% cut under three scoring rules."""
    df = df.copy()
    grp = df.groupby("course")["gpa"]
    df["score_raw"] = df["gpa"]
    df["score_z"] = (df["gpa"] - grp.transform("mean")) / grp.transform("std")
    df["score_adj"] = df["gpa"] - df["course"].map(adj_eff["effect"])
    k = int(round(TOP_SHARE * len(df)))
    picked = {}
    for rule in ["raw", "z", "adj"]:
        # Ties are broken at random so no degree benefits from row order.
        ranked = df.sample(frac=1, random_state=SEED).sort_values(f"score_{rule}", ascending=False, kind="stable")
        picked[rule] = set(ranked.index[:k])
        df[f"sel_{rule}"] = df.index.isin(picked[rule])
    by_degree = df.groupby("course")[["sel_raw", "sel_z", "sel_adj"]].mean()
    by_degree["n"] = df.groupby("course").size()
    swaps = {
        "places": k,
        "changed_raw_vs_z": len(picked["raw"] - picked["z"]),
        "changed_raw_vs_adj": len(picked["raw"] - picked["adj"]),
    }
    return by_degree.sort_values("sel_raw"), swaps


def fig_selection(by_degree: pd.DataFrame) -> None:
    order = by_degree.index
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.barh(y + 0.2, 100 * by_degree["sel_raw"], height=0.4, color="tab:gray", label="Ranked by raw GPA")
    ax.barh(y - 0.2, 100 * by_degree["sel_z"], height=0.4, color="tab:blue", label="Ranked by within-degree z-score")
    ax.axvline(100 * TOP_SHARE, color="tab:red", ls="--", lw=1, label="Equal access (20%)")
    ax.set_yticks(y, order)
    ax.set_xlabel("Students of the degree selected in a top-20% cut (%)")
    fig.legend(frameon=False, loc="upper center", ncol=3, fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "selection_by_degree.pdf")
    fig.savefig(FIG / "selection_by_degree.png", dpi=200)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(exist_ok=True)
    RES.mkdir(exist_ok=True)
    raw, df = load_raw(), load_clean()
    courses = list(df["course"].unique())

    summary = degree_summary(raw, df)
    summary.round(3).to_csv(RES / "degree_summary.csv")
    fig_boxplot(df, list(summary.index))

    m_degree, m_controls, m_full = fit_models(df)
    raw_eff, adj_eff = degree_effects(m_degree, courses), degree_effects(m_full, courses)
    effects = raw_eff.join(adj_eff, lsuffix="_raw", rsuffix="_adj").sort_values("effect_raw")
    effects.round(3).to_csv(RES / "degree_effects.csv")
    fig_effects(raw_eff, adj_eff)

    by_degree, swaps = selection_simulation(df, adj_eff)
    by_degree.round(3).to_csv(RES / "selection_by_degree.csv")
    fig_selection(by_degree)

    f_test = m_full.compare_f_test(m_controls)
    stats = {
        "n_students": int(len(df)),
        "n_degrees": len(courses),
        "gpa_mean": float(df["gpa"].mean()),
        "gpa_sd": float(df["gpa"].std()),
        "raw_gap_max_minus_min": float(summary["gpa_mean"].max() - summary["gpa_mean"].min()),
        "r2_degree_only": float(m_degree.rsquared),
        "r2_controls_only": float(m_controls.rsquared),
        "r2_controls_plus_degree": float(m_full.rsquared),
        "f_test_degree_given_controls": {"F": float(f_test[0]), "p": float(f_test[1]), "df": float(f_test[2])},
        "sd_degree_effects_raw": float(raw_eff["effect"].std(ddof=0)),
        "sd_degree_effects_adjusted": float(adj_eff["effect"].std(ddof=0)),
        "adjusted_gap_max_minus_min": float(adj_eff["effect"].max() - adj_eff["effect"].min()),
        "corr_raw_vs_adjusted_effects": float(raw_eff["effect"].corr(adj_eff["effect"])),
        "admission_grade_coef": float(m_full.params["admission_grade"]),
        "cv_rmse": cross_validated_rmse(df),
        "selection": swaps,
    }
    (RES / "summary_stats.json").write_text(json.dumps(stats, indent=2))

    print(json.dumps(stats, indent=2))
    print(summary.round(2).to_string())
    print(effects.round(2).to_string())
    print((100 * by_degree[["sel_raw", "sel_z", "sel_adj"]]).round(1).join(by_degree["n"]).to_string())


if __name__ == "__main__":
    main()
