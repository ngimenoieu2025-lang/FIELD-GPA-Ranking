"""Compare ranking rules against common criteria (Issue #4).

Students are ranked on their first-semester grade under four rules and the top
20% is selected. Each rule is then judged on what happens afterwards, in the
second semester, which the ranking never saw:

- future raw grade: mean second-semester grade of the selected students;
- future standing within degree: mean within-degree z-score of that grade;
- stability: rank correlation between the rule's score in semester 1 and the
  same rule's score in semester 2 (how much the rule measures something that
  persists rather than noise);
- entry profile: mean standardised admission grade of the selected students;
- balance: standard deviation of selection rates across degrees.

The first two criteria favour different rules by construction, so which one
matters is a choice about what a grade difference between degrees means.
Uncertainty comes from 1,000 bootstrap resamples of students.
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
from scipy.stats import spearmanr

from analysis import CONTROLS, degree_effects
from load_data import ROOT, load_clean

FIG = ROOT / "figures"
RES = ROOT / "results"
SEED = 42
TOP_SHARE = 0.20
N_BOOT = 1000
RULES = ["raw GPA", "regression-adjusted", "within-degree z-score", "within-degree percentile"]

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def load() -> pd.DataFrame:
    """Students with a grade in both semesters; entry grades standardised within admission route."""
    df = load_clean()
    df = df[(df["approved_1"] > 0) & (df["approved_2"] > 0)].copy()
    for c in ["admission_grade", "prev_grade"]:
        g = df.groupby("app_mode")[c]
        df[c] = ((df[c] - g.transform("mean")) / g.transform("std")).fillna(0)
    return df.reset_index(drop=True)


def scores(df: pd.DataFrame, grade: str) -> pd.DataFrame:
    """Score of every student under each rule, computed from one semester's grade."""
    grp = df.groupby("course")[grade]
    m = smf.ols(f"{grade} ~ " + " + ".join(CONTROLS) + " + C(course, Sum)", df).fit()
    eff = degree_effects(m, sorted(df["course"].unique()))["effect"]
    return pd.DataFrame({
        "raw GPA": df[grade],
        "regression-adjusted": df[grade] - df["course"].map(eff),
        "within-degree z-score": (df[grade] - grp.transform("mean")) / grp.transform("std"),
        "within-degree percentile": grp.rank(pct=True),
    }, index=df.index)


def top(score: pd.Series, k: int, rng: np.random.Generator) -> np.ndarray:
    """Indices of the k best scores, ties broken at random."""
    jitter = rng.random(len(score)) * 1e-9
    return np.argsort(-(score.to_numpy() + jitter))[:k]


def evaluate(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    s1, s2 = scores(df, "grade_1"), scores(df, "grade_2")
    future_z = s2["within-degree z-score"].to_numpy()
    k = int(round(TOP_SHARE * len(df)))
    rows = {}
    for rule in RULES:
        sel = top(s1[rule], k, rng)
        rate = pd.Series(np.isin(np.arange(len(df)), sel)).groupby(df["course"].to_numpy()).mean()
        rows[rule] = {
            "future_raw_grade": df["grade_2"].to_numpy()[sel].mean(),
            "future_within_degree_z": future_z[sel].mean(),
            "stability_spearman": spearmanr(s1[rule], s2[rule]).statistic,
            "entry_admission_z": df["admission_grade"].to_numpy()[sel].mean(),
            "sd_selection_rate": rate.std(ddof=0),
        }
    return pd.DataFrame(rows).T


def bootstrap(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    point = evaluate(df, rng)
    reps = []
    for _ in range(N_BOOT):
        b = df.sample(len(df), replace=True, random_state=int(rng.integers(1e9))).reset_index(drop=True)
        reps.append(evaluate(b, rng))
    stack = pd.concat(reps, keys=range(N_BOOT))
    lo = stack.groupby(level=1).quantile(0.025).loc[RULES]
    hi = stack.groupby(level=1).quantile(0.975).loc[RULES]
    return point, lo, hi


def figure(point: pd.DataFrame, lo: pd.DataFrame, hi: pd.DataFrame) -> None:
    panels = [
        ("future_raw_grade", "Mean 2nd-semester grade\nof selected students (0-20)"),
        ("future_within_degree_z", "Mean 2nd-semester standing\nwithin degree (z-score)"),
        ("stability_spearman", "Rank stability between\nsemesters (Spearman)"),
        ("sd_selection_rate", "Spread of selection rates\nacross degrees (SD)"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.4), sharey=True)
    y = np.arange(len(RULES))
    for ax, (col, title) in zip(axes, panels):
        err = np.vstack([point[col] - lo[col], hi[col] - point[col]]).astype(float)
        ax.errorbar(point[col].astype(float), y, xerr=err, fmt="o", color="tab:blue", capsize=3)
        ax.set_title(title, fontsize=9)
        ax.grid(axis="x", alpha=0.3)
    axes[0].set_yticks(y, RULES)
    axes[0].invert_yaxis()
    fig.supxlabel("Points: estimate on all students; bars: 95% bootstrap interval (1,000 resamples)", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(FIG / "ranking_rules.pdf")
    fig.savefig(FIG / "ranking_rules.png", dpi=200)
    plt.close(fig)


def main() -> None:
    df = load()
    point, lo, hi = bootstrap(df)
    figure(point, lo, hi)
    out = {"n_students": int(len(df)), "top_share": TOP_SHARE, "n_bootstrap": N_BOOT,
           "estimate": point.astype(float).round(4).to_dict(orient="index"),
           "ci95_low": lo.astype(float).round(4).to_dict(orient="index"),
           "ci95_high": hi.astype(float).round(4).to_dict(orient="index")}
    (RES / "ranking_rules.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    table = point.astype(float).round(3).astype(str) + " [" + lo.astype(float).round(3).astype(str) + ", " + hi.astype(float).round(3).astype(str) + "]"
    print(f"{len(df)} students\n" + table.to_string())


if __name__ == "__main__":
    main()
