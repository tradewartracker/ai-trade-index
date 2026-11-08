# Technical Documentation

This document describes the repository structure, data pipeline, and how to reproduce the analysis in "Trade in AI-Related Products."

## Requirements

- Python 3.12+
- Key packages: `pandas`, `pyarrow`, `matplotlib`, `anthropic`, `bokeh`
- Anthropic API key (for LLM classification notebooks only)

## Repository Structure

```
ai-trade-index/
│
├── data-input/                        # Raw data and classification files
│   ├── TOTALdata-current.parquet      # U.S. imports (all countries aggregated)
│   ├── ALL-data-current.parquet       # U.S. imports by country
│   ├── TOTALexports-combined.parquet  # U.S. exports (aggregated)
│   ├── All-country-exports.parquet    # U.S. exports by country
│   ├── hs10_classification_final_v3.csv  # LLM classification (active)
│   ├── hs10_classification_imports_exports.csv  # Combined import/export classification
│   ├── unique_hs10_naics_descriptions.csv       # HS10-NAICS crosswalk
│   ├── unique_hs10_commodities.csv              # Import HS10 codes
│   ├── unique_hs10_export_commodities.csv       # Export HS10 codes
│   └── tariff-exemption-lists/        # Tariff exemption CSVs
│
├── data-output/                       # Exported analysis data
│   └── ai_trade_index_series.csv      # Monthly index series (2023=100)
│
├── paper/                             # LaTeX paper and outputs
│   ├── ai-trade.tex                   # Main paper source
│   ├── tables/                        # Generated LaTeX tables
│   │   ├── ai-trade-results.tex       # LaTeX macros with key numbers
│   │   ├── trade_hierarchical.tex     # Import breakdown by category
│   │   ├── trade_hierarchical_exports.tex
│   │   ├── counterfactual_summary.tex
│   │   └── ...
│   └── figures/                       # Generated figures (PNG + PDF)
│
├── code/                              # Notebooks and classifier modules
│   ├── 01-make-hs10-list.ipynb        # Extract unique HS10 codes
│   ├── 02-make-naics-descriptions.ipynb
│   ├── 03-make-imports-dataset.ipynb
│   ├── 04-classify-imports.ipynb      # LLM classification (requires API key)
│   ├── 05-classify-exports.ipynb
│   ├── 06-section2-products.ipynb     # Analysis notebooks (06-12)
│   ├── 07-section2-growth.ipynb
│   ├── 08-section2-countries.ipynb
│   ├── 09-section2-tariffs.ipynb
│   ├── 10-section3-exports.ipynb
│   ├── 11-counterfactual.ipynb
│   ├── 12-robustness.ipynb
│   ├── hs10_llm_classifier_naics.py   # LLM classifier module (with NAICS context)
│   ├── hs10_llm_classifier_demo.py    # LLM classifier module (basic)
│   └── hs10_datacenter_classifier.py  # Rule-based classifier (legacy)
│
├── README.md                          # Results walkthrough with figures and tables
├── HS10_CLASSIFIER_DOCUMENTATION.md   # LLM classification methodology
├── AI_TRADE_HIGH_RELEVANCE_PRODUCTS.md # Full listing of high-relevance products
│
├── archive/                           # Earlier notebook versions
└── related-papers/                    # Reference literature
```

## Notebook Pipeline

All notebooks live in the `code/` folder and are numbered to run in order. Notebooks 01-05 build the data; 06-12 produce the analysis.

| Notebook | Purpose | Key Outputs |
|---|---|---|
| **01-make-hs10-list** | Extract unique HS10 codes from Census import data | `unique_hs10_commodities.csv` |
| **02-make-naics-descriptions** | Build HS10-to-NAICS crosswalk for classifier context | `unique_hs10_naics_descriptions.csv` |
| **03-make-imports-dataset** | Assemble monthly import parquet files from Census API | `TOTALdata-current.parquet`, `ALL-data-current.parquet` |
| **04-classify-imports** | LLM classification of import HS10 codes (requires API key) | `hs10_classification_final_v3.csv` |
| **05-classify-exports** | LLM classification of export HS10 codes (requires API key) | `hs10_classification_exports_final.csv` |
| **06-section2-products** | Product classification tables and top-10 lists | `trade_hierarchical.tex`, `top10_*.tex` |
| **07-section2-growth** | Import growth index and AI trade share | `ai-trade-index.png`, `ai-trade-share.png`, `ai_trade_index_series.csv` |
| **08-section2-countries** | Country-level import analysis | `ai-by-country.png`, `ai-by-country-category.png` |
| **09-section2-tariffs** | Tariff comparison and exemption analysis | `ai-tariffs.png`, exemption tables |
| **10-section3-exports** | Export-side analysis | `ai-exports-index.png`, `ai-exports-share.png` |
| **11-counterfactual** | Counterfactual trade balance exercise | `counterfactual-balance.png`, `counterfactual_summary.tex` |
| **12-robustness** | Robustness checks | Additional tables |

## LLM Classification

The classifier uses Claude (Sonnet) to evaluate each HS10 commodity code's relevance to AI data center infrastructure. Each code receives:

- **Relevance**: High, Medium, or Low
- **Category**: Compute Hardware, Electrical Power, Networking Telecom, Cooling HVAC, Building Structure, Fire Safety Security, Specialty Materials, or Not DC Related
- **Confidence**: 0-100%

The active classification file is `data-input/hs10_classification_final_v3.csv` with 19,424 codes (655 High, 2,582 Medium, 16,187 Low).

Full methodology: [HS10_CLASSIFIER_DOCUMENTATION.md](HS10_CLASSIFIER_DOCUMENTATION.md)

## Running the Analysis

Refreshing the trade data is a separate, scripted step: `python code/00-refresh-data-input.py` pulls the current vintage from the canonical `C:/heroku/trade-data` repo into `data-input/` and stashes the previous one. Every refresh is logged in [REFRESH-LOG.md](REFRESH-LOG.md); the procedure and the rules for chart windows, anchors, and classification upkeep are in [UPDATE-PLAN.md](UPDATE-PLAN.md).

**Reproduce from existing classifications (no API key needed):**

```bash
# Run notebooks 06-12 in the code/ folder
# Each notebook reads from ../data-input/ and writes to ../paper/tables/ and ../paper/figures/
```

**Reproduce from scratch (requires Anthropic API key):**

```bash
# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run notebooks 01-12 in the code/ folder
# Notebooks 04-05 will call the Claude API (~$150 total, several hours)
```

## Data Sources

- **U.S. Census Bureau**: International Trade data via API (`api.census.gov/data/timeseries/intltrade/imports/`)
- **Tariff exemption lists**: Executive Order 14257 (Consumer Electronics, Annex II) and Section 122 Surcharge
- Trade data covers monthly flows from January 2013 through the month recorded in REFRESH-LOG.md (July 2026 as of 2026-09-14)

## HS2 Exclusions

The following HS2 categories are excluded from the analysis due to price volatility or special treatment:

- 27: Mineral fuels, oils (oil price swings)
- 71: Precious metals and stones
- 98-99: Special classification provisions
