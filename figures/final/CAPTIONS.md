# Caption notes for the final figures

File numbers are not report numbers: the report numbers its figures in order of appearance (for example fig9_background is Figure 1 and fig1_field_effects is Figure 3). Facts each caption must state when the figure goes into the Final Report. They are notes, not caption text: write the captions yourselves. Every number below comes from `results/final_figures_stats.json`, written by `src/final_figures.py`.

## Figure 1: field effects (`fig1_field_effects.pdf`, single column)
- What it shows: each field's average distance from the mean of all fields in the same university and year.
- Data: SIIU, 12,125 university-field-year means, 89 universities, 2015-16 to 2023-24, 5-10 scale.
- Uncertainty: 95% confidence intervals clustered by university (median half-width about 0.05 points).
- Range: Nursing +0.53 to Architecture -0.53.
- Colour: blue above average, orange below.

## Figure 2: persistence (`fig2_persistence.pdf`, single column)
- What it shows: a field's university-specific deviation (after removing the effect it has in all universities) in year t against year t+1.
- Correlation r = 0.84 (95% CI 0.84-0.85), 10,413 consecutive-year pairs; least-squares slope 0.85.
- Black line: least-squares fit; dashed red line: perfect persistence.

## Figure 3: intake and size (`fig3_confounders.pdf`, single column)
- What it shows: field effects with field only (x) against field effects after adding admission grade and size (y).
- Sample: 47 public universities only (admission grades are not published for private universities), 8,043 observations.
- Must say: admission grade is published per broad branch (5 branches for 29 fields), so it cannot separate fields within the same branch. This makes the test weak; the near-identity (r = 0.99) is partly built in.
- Same model as Figure 1 on a smaller sample, so values differ slightly from Figure 1.
- 95% CIs clustered by university. Dashed red line: no change.

## Figure 4: selection (`fig4_selection.pdf`, single column)
- Must say: simulated, not observed. Within-field grades approximated as normal from the reported mean and quartiles; graduate-weighted top-20% cut per university-year; 664 university-years.
- Points: median university-year; bars: interquartile range; dashed red line: equal access (20%).
- Robustness: replacing the normal by a normal truncated to 5-10 changes shares by 0.04 percentage points on average and no field changes rank.
- Nursing median 41% vs Business Administration 6%.

## Figure 5: Spain vs US (`fig5_us_spain.pdf`, single column)
- What it shows: broad-area effects in Spain (graduates' final averages, 5-10 scale) against the US (course-section GPA, 0-4 scale), 10 broad areas.
- Pearson r = 0.61, 95% CI -0.03 to 0.90 (10 points, interval includes zero); 8 of 10 areas share the sign.
- Must say: moderate agreement, not conclusive; scales and grade types differ, so compare signs and ordering, not magnitudes.
- 95% CIs clustered by university in both countries.

## Figure 6: ranking rules (`fig6_ranking_rules.pdf`, full page width)
- What it shows: four rules ranking Portuguese students on first-semester grades, evaluated on the second semester; top 20% selected.
- 95% bootstrap intervals (1,000 resamples of students).
- Must say: axes are zoomed; the 0.13-point gap in the first panel is small on the 0-20 scale and the intervals overlap.
- Rank stability of raw GPA is partly inflated by the persistent gap between degrees.

## Figure 7: adjusted marks (`fig7_adjusted_marks.pdf`, single column)
- What it shows: the selection simulation of Figure 4 repeated with the instructor's adjusted mark (mark minus the field's deviation). The deviation subtracted is the field's average deviation at the same university in earlier years only, so the correction could be applied in practice.
- Same statistic as Figure 4: median university-year and interquartile range. Sample: 2016-2023 (2015 has no earlier year), 595 university-years, 79 universities, so raw values differ slightly from Figure 4.
- Mean absolute distance from 20%, weighted by graduates: 11.8 pp raw (95% CI 11.0-12.6) to 5.1 pp adjusted (4.8-5.3); bootstrap over universities. Upper bound with the same year's deviation: 3.6 pp.
- Nursing median 40.6% -> 13.0%; Business administration 5.4% -> 19.5%.
- Must say: equalising means does not equalise access because spreads differ by field (e.g. Nursing has a narrow spread and falls below 20%). Within-degree percentiles (Figure 6) also remove this.
- Source: results/adjusted_mark_stats.json, results/adjusted_mark_field_distribution.csv.

## Figure 8: model tuning (`fig8_model_tuning.pdf`, full page width)
- What it shows: expanding-window validation error (train on years before v, validate on v = 2018-2021, averaged) for each value of the tuned hyperparameter. The test years 2022-2023 were never used for tuning.
- Dashed grey line: common field effect only (validation RMSE 0.219), the model without university profiles.
- (a) shrinkage k: weight n/(n+k) on the university's own past deviation; chosen k = 0.25 (validation RMSE 0.116). Large k tends to the common field effect.
- (b) ridge alpha: chosen 0.22 (0.116); the two models are two forms of the same partial pooling and give the same result.
- (c) gradient boosting: best number of trees (100, 300 or 600) for each depth and learning rate; chosen depth 8, learning rate 0.03, 600 trees (0.114). The curve is almost flat (0.116 at depth 2), so the gain from more complexity is small.
- Test RMSE 2022-2023: baseline 0.365, common field 0.225, shrunk profile 0.138, ridge 0.138, boosting 0.133.
- Source: results/model_selection_tuning.csv, results/model_selection_stats.json.

## Figure 9: student background by degree (`fig9_background.pdf`, full page width; Figure 1 of the report)
- What it shows: the background of the students of each degree. Data: 3,703 students, 15 degrees, one Portuguese polytechnic, cohorts 2008-09 to 2018-19. Panels show the share with a parent who holds a higher-education degree, scholarship holders, women, and mean first-year GPA.
- Definition: a parent with a completed higher-education degree is a mother or father with UCI code 2, 3, 4, 5, 40, 43 or 44 (bachelor's, master's or doctorate).
- Degrees are ordered by mean GPA. The dashed line marks all students.
- Every difference between degrees is far larger than chance (chi-square tests, 14 df, p < 1e-25; ANOVA of the standardised entry grade, F = 12.6). Parent with higher education ranges from 7% (Social Service, evening) to 50% (Equinculture). Across degrees, mean GPA correlates 0.40 with that share.
- Must say: descriptive only, with no causal claim. It motivates why degrees differ in who enters them.
- Source: results/background_stats.json, results/background_by_degree.csv (src/background.py).
