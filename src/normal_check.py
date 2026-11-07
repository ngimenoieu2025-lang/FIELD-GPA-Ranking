import json

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import roots_legendre
from scipy.stats import norm, truncnorm

from load_data import ROOT
from ministry import IQR_TO_SD, TOP_SHARE, load
from progress import load_covariates


def check_normality(data):
    result = data.copy()
    result["mean_minus_median"] = result["mean"] - result["q2"]
    result["mean_median_gap_sd"] = result["mean_minus_median"] / result["sd"]
    result["normal_mass_outside_5_10"] = (
        norm.cdf(5, result["mean"], result["sd"])
        + norm.sf(10, result["mean"], result["sd"])
    )
    maximum = result.dropna(subset=["max"]).copy()
    counts = maximum["graduates"].to_numpy()
    nodes, weights = roots_legendre(128)
    probabilities = (nodes + 1) / 2
    unique_counts = np.unique(counts)
    maximum_z = norm.isf(-np.expm1(np.log(probabilities)[None, :] / unique_counts[:, None]))
    expected_z = dict(zip(unique_counts, maximum_z @ (weights / 2)))
    maximum["expected_normal_max"] = maximum["mean"] + maximum["sd"] * maximum["graduates"].map(expected_z)
    for probability, column in [(0.025, "normal_max_lower95"), (0.975, "normal_max_upper95")]:
        z = norm.isf(-np.expm1(np.log(probability) / counts))
        maximum[column] = maximum["mean"] + maximum["sd"] * z
    maximum["observed_minus_expected_max"] = maximum["max"] - maximum["expected_normal_max"]
    maximum["max_outside_normal_interval"] = (
        (maximum["max"] < maximum["normal_max_lower95"] - 0.01)
        | (maximum["max"] > maximum["normal_max_upper95"] + 0.01)
    )
    columns = ["expected_normal_max", "normal_max_lower95", "normal_max_upper95",
               "observed_minus_expected_max", "max_outside_normal_interval"]
    return result.join(maximum[columns])


def compare_selection(data):
    rows = []
    maximum_capacity_error = 0.0
    for (university, year), group in data.groupby(["univ", "year"]):
        if len(group) < 4:
            continue
        means = group["mean"].to_numpy()
        scales = group["sd"].to_numpy()
        weights = group["graduates"].to_numpy()
        weights = weights / weights.sum()
        normal = norm(loc=means, scale=scales)
        truncated = truncnorm((5 - means) / scales, (10 - means) / scales,
                              loc=means, scale=scales)
        rates = {}
        cutoffs = {}
        for name, distribution, bounds in [
            ("normal", normal, (0, 15)),
            ("truncated", truncated, (5, 10)),
        ]:
            cutoff = brentq(lambda value: np.dot(weights, distribution.sf(value)) - TOP_SHARE, *bounds)
            rates[name] = distribution.sf(cutoff)
            cutoffs[name] = cutoff
            error = abs(float(np.dot(weights, rates[name])) - TOP_SHARE)
            maximum_capacity_error = max(maximum_capacity_error, error)
        result = group[["univ", "field", "year", "graduates"]].copy()
        result["normal_share"] = rates["normal"]
        result["truncated_share"] = rates["truncated"]
        result["difference_pp"] = 100 * (rates["truncated"] - rates["normal"])
        result["normal_cutoff"] = cutoffs["normal"]
        result["truncated_cutoff"] = cutoffs["truncated"]
        rows.append(result)
    if not rows:
        raise RuntimeError("No university-years have at least four fields with valid grades and graduate counts.")
    if maximum_capacity_error > 1e-8:
        raise RuntimeError("Selection rates do not preserve the required number of places.")
    selection = pd.concat(rows, ignore_index=True)
    summaries = []
    for field, group in selection.groupby("field"):
        normal_share = np.average(group["normal_share"], weights=group["graduates"])
        truncated_share = np.average(group["truncated_share"], weights=group["graduates"])
        summaries.append({
            "field": field, "normal_share": float(normal_share),
            "truncated_share": float(truncated_share),
            "difference_pp": float(100 * (truncated_share - normal_share)),
            "n_university_years": len(group),
        })
    summary = pd.DataFrame(summaries)
    summary["normal_rank"] = summary["normal_share"].rank(ascending=False, method="min").astype(int)
    summary["truncated_rank"] = summary["truncated_share"].rank(ascending=False, method="min").astype(int)
    return selection, summary.sort_values("normal_rank"), maximum_capacity_error


def main():
    destination = ROOT / "results"
    destination.mkdir(parents=True, exist_ok=True)
    grades = load()
    _, graduates = load_covariates()
    data = grades.join(graduates, on=["univ", "field", "year"])
    data = data.dropna(subset=["mean", "q1", "q3", "graduates"])
    data = data[
        (data["q3"] > data["q1"]) & (data["graduates"] >= 1)
        & data["mean"].between(5, 10) & data["q1"].between(5, 10)
        & data["q3"].between(5, 10)
    ].copy()
    if data.empty:
        raise RuntimeError("No valid grade records match graduate counts.")
    data["sd"] = (data["q3"] - data["q1"]) / IQR_TO_SD
    print(f"Checking {len(data):,} university-field-year records...", flush=True)
    diagnostics = check_normality(data)
    print("Comparing normal and truncated-normal selection...", flush=True)
    selection, summary, capacity_error = compare_selection(data)
    maximum = diagnostics.dropna(subset=["expected_normal_max"])
    median_gap = diagnostics["mean_median_gap_sd"].dropna()
    stats = {
        "n_original_grade_records": len(grades), "n_matched_valid_records": len(data),
        "n_excluded_records": len(grades) - len(data),
        "n_records_with_median": len(median_gap), "n_records_with_maximum": len(maximum),
        "median_absolute_mean_median_gap_sd": float(median_gap.abs().median()) if len(median_gap) else None,
        "median_normal_mass_outside_5_10": float(diagnostics["normal_mass_outside_5_10"].median()),
        "share_maxima_outside_normal_95_interval": float(maximum["max_outside_normal_interval"].mean()) if len(maximum) else None,
        "mean_observed_minus_expected_max": float(maximum["observed_minus_expected_max"].mean()) if len(maximum) else None,
        "n_selection_university_years": int(selection.groupby(["univ", "year"]).ngroups),
        "n_selection_universities": int(selection["univ"].nunique()),
        "graduate_weighted_absolute_change_pp": float(np.average(selection["difference_pp"].abs(), weights=selection["graduates"])),
        "largest_absolute_field_average_change_pp": float(summary["difference_pp"].abs().max()),
        "n_fields_with_changed_rank": int((summary["normal_rank"] != summary["truncated_rank"]).sum()),
        "maximum_selection_capacity_error": capacity_error,
        "methods": {
            "sd": "(Q3-Q1)/1.349, as in the existing simulation.",
            "expected_maximum": "Numerical expectation from the normal maximum quantile function using 128-point Gaussian quadrature.",
            "maximum_interval": "Pointwise 95% predictive interval using P(maximum <= x)=Phi((x-mean)/sd)^n; allows 0.01 grade points for rounding.",
            "selection": "Graduate-weighted top-20% cutoff within university-year, with at least four observed fields. Same records and weights for both distributions.",
            "truncation": "Restricts the existing normal to [5,10], retaining its underlying location and scale. Truncation changes the resulting mean and IQR; parameters are not refitted.",
        },
        "limitations": [
            "Published summaries cannot establish normality or support an individual-level normality test.",
            "Mean-median gaps are descriptive evidence of asymmetry, not a formal significance test.",
            "Maximum diagnostics assume independent grades and treat estimated means, scales and matched graduate counts as known; intervals are pointwise, not simultaneous.",
            "Missing fields are excluded; selection represents graduates in available fields, not necessarily the complete university.",
            "Selection compares model-implied rates, not the identities of individual selected students.",
        ],
    }
    diagnostics.to_csv(destination / "normal_diagnostics.csv", index=False)
    selection.to_csv(destination / "normal_selection_comparison.csv", index=False)
    summary.to_csv(destination / "normal_selection_by_field.csv", index=False)
    (destination / "normal_check_stats.json").write_text(json.dumps(stats, indent=2, allow_nan=False), encoding="utf-8")
    print("\nMean and median:")
    print(f"  Median absolute gap in SD units: {stats['median_absolute_mean_median_gap_sd']}")
    print("\nMaximum-grade check:")
    if len(maximum):
        print(f"  Maxima outside the normal 95% interval: {100 * stats['share_maxima_outside_normal_95_interval']:.2f}%")
    print("\nSelection sensitivity:")
    print(f"  Graduate-weighted absolute change: {stats['graduate_weighted_absolute_change_pp']:.3f} percentage points")
    print(f"  Largest field-average absolute change: {stats['largest_absolute_field_average_change_pp']:.3f} percentage points")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nSaved three CSV tables and normal_check_stats.json in {destination}")


if __name__ == "__main__":
    main()
