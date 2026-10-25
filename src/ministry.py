"""Spanish Ministry of Universities (SIIU) data: graduates' final grade average
by university, field of study and academic year, with quartiles.

1. Field effects: how far each field sits from the average field once the
   university and the year are held fixed.
2. Within-university gaps between pairs of fields.
3. Selection simulation: share of each field's graduates that would fall in the
   top 20% of a single university-wide ranking by raw grade.
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
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from load_data import ROOT

RAW = ROOT / "data" / "raw" / "ministerio" / "Nota_Expediente_Grado_Univ.csv"
FIG = ROOT / "figures"
RES = ROOT / "results"
TOP_SHARE = 0.20
IQR_TO_SD = 1.349  # interquartile range of a normal distribution, in SDs

# Short English labels for the detailed fields (aggregates starting with "Total" are dropped).
FIELDS = {
    "Formación de docentes de enseñanza infantil": "Early childhood teaching",
    "Formación de docentes de enseñanza primaria": "Primary teaching",
    "Otra Formación de personal docente y ciencias de la educación": "Other education",
    "Técnicas audiovisuales y medios de comunicación": "Audiovisual & media",
    "Artes": "Arts",
    "Lenguas": "Languages",
    "Humanidades": "Humanities",
    "Psicología": "Psychology",
    "Economía": "Economics",
    "Otras Ciencias sociales y del comportamiento": "Other social sciences",
    "Periodismo e información": "Journalism",
    "Administración y gestión de empresas": "Business administration",
    "Otra Educación comercial y empresarial": "Other business",
    "Derecho": "Law",
    "Ciencias de la vida": "Life sciences",
    "Ciencias Físicas, químicas, geológicas": "Physical sciences",
    "Matemáticas y Estadística": "Mathematics & statistics",
    "Informática": "Computer science",
    "Ingenierías": "Engineering",
    "Arquitectura y construcción": "Architecture",
    "Agricultura, ganadería y pesca": "Agriculture",
    "Veterinaria": "Veterinary",
    "Medicina": "Medicine",
    "Enfermería y atención a enfermos": "Nursing",
    "Otras ciencias de la Salud": "Other health",
    "Trabajo social y orientación": "Social work",
    "Deportes": "Sports",
    "Turismo y Hostelería": "Tourism",
    "Otros Servicios": "Other services",
}
INDICATORS = {"Nota media": "mean", "1º cuartil": "q1", "2º cuartil": "q2", "3º cuartil": "q3", "Máximo": "max"}

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def load() -> pd.DataFrame:
    """One row per university, field and year, with mean and quartiles (both sexes)."""
    df = pd.read_csv(RAW, sep=";", encoding="utf-8", dtype=str)
    df.columns = ["univ", "field", "sex", "indicator", "period", "value"]
    df["field"] = df["field"].str.replace(r"\s+", " ", regex=True)
    df = df[(df["sex"] == "Ambos sexos") & (df["univ"] != "Total") & df["field"].isin(FIELDS)]
    df = df.assign(
        value=pd.to_numeric(df["value"].str.replace(",", "."), errors="coerce"),
        field=df["field"].map(FIELDS),
        indicator=df["indicator"].map(INDICATORS),
        year=df["period"].str[:4].astype(int),
    ).dropna(subset=["value"])
    wide = df.pivot_table(index=["univ", "field", "year"], columns="indicator", values="value").reset_index()
    wide.columns.name = None
    return wide.dropna(subset=["mean"])


def field_effects(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sum-coded field effects from OLS with university and year fixed effects."""
    base = smf.ols("mean ~ C(univ) + C(year)", df).fit()
    full = smf.ols("mean ~ C(field, Sum) + C(univ) + C(year)", df).fit()
    names = [n for n in full.params.index if n.startswith("C(field, Sum)")]
    est = full.params[names].to_numpy()
    cov = full.cov_params().loc[names, names].to_numpy()
    ones = np.ones(len(names))
    eff = pd.DataFrame(
        {"effect": np.append(est, -est.sum()), "se": np.append(np.sqrt(np.diag(cov)), np.sqrt(ones @ cov @ ones))},
        index=sorted(df["field"].unique()),
    ).sort_values("effect")
    f = full.compare_f_test(base)
    stats = {"r2_univ_year": float(base.rsquared), "r2_with_field": float(full.rsquared),
             "f_test_field": {"F": float(f[0]), "p": float(f[1]), "df": float(f[2])},
             "n_obs": int(len(df)), "n_univ": int(df["univ"].nunique()), "n_fields": int(df["field"].nunique())}
    return eff, stats


def paired_gap(df: pd.DataFrame, a: str, b: str) -> dict:
    """Mean of (a - b) across university-years that report both fields."""
    w = df[df["field"].isin([a, b])].pivot_table(index=["univ", "year"], columns="field", values="mean").dropna()
    d = w[a] - w[b]
    by_univ = d.groupby("univ").mean()
    return {"pair": f"{a} minus {b}", "n_univ_years": int(len(d)), "n_univ": int(len(by_univ)),
            "mean_gap": float(d.mean()), "share_univ_negative": float((by_univ < 0).mean()),
            "se_clustered_by_univ": float(by_univ.std() / np.sqrt(len(by_univ)))}


def top_share_by_field(group: pd.DataFrame) -> pd.Series:
    """Share of each field above a university-wide top-20% cutoff.

    Each field's grades are approximated by a normal distribution with the
    reported mean and SD = IQR / 1.349. Fields are weighted equally because the
    table does not report the number of graduates per field.
    """
    mu, sd = group["mean"].to_numpy(), ((group["q3"] - group["q1"]) / IQR_TO_SD).to_numpy()
    cutoff = brentq(lambda c: norm.sf(c, mu, sd).mean() - TOP_SHARE, 0, 15)
    return pd.Series(norm.sf(cutoff, mu, sd), index=group["field"])


def selection(df: pd.DataFrame, min_fields: int = 4) -> pd.DataFrame:
    """Top-20% share per university, field and year, for universities with enough fields."""
    ok = df.dropna(subset=["q1", "q3"])
    ok = ok[ok["q3"] > ok["q1"]]
    rows = []
    for (univ, year), g in ok.groupby(["univ", "year"]):
        if len(g) >= min_fields:
            s = top_share_by_field(g)
            rows.append(pd.DataFrame({"univ": univ, "year": year, "field": s.index, "top_share": s.to_numpy()}))
    return pd.concat(rows, ignore_index=True)


def unseen_university_rmse(df: pd.DataFrame) -> dict:
    """Does the field ranking learned on some universities hold in others?

    Target: a field's mean minus the average of all fields in the same university
    and year. Model: one-hot field (ridge), evaluated with folds that keep each
    university entirely in train or in test.
    """
    y = df["mean"] - df.groupby(["univ", "year"])["mean"].transform("mean")
    model = make_pipeline(OneHotEncoder(handle_unknown="ignore"), RidgeCV(alphas=np.logspace(-3, 3, 25)))
    scores = cross_val_score(model, df[["field"]], y, groups=df["univ"], cv=GroupKFold(n_splits=10),
                             scoring="neg_root_mean_squared_error")
    return {"baseline_rmse_no_field": float(np.sqrt((y ** 2).mean())), "field_model_rmse": float(-scores.mean())}


def fig_eda(df: pd.DataFrame) -> None:
    """Spread of university-level mean grades within each field, latest year."""
    last = df[df["year"] == df["year"].max()]
    order = last.groupby("field")["mean"].median().sort_values().index
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.boxplot([last.loc[last["field"] == f, "mean"] for f in order], orientation="horizontal",
               tick_labels=order, showfliers=False, medianprops={"color": "black"})
    ax.set_xlabel(f"Mean final grade of graduates, {last['year'].max()}-{str(last['year'].max() + 1)[2:]} (5-10 scale)\n"
                  "Each box: distribution across Spanish universities")
    fig.tight_layout()
    fig.savefig(FIG / "spain_grades_by_field.pdf")
    fig.savefig(FIG / "spain_grades_by_field.png", dpi=200)
    plt.close(fig)


def fig_field_effects(eff: pd.DataFrame) -> None:
    y = np.arange(len(eff))
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.barh(y, eff["effect"], xerr=1.96 * eff["se"], color="tab:blue", error_kw={"lw": 0.8})
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(y, eff.index)
    ax.set_xlabel("Difference from the average field in the same university and year\n(grade points on the 5-10 scale, 95% CI)")
    fig.tight_layout()
    fig.savefig(FIG / "spain_field_effects.pdf")
    fig.savefig(FIG / "spain_field_effects.png", dpi=200)
    plt.close(fig)


def fig_selection(sel_mean: pd.Series) -> None:
    s = sel_mean.sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 7))
    ax.barh(np.arange(len(s)), 100 * s, color="tab:blue")
    ax.axvline(100 * TOP_SHARE, color="tab:red", ls="--", lw=1, label="Equal access (20%)")
    ax.set_yticks(np.arange(len(s)), s.index)
    ax.set_xlabel("Graduates of the field inside their university's top 20% by raw grade (%)")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "spain_selection_by_field.pdf")
    fig.savefig(FIG / "spain_selection_by_field.png", dpi=200)
    plt.close(fig)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = load()
    (ROOT / "data" / "processed").mkdir(exist_ok=True)
    df.to_csv(ROOT / "data" / "processed" / "spain_univ_field_year.csv", index=False)

    eff, stats = field_effects(df)
    eff.round(3).to_csv(RES / "spain_field_effects.csv")
    fig_field_effects(eff)
    fig_eda(df)
    stats["unseen_university_cv"] = unseen_university_rmse(df)
    last = df[df["year"] == df["year"].max()]
    stats["latest_year"] = {"year": int(last["year"].max()), "n_obs": int(len(last)), "n_univ": int(last["univ"].nunique()),
                            "national_mean_fields": float(last["mean"].mean())}

    stats["paired_gaps"] = [paired_gap(df, "Mathematics & statistics", b)
                            for b in ["Business administration", "Law", "Economics", "Other social sciences"]]
    stats["paired_gaps"].append(paired_gap(df, "Engineering", "Business administration"))

    sel = selection(df)
    sel_mean = sel.groupby("field")["top_share"].mean()
    sel_mean.round(3).to_csv(RES / "spain_selection_by_field.csv")
    fig_selection(sel_mean)
    stats["selection"] = {"n_univ_years": int(sel.groupby(["univ", "year"]).ngroups),
                          "n_univ": int(sel["univ"].nunique())}

    stats["national_mean_by_year"] = df.groupby("year")["mean"].mean().round(3).to_dict()
    (RES / "spain_summary_stats.json").write_text(json.dumps(stats, indent=2))

    print(json.dumps(stats, indent=2))
    print(eff.round(3).to_string())
    print((100 * sel_mean.sort_values()).round(1).to_string())


if __name__ == "__main__":
    main()
