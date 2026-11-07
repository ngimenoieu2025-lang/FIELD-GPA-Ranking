import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from patsy import build_design_matrices, dmatrix

from load_data import ROOT
from ministry import load


def profiles(df, fit):
    fields = sorted(df.field.unique())
    reference_year = int(df.year.max())
    grid = pd.DataFrame({"field": fields, "year": reference_year})
    training_design = dmatrix("C(field, Sum) + C(year)", df, return_type="dataframe")
    if list(training_design.columns) != list(fit.fe_params.index):
        raise RuntimeError("Profile predictors do not match the fitted model.")
    design = np.asarray(build_design_matrices([training_design.design_info], grid)[0])
    common_means = np.asarray(fit.model.predict(fit.fe_params, exog=design))
    common = dict(zip(fields, common_means - common_means.mean()))
    fixed = np.asarray(fit.model.exog @ np.asarray(fit.fe_params))
    fitted = np.asarray(fit.fittedvalues)
    university_var = float(fit.cov_re.iloc[0, 0])
    field_var = float(fit.vcomp[0])
    residual_var = float(fit.scale)
    if min(university_var, field_var, residual_var) <= 0:
        raise RuntimeError("Boundary variance estimate: review the model before computing profiles.")
    rows = []
    largest_difference = 0.0
    for university, group in df.groupby("univ", sort=True):
        positions = group.index.to_numpy()
        local_fields = sorted(group.field.unique())
        codes = pd.Categorical(group.field, categories=local_fields).codes
        z = np.column_stack([np.ones(len(group)), np.eye(len(local_fields))[codes]])
        prior_variances = np.r_[university_var, np.repeat(field_var, len(local_fields))]
        covariance = np.linalg.inv(np.diag(1 / prior_variances) + z.T @ z / residual_var)
        effects = covariance @ z.T @ (group["mean"].to_numpy() - fixed[positions]) / residual_var
        expected = fitted[positions] - fixed[positions]
        largest_difference = max(largest_difference, float(np.max(np.abs(z @ effects - expected))))
        for j, field in enumerate(local_fields, start=1):
            adjustment = float(effects[0] + effects[j])
            se = float(np.sqrt(covariance[0, 0] + covariance[j, j] + 2 * covariance[0, j]))
            field_se = float(np.sqrt(covariance[j, j]))
            reference_mean = float(common_means[fields.index(field)] + adjustment)
            rows.append({
                "univ": university, "field": field, "reference_year": reference_year,
                "n_years": int((group.field == field).sum()),
                "common_field_effect": float(common[field]),
                "university_effect": float(effects[0]),
                "university_field_effect": float(effects[j]),
                "university_field_conditional_se": field_se,
                "university_field_lower95": float(effects[j] - 1.96 * field_se),
                "university_field_upper95": float(effects[j] + 1.96 * field_se),
                "predicted_mean_reference_year": reference_mean,
                "conditional_lower95": reference_mean - 1.96 * se,
                "conditional_upper95": reference_mean + 1.96 * se,
            })
    if largest_difference > 1e-6:
        raise RuntimeError(f"Profile calculations disagree with fitted random effects: {largest_difference}")
    return pd.DataFrame(rows), largest_difference


def main():
    destination = ROOT / "results"
    destination.mkdir(parents=True, exist_ok=True)
    df = load().dropna(subset=["mean", "univ", "field", "year"]).reset_index(drop=True)
    print(f"Fitting {len(df):,} university-field-year means from {df.univ.nunique()} universities...", flush=True)
    formula = "mean ~ C(field, Sum) + C(year)"
    model = smf.mixedlm(formula, df, groups=df["univ"], re_formula="1",
                        vc_formula={"university_field": "0 + C(field)"})
    attempts = []
    fit = None
    for method in ["lbfgs", "bfgs"]:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            candidate = model.fit(reml=True, method=method, maxiter=1000, disp=False)
        attempts.append({"method": method, "converged": bool(candidate.converged),
                         "warnings": [str(w.message) for w in captured]})
        if candidate.converged:
            fit = candidate
            break
    if fit is None:
        raise RuntimeError(f"Model did not converge; do not report these estimates. Details: {attempts}")
    variances = {"university": float(fit.cov_re.iloc[0, 0]),
                 "university_field": float(fit.vcomp[0]), "residual": float(fit.scale)}
    table, agreement = profiles(df, fit)
    table.to_csv(destination / "mixed_model_profiles.csv", index=False)
    common_lookup = table.drop_duplicates("field").set_index("field")["common_field_effect"]
    common_variance = float(np.var(df.field.map(common_lookup), ddof=0))
    denominator = common_variance + variances["university_field"] + variances["residual"]
    shares = {"common_field": common_variance / denominator,
              "university_specific_field": variances["university_field"] / denominator,
              "residual": variances["residual"] / denominator}
    old_path = ROOT / "results" / "progress_stats.json"
    previous = json.loads(old_path.read_text(encoding="utf-8"))["decomposition"] if old_path.exists() else None
    stats = {
        "formula": formula, "random_intercept": "university",
        "vc_formula": {"university_field": "0 + C(field)"}, "estimation": "REML",
        "n_rows": len(df), "n_universities": int(df.univ.nunique()),
        "n_fields": int(df.field.nunique()), "years": sorted(map(int, df.year.unique())),
        "optimizer_attempts": attempts, "variance_components_grade_points_squared": variances,
        "random_and_residual_variance_shares": {k: v / sum(variances.values()) for k, v in variances.items()},
        "descriptive_common_field_variance": common_variance,
        "descriptive_three_way_shares": shares, "previous_ols_decomposition": previous,
        "comparison_note": "The previous 65/28/7 split uses reductions in OLS residual sums of squares after university-year adjustment. The descriptive mixed-model split uses fixed-field fitted-value variance plus estimated university-field and residual variances, excluding the university intercept and year effects. Different estimands: not an exact like-for-like decomposition.",
        "uncertainty_note": "95% conditional empirical-Bayes intervals hold fixed effects and variance parameters at fitted estimates; they omit parameter-estimation uncertainty. Aggregate-mean uncertainty is not individual-grade uncertainty.",
        "profile_blup_max_abs_difference": agreement,
        "limitations": ["Each university-field-year mean has equal weight; no graduate-count weighting.",
                        "Residuals represent unexplained variation in aggregate means, not individual student grades.",
                        "University and field differences are associations, not causal grading effects."]
    }
    (destination / "mixed_model_stats.json").write_text(json.dumps(stats, indent=2, allow_nan=False), encoding="utf-8")
    (destination / "mixed_model_summary.txt").write_text(str(fit.summary()) + "\n\n" + stats["comparison_note"] + "\n\n" + stats["uncertainty_note"] + "\n", encoding="utf-8")
    print(fit.summary())
    print("\nDescriptive comparison (different estimand from the old 65/28/7 split):")
    for name, value in shares.items():
        print(f"  {name}: {100 * value:.2f}%")
    print(f"\nSaved mixed_model_profiles.csv, mixed_model_stats.json and mixed_model_summary.txt in {destination}")


if __name__ == "__main__":
    main()
