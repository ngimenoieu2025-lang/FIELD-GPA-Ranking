# Add US replication of Spanish field effects across public institutions

Adds a reproducible comparison using Jeong et al.'s 33-institution grade dataset.
All 33 CSVs are loaded; 29 institutions have enrolment counts for the main model.
Department names and the authors' institution-specific categories are mapped to
ten common broad areas, covering all 29 Spanish fields. Both country models are
refitted with the same sum-coded field, university and year effects as ministry.py.

The broad-area comparison gives Pearson r = 0.613 and Spearman rho = 0.612,
with eight of ten effects sharing a sign. Education and health are relatively
high in both countries; humanities differs in sign. This is partial descriptive
replication, not evidence of a causal grading-policy effect.

Includes the script, editable crosswalk, exclusion audit, results, comparison
figure, findings note, download instructions and raw-data ignore rule. Existing
Spanish analysis code and outputs are unchanged. Raw US data are not committed.

Validation: full run on 33 input files; six passing numerical tests; the new
OLS implementation reproduces saved Spanish effects and SEs to their stored
three-decimal precision. Equal-section weighting, A+ capped at 4, common-year
and leave-one-university-out checks are included.

Review focus: broad-area department assignments; course/section outcomes versus
Spanish graduate averages; inclusion of multiple US course levels; and the four
institutions with missing enrolments. Crosswalk assignments are transparent
rule-based proposals, not individually certified subject mappings.
