# FIELD: How Much Does the Field of Study Shape University GPA Rankings?

*FIELD: Field Influence on Evaluation Levels across Degrees.*

Machine Learning & Communication Skills project, Bachelor in Applied Mathematics, IE University (2026-27).
Group: Adam Bajer, Pablo Torres, Ignacio Gimeno.

## Question

How much of a student's position in a university-wide GPA ranking depends on their field of study, and how would ranking students within their degree change who is selected for a fixed number of places?

## Data

| File | Source | Used for |
|---|---|---|
| `data/raw/data.csv` | UCI "Predict Students' Dropout and Academic Success" (dataset 697), 4,424 students of a Portuguese polytechnic | Individual-level check with entry grades |
| `data/raw/ministerio/Nota_Expediente_Grado_Univ.csv` | Spanish Ministry of Universities (SIIU): mean, quartiles and maximum final grade of graduates by university, field and year | Main dataset |
| `data/raw/ministerio/Abandono_Grado_Univ.csv` | SIIU: dropout rates by university and field | Confounder |
| `data/raw/ministerio/px_estu_grado_egre_edad_ambito_univ.csv` | SIIU: graduates by university and field | Weights and size |
| `data/raw/ministerio/px_estu_grado_ni_media_*.csv` | SIIU: admission grades of new entrants (by university and branch; by field) | Confounder |

Sources: https://archive.ics.uci.edu/dataset/697/predict+students+dropout+and+academic+success and https://estadisticas.ciencia.gob.es

## Run

```
pip install -r requirements.txt
python src/load_data.py     # data checks and per-degree summary (Portuguese records)
python src/analysis.py      # proposal: degree effects and selection simulation
python src/ministry.py      # proposal: field effects across Spanish universities
python src/model_eval.py    # proposal: model comparison with a held-out test set
python src/progress.py      # progress report: decomposition, temporal validation, confounders, clustering
python src/mixed_model.py   # mixed-effects model and university-field profiles
python src/normal_check.py  # normal approximation checks and selection sensitivity
```

All scripts use fixed random seeds (42) and write their numbers to `results/` and their figures to `figures/`.

## Layout

- `src/` analysis code
- `data/raw/` original data, never modified
- `data/processed/` tidy tables written by the scripts
- `results/` tables and JSON files with every number reported
- `figures/` figures as PDF (for LaTeX) and PNG
- `reports/` LaTeX sources of the submitted reports

## Project log

- 11 Oct 2026: Project Proposal (Portuguese records and Spanish Ministry data; degree effects, held-out evaluation, selection simulation).
- 25 Oct 2026: Progress Report (variance decomposition, temporal validation, confounders, clustering, ranking rules). Repository created on this date; earlier work was developed locally and added in the commits below.

## US replication (Adam)

The US replication checks whether the Spanish field patterns also appear in
Jeong, Weiss, Leung and Leeds (2024), **Course Grades from 33 Public Universities**.
Dataset: https://www.kaggle.com/datasets/hyunjeong2023/edm-grading-dataset
Paper: https://www.educationaldatamining.org/edm2024/proceedings/2024.EDM-posters.67/

### Download and run

1. Open the Kaggle link, sign in if required, and select **Download**.
2. Extract the archive. Copy the **33 CSVs** from `Grade_datasets/` and
   `dept_name_code_field_mapping.xlsx` into `data/raw/us33/`.
   Keep the original university filenames. The workbook must be directly inside
   `us33/`; the CSVs can be there or in a subfolder. Approximately 274 MB is
   required for the extracted files. Do not commit these files: the entire
   `data/raw/us33/` folder is ignored by Git.
3. From the repository root:

```bash
pip install -r requirements.txt
python src/us_replication.py
python -m unittest discover -s tests -v
```

The script reads all 33 CSVs and runs the analysis. It also writes the tidy
section/course table to `data/processed/us_sections.csv.gz`, which is ignored.
No Kaggle API key is required when downloading through the website.

### Grade calculation and model

For each source row, compute `GPA = sum(grade_percentage * grade_points) /
sum(numeric_grade_percentages)`. We follow the paper's mapping:
A+=4.30, A=4, A-=3.67, B+=3.33, B=3, B-=2.67, C+=2.33, C=2,
C-=1.67, D+=1.33, D=1, D-=0.67, F=0. Pass, pass/fail Fail, W and Other
are excluded from this calculation. F remains a zero grade. Blank numeric-grade
categories are treated as zero; rows with no numeric grades are excluded.
Negative or >100 category percentages, nonnumeric values, or numeric-grade
percentages summing to >101 are rejected; the one-point tolerance permits
small rounding errors. Exact duplicate rows are removed. The audit gives
counts by institution. These are section **or course** observations according
to the source, not individual student GPAs.

Within each university–broad-area–year cell, section/course GPAs are weighted
by reported total enrolment. Four institutions have no enrolment counts and
are excluded from this weighted analysis, but enter the equal-section-weight
sensitivity analysis. We do not invent their enrolments. Total enrolment
weighting follows the paper; it is not weighting by credit hours or by the
estimated number of numeric grades.

The regression uses the same specification as `src/ministry.py`:

```text
mean ~ C(field, Sum) + C(univ) + C(year)
```

Each university–area–year cell receives equal weight in OLS, as in the Spanish
model. Enrolment weighting happens when constructing US cell means, not as
regression weights. Field effects sum to zero across the included areas.
`src/us_model.py` implements this design with NumPy/SciPy and checks that it is
identified. Its detailed-field Spanish coefficients and standard errors match
the committed `spain_field_effects.csv` at the file's three-decimal precision.
Standard errors use conventional OLS, matching `ministry.py`; they are not
clustered. Existing Spanish code and outputs are unchanged.

### Department mapping

We use **ten common broad areas**, rather than claiming exact equivalence
between US departments and all 29 Spanish fields:

| Broad area | Spanish fields combined |
|---|---|
| Education | Early childhood teaching; Primary teaching; Other education |
| Arts, media & architecture | Arts; Audiovisual & media; Architecture |
| Humanities & languages | Humanities; Languages |
| Social sciences & law | Psychology; Economics; Other social sciences; Journalism; Law; Social work |
| Business | Business administration; Other business |
| Science, mathematics & computing | Life sciences; Physical sciences; Mathematics & statistics; Computer science |
| Engineering | Engineering |
| Agriculture | Agriculture |
| Health & veterinary | Medicine; Nursing; Other health; Veterinary |
| Sports, tourism & services | Sports; Tourism; Other services |

`data/mappings/us_department_to_area.csv` records the university, department
code/name, authors' original category, chosen broad area, and rule/exclusion
reason. The starting point is the authors' Excel workbook; ordered name rules
in `src/us_mapping.py` separate education, agriculture, health and services
from mixed source categories. Ambiguous general programmes, military studies
and unmatched departments are excluded. Missing department codes are resolved
only through a unique exact department-name match within that university
(needed for UC Irvine). Codes are never assumed to have the same meaning at
different institutions.

The crosswalk is transparent and editable, but remains a substantive modelling
choice for review, particularly mixed departments and the services category.
Edit the CSV to revise individual assignments; ordinary runs preserve edits.
`python src/us_replication.py --rebuild-mapping` deliberately regenerates it
from the workbook and rules, replacing manual edits.

`data/mappings/spain_field_to_area.csv` maps every original Spanish label to
its English field and broad area. Spanish original field means are averaged
equally within each university–area–year cell because the Ministry grade table
does not contain enrolments. Both country models are refitted on the same
common broad areas; we do not correlate broad US coefficients with unmatched
29-field Spanish coefficients.

### Outputs and interpretation

- `results/us_spain_field_comparison.csv`: both countries' adjusted effects and SEs.
- `figures/us_spain_field_effects.png` and `.pdf`: comparison scatterplot.
- `results/us_replication_stats.json`: correlations, model statistics, sensitivity
  checks, omitted institutions, coverage and input checksums.
- `results/us_data_audit.csv`: row counts and exclusions by institution (audit
  flags overlap and should not be added together).
- `results/us_mapping_coverage.csv`: observed department coverage, including exclusions.
- `results/us_leave_one_university_out.csv`: sensitivity to each US university.
- `reports/us_replication/FINDINGS.md`: findings and limitations.

The checks compare equal-section weights across all 33 institutions, A+ capped
at 4.0, common years only, and leaving each weighted-sample university out.
US course grades and Spanish graduates' final grades measure different things;
course levels, subject composition and selection remain potential confounders.
US years are the reported source years; Spanish years are the start of the
academic year, following ministry.py. These are not identical time windows.
The Spanish sample follows `ministry.py` and includes its full university
sample, not only public universities. Correlations across ten areas are
**descriptive evidence of partial replication**, not proof of causal grading
bias or confirmation of every detailed-field result.
