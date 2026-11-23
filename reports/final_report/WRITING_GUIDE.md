# Final Report: writing guide

Due on Wednesday 25 November 2026. Upload to both courses:

- Communication Skills, Turnitin: closes at 23:39.
- Machine Learning, "Final Report ML+CS": closes at 23:59, one attempt only.

**Your sections are due on Monday 23 November at 22:00**, merged through a pull request. On Tuesday morning Ignacio integrates them and checks every number. On Tuesday evening we all read the whole report and approve it.

## Feedback we must answer

Both instructors commented on the Sentence Outline. Idris gave 8/10; most groups got 9.5 to 10. Each point below has a place in the report, and the guide boxes in those places say what to do.

| Feedback | Where it is answered |
|---|---|
| Irene: begin with how students' backgrounds shape their choice of degree, then explain why GPA comparisons across fields raise a fairness question | §1.1 with Figure 1 (background by degree), then §1.2 |
| Irene: use the first-person plural consistently | everywhere: "we estimated", "we find", never "the team" or "it was estimated" |
| Irene: add another level of detail | every claim backed by a specific number, figure or source in the same paragraph (the guides list them) |
| Irene: expand the literature beyond five references | 35 checked references in `90_works_cited.tex`; cite those marked for your section |
| Irene: use graphs to help readers understand the analysis | Figure 1 (background), Figure 2 (map of the analysis), and eight result figures (Figures 3–10) |
| Irene: state the computing setup | §3.10 and Appendix A |
| Irene: interpret the visuals | each figure gets a paragraph saying what to notice, the key number, and what it means |
| Idris: what the model is, its errors and its tuning | §3.6, Algorithm 1, Table 2, Figure 5, §4.2 |
| Idris: try his adjusted mark and see if it makes access more equal | §3.7, §4.5, Table 3, Figure 8 |
| Idris (Progress Report): data hard to understand; give a real-life example | §2 with Table 1; worked example in §4.5 |

Figure and table numbers are those of the current draft. LaTeX renumbers them automatically, so always use `\ref`.

## Who writes what

Open `main.tex` to see the order. Each file in `sections/` belongs to one person. Edit only your own files. If you find a problem in someone else's file, tell them.

The work was rebalanced on 22 November so that each of us writes a similar amount: Ignacio about 2,750 words, Pablo 2,320 and Adam 2,090. Ignacio also integrates the report and checks every number.

| File | Section | Writer | Words |
|---|---|---|---|
| `00_abstract.tex` (write it last) | Abstract | Ignacio | 240 |
| `01a_intro_background.tex`, Figure 1 caption | 1.1 Backgrounds and degree choice | Ignacio | 280 |
| `01b_intro_fairness.tex` | 1.2 The fairness question | **Adam** | 300 |
| `01c_intro_objectives.tex` | 1.3 Question and objectives | Ignacio | 230 |
| `02_data.tex`, Table 1 caption | 2 Data (Spain, Portugal) | Pablo | 480 |
| `02b_data_us.tex` | 2.3 US data | Adam | 170 |
| `03a_methods_core.tex`, Figure 2 caption (`tables/fig_overview.tex`) | 3.1–3.5 Methodology | Pablo | 1,000 |
| `03b_methods_prediction_selection.tex` | 3.6–3.8 Models, adjusted marks, ranking rules | Ignacio | 690 |
| `03c_methods_us.tex` | 3.9 US replication design | Adam | 230 |
| `03d_methods_computing.tex` | 3.10 Computing setup | **Adam** | 80 |
| `04a_results_field_effects.tex` | 4.1 Field effects | Ignacio | 290 |
| `04b_results_mixed_model.tex` | 4.1 Mixed-model paragraph | Pablo | 170 |
| `04c_results_prediction.tex`, Table 2 caption | 4.2 Prediction and tuning | Ignacio | 460 |
| `04d_results_confounders.tex` | 4.3 Intake, size, dropout | **Pablo** | 270 |
| `04e_results_selection.tex` | 4.4 Selection | **Pablo** | 150 |
| `04f_results_normal_check.tex` | 4.4 Normal-approximation checks | Pablo | 180 |
| `04g_results_adjusted_marks.tex`, Table 3 caption | 4.5 Adjusted marks | Ignacio | 320 |
| `04h_results_ranking_rules.tex` | 4.6 Ranking rules | **Adam** | 310 |
| `04i_results_us.tex` | 4.7 US replication | Adam | 330 |
| `04j_results_limitations.tex` | 4.8 Limitations | **Adam** | 200 |
| `05_conclusions.tex` | 5 Conclusions and Future Work | **Adam** | 300 |
| `90_works_cited.tex` (add only checked entries) | Works Cited | Ignacio | - |
| `91_declaration_team.tex` | Declaration: teamwork | Ignacio | 120 |
| `92_declaration_adam.tex` | Declaration: Adam | Adam | 70 |
| `93_declaration_pablo.tex` | Declaration: Pablo | Pablo | 70 |
| `94_declaration_ignacio.tex` | Declaration: Ignacio | Ignacio | 80 |
| `99_appendix_reproducibility.tex`, Tables 4–5 captions | Appendix A | **Adam** | 100 |

Sections in **bold** changed writer on 22 November.
The word counts are what fits in 10–12 pages, which the brief requires excluding the bibliography and appendices. Stay within about 10% of your number. The grey boxes in the PDF show this space.
## How to work

1. Update and create your branch:
   ```bash
   git checkout main
   git pull
   git checkout -b adam/report-us        # or pablo/report-data-methods
   ```
2. Open your files. Each paragraph has a blue `\guide{...}{...}` box that says:
   - what the paragraph must establish;
   - which outline sentence it develops;
   - the numbers, and which file in `results/` they come from.

   Below each guide is a grey `\budget{words}{name}` box that marks the space.
3. Write the paragraph in your own words, replacing the `\guide` and `\budget` lines. Write the captions marked `\capguide{...}` in your figures and tables.
4. Compile. Use one of the two options below.
5. Commit, push, and open a PR to `main` with Ignacio as reviewer:
   ```bash
   git add reports/final_report/sections/<your files>
   git commit -m "Final report: <your section>"
   git push -u origin <your branch>
   ```
   Commit more than once as you go; the brief values a real history of changes.

### Compiling

- **Overleaf:** the whole repository is too large to upload (about 150 MB).
  1. Run `python reports/final_report/make_overleaf_zip.py`. It writes `reports/final_report/final_report_overleaf.zip`, under 1 MB, with the report and the figures at the right paths.
  2. In Overleaf, choose New Project → Upload Project and upload that zip.
  3. Open Menu, and set Main document to `reports/final_report/main.tex`.
  4. Compiler: pdfLaTeX.

  Copy your text back into the repository files when you are done; Overleaf is not linked to GitHub.
- **Locally:** run `latexmk -pdf main.tex` inside `reports/final_report/`, or use any LaTeX installation.

The figures are read from `figures/final/`, so keep the folder structure.

## Rules (from the brief and the template)

- **Use the exact numbers in the guides.** They were checked against `results/`. If you use a number that is not in a guide, take it from the file in `results/` and tell Ignacio, so the whole report stays consistent.
- **Define every symbol** of an equation in the text. Keep the notation in the equations; change it only after talking to the others.
- **Introduce every figure and table in the text** (`Figure~\ref{fig:us}`) and say what the reader should see in it. A caption alone is not enough.
  - Captions must stand on their own: what is shown, the data, the units, the uncertainty, and the source.
  - `figures/final/CAPTIONS.md` lists what each caption must say.
- **Cite in MLA, in the text:** `(Achen and Courant)`, `(Jeong et al.)`, `(Realinho et al.)`, `(Ministerio de Ciencia, Innovación y Universidades, "Media")`. Add a page number when you point to a specific statement. Every source must be in `90_works_cited.tex`. Do not add an entry you have not checked.
- **Style:**
  - Use British spelling, as in the outline: *standardised*, *analyse*.
  - Use "we" for everything the team did, in every section (Irene asked for the first-person plural consistently). Write "we estimated", not "it was estimated" or "the model was fitted".
  - Use the past tense for what we did and the present tense for what the results show.
  - Spell out an abbreviation the first time you use it.
- **Do not overclaim.** These are associations from aggregated data, not causes. Do not say a field is "harder" or "easier"; say it grades higher or lower.
- Before the final version, `\FIELDdraftfalse` in `main.tex` makes compilation stop if any guide, budget or caption placeholder is left.
