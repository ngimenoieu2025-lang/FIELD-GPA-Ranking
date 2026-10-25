"""Progress Report analyses, following the instructor's feedback on the proposal.

The question to answer: is the deviation of a field from its university's
average the same in every university (a common field effect), or does it change
from one university to another (university-specific grading by field)? And what
could explain the field effects?

1. Variance decomposition: university-year, common field, university-by-field
   interaction, residual year-to-year noise.
2. Persistence: does a university's field-specific deviation repeat next year?
3. Temporal validation: train on 2015-2021, test on 2022-2023, with and without
   the university's own past field deviations.
4. Confounders: admission grade, dropout and size; how much do field effects
   shrink when they are controlled for?
5. Selection simulation weighted by the number of graduates.
6. k-means and PCA on field grading profiles.
7. Portuguese records: logistic regression for reaching the top 20%, and a
   comparison of normalisation rules.
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
from scipy.optimize import brentq
from scipy.stats import norm
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import roc_auc_score, root_mean_squared_error, silhouette_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analysis import CONTROLS, degree_effects
from load_data import ROOT, load_clean
from ministry import FIELDS, IE, IE_FIELDS, IQR_TO_SD, TOP_SHARE, load as load_spain

RAW = ROOT / "data" / "raw" / "ministerio"
FIG = ROOT / "figures"
RES = ROOT / "results"
SEED = 42
ALPHAS = np.logspace(-3, 3, 25)

# Approximate mapping of the detailed fields to the five Spanish "ramas"
# (admission grades by university are only published per rama).
RAMA = {
    "Early childhood teaching": "Ciencias Sociales y Jurídicas", "Primary teaching": "Ciencias Sociales y Jurídicas",
    "Other education": "Ciencias Sociales y Jurídicas", "Audiovisual & media": "Ciencias Sociales y Jurídicas",
    "Arts": "Artes y Humanidades", "Languages": "Artes y Humanidades", "Humanities": "Artes y Humanidades",
    "Psychology": "Ciencias de la Salud", "Economics": "Ciencias Sociales y Jurídicas",
    "Other social sciences": "Ciencias Sociales y Jurídicas", "Journalism": "Ciencias Sociales y Jurídicas",
    "Business administration": "Ciencias Sociales y Jurídicas", "Other business": "Ciencias Sociales y Jurídicas",
    "Law": "Ciencias Sociales y Jurídicas", "Life sciences": "Ciencias", "Physical sciences": "Ciencias",
    "Mathematics & statistics": "Ciencias", "Computer science": "Ingeniería y Arquitectura",
    "Engineering": "Ingeniería y Arquitectura", "Architecture": "Ingeniería y Arquitectura",
    "Agriculture": "Ingeniería y Arquitectura", "Veterinary": "Ciencias de la Salud", "Medicine": "Ciencias de la Salud",
    "Nursing": "Ciencias de la Salud", "Other health": "Ciencias de la Salud",
    "Social work": "Ciencias Sociales y Jurídicas", "Sports": "Ciencias Sociales y Jurídicas",
    "Tourism": "Ciencias Sociales y Jurídicas", "Other services": "Ciencias Sociales y Jurídicas",
}

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


# ---------------------------------------------------------------- loading
def read_table(name: str, cols: list[str]) -> pd.DataFrame:
    df = pd.read_csv(RAW / f"{name}.csv", sep=";", encoding="utf-8", dtype=str)
    df.columns = cols
    df["value"] = pd.to_numeric(df["value"].str.replace(".", "", regex=False).str.replace(",", "."), errors="coerce")
    if "field" in df:
        df["field"] = df["field"].str.replace(r"\s+", " ", regex=True).map(FIELDS)
    return df.dropna(subset=["value"])


def load_covariates() -> pd.DataFrame:
    """University-by-field averages of dropout and graduate counts."""
    ab = read_table("Abandono_Grado_Univ", ["univ", "field", "sex", "ind", "period", "value"])
    ab = ab[(ab["sex"] == "Ambos sexos") & (ab["ind"] == "Tasa global de abandono") & ab["field"].notna()]
    dropout = ab.groupby(["univ", "field"])["value"].mean().rename("dropout")

    eg = read_table("px_estu_grado_egre_edad_ambito_univ", ["univ", "sex", "age", "field", "period", "value"])
    eg = eg[(eg["sex"] == "Ambos sexos") & (eg["age"] == "Total") & eg["field"].notna()]
    eg["year"] = eg["period"].str[:4].astype(int)
    grads = eg.set_index(["univ", "field", "year"])["value"].rename("graduates")
    return dropout, grads


def load_admission() -> tuple[pd.Series, pd.Series]:
    """National admission grade by field, and university admission grade by rama (public universities)."""
    nat = read_table("px_estu_grado_ni_media_ambito_tot", ["adm", "field", "sex", "ind", "period", "value"])
    nat = nat[(nat["adm"] == "Total") & (nat["sex"] == "Ambos sexos") & (nat["ind"] == "Nota media") & nat["field"].notna()]
    by_field = nat.groupby("field")["value"].mean().rename("admission_field")
    uni = read_table("px_estu_grado_ni_media_rama_univ", ["univ", "adm", "rama", "sex", "ind", "period", "value"])
    uni = uni[(uni["adm"] == "Total") & (uni["sex"] == "Ambos sexos") & (uni["ind"] == "Nota media") & (uni["rama"] != "Total")]
    by_univ_rama = uni.groupby(["univ", "rama"])["value"].mean().rename("admission_univ_rama")
    return by_field, by_univ_rama


# ---------------------------------------------------------------- 1-2. decomposition and persistence
def decomposition(df: pd.DataFrame) -> dict:
    m_uy = smf.ols("mean ~ C(univ):C(year)", df).fit()
    m_f = smf.ols("mean ~ C(univ):C(year) + C(field)", df).fit()
    m_fu = smf.ols("mean ~ C(univ):C(year) + C(field) + C(univ):C(field)", df).fit()
    tss = ((df["mean"] - df["mean"].mean()) ** 2).sum()
    within = m_uy.ssr  # variation left once each university-year average is removed
    f = m_fu.compare_f_test(m_f)
    return {
        "share_total_university_year": float(1 - m_uy.ssr / tss),
        "share_within_common_field": float((m_uy.ssr - m_f.ssr) / within),
        "share_within_university_specific_field": float((m_f.ssr - m_fu.ssr) / within),
        "share_within_year_noise": float(m_fu.ssr / within),
        "f_test_interaction": {"F": float(f[0]), "p": float(f[1]), "df": float(f[2])},
        "n_univ_field_cells": int(df.groupby(["univ", "field"]).ngroups),
    }


def specific_deviation(df: pd.DataFrame) -> pd.DataFrame:
    """Deviation of a university-field-year from its university-year average and
    from the common field effect (estimated by OLS)."""
    df = df.copy()
    df["dev"] = df["mean"] - df.groupby(["univ", "year"])["mean"].transform("mean")
    common = smf.ols("dev ~ C(field) - 1", df).fit().params
    df["common"] = df["field"].map({k.split("[")[1].rstrip("]"): v for k, v in common.items()})
    df["specific"] = df["dev"] - df["common"]
    return df


def persistence(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    s = df.set_index(["univ", "field", "year"])["specific"].sort_index()
    nxt = s.groupby(level=[0, 1]).shift(-1)
    pair = pd.DataFrame({"t": s, "t1": nxt}).dropna()
    pair = pair[pair.index.get_level_values("year").isin(range(2015, 2023))]
    gap = s.reset_index()
    gap["next_year"] = gap.groupby(["univ", "field"])["year"].shift(-1)
    consecutive = gap.dropna(subset=["next_year"])
    consecutive = consecutive[consecutive["next_year"] == consecutive["year"] + 1].set_index(["univ", "field", "year"]).index
    pair = pair.loc[pair.index.intersection(consecutive)]
    r, n = float(pair["t"].corr(pair["t1"])), len(pair)
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    return {"lag1_correlation": r, "ci95": [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))],
            "n_pairs": int(n)}, pair


def fig_persistence(pair: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    ax.scatter(pair["t"], pair["t1"], s=5, alpha=0.25, color="tab:blue", edgecolors="none",
               label="One university and field, two consecutive years")
    lim = np.nanpercentile(np.abs(pair.to_numpy()), 99.5)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axhline(0, color="gray", lw=0.6)
    ax.axvline(0, color="gray", lw=0.6)
    b = np.polyfit(pair["t"], pair["t1"], 1)
    xs = np.linspace(-lim, lim, 10)
    ax.plot(xs, np.polyval(b, xs), color="black", lw=1.2, label=f"Least-squares line (slope {b[0]:.2f})")
    ax.plot(xs, xs, color="tab:red", lw=1, ls="--", label="Perfect persistence (slope 1)")
    ax.set_xlabel("Year t: deviation not explained by the common field effect\n(grade points, 5-10 scale)")
    ax.set_ylabel("Year t+1: same university and field (grade points)")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.text(0.98, 0.03, f"r = {pair['t'].corr(pair['t1']):.2f}\n{len(pair):,} pairs",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "persistence.pdf")
    fig.savefig(FIG / "persistence.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- 3. temporal validation
def temporal_validation(df: pd.DataFrame, covars: pd.DataFrame) -> dict:
    d = df.join(covars, on=["univ", "field"])
    d["uf"] = d["univ"] + "|" + d["field"]
    tr, te = d[d["year"] <= 2021], d[d["year"] >= 2022]
    te = te[te["uf"].isin(tr["uf"])]  # future years of university-fields seen in training
    y_tr, y_te = tr["dev"], te["dev"]

    def ridge(cats):
        return make_pipeline(ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), cats)]), RidgeCV(alphas=ALPHAS))

    num = ["dropout_z", "log_grads_z"]
    gbm = make_pipeline(
        ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["field"]),
                           ("n", "passthrough", num)]),
        HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=300, random_state=SEED))
    models = {
        "baseline: zero deviation": DummyRegressor(strategy="constant", constant=0.0),
        "ridge: common field effect": ridge(["field"]),
        "ridge: field + university-by-field": ridge(["field", "uf"]),
        "gradient boosting: field + dropout + size": gbm,
    }
    out = {"n_train": int(len(tr)), "n_test": int(len(te)), "n_test_univ": int(te["univ"].nunique())}
    rng = np.random.default_rng(SEED)
    univs = te["univ"].unique()
    boot_idx = [np.concatenate([np.flatnonzero(te["univ"].to_numpy() == u) for u in rng.choice(univs, len(univs))])
                for _ in range(1000)]
    for name, m in models.items():
        cols = ["field", "uf"] + num
        m.fit(tr[cols].fillna(0), y_tr)
        err2 = (y_te.to_numpy() - m.predict(te[cols].fillna(0))) ** 2
        boots = [np.sqrt(err2[i].mean()) for i in boot_idx]
        out[name] = {"rmse": float(np.sqrt(err2.mean())),
                     "ci95_bootstrap_universities": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]}
    return out


# ---------------------------------------------------------------- 4. confounders
def confounders(df: pd.DataFrame, covars: pd.DataFrame, adm_field: pd.Series, adm_univ: pd.Series) -> tuple[dict, pd.DataFrame]:
    d = df.join(covars, on=["univ", "field"])
    d["rama"] = d["field"].map(RAMA)
    d = d.join(adm_univ, on=["univ", "rama"])
    out = {}
    # (a) field level: do fields with stronger intakes have higher grades?
    fe = d.groupby("field")["common"].first().to_frame().join(adm_field).dropna()
    fit = smf.ols("common ~ admission_field", fe).fit()
    out["field_level_admission"] = {"slope": float(fit.params["admission_field"]), "p": float(fit.pvalues["admission_field"]),
                                    "r2": float(fit.rsquared), "n_fields": int(len(fe))}
    # (b) within university: field effects with and without dropout, size and admission grade.
    s = d.dropna(subset=["dropout", "log_grads", "admission_univ_rama"]).copy()
    # Admission grades are standardised before use: z-score across all
    # university-branch averages, so the coefficient is per standard deviation
    # of intake quality rather than per point of a scale that differs by branch.
    a = s["admission_univ_rama"]
    s["adm_z"] = (a - a.mean()) / a.std()
    s["adm_dev"] = s["adm_z"] - s.groupby(["univ", "year"])["adm_z"].transform("mean")
    s["drop_dev"] = s["dropout"] - s.groupby(["univ", "year"])["dropout"].transform("mean")
    s["size_dev"] = s["log_grads"] - s.groupby(["univ", "year"])["log_grads"].transform("mean")
    base = smf.ols("dev ~ C(field, Sum)", s).fit()
    pre = smf.ols("dev ~ C(field, Sum) + adm_dev + size_dev", s).fit()
    full = smf.ols("dev ~ C(field, Sum) + adm_dev + size_dev + drop_dev", s).fit()
    eff_b, eff_p, eff_f = degree_effects_field(base), degree_effects_field(pre), degree_effects_field(full)
    out["within_university"] = {
        "n_obs": int(len(s)), "n_univ": int(s["univ"].nunique()),
        "coef_pre": {k: float(pre.params[k]) for k in ["adm_dev", "size_dev"]},
        "p_pre": {k: float(pre.pvalues[k]) for k in ["adm_dev", "size_dev"]},
        "coef_full": {k: float(full.params[k]) for k in ["adm_dev", "size_dev", "drop_dev"]},
        "p_full": {k: float(full.pvalues[k]) for k in ["adm_dev", "size_dev", "drop_dev"]},
        "sd_field_effects": {"field_only": float(eff_b["effect"].std(ddof=0)),
                             "plus_admission_size": float(eff_p["effect"].std(ddof=0)),
                             "plus_dropout": float(eff_f["effect"].std(ddof=0))},
        "corr_effects_before_after_pre": float(eff_b["effect"].corr(eff_p["effect"])),
        "corr_effects_before_after_full": float(eff_b["effect"].corr(eff_f["effect"])),
        "r2": {"field_only": float(base.rsquared), "plus_admission_size": float(pre.rsquared),
               "plus_dropout": float(full.rsquared)},
        "note": "public universities only (admission grade by rama is only published for them)",
    }
    eff = eff_b.join(eff_p, lsuffix="_before", rsuffix="_after")
    return out, eff


def degree_effects_field(model) -> pd.DataFrame:
    """Sum-coded field effects with standard errors (the last level is minus the sum of the others)."""
    names = [n for n in model.params.index if n.startswith("C(field, Sum)")]
    est = model.params[names].to_numpy()
    cov = model.cov_params().loc[names, names].to_numpy()
    ones = np.ones(len(names))
    levels = sorted(model.model.data.frame["field"].unique())
    return pd.DataFrame({"effect": np.append(est, -est.sum()),
                         "se": np.append(np.sqrt(np.diag(cov)), np.sqrt(ones @ cov @ ones))},
                        index=pd.Index(levels, name="field"))


def fig_confounders(eff: pd.DataFrame) -> None:
    eff = eff.sort_values("effect_before")
    y = np.arange(len(eff))
    fig, ax = plt.subplots(figsize=(7.5, 6.6))
    ax.errorbar(eff["effect_before"], y + 0.15, xerr=1.96 * eff["se_before"], fmt="o", color="tab:gray",
                capsize=2, label="Field only")
    ax.errorbar(eff["effect_after"], y - 0.15, xerr=1.96 * eff["se_after"], fmt="s", color="tab:blue",
                capsize=2, label="Field + admission grade (standardised) + size")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, eff.index)
    ax.set_xlabel("Field deviation from its university-year average (grade points, 95% CI)\nPublic Spanish universities")
    fig.legend(frameon=False, loc="upper center", ncol=2)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "confounders.pdf")
    fig.savefig(FIG / "confounders.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- 5. weighted selection
def weighted_selection(df: pd.DataFrame, grads: pd.Series) -> tuple[pd.DataFrame, dict]:
    d = df.join(grads, on=["univ", "field", "year"]).dropna(subset=["q1", "q3", "graduates"])
    d = d[(d["q3"] > d["q1"]) & (d["graduates"] > 0)]
    rows = []
    for (u, yr), g in d.groupby(["univ", "year"]):
        if len(g) < 4:
            continue
        mu, sd, w = g["mean"].to_numpy(), ((g["q3"] - g["q1"]) / IQR_TO_SD).to_numpy(), g["graduates"].to_numpy()
        w = w / w.sum()
        cut = brentq(lambda c: (w * norm.sf(c, mu, sd)).sum() - TOP_SHARE, 0, 15)
        rows.append(pd.DataFrame({"univ": u, "year": yr, "field": g["field"], "share": norm.sf(cut, mu, sd),
                                  "graduates": g["graduates"]}))
    r = pd.concat(rows)
    g = r.groupby("field")
    summary = pd.DataFrame({
        "weighted_mean": g.apply(lambda x: np.average(x["share"], weights=x["graduates"]), include_groups=False),
        "q1": g["share"].quantile(0.25), "median": g["share"].median(), "q3": g["share"].quantile(0.75),
        "n_univ_years": g.size(),
    }).sort_values("weighted_mean")
    return summary, {"n_univ_years": int(r.groupby(["univ", "year"]).ngroups), "n_univ": int(r["univ"].nunique())}


# ---------------------------------------------------------------- 6. clustering
def cluster_fields(df: pd.DataFrame, covars: pd.DataFrame, adm_field: pd.Series) -> tuple[pd.DataFrame, dict]:
    d = df.join(covars, on=["univ", "field"])
    d["iqr"] = d["q3"] - d["q1"]
    slope = d.groupby("field").apply(lambda g: np.polyfit(g["year"], g["dev"], 1)[0] if g["year"].nunique() > 2 else np.nan,
                                     include_groups=False)
    prof = pd.DataFrame({
        "field_effect": d.groupby("field")["common"].first(),
        "spread_iqr": d.groupby("field")["iqr"].mean(),
        "between_univ_sd": d.groupby("field")["specific"].std(),
        "trend_per_year": slope,
        "dropout": d.groupby("field")["dropout"].mean(),
        "admission": adm_field,
    }).dropna()
    X = StandardScaler().fit_transform(prof)
    scores = {k: float(silhouette_score(X, KMeans(k, n_init=20, random_state=SEED).fit_predict(X))) for k in range(2, 7)}
    k = max(scores, key=scores.get)
    prof["cluster"] = KMeans(k, n_init=20, random_state=SEED).fit_predict(X)
    pca = PCA(2, random_state=SEED).fit(X)
    pcs = pca.transform(X)
    prof["pc1"], prof["pc2"] = pcs[:, 0], pcs[:, 1]
    load = pd.DataFrame(pca.components_.T, index=prof.columns[:6], columns=["pc1", "pc2"])
    return prof, {"silhouette": scores, "k": int(k), "explained_variance": pca.explained_variance_ratio_.round(3).tolist(),
                  "loadings": load.round(3).to_dict()}


def fig_clusters(prof: pd.DataFrame, info: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    colors = plt.cm.tab10.colors
    for c, g in prof.groupby("cluster"):
        ax.scatter(g["pc1"], g["pc2"], s=40, color=colors[c], label=f"Cluster {c + 1}")
    for f, r in prof.iterrows():
        ax.annotate(f, (r["pc1"], r["pc2"]), fontsize=7.5, xytext=(3, 3), textcoords="offset points")
    ev = info["explained_variance"]
    ax.set_xlabel(f"PC1 ({100 * ev[0]:.0f}% of variance)")
    ax.set_ylabel(f"PC2 ({100 * ev[1]:.0f}% of variance)")
    ax.axhline(0, color="gray", lw=0.5)
    ax.axvline(0, color="gray", lw=0.5)
    fig.legend(frameon=False, loc="upper center", ncol=info["k"])
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG / "field_clusters.pdf")
    fig.savefig(FIG / "field_clusters.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- 7. Portuguese records
def portugal() -> dict:
    df = load_clean()
    # Entry grades are only comparable within an admission route (general
    # contingent, over-23 exam, transfer, ...), so they are standardised within
    # application mode before entering any model.
    for c in ["admission_grade", "prev_grade"]:
        g = df.groupby("app_mode")[c]
        df[c] = ((df[c] - g.transform("mean")) / g.transform("std")).fillna(0)
    k = int(round(TOP_SHARE * len(df)))
    grp = df.groupby("course")["gpa"]
    rules = {
        "raw GPA": df["gpa"],
        "within-degree z-score": (df["gpa"] - grp.transform("mean")) / grp.transform("std"),
        "within-degree percentile": grp.rank(pct=True),
    }
    m = smf.ols("gpa ~ " + " + ".join(CONTROLS) + " + C(course, Sum)", df).fit()
    eff = degree_effects(m, sorted(df["course"].unique()))["effect"]
    rules["regression-adjusted GPA"] = df["gpa"] - df["course"].map(eff)
    sel, out = {}, {}
    for name, score in rules.items():
        top = df.assign(s=score).sample(frac=1, random_state=SEED).sort_values("s", ascending=False, kind="stable").index[:k]
        sel[name] = set(top)
        rate = df.index.isin(top)
        by = pd.Series(rate, index=df.index).groupby(df["course"]).mean()
        out[name] = {"sd_selection_rate_across_degrees": float(by.std(ddof=0)), "min_rate": float(by.min()),
                     "max_rate": float(by.max()), "places_changed_vs_raw": int(len(sel["raw GPA"] - set(top))),
                     "mean_admission_grade_selected": float(df.loc[top, "admission_grade"].mean())}
    # Logistic regression: does the degree predict reaching the raw-GPA top 20% beyond entry grades?
    y = df.index.isin(list(sel["raw GPA"])).astype(int)
    cv = StratifiedKFold(10, shuffle=True, random_state=SEED)

    def auc(features):
        cat = [c for c in features if c == "course"]
        num = [c for c in features if c != "course"]
        pre = ColumnTransformer([("n", StandardScaler(), num)] + ([("c", OneHotEncoder(), cat)] if cat else []))
        p = cross_val_predict(make_pipeline(pre, LogisticRegression(max_iter=2000)), df[features], y, cv=cv,
                              method="predict_proba")[:, 1]
        folds = [roc_auc_score(y[te], p[te]) for _, te in cv.split(df, y)]
        return {"auc": float(roc_auc_score(y, p)), "fold_sd": float(np.std(folds, ddof=1))}

    out["logistic_top20"] = {"controls": auc(CONTROLS), "controls_plus_degree": auc(CONTROLS + ["course"]),
                             "degree_only": auc(["course"]), "base_rate": float(y.mean())}
    m2 = smf.ols("gpa ~ " + " + ".join(CONTROLS) + " + C(course, Sum)", df).fit()
    e2 = degree_effects(m2, sorted(df["course"].unique()))["effect"]
    m0 = smf.ols("gpa ~ C(course, Sum)", df).fit()
    e0 = degree_effects(m0, sorted(df["course"].unique()))["effect"]
    out["degree_gap"] = {"raw_max_minus_min": float(e0.max() - e0.min()),
                         "adjusted_standardised_max_minus_min": float(e2.max() - e2.min()),
                         "f_test_degree": [float(x) for x in m2.compare_f_test(smf.ols("gpa ~ " + " + ".join(CONTROLS), df).fit())]}
    return out


# ---------------------------------------------------------------- main
def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = specific_deviation(load_spain())
    dropout, grads = load_covariates()
    covars = dropout.to_frame()
    g_avg = grads.groupby(level=[0, 1]).mean()
    covars = covars.join(np.log(g_avg).rename("log_grads"), how="outer")
    for c in ["dropout", "log_grads"]:
        covars[c + "_z"] = (covars[c] - covars[c].mean()) / covars[c].std()
    adm_field, adm_univ = load_admission()

    stats = {"match": {"spain_univs": int(df["univ"].nunique()),
                       "with_dropout": int(df["univ"].isin(dropout.index.get_level_values(0)).groupby(df["univ"]).first().sum()),
                       "with_admission": int(df["univ"].isin(adm_univ.index.get_level_values(0)).groupby(df["univ"]).first().sum())}}
    stats["decomposition"] = decomposition(df)
    stats["persistence"], pair = persistence(df)
    fig_persistence(pair)
    stats["temporal_validation"] = temporal_validation(df, covars)
    stats["confounders"], eff = confounders(df, covars, adm_field, adm_univ)
    eff.round(3).to_csv(RES / "confounder_field_effects.csv")
    fig_confounders(eff)
    sel, info = weighted_selection(df, grads)
    sel.round(3).to_csv(RES / "weighted_selection_by_field.csv")
    stats["weighted_selection"] = info
    prof, cinfo = cluster_fields(df, covars, adm_field)
    prof.round(3).to_csv(RES / "field_profiles_clusters.csv")
    stats["clusters"] = {**cinfo, "members": prof.groupby("cluster").apply(lambda g: list(g.index), include_groups=False).to_dict()}
    fig_clusters(prof, cinfo)
    stats["portugal"] = portugal()
    (RES / "progress_stats.json").write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    print(json.dumps(stats, indent=2, default=str, ensure_ascii=False))
    print(eff.round(3).to_string())
    print(prof.round(2).to_string())


if __name__ == "__main__":
    main()
