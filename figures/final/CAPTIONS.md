# Caption notes for the final figures

Facts each caption must state when the figure goes into the Final Report. They are notes, not caption text: write the captions yourselves. Every number below comes from `results/final_figures_stats.json`, written by `src/final_figures.py`.

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
