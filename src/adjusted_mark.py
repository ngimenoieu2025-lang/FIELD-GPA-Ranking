"""Adjusted marks: does subtracting the field deviation make selection more equal?

Instructor's suggestion (Progress Report feedback): adjusted mark = original mark
minus the deviation of the student's field. We test it on the Spanish Ministry
data with the same top-20% selection simulation used in progress.py.

The deviation subtracted in year t is always estimated from years before t, so
the correction could be applied in practice (no information from the year being
ranked). Four corrections are compared with the raw marks:

  common_prior     average deviation of the field across all universities, years < t
  univ_last_year   deviation of the same field at the same university in year t-1
  univ_prior_mean  average deviation of that field at that university, years < t
  oracle_current   deviation in year t itself (upper bound, not usable in practice)

University-specific corrections fall back to common_prior when the university
has no earlier record for the field. The spread of each graduate's grade (SD
from the interquartile range) is not changed; only the field mean is shifted.

Outputs: results/adjusted_mark_stats.json, results/adjusted_mark_by_field.csv
(graduate-weighted mean share per field), results/adjusted_mark_field_distribution.csv
(median and interquartile range across university-years, the statistic of
Figure 4), figures/adjusted_mark_selection.pdf/.png (exploratory). The report
version of the figure is made by final_figures.py (fig7).
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
from scipy.optimize import brentq
from scipy.stats import norm

from ministry import IQR_TO_SD, TOP_SHARE, load as load_spain
from progress import FIG, RES, load_covariates, specific_deviation

SEED = 42
METHODS = ["raw", "common_prior", "univ_last_year", "univ_prior_mean", "oracle_current"]
LABELS = {
    "raw": "Raw mark",
    "common_prior": "Minus field deviation (all universities, past years)",
    "univ_last_year": "Minus field deviation at the university, last year",
    "univ_prior_mean": "Minus field deviation at the university, past years",
    "oracle_current": "Minus current-year deviation (upper bound)",
}


def corrections(df: pd.DataFrame) -> pd.DataFrame:
    """Add one column per correction, each using only information available before year t."""
    df = df.sort_values(["univ", "field", "year"]).copy()
    years = sorted(df["year"].unique())
    # common field deviation from all earlier years
    common = {}
    for t in years:
        past = df[df["year"] < t]
        common[t] = past.groupby("field")["dev"].mean() if len(past) else pd.Series(dtype=float)
    df["common_prior"] = [common[t].get(f, np.nan) for f, t in zip(df["field"], df["year"])]
    g = df.groupby(["univ", "field"])
    prev = g["dev"].shift(1)
    prev_year = g["year"].shift(1)
    df["univ_last_year"] = prev.where(prev_year == df["year"] - 1)
    df["univ_prior_mean"] = g["dev"].transform(lambda s: s.expanding().mean().shift(1))
    for c in ["univ_last_year", "univ_prior_mean"]:
        df[c] = df[c].fillna(df["common_prior"])
    df["oracle_current"] = df["dev"]
    df["raw"] = 0.0
    return df


def select(d: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    for (u, yr), g in d.groupby(["univ", "year"]):
        if len(g) < 4:
            continue
        mu = (g["mean"] - g[method]).to_numpy()
        sd = ((g["q3"] - g["q1"]) / IQR_TO_SD).to_numpy()
        w = g["graduates"].to_numpy() / g["graduates"].sum()
        cut = brentq(lambda c: (w * norm.sf(c, mu, sd)).sum() - TOP_SHARE, -20, 30)
        # spread of field means within the university-year, weighted by graduates
        m_w = np.average(mu, weights=w)
        rows.append(pd.DataFrame({"univ": u, "year": yr, "field": g["field"].to_numpy(),
                                  "share": norm.sf(cut, mu, sd), "graduates": g["graduates"].to_numpy(),
                                  "mean_sd_within": np.sqrt(np.average((mu - m_w) ** 2, weights=w))}))
    return pd.concat(rows, ignore_index=True)


def summarise(r: pd.DataFrame, rng: np.random.Generator) -> dict:
    w = r["graduates"]
    gap = (r["share"] - TOP_SHARE).abs()
    by_uy = r.groupby(["univ", "year"])["mean_sd_within"].first()
    field = r.groupby("field").apply(lambda x: np.average(x["share"], weights=x["graduates"]), include_groups=False)
    # bootstrap over universities for the main metric
    univs = r["univ"].unique()
    idx = {u: np.flatnonzero(r["univ"].to_numpy() == u) for u in univs}
    g_arr, w_arr = gap.to_numpy(), w.to_numpy()
    boots = []
    for _ in range(1000):
        i = np.concatenate([idx[u] for u in rng.choice(univs, len(univs))])
        boots.append(np.average(g_arr[i], weights=w_arr[i]))
    return {
        "mean_abs_gap_pp": float(100 * np.average(gap, weights=w)),
        "mean_abs_gap_ci95_pp": [float(100 * np.percentile(boots, 2.5)), float(100 * np.percentile(boots, 97.5))],
        "sd_field_shares_pp": float(100 * field.std(ddof=0)),
        "max_min_field_share_pp": [float(100 * field.max()), float(100 * field.min())],
        "max_field": str(field.idxmax()), "min_field": str(field.idxmin()),
        "median_within_univ_sd_of_field_means": float(by_uy.median()),
        "n_univ_field_years": int(len(r)), "n_univ_years": int(len(by_uy)), "n_univ": int(r["univ"].nunique()),
    }, field, distribution(r)


def distribution(r: pd.DataFrame) -> pd.DataFrame:
    """Median and interquartile range across university-years of each field's share (as in Figure 4)."""
    g = r.groupby("field")["share"]
    return pd.DataFrame({"median": g.median(), "q1": g.quantile(0.25), "q3": g.quantile(0.75),
                         "n_univ_years": g.size()})


def fig(by_field: pd.DataFrame) -> None:
    show = ["raw", "univ_prior_mean", "oracle_current"]
    order = by_field["raw"].sort_values().index
    y = np.arange(len(order))
    fig_, ax = plt.subplots(figsize=(7.5, 7))
    marks = {"raw": ("o", "tab:gray"), "univ_prior_mean": ("s", "tab:blue"), "oracle_current": ("^", "tab:green")}
    for m in show:
        ax.scatter(100 * by_field.loc[order, m], y, marker=marks[m][0], color=marks[m][1], s=22, label=LABELS[m], zorder=3)
    for i, f in enumerate(order):
        ax.plot(100 * by_field.loc[f, show].to_numpy(dtype=float)[[0, 1]], [i, i], color="lightgray", lw=1, zorder=1)
    ax.axvline(100 * TOP_SHARE, color="black", lw=0.8, ls="--")
    ax.set_yticks(y, order)
    ax.set_xlabel("Share of the field's graduates in the university's top 20%\n(%, weighted by graduates; dashed line = equal access)")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig_.tight_layout()
    fig_.savefig(FIG / "adjusted_mark_selection.pdf")
    fig_.savefig(FIG / "adjusted_mark_selection.png", dpi=200)
    plt.close(fig_)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = specific_deviation(load_spain())
    _, grads = load_covariates()
    df = corrections(df)
    d = df.join(grads, on=["univ", "field", "year"]).dropna(subset=["q1", "q3", "graduates"])
    d = d[(d["q3"] > d["q1"]) & (d["graduates"] > 0) & (d["year"] > d["year"].min())]  # first year has no past
    stats, fields, dists = {"evaluation_years": [int(d["year"].min()), int(d["year"].max())]}, {}, []
    for m in METHODS:
        stats[m], fields[m], dist = summarise(select(d, m), np.random.default_rng(SEED))
        dists.append(dist.assign(method=m))
        stats[m]["median_share_pp"] = {f: float(100 * dist.loc[f, "median"])
                                       for f in ["Nursing", "Business administration"]}
    by_field = pd.DataFrame(fields)
    # Within-field spread (SD = IQR/1.349) explains why equal means do not give equal access.
    by_field["median_within_field_sd"] = ((d["q3"] - d["q1"]) / IQR_TO_SD).groupby(d["field"]).median()
    by_field.round(4).to_csv(RES / "adjusted_mark_by_field.csv")
    pd.concat(dists).reset_index().round(4).to_csv(RES / "adjusted_mark_field_distribution.csv", index=False)
    fig(by_field)
    raw = stats["raw"]["mean_abs_gap_pp"]
    stats["reduction_vs_raw_pct"] = {m: float(100 * (1 - stats[m]["mean_abs_gap_pp"] / raw)) for m in METHODS[1:]}
    (RES / "adjusted_mark_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print((100 * by_field).round(1).sort_values("raw").to_string())


if __name__ == "__main__":
    main()
