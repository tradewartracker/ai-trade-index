"""
Generates three notebooks for the domestic/re-export pilot:
  1. ../us-exports-hs10/make-exports-hs10-DF-dataset.ipynb
  2. ../us-exports-hs10/combine-exports-hs10-DF-dataset.ipynb
  3. ./13-section3-reexports.ipynb

Run from c:\\github\\ai-trade-index\\code\\
"""
import json
import os

REPO = r"c:\github\ai-trade-index"
EXPORTS_REPO = r"c:\heroku\us-exports-hs10"


def nb(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def code(src):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src.splitlines(keepends=True)}


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}


# ============================================================
# Notebook 1: make-exports-hs10-DF-dataset.ipynb
# ============================================================
make_nb = nb([
    md("""# Pilot: Export HS10 data with Domestic/Foreign (DF) breakout

Downloads U.S. exports HS10 data with the `DF` parameter so we can split each (country, month, HS10) into:
- Total exports (DF=-)
- Domestic exports (DF=1)
- Re-exports / foreign exports (DF=2)

Pilot scope: **2022-01 through 2026-03** (~51 months). Top 31 destinations + Canada (0003 = EU code reused as misc) + USMCA (0020).

Output: `data/exports-hs10-DF/{country_label}data-{YYYY-MM}.parquet` with columns `CTY_NAME`, `export_type`, `ALL_VAL_MO`, `E_COMMODITY`, `E_COMMODITY_SDESC`, `time`, `COMM_LVL`.

Sister to `make-exports-hs10-dataset.ipynb` — same retry logic, same country list.
"""),
    code("""import pandas as pd
import datetime as dt
import numpy as np
import time
import requests
import os
import pyarrow as pa
import pyarrow.parquet as pq
from requests.exceptions import ConnectTimeout, ReadTimeout, RequestException
"""),
    code("""# Pilot date range
start_date = "2022-01"
end_date   = "2026-03"

my_key = "&key=34e40301bda77077e24c859c6c6c0b721ad73fc7"
"""),
    code("""# Build country list — same as existing pipeline (top 31 by total exports)
end_use = "naics?get=ALL_VAL_MO,CTY_CODE,CTY_NAME,SUMMARY_LVL"
url = "https://api.census.gov/data/timeseries/intltrade/exports/" + end_use + my_key + "&time==from+2013-01"
r = requests.get(url)
print(r)

df = pd.DataFrame(r.json()[1:])
df.columns = r.json()[0]
df["total_exports"] = df["ALL_VAL_MO"].astype(float)
df = df[df.SUMMARY_LVL == "DET"]

top_products = df.groupby("CTY_NAME").agg({"total_exports": "sum", "CTY_CODE": "first"})
country_list = list(top_products.sort_values("total_exports", ascending=False).CTY_CODE)[0:31]
country_list[0] = ""              # blank = TOTAL FOR ALL COUNTRIES
country_list.extend(["0003", "0020"])  # EU, USMCA

print(f"Countries: {len(country_list)}")
"""),
    code("""# Build month list from start_date to end_date inclusive
start = dt.datetime.strptime(start_date, "%Y-%m").date()
end   = dt.datetime.strptime(end_date, "%Y-%m").date()

month_list = []
cur = start
while cur <= end:
    month_list.append(cur.strftime("%Y-%m"))
    if cur.month == 12:
        cur = dt.date(cur.year + 1, 1, 1)
    else:
        cur = dt.date(cur.year, cur.month + 1, 1)

print(f"Months: {month_list[0]} to {month_list[-1]} ({len(month_list)} months)")
print(f"Total files to download: {len(month_list) * len(country_list)}")
"""),
    code("""# Download per (country, month). Skips files that already exist.
end_use = "hs?get=CTY_NAME,DF,ALL_VAL_MO,E_COMMODITY,E_COMMODITY_SDESC"
surl = "https://api.census.gov/data/timeseries/intltrade/exports/" + end_use + my_key + "&COMM_LVL=HS10"

data_dir = ".\\\\data\\\\exports-hs10-DF"
os.makedirs(data_dir, exist_ok=True)

DF_MAP = {"-": "Total Exports", "1": "Domestic Exports", "2": "Re-Exports"}

for xxx in country_list:
    country_label = "TOTAL" if xxx == "" else xxx

    for month in month_list:
        out_file = os.path.join(data_dir, f"{country_label}data-{month}.parquet")
        if os.path.exists(out_file):
            continue

        print(f"Downloading {country_label} for {month}")

        url = surl + "&time=" + month
        if xxx != "":
            url = url + "&CTY_CODE=" + xxx

        max_retries = 5
        retry_count = 0
        r = None

        while retry_count < max_retries:
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    break
                else:
                    print(f"  status {r.status_code}, waiting 30s...")
                    time.sleep(30)
                    retry_count += 1
            except (ConnectTimeout, ReadTimeout) as e:
                retry_count += 1
                wait_time = 30 * (2 ** (retry_count - 1))
                print(f"  timeout attempt {retry_count}/{max_retries}; waiting {wait_time}s")
                if retry_count < max_retries:
                    time.sleep(wait_time)
            except RequestException as e:
                print(f"  request error: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(30)

        if r is None or r.status_code != 200:
            print(f"  FAILED {country_label} {month} after {max_retries} attempts")
            continue

        try:
            data = r.json()
            if len(data) < 2:
                print(f"  no data {country_label} {month}")
                continue

            foo = pd.DataFrame(data[1:])
            foo.columns = data[0]

            # Rename DF column values to readable labels
            foo["export_type"] = foo["DF"].map(DF_MAP)
            unmapped = foo["DF"][foo["export_type"].isna()].unique()
            if len(unmapped) > 0:
                print(f"  WARNING unexpected DF values: {unmapped}")
            foo = foo.drop(columns=["DF"])

            pq.write_table(pa.Table.from_pandas(foo), out_file)
        except Exception as e:
            print(f"  error processing {country_label} {month}: {e}")

print("Done!")
"""),
    code("""# Quick sanity-check: read one file and verify the three DF rows are present
sample = pq.read_table(os.path.join(data_dir, f"TOTALdata-{month_list[-1]}.parquet")).to_pandas()
print(f"Sample rows for {month_list[-1]} TOTAL: {len(sample):,}")
print(f"export_type values: {sample['export_type'].value_counts().to_dict()}")
print()
sample.head(6)
"""),
])


# ============================================================
# Notebook 2: combine-exports-hs10-DF-dataset.ipynb
# ============================================================
combine_nb = nb([
    md("""# Combine pilot DF export files

Combines the per-(country, month) parquets from `data/exports-hs10-DF/` into:
- `{country_label}data-combined.parquet` — per-country, all months
- `All-country-exports-DF.parquet` — all individual countries (excludes TOTAL and USMCA)
- `TOTALexports-combined-DF.parquet` — TOTAL FOR ALL COUNTRIES only

Sister to `combine-exports-hs10-dataset.ipynb` but built for the from-scratch pilot. Also includes a sanity check that `Domestic Exports + Re-Exports == Total Exports` for each (country, month, HS10).
"""),
    code("""import pandas as pd
import numpy as np
import os
import glob
import requests
import pyarrow as pa
import pyarrow.parquet as pq
"""),
    code("""my_key = "&key=34e40301bda77077e24c859c6c6c0b721ad73fc7"

end_use = "naics?get=ALL_VAL_MO,CTY_CODE,CTY_NAME,SUMMARY_LVL"
url = "https://api.census.gov/data/timeseries/intltrade/exports/" + end_use + my_key + "&time==from+2013-01"
r = requests.get(url)

df = pd.DataFrame(r.json()[1:])
df.columns = r.json()[0]
df["total_exports"] = df["ALL_VAL_MO"].astype(float)
df = df[df.SUMMARY_LVL == "DET"]

top_products = df.groupby("CTY_NAME").agg({"total_exports": "sum", "CTY_CODE": "first"})
country_list = list(top_products.sort_values("total_exports", ascending=False).CTY_CODE)[0:31]
country_list[0] = ""
country_list.extend(["0003", "0020"])
"""),
    code("""# Step 1 — Combine all monthly files into per-country combined files
data_dir = ".\\\\data\\\\exports-hs10-DF"

for xxx in country_list:
    country_label = "TOTAL" if xxx == "" else xxx

    pattern = os.path.join(data_dir, f"{country_label}data-*.parquet")
    monthly_files = sorted(glob.glob(pattern))

    # Exclude any existing combined file from the input list
    monthly_files = [f for f in monthly_files if "combined" not in os.path.basename(f)]

    if not monthly_files:
        print(f"No files for {country_label}, skipping...")
        continue

    dfs = []
    for f in monthly_files:
        try:
            dfs.append(pq.read_table(f).to_pandas())
        except Exception as e:
            print(f"  Error reading {f}: {e}")

    if not dfs:
        continue

    combined = pd.concat(dfs, ignore_index=True)
    out_file = os.path.join(data_dir, f"{country_label}data-combined.parquet")
    pq.write_table(pa.Table.from_pandas(combined), out_file)
    print(f"{country_label}: {len(combined):,} rows over {len(monthly_files)} months")

print("\\nDone combining per-country files.")
"""),
    code("""# Step 2 — Stack all individual-country files into All-country-exports-DF.parquet
# Excludes TOTAL and USMCA (0020) since those are aggregates (EU is 0003 and is included)
exclude_labels = {"TOTAL", "0020"}

all_combined = sorted(glob.glob(os.path.join(data_dir, "*data-combined.parquet")))
country_files = [
    f for f in all_combined
    if not any(os.path.basename(f).startswith(lbl + "data-") for lbl in exclude_labels)
    and os.path.basename(f) != "All-country-exports-DF.parquet"
]

print(f"Stacking {len(country_files)} country files...")

dfs = []
for f in country_files:
    try:
        dfs.append(pq.read_table(f).to_pandas())
    except Exception as e:
        print(f"  Error reading {f}: {e}")

if dfs:
    all_countries = pd.concat(dfs, ignore_index=True)
    out_path = os.path.join(data_dir, "All-country-exports-DF.parquet")
    pq.write_table(pa.Table.from_pandas(all_countries), out_path)
    print(f"Saved {len(all_countries):,} rows to {out_path}")
"""),
    code("""# Step 3 — TOTALexports-combined-DF.parquet (TOTAL FOR ALL COUNTRIES only)
total_in  = os.path.join(data_dir, "TOTALdata-combined.parquet")
total_out = os.path.join(data_dir, "TOTALexports-combined-DF.parquet")

if os.path.exists(total_in):
    tdf = pq.read_table(total_in).to_pandas()
    pq.write_table(pa.Table.from_pandas(tdf), total_out)
    print(f"Saved {len(tdf):,} rows to {total_out}")
"""),
    code("""# Step 4 — Sanity check: Domestic + Re-Export should equal Total for each (country, month, HS10)
all_df = pq.read_table(os.path.join(data_dir, "All-country-exports-DF.parquet")).to_pandas()
all_df["ALL_VAL_MO"] = all_df["ALL_VAL_MO"].astype(float)

wide = all_df.pivot_table(
    index=["CTY_NAME", "time", "E_COMMODITY"],
    columns="export_type",
    values="ALL_VAL_MO",
    aggfunc="sum",
)

# Where all three are present, check
mask = wide[["Total Exports", "Domestic Exports", "Re-Exports"]].notna().all(axis=1)
checkable = wide[mask].copy()
checkable["sum_components"] = checkable["Domestic Exports"] + checkable["Re-Exports"]
checkable["diff"] = checkable["Total Exports"] - checkable["sum_components"]
checkable["rel_err"] = checkable["diff"].abs() / checkable["Total Exports"].replace(0, np.nan)

print(f"Rows with all three DF values: {len(checkable):,}")
print(f"Max absolute diff: ${checkable['diff'].abs().max():,.2f}")
print(f"Max relative error: {checkable['rel_err'].max():.4%}")
print(f"Rows with rel error > 0.01: {(checkable['rel_err'] > 0.01).sum():,}")

# Display worst offenders
print("\\nTop 10 by absolute diff:")
print(checkable.sort_values("diff", key=abs, ascending=False).head(10))
"""),
])


# ============================================================
# Notebook 3: 13-section3-reexports.ipynb
# ============================================================
explore_nb = nb([
    md("""# Section 3 Pilot — Domestic vs. Re-Export Decomposition

Question: how much of U.S. AI-related exports are genuinely U.S.-produced (domestic exports) versus simply imported and re-exported (foreign / re-exports)?

The paper currently hypothesizes (§3 last paragraph) that AI-related products are being imported into the U.S. and re-exported to Mexico. This notebook is the first direct test of that hypothesis.

Inputs:
- `All-country-exports-DF.parquet` from the `us-exports-hs10` repo's `data/exports-hs10-DF/` folder (currently `c:\\heroku\\us-exports-hs10\\`; the path cell below resolves it)
- `TOTALexports-combined-DF.parquet` (same folder)
- `data-input/hs10_classification_imports_exports.csv` for AI classification

Outputs: figures + tables (saved to `paper/figures/` and printed) covering:
1. Overall domestic vs re-export shares (totals)
2. AI-related vs non-AI domestic/re-export split
3. By AI product category (Compute Hardware, Electrical Power, etc.)
4. By destination country (Mexico, Canada, China, etc.)
5. Time trend 2022-2026

**Pilot only** — no paper-output writes (no LaTeX macros, no `paper/tables/` updates).
"""),
    code("""import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
"""),
    code("""# Paths — the DF parquets live in the sister us-exports-hs10 repo, which has
# moved between drives. Take the first location that actually has the files.
DF_DIR_CANDIDATES = [
    '../data-input',                                    # local copy, if one is ever made
    r"c:\\heroku\\us-exports-hs10\\data\\exports-hs10-DF",  # current location
    r"..\\..\\us-exports-hs10\\data\\exports-hs10-DF",      # old c:\\github location
]

DF_DATA_DIR = next((p for p in DF_DIR_CANDIDATES
                    if os.path.exists(os.path.join(p, "TOTALexports-combined-DF.parquet"))), None)

if DF_DATA_DIR is None:
    raise FileNotFoundError(
        "TOTALexports-combined-DF.parquet not found in any of: "
        + ", ".join(DF_DIR_CANDIDATES))

ALL_FILE   = os.path.join(DF_DATA_DIR, "All-country-exports-DF.parquet")
TOTAL_FILE = os.path.join(DF_DATA_DIR, "TOTALexports-combined-DF.parquet")
CLASS_FILE = "../data-input/hs10_classification_imports_exports.csv"

assert os.path.exists(ALL_FILE),   f"missing: {ALL_FILE}"
assert os.path.exists(TOTAL_FILE), f"missing: {TOTAL_FILE}"

print("DF data directory:", DF_DATA_DIR)
"""),
    code("""# Load TOTAL series for the headline split
tot = pd.read_parquet(TOTAL_FILE)
tot["ALL_VAL_MO"] = tot["ALL_VAL_MO"].astype(float)
tot["E_COMMODITY"] = tot["E_COMMODITY"].astype(str).str.zfill(10)
tot["HS10"] = tot["E_COMMODITY"].astype("int64")
tot["HS2"]  = tot["E_COMMODITY"].str[:2]
tot["time"] = pd.to_datetime(tot["time"], format="%Y-%m")
tot = tot[~tot["HS2"].isin(["27","71","98","99"])]

# Load classification
mat = pd.read_csv(CLASS_FILE)
mat = mat.rename(columns={"hs10_code":"HS10"})
tot = tot.merge(mat[["HS10","relevance","primary_category"]], on="HS10", how="left")

# Filter to pilot range only
tot = tot[tot["time"] >= "2022-01-01"]
print(f"TOTAL rows after filter: {len(tot):,}")
print(f"Date range: {tot['time'].min().date()} to {tot['time'].max().date()}")
print(f"export_type breakdown:")
print(tot["export_type"].value_counts())
"""),
    md("## 1. Headline: domestic vs re-export shares (TOTAL, all products, 2022-2025)"),
    code("""# Yearly totals by export type
tot["year"] = tot["time"].dt.year
yearly = tot.groupby(["year","export_type"])["ALL_VAL_MO"].sum().unstack() / 1e9
yearly = yearly[["Total Exports","Domestic Exports","Re-Exports"]]
yearly["Re-Export Share %"] = 100 * yearly["Re-Exports"] / yearly["Total Exports"]
yearly["Domestic Share %"]  = 100 * yearly["Domestic Exports"] / yearly["Total Exports"]
print("All U.S. exports (excluding HS2 27/71/98/99):")
print(yearly.round(2))
"""),
    md("## 2. AI-related vs non-AI: domestic vs re-export split"),
    code("""# By AI relevance
ai_split = tot.groupby(["year","relevance","export_type"])["ALL_VAL_MO"].sum().unstack(fill_value=0) / 1e9
ai_split = ai_split[["Total Exports","Domestic Exports","Re-Exports"]]
ai_split["Re-Export Share %"] = 100 * ai_split["Re-Exports"] / ai_split["Total Exports"]
print("By AI relevance:")
print(ai_split.round(2))

print()
print("Re-export share comparison (AI High vs non-AI), by year:")
pivot = (100 * tot.groupby(["year","relevance","export_type"])["ALL_VAL_MO"].sum().unstack()
                       .pipe(lambda d: d["Re-Exports"] / d["Total Exports"]))
print(pivot.unstack().round(2))
"""),
    md("## 3. By AI product category"),
    code("""# High-relevance only, by category
cat_data = tot[tot["relevance"] == "High"].copy()
cat = cat_data.groupby(["primary_category","export_type"])["ALL_VAL_MO"].sum().unstack(fill_value=0) / 1e9
cat = cat[["Total Exports","Domestic Exports","Re-Exports"]]
cat["Re-Export Share %"] = 100 * cat["Re-Exports"] / cat["Total Exports"]
cat = cat.sort_values("Total Exports", ascending=False)
print("AI High-relevance categories, 2022-2026 cumulative:")
print(cat.round(2))
"""),
    md("## 4. By destination country (focus on the Mexico re-export hypothesis)"),
    code("""# Load by-country file
cty = pd.read_parquet(ALL_FILE)
cty["ALL_VAL_MO"] = cty["ALL_VAL_MO"].astype(float)
cty["E_COMMODITY"] = cty["E_COMMODITY"].astype(str).str.zfill(10)
cty["HS10"] = cty["E_COMMODITY"].astype("int64")
cty["HS2"]  = cty["E_COMMODITY"].str[:2]
cty["time"] = pd.to_datetime(cty["time"], format="%Y-%m")
cty = cty[~cty["HS2"].isin(["27","71","98","99"])]
cty = cty.merge(mat[["HS10","relevance","primary_category"]], on="HS10", how="left")
cty = cty[cty["time"] >= "2022-01-01"]
cty["year"] = cty["time"].dt.year
print(f"By-country rows: {len(cty):,}")
print(f"Countries: {cty['CTY_NAME'].nunique()}")
"""),
    code("""# Re-export share of AI-High exports, by destination, 2024-2025 combined
recent = cty[(cty["year"].isin([2024, 2025])) & (cty["relevance"] == "High")].copy()
by_cty = recent.groupby(["CTY_NAME","export_type"])["ALL_VAL_MO"].sum().unstack(fill_value=0) / 1e9

if "Total Exports" in by_cty.columns:
    by_cty["Re-Export Share %"] = 100 * by_cty.get("Re-Exports", 0) / by_cty["Total Exports"].replace(0, np.nan)
    by_cty = by_cty.sort_values("Total Exports", ascending=False)
    print("AI-High exports to top destinations, 2024-2025 (excluding aggregates):")
    print(by_cty.head(15).round(2))
"""),
    md("## 5. Time trend — re-export share of AI exports, monthly 2022-2026"),
    code("""# Monthly re-export share of AI-High exports (using TOTAL row series)
ai_high_monthly = tot[tot["relevance"] == "High"].groupby(["time","export_type"])["ALL_VAL_MO"].sum().unstack(fill_value=0)
ai_high_monthly["Re-Export Share %"] = 100 * ai_high_monthly["Re-Exports"] / ai_high_monthly["Total Exports"]

# Plot
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(ai_high_monthly.index, ai_high_monthly["Re-Export Share %"], color="#8B0000", linewidth=2)
ax.set_ylabel("Re-Export Share of AI-High Exports (%)", fontsize=13, fontweight="bold")
ax.set_title("Re-Export Share of U.S. AI-Related Exports, Monthly", fontsize=15, fontweight="bold")
ax.grid(axis="y", alpha=0.3, linestyle="--")
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.show()

# Print yearly averages
yearly_share = ai_high_monthly.groupby(ai_high_monthly.index.year)["Re-Export Share %"].mean()
print()
print("Yearly average re-export share of AI-High exports:")
print(yearly_share.round(2))
"""),
    md("""## Summary
After running this notebook, the key numbers to extract for the paper §3 narrative:

1. **What fraction of all U.S. AI-related exports are re-exports?** (yearly, 2022-2025)
2. **Is the re-export share rising or stable?**
3. **Which destinations have the highest re-export share?** (Mexico specifically — does the data confirm the paper's hypothesis?)
4. **Which AI categories are most re-export heavy?** (Likely Compute Hardware, given it's the most tradeable AI input)

If results show a meaningful re-export story (>20% share for Mexico, or rising trend), justify updating notebook 10 / §3 with the split. Otherwise, document as a null result.
"""),
])


# ============================================================
# Write files
# ============================================================
out_paths = [
    (os.path.join(EXPORTS_REPO, "make-exports-hs10-DF-dataset.ipynb"),    make_nb),
    (os.path.join(EXPORTS_REPO, "combine-exports-hs10-DF-dataset.ipynb"), combine_nb),
    (os.path.join(REPO, "code", "13-section3-reexports.ipynb"),           explore_nb),
]

for path, content in out_paths:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=1)
    print(f"Wrote {path}")
