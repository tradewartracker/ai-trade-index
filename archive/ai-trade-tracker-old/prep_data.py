"""
Prepare pre-computed data for the AI Trade Tracker Bokeh app.

Reads from the main repo's data-input/ files and produces a small parquet
with monthly series (both dollar values in $B and index with 2023=100)
for 9 series: AI Related, Non-AI Related, and 7 High-relevance subcategories.

Usage:
    python prep_data.py
"""
import os
import pandas as pd

# ---------- paths ----------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRADE_FILE = os.path.join(REPO_ROOT, "data-input", "TOTALdata-current.parquet")
CLASS_FILE = os.path.join(REPO_ROOT, "data-input", "hs10_classification_final_v3.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ai_trade_series.parquet")

# ---------- series definitions ----------
# Each entry: (display_name, column_prefix, filter_function)
# filter_function takes a DataFrame and returns a boolean mask
CATEGORIES = [
    ("Compute Hardware",    "compute_hardware",    lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Compute_Hardware")),
    ("Electrical Power",    "electrical_power",    lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Electrical_Power")),
    ("Networking Telecom",  "networking_telecom",  lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Networking_Telecom")),
    ("Cooling HVAC",        "cooling_hvac",        lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Cooling_HVAC")),
    ("Building Structure",  "building_structure",  lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Building_Structure")),
    ("Fire Safety Security","fire_safety_security", lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Fire_Safety_Security")),
    ("Specialty Materials", "specialty_materials",  lambda d: (d["relevance"] == "High") & (d["primary_category"] == "Specialty_Materials")),
]


def compute_series(df, mask, base_year="2023"):
    """Compute monthly dollar values ($B) and index (base_year=100) for a subset."""
    subset = df.loc[mask].groupby("time")["imports"].sum()
    dollars = subset / 1e9
    base_total = subset.loc[base_year].sum()
    index = 100 * 12 * subset / base_total
    return dollars, index


def main():
    # --- load and prepare trade data (mirrors notebook 07) ---
    print("Loading trade data...")
    df = pd.read_parquet(TRADE_FILE)
    df.rename(columns={"I_COMMODITY": "HS10"}, inplace=True)
    df["HS2"] = df["HS10"].str[0:2]
    df["HS10"] = df["HS10"].astype("int64")
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m")
    df["imports"] = df["CON_VAL_MO"].astype(float)

    # Exclude volatile/special HS2 categories
    df = df[~df["HS2"].isin(["27", "71", "98", "99"])]

    # --- load and merge classification ---
    print("Loading classification...")
    matlist = pd.read_csv(CLASS_FILE)
    matlist.rename(columns={"hs10_code": "HS10"}, inplace=True)
    df = df.merge(matlist[["HS10", "relevance", "primary_category"]], on="HS10", how="left")

    # Filter to 2023 onwards
    df = df[df["time"] >= "2023-01-01"]
    df.set_index("time", inplace=True)

    # --- compute all series ---
    result = pd.DataFrame()

    # AI Related (High relevance, all categories)
    print("Computing series...")
    ai_dollars, ai_index = compute_series(df, df["relevance"] == "High")
    result["ai_related_dollars"] = ai_dollars
    result["ai_related_index"] = ai_index

    # Non-AI Related (Low relevance)
    non_ai_dollars, non_ai_index = compute_series(df, df["relevance"] == "Low")
    result["non_ai_related_dollars"] = non_ai_dollars
    result["non_ai_related_index"] = non_ai_index

    # Subcategories
    for display_name, col_prefix, filter_fn in CATEGORIES:
        mask = filter_fn(df)
        dollars, index = compute_series(df, mask)
        result[f"{col_prefix}_dollars"] = dollars
        result[f"{col_prefix}_index"] = index

    result.index.name = "date"

    # --- save ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    result.to_parquet(OUTPUT_FILE)
    print(f"Saved {len(result)} rows x {len(result.columns)} columns to {OUTPUT_FILE}")

    # --- validate against existing CSV ---
    validation_file = os.path.join(REPO_ROOT, "data-output", "ai_trade_index_series.csv")
    if os.path.exists(validation_file):
        ref = pd.read_csv(validation_file, parse_dates=["date"])
        ref.set_index("date", inplace=True)
        ai_diff = (result["ai_related_index"] - ref["AI_Relevant"]).abs().max()
        non_ai_diff = (result["non_ai_related_index"] - ref["Not_AI_Relevant"]).abs().max()
        print(f"\nValidation vs existing CSV:")
        print(f"  AI Related index max diff:     {ai_diff:.10f}")
        print(f"  Non-AI Related index max diff: {non_ai_diff:.10f}")
        if ai_diff < 0.01 and non_ai_diff < 0.01:
            print("  PASS")
        else:
            print("  WARNING: differences exceed threshold")

    # Preview
    print(f"\nPreview:")
    print(result.head())


if __name__ == "__main__":
    main()
