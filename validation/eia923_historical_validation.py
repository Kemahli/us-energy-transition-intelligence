import pandas as pd

PROCESSED_FILE = "data/processed/eia923_generation_2025.csv"
API_SAMPLE_FILE = "data/raw/eia_barry_2025.csv"

# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

historical = pd.read_csv(PROCESSED_FILE)
api = pd.read_csv(API_SAMPLE_FILE)

historical["period"] = pd.to_datetime(historical["period"])
api["period"] = pd.to_datetime(api["period"])

# --------------------------------------------------
# 2. Filter historical data to Barry Plant
# --------------------------------------------------

barry_hist = historical[
    historical["plant_code"] == 3
].copy()

# API contains aggregate rows.
# Keep only detailed observations.
barry_api = api[
    (api["fuel2002"] != "ALL") &
    (api["primeMover"] != "ALL")
].copy()

barry_api["generation"] = pd.to_numeric(
    barry_api["generation"],
    errors="coerce"
)

# --------------------------------------------------
# 3. Standardize columns
# --------------------------------------------------

barry_api = barry_api.rename(
    columns={
        "fuel2002": "fuel_code",
        "primeMover": "prime_mover",
        "generation": "api_generation_mwh"
    }
)

barry_hist = barry_hist.rename(
    columns={
        "generation_mwh": "historical_generation_mwh"
    }
)

# --------------------------------------------------
# 4. Merge API vs historical
# --------------------------------------------------

comparison = barry_hist.merge(
    barry_api[
        [
            "period",
            "plantCode",
            "fuel_code",
            "prime_mover",
            "api_generation_mwh"
        ]
    ],
    left_on=[
        "period",
        "plant_code",
        "fuel_code",
        "prime_mover"
    ],
    right_on=[
        "period",
        "plantCode",
        "fuel_code",
        "prime_mover"
    ],
    how="outer",
    indicator=True
)

# --------------------------------------------------
# 5. Compare values
# --------------------------------------------------

comparison["difference"] = (
    comparison["historical_generation_mwh"]
    - comparison["api_generation_mwh"]
)

print("=== BARRY API VS HISTORICAL VALIDATION ===")

print(f"Historical rows: {len(barry_hist)}")
print(f"API detailed rows: {len(barry_api)}")

print("\nMerge status:")
print(comparison["_merge"].value_counts())

matched = comparison[
    comparison["_merge"] == "both"
]

print("\nMatched rows:", len(matched))

print(
    "Rows with generation difference:",
    (
        matched["difference"]
        .abs()
        .fillna(0)
        > 0.005
    ).sum()
)

print("\nMaximum absolute difference:")
print(
    matched["difference"]
    .abs()
    .max()
)

print("\nRows with missing historical generation:")
print(
    barry_hist["historical_generation_mwh"]
    .isna()
    .sum()
)

print("\nSample comparison:")
print(
    matched[
        [
            "period",
            "fuel_code",
            "prime_mover",
            "historical_generation_mwh",
            "api_generation_mwh",
            "difference"
        ]
    ]
    .head(20)
    .to_string(index=False)
)