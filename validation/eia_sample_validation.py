import pandas as pd

FILE_PATH = "data/raw/eia_barry_2025.csv"

df = pd.read_csv(FILE_PATH)

# Convert numeric measures
numeric_cols = [
    "generation",
    "gross-generation",
    "total-consumption-btu"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# 1. Basic checks
print("=== BASIC CHECKS ===")
print(f"Rows: {len(df)}")
print(f"Plants: {df['plantCode'].nunique()}")
print(f"Periods: {df['period'].nunique()}")


# 2. Missing months
expected_months = [f"2025-{month:02d}" for month in range(1, 13)]
actual_months = sorted(df["period"].unique())

missing_months = sorted(set(expected_months) - set(actual_months))

print("\n=== PERIOD CHECK ===")
print(f"Actual periods: {actual_months}")
print(f"Missing periods: {missing_months}")


# 3. Duplicate exact rows
duplicates = df.duplicated().sum()

print("\n=== DUPLICATE CHECK ===")
print(f"Exact duplicate rows: {duplicates}")


# 4. Compare plant totals with detailed rows
plant_totals = (
    df[
        (df["fuel2002"] == "ALL") &
        (df["primeMover"] == "ALL")
    ]
    [["period", "generation"]]
    .rename(columns={"generation": "reported_total_generation"})
)

detailed = df[
    (df["fuel2002"] != "ALL") &
    (df["primeMover"] != "ALL")
]

detail_totals = (
    detailed
    .groupby("period", as_index=False)["generation"]
    .sum()
    .rename(columns={"generation": "detailed_generation_sum"})
)

comparison = plant_totals.merge(
    detail_totals,
    on="period",
    how="left"
)

comparison["difference"] = (
    comparison["reported_total_generation"]
    - comparison["detailed_generation_sum"]
)

print("\n=== AGGREGATION VALIDATION ===")
print(comparison.to_string(index=False))