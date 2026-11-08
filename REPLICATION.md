# Replicating the published version

"Trade in AI-Related Products" appeared in the Federal Reserve Bank of Minneapolis *Quarterly
Review* 46 (1), June 2026 (https://doi.org/10.21034/qr.4612). This note says what in the
repository is frozen, what "replicate" can mean for each layer of the work, and gives the
recipe and the expected result. The recipe was last run on 2026-11-08; section 5 reports what
it produced.

**Short version.** The typesetting replicates exactly. The analysis pipeline, run from the
tagged code on a data cut ending March 2026, reproduces every figure and every number in the
paper up to Census revisions of the trade history, which move the 2023 to 2025 values by about
one percent or less. The LLM classification of HS10 codes is a frozen input: it is not rerun,
and rerunning it would not give the same file.

---

## 1. What is frozen, and where

| Item | Where | Notes |
|---|---|---|
| Code, classification files, paper source and outputs as submitted | git tag `qr-published-2026-06` (commit `fa26454`) | The working tree matched the submitted source zip byte for byte when tagged |
| Pipeline-proof copy of the article | `paper/published/` | Typeset article `qr4612.pdf`, author PDF, `ai-trade.tex`, `figures/`, `tables/`, source zip. Nothing in this folder is ever written by the notebooks |
| Classification of HS10 codes | `data-input/hs10_classification_final_v3.csv` (imports), `data-input/hs10_classification_imports_exports.csv` (exports), `data-input/tariff-exemption-lists/` | Tracked in git, so present in every checkout |

The Census trade data (about 1.5 GB in six parquet files) is not in git. See section 3.

## 2. Three layers, three standards

| Layer | Inputs | Outputs | Reproducible? |
|---|---|---|---|
| Typesetting | `ai-trade.tex`, `tables/*.tex`, `figures/*`, bibliography | `ai-trade.pdf` | Exactly. Follow `paper/README-compile.txt` (pdflatex, bibtex, pdflatex twice) in `paper/published/` or in a checkout of the tag |
| Analysis pipeline | Six Census parquets, classification CSVs, exemption lists | `paper/figures/*`, `paper/tables/*.tex`, the macro file `paper/tables/ai-trade-results.tex` | Up to Census revisions. This document |
| Classification | Census HS10 code list, NAICS crosswalk, Claude (Sonnet) | The classification CSVs | No. The LLM's output varies run to run. Treat the CSVs as frozen inputs; the method is in `HS10_CLASSIFIER_DOCUMENTATION.md` |

Everything in the paper is therefore conditional on the committed classification. That is a
feature of the design, not an accident: the paper's claims are about trade in the products the
classification selected.

## 3. Why "up to revisions"

Census revises the whole monthly history with every release, and the published paper used the
vintage pulled on 2026-05-12, with data through March 2026. That vintage is not distributed
and is not fully preserved locally, so the practical standard is: take the current vintage,
truncate it at March 2026, and accept revision-sized differences. In the check of 2026-11-08
these were 0.1 to 1 percent on dollar totals and growth rates for 2023 to 2025, with larger
percentage moves only on small numbers (a 3 becoming a 2).

The repository's data comes from the author's canonical build of the Census API data
(`C:/heroku/trade-data`, see `code/00-refresh-data-input.py`). Anyone else needs the same six
files in the legacy schema documented in that script's docstring: imports with
`CTY_NAME, CON_VAL_MO, CAL_DUT_MO, I_COMMODITY, I_COMMODITY_SDESC, time, COMM_LVL, CTY_CODE`
and exports with `CTY_NAME, ALL_VAL_MO, E_COMMODITY, E_COMMODITY_SDESC, COMM_LVL, time,
CTY_CODE, export_type`, all columns strings and `time` as `YYYY-MM`.

## 4. Recipe

Requirements: Python 3.12 or later with pandas, pyarrow, matplotlib and jupyter (nbconvert);
a TeX distribution for the last step. The check in section 5 used Python 3.13.9, pandas 2.3.3,
pyarrow 21.0.0, matplotlib 3.10.6, nbconvert 7.16.6.

Commands are for Git Bash. In PowerShell, set the environment variable with
`$env:PYTHONUTF8 = '1'` and use `;` instead of `&&`.

```bash
# 1. Build a data cut ending March 2026 (about 2 minutes).
#    Writes data-input/replicate-2026-03/ (gitignored); data-input/ itself is untouched.
python code/00-refresh-data-input.py --through 2026-03

# 2. Check out the published code next to the repository, without disturbing the working tree.
git worktree add --detach ../ai-trade-published qr-published-2026-06

# 3. Give it the data. The classification CSVs are already there, since they are tracked.
cp data-input/replicate-2026-03/*.parquet ../ai-trade-published/data-input/

# 4. Run notebooks 06 to 11, in order. 06 creates the macro file, 07 to 11 append to it.
#    UTF-8 mode matters on Windows: the notebooks print non-ASCII characters.
#    (code/run-paper.ipynb does the same from inside Jupyter.)
export PYTHONUTF8=1
(cd ../ai-trade-published/code && \
 for nb in 06-section2-products 07-section2-growth 08-section2-countries \
           09-section2-tariffs 10-section3-exports 11-counterfactual; do
   jupyter nbconvert --to notebook --execute --inplace $nb.ipynb || break
 done)

# 5. Compare with the published outputs.
python code/compare-macros.py paper/published/tables/ai-trade-results.tex \
                              ../ai-trade-published/paper/tables/ai-trade-results.tex
python code/compare-figures.py paper/published/figures ../ai-trade-published/paper/figures ../figure-check

# 6. Typeset.
(cd ../ai-trade-published/paper && pdflatex ai-trade && bibtex ai-trade && pdflatex ai-trade && pdflatex ai-trade)

# 7. Clean up. The worktree is dirty (executed notebooks), hence --force.
git worktree remove --force ../ai-trade-published
```

Notes.

- Step 1 keeps the revisions carried by the current upstream build. `--out DIR` writes the cut
  somewhere else. The script refuses to overwrite files that already exist in the target.
- The tagged notebooks hard-code the x-axis end at March 2026, so they must be run on a cut
  ending at that month. Running them on a longer vintage clips the time-series charts.
- Notebook 10 looks for the domestic/re-export (`*-DF.parquet`) files in `data-input/` first;
  the cut includes them.
- Notebook 12 (robustness) is not part of the paper pipeline and reads earlier classification
  files that are not in the repository.
- The run takes about five minutes.

## 5. What to expect

Results of the check run on 2026-11-08, with a cut built from the upstream build of 2026-11-04
(data through September 2026, truncated at March 2026).

**Macros.** The published macro file has 100 macros. 72 came back identical. The other 28 moved
by revision-sized amounts:

| Macro | Published | Replicated | Macro | Published | Replicated |
|---|---|---|---|---|---|
| `highAiPctChange` | 73 | 72 | `cfActualDeficit` | 1,235 | 1,226 |
| `totalHighAiPctChange` | 73 | 72 | `cfCounterfactualDeficit` | 1,041 | 1,031 |
| `lowAiPctChange` | 3 | 2 | `cfExcessAiExports` | 71 | 70 |
| `lowAiTwentyFive` | 1881 | 1880 | `cfNetAiEffect` | 194 | 195 |
| `totalTradeTwentyFive` | 2884 | 2882 | `aiExportGrowth` | 34.5 | 34.7 |
| `totalTradeHsCodes` | 18,364 | 18,362 | `domesticAiExportGrowth` | 22.8 | 23.1 |
| `CoolingHVACTwentyFive` | 48 | 47 | `exemptionCEDollars` | 424 | 425 |
| `FireSafetySecurityPctChange` | 10 | 11 | `exemptionElectricalPowerPct` | 13.5 | 13.4 |
| `SpecialtyMaterialsPctChange` | 23 | 22 | `exemptionNetworkingTelecomPct` | 85.1 | 85.3 |
| `tariffCoolingHVACTwentyFour` | 3.0 | 3.1 | `exemptionSpecialtyMaterialsPct` | 60.8 | 60.9 |
| `tariffElectricalPowerTwentyFive` | 13.8 | 13.7 | `mexicoHighAiImportGrowthTwentyFiveVsTwentyFour` | 40.7 | 41.3 |
| `tariffLowTwentyFive` | 12.1 | 12.0 | `mexicoLowAiImportGrowthTwentyFiveVsTwentyFour` | -4.2 | -3.8 |
| `cfActualBalance` | -1235 | -1226 | `mexicoTotalImportGrowthTwentyFiveVsTwentyFour` | 6.4 | 6.8 |
| `cfCounterfactualBalance` | -1041 | -1031 | `canadaHighAiImportGrowthTwentyFiveVsTwentyFour` | -4.2 | -4.5 |

Anything outside this pattern (a macro that moves by more than a rounding step for no
revision-sized reason) is a bug or a changed definition, not a revision.

**Figures.** All thirteen PNG figures came back within one percent of pixels of the published
ones; the visible differences are value labels that moved by a revision (for example a bar
label reading 47 instead of 48).

**Tables.** The hierarchical trade tables and the exemption tables differ only in the same
revised values.

**The living code on the same cut.** Running the working-tree notebooks (HEAD) on the cut gives
the same 72 identical macros and the same 28 revision-sized moves, plus a few macros that
exist only in the living file. The numbers in the paper therefore replicate with the living
code at any date. The figures do not all replicate, by design: since the September 2026
refresh the country chart adds a bar for the partial current year and ranks countries on the
two most recent years, the three tariff charts add a bar for the latest month, the export
destinations by category chart uses the two most recent years, and the index charts size
their axes to the data. Five charts differ visibly for those reasons, three index charts
differ only in axis headroom, and the other five are within one percent of pixels. For the
published figures, use the tag.

## 6. Check the numbers, not just the pictures

Each notebook prints the values it writes to the macro file and the values it plots. Read
those printouts in the executed notebooks before trusting a figure. In one of four executions
of the tagged tariff notebook during the check, one chart rendered a country's bars at zero
while the data were present; the other three executions were correct and no cause was found.
A chart that looks wrong is a reason to rerun that notebook, and the printed values decide.

## 7. Replicating a refresh instead of the published version

Each refresh of the living version is tagged `refresh-YYYY-MM` and logged in `REFRESH-LOG.md`.
The same recipe applies with that tag in step 2 and that month in step 1. For the living
version, published-meaning macros keep their definitions across refreshes (`UPDATE-PLAN.md`,
section 6), so the paper's sentences stay true to what they describe; charts follow the data.

## 8. History of this check

- 2026-11-08. First run. Found that notebook 10 had, since the September redesign, computed
  the four Mexico category-share macros (`\mexicoComputeExportShare` and siblings) over the
  chart's rolling two-year window instead of the published 2024 to 2025 window, so the living
  version would have rewritten a published sentence with a differently defined number (33
  became 38 for Compute Hardware with no change in the data). Fixed the same day: the four
  macros are pinned to the published window and `...Latest` variants carry the rolling window.
  The `--through` option of the refresh script and the two `compare-*.py` tools were added for
  this check.
