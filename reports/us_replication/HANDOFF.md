# Put these changes into your GitHub project

The ZIP contains **only new or changed project files**, preserving paths. It
excludes raw data and intermediate tables. The analysis and figure are already
computed; `FINDINGS.md` explains the results.

## Using GitHub Desktop (no terminal needed)

1. Open your local `FIELD-GPA-Ranking` repository in GitHub Desktop.
2. Fetch/pull the latest main branch. Create a branch named `adam/us-replication`.
3. Extract the supplied changes ZIP elsewhere. Copy its contents into the
   repository, preserving folders. The package replaces `.gitignore`, `README.md`
   and `requirements.txt` from the uploaded snapshot. If teammates edited these
   since that snapshot, merge the US additions instead of overwriting their work.
4. To rerun locally, copy the Kaggle CSVs and workbook into `data/raw/us33/` as
   explained in README. Raw US files should not appear in GitHub Desktop's changes.
5. Review the changes. Use commit message `Add US broad-area replication` and
   commit to the new branch, then **Publish branch / Push origin**.
6. Select **Create Pull Request**. Use the title and text in `PR_DESCRIPTION.md`,
   with `main` as the base and `adam/us-replication` as the compare branch.

If you lack push permission, fork the repository and open the PR from your fork.
Do not merge the PR yourself unless your group has agreed to that.

## Terminal equivalent (inside your existing clone)

Start from a clean working tree. After fetching the current main branch and
creating `adam/us-replication`, copy/merge the ZIP contents into that clone.
Then run:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/us_replication.py

git check-ignore data/raw/us33/example.csv
git add .gitignore README.md requirements.txt src/us_replication.py src/us_mapping.py src/us_model.py tests/test_us_replication.py data/mappings reports/us_replication
git add results/us_data_audit.csv results/us_mapping_coverage.csv results/us_field_effects.csv results/us_spain_field_comparison.csv results/us_replication_stats.json results/us_leave_one_university_out.csv
git add figures/us_spain_field_effects.png figures/us_spain_field_effects.pdf
git diff --cached --stat
git commit -m "Add US broad-area replication"
git push -u origin adam/us-replication
```

On GitHub, open the suggested pull request. If GitHub CLI is installed and
already authenticated, the equivalent is:

```bash
gh pr create --base main --head adam/us-replication --title "Add US replication of Spanish field effects" --body-file reports/us_replication/PR_DESCRIPTION.md
```

No pull request has been opened by the assistant: the workspace's GitHub
connection is disabled by the administrator. All results in this package come
from the supplied data; publishing the branch and opening the PR remain to do.
