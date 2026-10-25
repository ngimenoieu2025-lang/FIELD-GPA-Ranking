"""Load and clean the UCI 'Predict Students' Dropout and Academic Success' dataset."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "data.csv"

# Degree codes as documented by the dataset authors (UCI repository, dataset 697).
COURSES = {
    33: "Biofuel Production Tech.",
    171: "Animation & Multimedia",
    8014: "Social Service (evening)",
    9003: "Agronomy",
    9070: "Communication Design",
    9085: "Veterinary Nursing",
    9119: "Informatics Engineering",
    9130: "Equinculture",
    9147: "Management",
    9238: "Social Service",
    9254: "Tourism",
    9500: "Nursing",
    9556: "Oral Hygiene",
    9670: "Advertising & Marketing",
    9773: "Journalism & Communication",
    9853: "Basic Education",
    9991: "Management (evening)",
}

RENAME = {
    "Course": "course_code",
    "Application mode": "app_mode",
    "Admission grade": "admission_grade",
    "Previous qualification (grade)": "prev_grade",
    "Age at enrollment": "age",
    "Gender": "male",
    "Scholarship holder": "scholarship",
    "Displaced": "displaced",
    "International": "international",
    "Debtor": "debtor",
    "Curricular units 1st sem (enrolled)": "enrolled_1",
    "Curricular units 1st sem (approved)": "approved_1",
    "Curricular units 1st sem (grade)": "grade_1",
    "Curricular units 2nd sem (enrolled)": "enrolled_2",
    "Curricular units 2nd sem (approved)": "approved_2",
    "Curricular units 2nd sem (grade)": "grade_2",
    "Target": "target",
}


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns=RENAME)
    df["course"] = df["course_code"].map(COURSES)
    return df


def load_clean(min_course_size: int = 50) -> pd.DataFrame:
    """Students with a usable first-year grade average.

    A semester grade of 0 means the student passed no unit that semester, so the
    average is undefined rather than a real mark of zero. The first-year GPA is the
    mean of the two semester averages, weighted by units approved, and is only
    defined for students who passed at least one unit.
    """
    df = load_raw()
    approved = df["approved_1"] + df["approved_2"]
    df = df[approved > 0].copy()
    df["gpa"] = (
        df["grade_1"] * df["approved_1"] + df["grade_2"] * df["approved_2"]
    ) / (df["approved_1"] + df["approved_2"])
    sizes = df["course"].value_counts()
    df = df[df["course"].isin(sizes[sizes >= min_course_size].index)].copy()
    return df.reset_index(drop=True)


if __name__ == "__main__":
    raw = load_raw()
    clean = load_clean()
    print("raw rows:", len(raw), "| clean rows:", len(clean))
    print("unmapped course codes:", raw.loc[raw["course"].isna(), "course_code"].unique())
    print("zero grade sem1:", (raw["grade_1"] == 0).sum(), "| sem2:", (raw["grade_2"] == 0).sum())
    print("no unit approved all year:", ((raw["approved_1"] + raw["approved_2"]) == 0).sum())
    print(raw["target"].value_counts().to_dict())
    summary = clean.groupby("course").agg(
        n=("gpa", "size"),
        gpa_mean=("gpa", "mean"),
        gpa_sd=("gpa", "std"),
        adm_mean=("admission_grade", "mean"),
    )
    raw_n = raw["course"].value_counts().rename("n_raw")
    print(summary.join(raw_n).sort_values("gpa_mean").round(2).to_string())
    print("gpa range:", clean["gpa"].min().round(2), clean["gpa"].max().round(2))
    print("corr gpa~admission:", clean["gpa"].corr(clean["admission_grade"]).round(3))
