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
