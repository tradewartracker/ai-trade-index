# Refresh log

One entry per data refresh, newest first. The procedure and the reasoning behind it
are in [UPDATE-PLAN.md](UPDATE-PLAN.md).

---

## 2026-09-14 | data through July 2026 | first refresh after publication

**Trigger.** Update the student-talk deck `slides/BEE-students/yale-som-ai-trade-slides.tex`.

**Data.** `C:/heroku/trade-data`, built 2026-09-03: imports and exports, HS10, 2013-01 to
2026-07, all seven build checks passing. Previous vintage in this repo ran through 2026-03
(May 2026 pull) and is stashed in `data-input/vintage-2026-03/`.

### What was done

1. **Published version frozen.** The working tree matched the submitted source zip byte for
   byte, so it was committed as `fa26454` and tagged `qr-published-2026-06`. A pipeline-proof
   copy lives in `paper/published/`.
2. **`data-input/` rebuilt.** Imports are a drop-in from trade-data's
   `data/products/tri-imports-hs10/` (TOTAL, 30 countries, EU, USMCA). Exports needed an
   adapter from the new schema to the legacy one, including the domestic/re-export split
   files. Both steps are now `code/00-refresh-data-input.py`. Checks: no duplicate
   (entity, month, HS10) keys; 2026 months identical to the old vintage; re-export splits
   identical to the old DF files to the dollar.
3. **Notebooks made vintage-aware** (07, 08, 09, 10): x-axis and y-axis limits follow the
   data; the country-share chart adds a bar for the partial current year and ranks countries
   on the two most recent years; the tariff charts add a third bar for the latest month
   (2024, Dec 2025, Jul 2026); the export country-by-category chart uses the two most recent
   years. Notebook 10 also lost a non-ASCII comment that only compiled under a UTF-8 shell.
4. **Pipeline run** 06 to 11 with nbconvert, macro file rebuilt (101 lines, no duplicates).
5. **Deck recompiled**: 8 pages, all six graphics resolved.

### Headline changes, published vintage to this one

| Quantity | Published (through Mar 2026) | This refresh (through Jul 2026) |
|---|---|---|
| AI-relevant import index, 2023 = 100 | 250 | 322 |
| Aggregate import index | 121 | 133 |
| Effective tariff, high AI relevance | 4.5% (Dec 2025) | 2.44% (Jul 2026) |
| Effective tariff, low AI relevance | 12.1% (Dec 2025) | 8.73% (Jul 2026) |
| Net AI effect on 2025 goods balance | $194B | $195B |
| Top import sources, share of high-AI imports | Mexico, Taiwan about 25% each (2025) | Taiwan 25.2%, Mexico 24.8%, Vietnam 11.3%, Thailand 9.7%, Korea 6.3% (Jan to Jul 2026) |

Census revisions carried by the full re-download move 2023 to 2025 values by roughly one
percent in either direction. Every 2026 month matches the old vintage exactly.

### Decisions taken

- Export country universe stays at the paper's 31 entities, although 60 are now available.
- Country rankings and two-year windows use the two most recent calendar years, with the
  current year partial and labelled as such.
- The tariff charts keep Dec 2025 as a fixed anchor and add the latest month, so the
  `*TwentyFive` tariff macros keep their published meaning.
- Paper prose and `README.md` were not touched. Both still describe the March 2026 vintage.

### Known gaps

- **Unclassified HS10 codes.** Codes introduced in 2026 are absent from both classification
  files. They carry 2.0% of import value in Feb to Jun 2026 and 3.7% ($11.9B, 400 codes) in
  Jul 2026; exports 1.0% in July. Largest AI-relevant misses: lithium-ion batteries
  (8507600090, 8507600030), heat-pump parts, PV frames, transistors, inverters. Skipped by
  choice this round. The AI High series is biased down accordingly.
- **Lost backup.** `data-input/vintage-2026-03/TOTALexports-combined.parquet` was overwritten
  by an empty stub during a failed build run and has no surviving copy. See the README in
  that folder. Published figures are unaffected.
- Refreshed outputs (figures, tables, macros, notebooks, data-output CSVs) were left
  uncommitted for review.

### Reproduce

```
python code/00-refresh-data-input.py
jupyter nbconvert --execute --inplace code/06-*.ipynb ... code/11-*.ipynb   (or run code/run-paper.ipynb)
cd slides/BEE-students && pdflatex yale-som-ai-trade-slides.tex && pdflatex yale-som-ai-trade-slides.tex
```
