"""Student background by degree (Portuguese records): who chooses which degree.

Instructor's feedback on the Sentence Outline (Communication Skills): start from
how students' backgrounds can shape their choice of degree. The Portuguese
records are the only dataset with individual background variables, so this
script describes how the intake of each degree differs.

Per degree (the 3,703 students of load_clean, 15 degrees):
- share with at least one parent holding a completed higher-education degree
  (UCI codes 2, 3, 4, 5, 40, 43, 44 for mother's or father's qualification);
- share of scholarship holders;
- share of women;
- mean admission grade, standardised within admission route (as in ranking_rules.py);
- mean first-year GPA (0-20).
Chi-square tests of independence between degree and each binary variable, and
a one-way ANOVA for the standardised admission grade, measure whether the
differences between degrees are larger than chance.

Outputs: results/background_by_degree.csv, results/background_stats.json.
The report figure is made by final_figures.py (fig9).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, f_oneway

from load_data import ROOT, load_clean

RES = ROOT / "results"
HIGHER_EDUCATION = {2, 3, 4, 5, 40, 43, 44}  # completed degrees in the UCI coding


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    clean = load_clean()
    # load_clean does not keep the parents' qualifications, so the same filters are
    # applied to the raw file (rows keep their order) and the match is asserted.
    raw = pd.read_csv(ROOT / "data" / "raw" / "data.csv", sep=";")
    raw.columns = [c.strip() for c in raw.columns]
    sub = raw[(raw["Curricular units 1st sem (approved)"] + raw["Curricular units 2nd sem (approved)"]) > 0]
    sizes = sub["Course"].value_counts()
    sub = sub[sub["Course"].isin(sizes[sizes >= 50].index)].reset_index(drop=True)
    assert len(sub) == len(clean)
    assert np.allclose(sub["Admission grade"].to_numpy(), clean["admission_grade"].to_numpy())
    assert (sub["Course"].to_numpy() == clean["course_code"].to_numpy()).all()

    d = clean.copy()
    d["parent_higher_ed"] = (sub["Mother's qualification"].isin(HIGHER_EDUCATION)
                             | sub["Father's qualification"].isin(HIGHER_EDUCATION)).astype(int).to_numpy()
    d["female"] = 1 - d["male"]
    g = d.groupby("app_mode")["admission_grade"]
    d["admission_z"] = ((d["admission_grade"] - g.transform("mean")) / g.transform("std")).fillna(0)

    by = d.groupby("course").agg(
        n=("gpa", "size"), gpa_mean=("gpa", "mean"),
        parent_higher_ed=("parent_higher_ed", "mean"), scholarship=("scholarship", "mean"),
        female=("female", "mean"), admission_z=("admission_z", "mean"),
    ).sort_values("gpa_mean")
    by.round(4).to_csv(RES / "background_by_degree.csv")

    stats = {"n_students": int(len(d)), "n_degrees": int(d["course"].nunique()),
             "higher_education_codes": sorted(HIGHER_EDUCATION), "overall": {}, "tests": {}}
    for v in ["parent_higher_ed", "scholarship", "female"]:
        stats["overall"][v] = float(d[v].mean())
        chi2, p, dof, _ = chi2_contingency(pd.crosstab(d["course"], d[v]))
        stats["tests"][v] = {"chi2": float(chi2), "df": int(dof), "p": float(p),
                             "min_degree": str(by[v].idxmin()), "min": float(by[v].min()),
                             "max_degree": str(by[v].idxmax()), "max": float(by[v].max())}
    f, p = f_oneway(*[x["admission_z"].to_numpy() for _, x in d.groupby("course")])
    stats["tests"]["admission_z"] = {"F": float(f), "p": float(p), "min_degree": str(by["admission_z"].idxmin()),
                                     "min": float(by["admission_z"].min()), "max_degree": str(by["admission_z"].idxmax()),
                                     "max": float(by["admission_z"].max())}
    stats["corr_degree_gpa_with"] = {v: float(by["gpa_mean"].corr(by[v]))
                                     for v in ["parent_higher_ed", "scholarship", "female", "admission_z"]}
    (RES / "background_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(by.round(3).to_string())


if __name__ == "__main__":
    main()
