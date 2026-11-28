# Final Report: submission checklist

Every requirement below comes from three sources, cited by these short names:

- **Brief:** the assignment brief, `project_ML_commskills_2026.pdf` on Blackboard.
- **Template:** the official BAM Project template (README and annotations).
- **Course:** Irene's Session 4 slides and the course announcements.

The last check before uploading goes through every line and records the proof, a command or a page number.

## Format and template

| # | Requirement | Source | How it is checked | Done |
|---|---|---|---|---|
| F1 | Official BAM Project template, unchanged `bam-project.cls` | Brief §2, §4; rubric "Writing and Formatting" | `bam-project.cls` matches the Overleaf copy of 18 Nov 2026, byte for byte | ☐ |
| F2 | Options `clean,twocolumn` | Brief §4 | first line of `main.tex` | ☐ |
| F3 | No placeholders, guidance boxes or illustrative examples | Brief §4; Template | `\FIELDdraftfalse` compiles without error; search the PDF for "Caption to write" and "words of text" | ☐ |
| F4 | 10–12 pages, excluding bibliography and appendices | Brief §4 | page where Works Cited starts, minus the cover page | ☐ |
| F5 | Abstract; Introduction with background and related work; Data; Methodology; Results and Discussion together; Conclusions and Future Work | Brief §4 | section list in the PDF | ☐ |
| F6 | No spelling, grammar or formatting errors | Rubric CS 10% | spell-check of every section file; read the PDF in full | ☐ |
| F7 | Every figure and table introduced, referenced and interpreted in the text; captions self-contained | Brief §3.4; Template | every `\label` has at least one `\ref`; read each caption alone | ☐ |
| F8 | Figures readable at 100% zoom, consistent style | Template; rubric CS "Visual Aids" 30% | figures made by `final_figures.py` at column width with 8 pt text | ☐ |
| F9 | Every equation introduced, all symbols defined | Template | read Section 3 | ☐ |

## Content (rubric)

| # | Requirement | Source | How it is checked | Done |
|---|---|---|---|---|
| C1 | Research question, motivation, objectives; each objective answered in a results subsection | Brief §4; Template | objectives O1–O6 in §1.3 each point to §4.x | ☐ |
| C2 | Data: sources, provenance, preparation, limitations, access and ethics | Brief §4 | §2 and Table 1 | ☐ |
| C3 | Methods justified; implementation and evaluation explained | Brief §3.2 | §3 | ☐ |
| C4 | **Idris: model, errors and tuning described** | ML feedback, outline | §3.6, Algorithm 1, Table 2, Figure 5, §4.2 | ☐ |
| C5 | **Idris: adjusted mark (mark minus field deviation) tried, and whether it makes access more equal** | ML feedback, progress report and outline | §3.7, Table 3, Figure 8, §4.5 | ☐ |
| C6 | **Idris: data easy to understand** | ML feedback, progress report | §2 with Table 1 (unit of observation row) | ☐ |
| C7 | **Idris: a real-life example of the deviation** | ML feedback, progress report | worked example in §4.5 | ☐ |
| C11 | **Irene: the introduction starts with students' backgrounds and degree choice, then moves to the fairness question** | CS feedback, outline | §1.1 and §1.2 in that order; Figure 1 interpreted in the text | ☐ |
| C12 | **Irene: first-person plural everywhere** | CS feedback, outline | search the section files for passive voice and for "the team"/"the authors"; outside the Declaration, "we" should be used | ☐ |
| C13 | **Irene: another level of detail** (each claim with specific evidence) | CS feedback, outline | every results paragraph has a number, a figure or table, or a citation | ☐ |
| C14 | **Irene: more literature than the outline's five references** | CS feedback, outline | count of works cited in the text (35 checked entries available) | ☐ |
| C15 | **Irene: graphs that help the reader** (background figure, map of the analysis) | CS feedback, outline | Figures 1 and 2 present, referenced and interpreted | ☐ |
| C16 | **Irene: computing setup stated** | CS feedback, outline | §3.10 and Appendix A (hardware, software, runtimes, seeds) | ☐ |
| C17 | **Irene: visuals interpreted, not only shown** | CS feedback, outline; Brief §3.4 | for each figure, a sentence in the text saying what to notice and what it means | ☐ || C8 | Model comparison, limitations, possible extensions | Brief §3.3, §4 | §4.2, §4.8, §5 | ☐ |
| C9 | Negative and uncertain results reported honestly | Template | the US interval includes 0; branch-level admission control is weak; boosting is at the edge of its grid | ☐ |
| C10 | Conclusions traceable to results; no new results in the Conclusions | Template | every number in §5 also appears in §4 | ☐ |

## Numbers

| # | Requirement | How it is checked | Done |
|---|---|---|---|
| N1 | Every number in the text matches `results/` | script: extract the numbers from the PDF and compare them with the JSON and CSV files; manual pass for the rest | ☐ |
| N2 | Same number, same rounding everywhere (abstract, results, conclusions) | search for each key number in the PDF | ☐ |
| N3 | Figure 7 (selection, 2015–2023, 664 university-years) vs Figure 8 (adjusted marks, 2016–2023, 595): the difference is explained | §4.5 | ☐ |

## References (MLA)

| # | Requirement | Source | How it is checked | Done |
|---|---|---|---|---|
| R1 | MLA style, in-text citations and Works Cited | Brief §4 | format of each entry | ☐ |
| R2 | Datasets, software, sources and prior work cited | Brief §4 ("failure to cite sources may result in a zero") | data in §2; libraries in the Appendix; methods in §3 | ☐ |
| R3 | Every Works Cited entry is cited in the text, and every in-text citation is in Works Cited | MLA | cross-check both lists | ☐ |
| R4 | Metadata checked | Template | done on 20 Nov 2026 against Crossref, JMLR, EU Publications Office and Kaggle; any new entry is checked the same way | ☐ |

## Repository and declaration

| # | Requirement | Source | How it is checked | Done |
|---|---|---|---|---|
| G1 | Link to the public GitHub repository in the report | Brief §4 | Appendix A and Declaration | ☐ |
| G2 | Meaningful history: each member commits their own sections | Brief §4, §5.1 | `git shortlog -sn` after the merges | ☐ |
| G3 | Reproducible: README run order, seeds, versions | Brief §3.2; Template | fresh clone, run the scripts, compare `results/` (`git status` clean) | ☐ |
| G4 | Final commit hash written in Appendix A | Template | `git rev-parse --short HEAD` after the last merge | ☐ |
| D1 | Declaration of Contributions: teamwork and one entry per member | Brief §4; Template | §Declaration | ☐ |
| D3 | Every member can explain the whole report and code | Brief §4, §5.1 | read-through on Tuesday 24 Nov | ☐ |

## Submission

| # | Requirement | Done |
|---|---|---|
| S1 | PDF uploaded to Communication Skills (Turnitin) **on 30 Nov, before the closing time shown on Blackboard**; receipt saved | ☐ |
| S2 | Same PDF uploaded to Machine Learning, "Final Report ML+CS" (**one attempt only**) before its closing time | ☐ |
| S3 | Uploaded PDF has the same hash as `reports/final_report/main.pdf` on `main` | ☐ |
