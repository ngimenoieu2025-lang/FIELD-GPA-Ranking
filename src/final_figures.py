"""Final figures for the Final Report (two-column BAM template).

One consistent style for every figure: column width 3.4 in (single column) or
7.0 in (full page width), 8 pt text, one colour-blind-safe palette, and every
encoding explained in the axis labels or legend.

Statistical choices shared by all figures:
- Confidence intervals for field effects use standard errors clustered by
  university, because the same university contributes up to nine years and
  those observations are not independent.
- Figures 1 and 3 use the same model: a field's mean minus the average of all
  fields in the same university and year, regressed on sum-coded fields.
  Figure 1 uses all universities; Figure 3 only the public universities for
  which admission grades are published.

Run after ministry.py, progress.py, us_replication.py, ranking_rules.py,
adjusted_mark.py and model_selection.py.
Output: figures/final/fig1_field_effects.pdf ... fig8_model_tuning.pdf, and
results/final_figures_stats.json with every number quoted in the captions.
`python src/final_figures.py fig7 fig8` remakes only the named figures (fig5
needs the US data, which is not in the repository).
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

from load_data import ROOT

RES = ROOT / "results"
OUT = ROOT / "figures" / "final"
COL, FULL = 3.4, 7.0  # inches
BLUE, ORANGE, GREY, RED = "#0072B2", "#E69F00", "#7F7F7F", "#D55E00"
STATS: dict = {}

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False,
    "axes.spines.right": False, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
})


def save(fig, name: str) -> None:
    # No creation date in the PDF, so rerunning the script does not change unchanged figures.
    fig.savefig(OUT / f"{name}.pdf", metadata={"CreationDate": None})
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)


def sum_coded_effects(formula: str, df: pd.DataFrame, factor: str = "field") -> pd.DataFrame:
    """Sum-coded effects of `factor` with standard errors clustered by university."""
    groups = pd.factorize(df["univ"])[0]
    fit = smf.ols(formula, df).fit(cov_type="cluster", cov_kwds={"groups": groups})
    names = [n for n in fit.params.index if n.startswith(f"C({factor}, Sum)")]
    est = fit.params[names].to_numpy()
    cov = fit.cov_params().loc[names, names].to_numpy()
    ones = np.ones(len(names))
    levels = sorted(df[factor].unique())
    return pd.DataFrame({"effect": np.append(est, -est.sum()),
                         "se": np.append(np.sqrt(np.diag(cov)), np.sqrt(ones @ cov @ ones))},
                        index=pd.Index(levels, name=factor))


def spain_deviations() -> pd.DataFrame:
    from ministry import load
    from progress import specific_deviation
    return specific_deviation(load())


def fig1_field_effects(dev: pd.DataFrame) -> None:
    """Field effects across all Spanish universities, 95% CIs clustered by university."""
    eff = sum_coded_effects("dev ~ C(field, Sum)", dev).sort_values("effect")
    q = dev.dropna(subset=["q1", "q3"])
    within_sd = (q["q3"] - q["q1"]) / 1.349  # SD of a normal with that IQR
    STATS["fig1"] = {"n_obs": int(len(dev)), "n_univ": int(dev["univ"].nunique()),
                     "max_field": eff.index[-1], "max_effect": float(eff["effect"].iloc[-1]),
                     "min_field": eff.index[0], "min_effect": float(eff["effect"].iloc[0]),
                     "median_ci_halfwidth": float(1.96 * eff["se"].median()),
                     "range_max_minus_min": float(eff["effect"].iloc[-1] - eff["effect"].iloc[0]),
                     "median_within_field_sd": float(within_sd.median()),
                     "n_with_quartiles": int(len(q))}
    eff.round(4).to_csv(RES / "final_fig1_field_effects.csv")
    y = np.arange(len(eff))
    fig, ax = plt.subplots(figsize=(COL, 4.6))
    colors = np.where(eff["effect"] >= 0, BLUE, ORANGE)
    ax.hlines(y, 0, eff["effect"], color=colors, lw=1.2)
    ax.errorbar(eff["effect"], y, xerr=1.96 * eff["se"], fmt="o", ms=3, color="black",
                ecolor="black", elinewidth=0.6, capsize=1.5)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_yticks(y, eff.index)
    ax.set_xlabel("Difference from the university-year\naverage (grade points, 95% CI)")
    ax.text(0.98, 0.02, "blue: above average\norange: below average", transform=ax.transAxes,
            ha="right", va="bottom", fontsize=6.5, color=GREY)
    save(fig, "fig1_field_effects")


def fig2_persistence(dev: pd.DataFrame) -> None:
    """University-specific deviation in year t against year t+1."""
    from progress import persistence
    info, pair = persistence(dev)
    STATS["fig2"] = info
    fig, ax = plt.subplots(figsize=(COL, COL))
    ax.scatter(pair["t"], pair["t1"], s=2, alpha=0.2, color=BLUE, edgecolors="none", rasterized=True)
    lim = float(np.nanpercentile(np.abs(pair.to_numpy()), 99.5))
    xs = np.linspace(-lim, lim, 10)
    b = np.polyfit(pair["t"], pair["t1"], 1)
    ax.plot(xs, np.polyval(b, xs), color="black", label=f"least-squares fit (slope {b[0]:.2f})")
    ax.plot(xs, xs, color=RED, ls="--", lw=0.8, label="perfect persistence (slope 1)")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axhline(0, color=GREY, lw=0.4)
    ax.axvline(0, color=GREY, lw=0.4)
    ax.set_xlabel("University-specific deviation, year t\n(grade points)")
    ax.set_ylabel("Same university and field, year t+1")
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.98, 0.03, f"r = {info['lag1_correlation']:.2f}\n{info['n_pairs']:,} pairs",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
    save(fig, "fig2_persistence")


def fig3_confounders(dev: pd.DataFrame) -> None:
    """Field effects before and after controlling for intake and size (public universities)."""
    from progress import RAMA, load_admission, load_covariates
    dropout, grads = load_covariates()
    log_grads = np.log(grads.groupby(level=[0, 1]).mean()).rename("log_grads")
    _, adm_univ = load_admission()
    d = dev.join(log_grads, on=["univ", "field"])
    d["rama"] = d["field"].map(RAMA)
    d = d.join(adm_univ, on=["univ", "rama"]).dropna(subset=["admission_univ_rama", "log_grads"]).copy()
    a = d["admission_univ_rama"]
    d["adm_z"] = (a - a.mean()) / a.std()
    for c in ["adm_z", "log_grads"]:
        d[c + "_dev"] = d[c] - d.groupby(["univ", "year"])[c].transform("mean")
    before = sum_coded_effects("dev ~ C(field, Sum)", d)
    after = sum_coded_effects("dev ~ C(field, Sum) + adm_z_dev + log_grads_dev", d)
    eff = before.join(after, lsuffix="_before", rsuffix="_after")
    r = float(eff["effect_before"].corr(eff["effect_after"]))
    STATS["fig3"] = {"n_obs": int(len(d)), "n_univ": int(d["univ"].nunique()), "r_before_after": r,
                     "sd_before": float(eff["effect_before"].std(ddof=0)),
                     "sd_after": float(eff["effect_after"].std(ddof=0)),
                     "n_branches": int(d["rama"].nunique()),
                     "note": "Admission grades are published per university and broad branch (5 branches for 29 fields), "
                             "so they cannot separate fields within the same branch."}
    eff.round(4).to_csv(RES / "final_fig3_confounders.csv")
    fig, ax = plt.subplots(figsize=(COL, COL))
    lim = 1.1 * float(np.abs(eff[["effect_before", "effect_after"]]).to_numpy().max())
    ax.plot([-lim, lim], [-lim, lim], color=RED, ls="--", lw=0.8, label="no change")
    ax.errorbar(eff["effect_before"], eff["effect_after"], xerr=1.96 * eff["se_before"],
                yerr=1.96 * eff["se_after"], fmt="o", ms=3, color=BLUE, elinewidth=0.5, label="field (95% CI)")
    for name in ["Nursing", "Mathematics & statistics", "Business administration", "Architecture", "Medicine"]:
        ax.annotate(name, (eff.loc[name, "effect_before"], eff.loc[name, "effect_after"]),
                    xytext=(4, -3), textcoords="offset points", fontsize=6)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axhline(0, color=GREY, lw=0.4)
    ax.axvline(0, color=GREY, lw=0.4)
    ax.set_xlabel("Field effect, field only (grade points)")
    ax.set_ylabel("Field effect, + admission grade\n(by branch) and size")
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.98, 0.03, f"r = {r:.2f}\n29 fields, {d['univ'].nunique()} public universities",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7)
    save(fig, "fig3_confounders")


def fig4_selection() -> None:
    """Simulated share of each field's graduates inside a university-wide top 20%."""
    s = pd.read_csv(RES / "weighted_selection_by_field.csv", index_col=0).sort_values("median")
    normal = json.loads((RES / "normal_check_stats.json").read_text(encoding="utf-8"))
    STATS["fig4"] = {"nursing_median": float(s.loc["Nursing", "median"]),
                     "business_median": float(s.loc["Business administration", "median"]),
                     "truncated_normal_mean_abs_change_pp": normal["graduate_weighted_absolute_change_pp"],
                     "truncated_normal_fields_changing_rank": normal["n_fields_with_changed_rank"]}
    y = np.arange(len(s))
    fig, ax = plt.subplots(figsize=(COL, 4.6))
    ax.hlines(y, 100 * s["q1"], 100 * s["q3"], color=BLUE, lw=2.2, alpha=0.45, label="interquartile range")
    ax.plot(100 * s["median"], y, "o", ms=3, color=BLUE, label="median university-year")
    ax.axvline(20, color=RED, ls="--", lw=0.8, label="equal access (20%)")
    ax.set_yticks(y, s.index)
    ax.set_xlabel("Simulated share of the field's graduates in\ntheir university's top 20% by raw grade (%)")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "fig4_selection")


def fig5_us_spain() -> None:
    """Broad-area effects in Spain and the US, clustered by university."""
    proc = ROOT / "data" / "processed"
    us = pd.read_csv(proc / "us_univ_field_year.csv")
    es = pd.read_csv(proc / "spain_broad_univ_field_year.csv")
    formula = "mean ~ C(field, Sum) + C(univ) + C(year)"
    c = sum_coded_effects(formula, es).join(sum_coded_effects(formula, us), lsuffix="_spain", rsuffix="_us")
    r = float(c["effect_spain"].corr(c["effect_us"]))
    n = len(c)
    z, se = np.arctanh(r), 1 / np.sqrt(n - 3)
    ci = [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]
    same_sign = int((np.sign(c["effect_spain"]) == np.sign(c["effect_us"])).sum())
    STATS["fig5"] = {"pearson_r": r, "pearson_r_ci95": ci, "n_areas": n, "same_sign": same_sign}
    c.round(4).to_csv(RES / "final_fig5_us_spain.csv")
    fig, ax = plt.subplots(figsize=(COL, COL))
    lim = 1.15 * float(np.abs(c[["effect_spain", "effect_us"]]).to_numpy().max())
    ax.axhline(0, color=GREY, lw=0.4)
    ax.axvline(0, color=GREY, lw=0.4)
    ax.errorbar(c["effect_spain"], c["effect_us"], xerr=1.96 * c["se_spain"], yerr=1.96 * c["se_us"],
                fmt="o", ms=3.5, color=BLUE, elinewidth=0.5)
    below = {"Arts, media & architecture"}  # label under the point to avoid overlap
    for name, row in c.iterrows():
        ax.annotate(name, (row["effect_spain"], row["effect_us"]), xytext=(3, -8) if name in below else (3, 3),
                    textcoords="offset points", fontsize=5.8)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("Spain: broad-area effect (grade points, 5-10 scale)")
    ax.set_ylabel("US: broad-area effect (GPA points, 0-4 scale)")
    ax.text(0.98, 0.03, f"Pearson r = {r:.2f} (95% CI {ci[0]:.2f} to {ci[1]:.2f})\n"
            f"{same_sign} of {n} areas with the same sign",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5)
    save(fig, "fig5_us_spain")


def fig6_ranking_rules() -> None:
    """Four ranking rules judged on second-semester outcomes."""
    d = json.loads((RES / "ranking_rules.json").read_text(encoding="utf-8"))
    est, lo, hi = (pd.DataFrame(d[k]).T for k in ["estimate", "ci95_low", "ci95_high"])
    rules = list(est.index)
    panels = [
        ("future_raw_grade", "2nd-semester grade of\nselected students (0-20)"),
        ("future_within_degree_z", "2nd-semester standing\nwithin degree (z-score)"),
        ("stability_spearman", "Rank stability between\nsemesters (Spearman)"),
        ("sd_selection_rate", "Spread of selection rates\nacross degrees (SD)"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(FULL, 1.9), sharey=True)
    y = np.arange(len(rules))
    for ax, (col, title) in zip(axes, panels):
        err = np.vstack([est[col] - lo[col], hi[col] - est[col]]).astype(float)
        ax.errorbar(est[col].astype(float), y, xerr=err, fmt="o", ms=3.5, color=BLUE, capsize=2, elinewidth=0.7)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3, lw=0.4)
    axes[0].set_yticks(y, rules)
    axes[0].invert_yaxis()
    axes[0].text(0.02, -0.28, "Axes are zoomed to the range of the estimates.", transform=axes[0].transAxes,
                 fontsize=6.5, color=GREY)
    save(fig, "fig6_ranking_rules")


def fig7_adjusted_marks() -> None:
    """Selection shares with raw and adjusted marks (instructor's suggestion), same statistic as Figure 4."""
    dist = pd.read_csv(RES / "adjusted_mark_field_distribution.csv")
    stats = json.loads((RES / "adjusted_mark_stats.json").read_text(encoding="utf-8"))
    raw = dist[dist["method"] == "raw"].set_index("field")
    adj = dist[dist["method"] == "univ_prior_mean"].set_index("field").loc[raw.index]
    order = raw["median"].sort_values().index
    raw, adj = raw.loc[order], adj.loc[order]
    STATS["fig7"] = {
        "adjustment": "univ_prior_mean: field deviation at the same university, averaged over earlier years",
        "evaluation_years": stats["evaluation_years"], "n_univ_years": stats["raw"]["n_univ_years"],
        "n_univ": stats["raw"]["n_univ"],
        "mean_abs_gap_pp": {m: stats[m]["mean_abs_gap_pp"] for m in ["raw", "univ_prior_mean", "oracle_current"]},
        "mean_abs_gap_ci95_pp": {m: stats[m]["mean_abs_gap_ci95_pp"] for m in ["raw", "univ_prior_mean"]},
        "median_share_pp": {m: stats[m]["median_share_pp"] for m in ["raw", "univ_prior_mean"]},
    }
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(COL, 4.6))
    for d, off, color, label in [(raw, 0.18, GREY, "raw mark"),
                                 (adj, -0.18, BLUE, "adjusted mark (minus the field's\npast deviation at that university)")]:
        ax.hlines(y + off, 100 * d["q1"], 100 * d["q3"], color=color, lw=2.0, alpha=0.45)
        ax.plot(100 * d["median"], y + off, "o", ms=3, color=color, label=label)
    ax.axvline(20, color=RED, ls="--", lw=0.8, label="equal access (20%)")
    ax.set_yticks(y, order)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlabel("Simulated share of the field's graduates in\ntheir university's top 20% (%; median and IQR)")
    g = STATS["fig7"]["mean_abs_gap_pp"]
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.42, 1.0), fontsize=6.5, ncol=1,
              title=f"mean distance from 20%: {g['raw']:.1f} pp (raw) → {g['univ_prior_mean']:.1f} pp (adjusted)",
              title_fontsize=6.5)
    save(fig, "fig7_adjusted_marks")


def fig8_model_tuning() -> None:
    """Expanding-window validation error against each tuned hyperparameter (2018-2021)."""
    t = pd.read_csv(RES / "model_selection_tuning.csv")
    sel = json.loads((RES / "model_selection_stats.json").read_text(encoding="utf-8"))
    common = float(t.loc[t["model"] == "common_field", "val_rmse"].iloc[0])
    STATS["fig8"] = {"validation_years": sel["validation_years"], "validation_rmse_best": sel["validation_rmse_best"],
                     "chosen": {m: sel["test"][m]["hyperparameter"] for m in
                                ["shrunk_profile", "ridge_profile", "gradient_boosting"]},
                     "test_rmse": {m: sel["test"][m]["rmse"] for m in
                                   ["baseline", "common_field", "shrunk_profile", "ridge_profile", "gradient_boosting"]}}
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.0), sharey=True)
    # (a) shrinkage k
    s = t[t["model"] == "shrunk_profile"].copy()
    s["k"] = s["hyperparameter"].astype(float)
    s = s[s["k"] < 1e8].sort_values("k")
    best = s.loc[s["val_rmse"].idxmin()]
    axes[0].plot(s["k"], s["val_rmse"], "o-", ms=3, color=BLUE)
    axes[0].plot(best["k"], best["val_rmse"], "o", ms=7, mfc="none", color=RED, label=f"chosen k = {best['k']:g}")
    axes[0].set_xscale("symlog", linthresh=0.25)
    axes[0].set_xlabel("Shrinkage k (weight on own past = n/(n+k))")
    axes[0].set_title("(a) Shrunk university profile")
    # (b) ridge alpha
    r = t[t["model"] == "ridge_profile"].copy()
    r["alpha"] = r["hyperparameter"].astype(float)
    r = r.sort_values("alpha")
    best = r.loc[r["val_rmse"].idxmin()]
    axes[1].plot(r["alpha"], r["val_rmse"], "o-", ms=3, color=BLUE)
    axes[1].plot(best["alpha"], best["val_rmse"], "o", ms=7, mfc="none", color=RED,
                 label=f"chosen α = {best['alpha']:.2g}")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Ridge penalty α")
    axes[1].set_title("(b) Ridge, field + university×field")
    # (c) gradient boosting: best over the number of trees, by depth and learning rate
    g = t[t["model"] == "gradient_boosting"].copy()
    hp = g["hyperparameter"].str.strip("()").str.split(",", expand=True).astype(float)
    g["depth"], g["lr"], g["trees"] = hp[0], hp[1], hp[2]
    gb = g.groupby(["lr", "depth"])["val_rmse"].min().reset_index()
    for lr, color in zip(sorted(gb["lr"].unique()), [ORANGE, BLUE, GREY]):
        d = gb[gb["lr"] == lr]
        axes[2].plot(d["depth"], d["val_rmse"], "o-", ms=3, color=color, label=f"learning rate {lr:g}")
    bg = g.loc[g["val_rmse"].idxmin()]
    axes[2].plot(bg["depth"], bg["val_rmse"], "o", ms=7, mfc="none", color=RED)
    axes[2].set_xlabel("Maximum tree depth")
    axes[2].set_title("(c) Gradient boosting")
    axes[2].set_xticks(sorted(g["depth"].unique()))
    for ax in axes:
        ax.axhline(common, color=GREY, ls="--", lw=0.8)
        ax.grid(axis="y", alpha=0.3, lw=0.4)
    axes[0].text(0.03, common, "common field effect only", transform=axes[0].get_yaxis_transform(),
                 va="bottom", fontsize=6.5, color=GREY)
    axes[0].set_ylabel("Validation RMSE, 2018-2021\n(grade points)")
    axes[0].legend(frameon=False, loc="upper left", fontsize=6.5)
    axes[1].legend(frameon=False, loc="upper left", fontsize=6.5)
    axes[2].legend(frameon=False, loc="upper right", fontsize=6.5,
                   title="best number of trees (100-600)", title_fontsize=6.5)
    save(fig, "fig8_model_tuning")


def fig9_background() -> None:
    """Who enters each degree: background of the 3,703 Portuguese students, by degree."""
    b = pd.read_csv(RES / "background_by_degree.csv", index_col=0).sort_values("gpa_mean")
    stats = json.loads((RES / "background_stats.json").read_text(encoding="utf-8"))
    STATS["fig9"] = {"n_students": stats["n_students"], "n_degrees": stats["n_degrees"],
                     "tests": stats["tests"], "overall": stats["overall"]}
    panels = [("parent_higher_ed", 100, "Parent with a higher-\neducation degree (%)"),
              ("scholarship", 100, "Scholarship\nholders (%)"),
              ("female", 100, "Women (%)"),
              ("gpa_mean", 1, "Mean first-year\nGPA (0-20)")]
    fig, axes = plt.subplots(1, 4, figsize=(FULL, 2.9), sharey=True)
    y = np.arange(len(b))
    for ax, (col, scale, title) in zip(axes, panels):
        x = scale * b[col]
        mean = scale * (stats["overall"][col] if col in stats["overall"] else np.average(b[col], weights=b["n"]))
        ax.hlines(y, mean, x, color=GREY, lw=0.8)
        ax.plot(x, y, "o", ms=3.5, color=BLUE if col != "gpa_mean" else ORANGE)
        ax.axvline(mean, color=RED, ls="--", lw=0.8)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.3, lw=0.4)
    axes[0].set_yticks(y, [f"{c} (n={n})" for c, n in zip(b.index, b["n"])])
    axes[0].text(0.0, -0.22, "Degrees ordered by mean GPA; dashed line: all students.", transform=axes[0].transAxes,
                 fontsize=6.5, color=GREY)
    save(fig, "fig9_background")


FIGURES = {"fig1": fig1_field_effects, "fig2": fig2_persistence, "fig3": fig3_confounders,
           "fig4": fig4_selection, "fig5": fig5_us_spain, "fig6": fig6_ranking_rules,
           "fig7": fig7_adjusted_marks, "fig8": fig8_model_tuning, "fig9": fig9_background}
NEEDS_DEV = {"fig1", "fig2", "fig3"}


def main() -> None:
    """Make every figure, or only those named on the command line (e.g. `fig7 fig8`).

    A partial run keeps the statistics of the other figures already saved in
    results/final_figures_stats.json.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(FIGURES)
    unknown = set(names) - set(FIGURES)
    if unknown:
        raise SystemExit(f"Unknown figure(s): {sorted(unknown)}. Choose from {list(FIGURES)}.")
    path = RES / "final_figures_stats.json"
    if sys.argv[1:] and path.exists():
        STATS.update(json.loads(path.read_text(encoding="utf-8")))
    dev = spain_deviations() if NEEDS_DEV & set(names) else None
    for name in names:
        FIGURES[name](dev) if name in NEEDS_DEV else FIGURES[name]()
    ordered = {k: STATS[k] for k in FIGURES if k in STATS}
    path.write_text(json.dumps(ordered, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: ordered[k] for k in names if k in ordered}, indent=2, default=str))


if __name__ == "__main__":
    main()
