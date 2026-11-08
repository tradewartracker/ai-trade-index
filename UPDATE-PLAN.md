# Keeping the analysis current when the data never stands still

How to think about, and run, an update of this project. Written 2026-09-14 after the
first post-publication refresh; see [REFRESH-LOG.md](REFRESH-LOG.md) for what each refresh did.

**Current state.** Published version frozen (`qr-published-2026-06`, `paper/published/`).
Working tree is the living version with Census data through July 2026. Paper prose and
`README.md` still describe the March 2026 vintage.

---

## 1. Four kinds of change, four different remedies

The data moves in four distinct ways. Treating them as one problem ("the numbers changed")
is what makes updates feel risky. Separated, each has a simple rule.

| Change | How often | What it does to the analysis | Remedy |
|---|---|---|---|
| **New months arrive** | Monthly, about five weeks after month end (FT900 release) | Extends every series; shifts "latest month" and, once a year, "latest full year" | Mechanical refresh (section 5). Code must derive dates from the data, never from literals. |
| **History is revised** | Every upstream build re-downloads all of 2013 onward | 2023 to 2025 values move by about 1% in either direction; 2026 months so far identical | Accept it. Stamp every output with its vintage. Never mix vintages within one document. Expect published numbers to drift by a point or two and say so when comparing. |
| **The product universe drifts** | Census adds and splits HS10 codes, visibly in Jan and Jul | New codes are unclassified, so the AI series undercounts. 2% of import value Feb to Jun 2026, 3.7% in Jul 2026 | Incremental classification of new codes only, triggered by a threshold (section 4). Never reclassify old codes in a routine refresh. |
| **Analysis anchors age** | Annually, or whenever a talk is given | "2025 as latest full year", "Dec 2025 tariff snapshot", "top five countries" all go stale | Make anchors explicit and role-based in one config cell; roll them deliberately, not by accident (section 3). |

A fifth thing drifts that is not data: **prose**. The paper text, `README.md`, and the
commented-out slides all carry hard-coded numbers. Section 6 treats these.

---

## 2. Three layers, kept apart

**Data vintages are immutable.** A vintage is identified by the last month it contains and
the upstream build date (`C:/heroku/trade-data/data/*/manifest.json`). `data-input/` holds
exactly one vintage. `00-refresh-data-input.py` stashes the previous one in
`data-input/vintage-<YYYY-MM>/` and refuses to overwrite a stash. Nothing edits a stash.

**Code is vintage-agnostic.** Notebooks read the vintage from the data: `last_month`,
`latest_full_year`, and the base year come from one place, and every chart window is a rule
applied to those, not a literal. Notebooks 07 to 10 already work this way after 2026-09-14;
06 and 11 still pin 2023 versus 2025 and are the next to convert.

**Outputs are stamped.** `\lastObsDate` already records the last month. Add `\dataVintage`
(upstream build date) and `\classificationVintage` (date of the classification files) to the
macro header written by notebook 06, and show them in a footnote on the living paper's title
page and in the deck footer. Every refresh gets a git tag `refresh-YYYY-MM`. Versions that are
circulated widely (a published article, a talk to a large audience) also get an on-disk copy,
as `paper/published/` does today.

---

## 3. Chart and table windows as rules

These are the conventions now encoded in the notebooks. Keep them, and apply them to any
new figure.

- **Monthly time series.** Start 2022-01, end at `last_month` plus 30 days. Y-limits from
  the data with the published limits as a floor, so nothing runs off the top again.
- **Bars by year.** 2023 through the current year. A partial year is labelled
  "YYYY (Jan-Mon)". Rankings (top five countries, top three per category) use the two most
  recent calendar years, so the current partial year counts.
- **Snapshot comparisons (tariffs).** Fixed anchors plus the latest month: 2024 as the
  pre-tariff full year, Dec 2025 as the end of the first tariff year, and `last_month`.
  Anchors are policy markers; add new ones deliberately (for instance a month after a
  regime change), do not roll them silently.
- **Two-year pooled windows.** The two most recent years, labelled with the end month
  when the second is partial ("2025-Jul 2026").
- **Base year 2023 = 100** stays until a deliberate rebase. Rebasing changes every index
  number in the paper and belongs with a new version, not a refresh.
- **Country universe.** Imports use the 30-country legacy list, exports the 31-entity list
  of the published paper. Upstream now carries 60 countries. Moving to 60 is a decision to
  take once, at an annual review, because it can change rankings.

---

## 4. Classification maintenance

This is the one drift with no automation yet, and it is the one that biases the headline
series. Rules:

1. **Measure every refresh.** Share of import and export value, by month, carried by codes
   absent from the classification files, plus the top unclassified codes by value.
   Today's ad hoc check should become `code/00b-check-unclassified.py`.
2. **Threshold.** Classify when unclassified value exceeds 1% of the total in the latest
   month, or when any single unclassified HS84 or HS85 code exceeds $0.5B a year. July 2026
   already trips both (lithium-ion batteries alone are $4.9B year to date).
3. **Incremental only.** A notebook that takes only the new codes, runs the same prompt as
   04 and 05, and appends rows with a `classified_on` column. Existing rows are never
   re-scored in a refresh, so the classification is a second, slowly growing vintage rather
   than a moving target. Re-scoring everything is a new paper version.
4. **Stopgap for splits.** A new code that is a split of a classified parent (same first
   eight digits) can inherit the parent's relevance and category, flagged as inherited.

---

## 5. The monthly procedure

Target: half an hour when nothing surprises. Data lands about five weeks after month end,
so August 2026 arrives in early October.

| Step | Command or action | Check |
|---|---|---|
| 0 | Upstream `trade-data` built and validated (already part of the heroku apps' FT900 runbook) | Both `manifest.json` files show the new `max_month` |
| 1 | `python code/00-refresh-data-input.py` | Prints row counts, last month, max duplicate key = 1; previous vintage stashed |
| 2 | Unclassified-code check (section 4) | Decide: classify now, or log the share and move on |
| 3 | Run `code/run-paper.ipynb` (notebooks 06 to 11) | All six exit cleanly; `ai-trade-results.tex` has no duplicate macro names |
| 4 | Diff `paper/tables/ai-trade-results.tex` against `git HEAD` | Latest-month macros should move; historical macros should move by about 1% or less. Anything larger is a revision worth a sentence in the log, or a bug |
| 5 | Look at the key figures | `ai-trade-index`, `ai-tariffs`, `ai-by-country`, `ai-exports-index`, `ai-exports-by-country-category`: nothing clipped, labels show the new month |
| 6 | Recompile the paper and any live deck, twice | Clean logs, page counts unchanged |
| 7 | Add an entry to `REFRESH-LOG.md`; commit `refresh: data through YYYY-MM`; tag `refresh-YYYY-MM` | |
| 8 | Prose (section 6) | Only when a claim has become false, or when circulating the document |

A talk-driven refresh is the same procedure, never a subset. Refreshing figures without the
log entry and tag is how a deck becomes irreproducible.

---

## 6. The two lives of the paper, and the prose problem

**Frozen:** the QR article. Never touched. Cite it.

**Living:** the working tree. The recommendation is to treat it as a maintained document
with a vintage footnote on the title page ("This version uses data through \lastObsDate;
the published version appeared in the Quarterly Review, June 2026"). Its text splits into
three tiers that need different handling:

1. **Macro-driven numbers** update themselves. Over time, replace year-named macros
   (`\aiShareTwentyFive`) with role-named ones (`\aiShareLatestFullYear`) and let the prose
   say "in \latestFullYear". Until then the year-named macros keep their published meaning,
   which is what today's tariff change preserved by adding a bar instead of replacing one.
2. **Anchored statements** ("in December 2025 the effective rate was...") stay true as
   written because their anchors are fixed. Add the latest month next to them rather than
   overwriting.
3. **Narrative claims** go stale silently: "Mexico and Taiwan each account for about a
   quarter", "China is among the top five sources", "AI imports have grown 73 percent since
   2023". Keep a short checklist of these claims, each paired with the macro or notebook
   printout that verifies it, and walk the list at step 8. Today, the China claim is already
   false in the 2026 data. The "73 percent since 2023" claim is a 2025-versus-2023 annual
   comparison and still holds for 2025, but the monthly index now sits 222 percent above
   its 2023 average, so any sentence that reads as "to date" needs the newer number.

`README.md` is the same problem in a different file, and it is the public face of the repo.
Either regenerate its tables from the macro file, or put a dated "numbers as of" banner at
the top and update it only at annual reviews.

---

## 7. Annual review (when December data lands, around early February)

- Roll `latest_full_year`; check every table and macro that compares 2023 with "the
  latest year".
- Decide whether to add a new snapshot anchor and whether Dec 2025 stays.
- Decide the country universe (30/31 versus 60).
- Consider a rebase only if a new paper version is planned.
- Re-score the classification if the incremental additions have grown large, and record
  the new `\classificationVintage`.
- Update `README.md` and `TECHNICAL-README.md` in one pass.

---

## 8. Things to build, in order

1. `run-paper.ipynb`: set `PYTHONUTF8=1` for the subprocesses, run the unclassified check
   first, print the macro diff at the end, and open a `REFRESH-LOG.md` stub.
2. `code/00b-check-unclassified.py` from today's ad hoc script.
3. The incremental classifier (04b/05b) with `classified_on`.
4. `\dataVintage` and `\classificationVintage` macros in notebook 06; vintage footnote in
   the paper and deck footers.
5. Convert notebooks 06 and 11 to role-based years; add role-named macros alongside the
   year-named ones.
6. The claims checklist for section 6, kept in this file.
7. `README.md` numbers regenerated or banner-dated.

---

## 9. Open decisions

- Is the living paper a maintained document, or does new data flow only to slides, README,
  and the tracker app? Recommendation: maintained, with the vintage footnote.
- Move both flows to the 60-country universe at the next annual review?
- Keep Dec 2025 as a permanent anchor, or roll to the latest December each year?
- Classify the 2026 codes now (about an hour, mostly API time) or wait for the incremental
  classifier?
