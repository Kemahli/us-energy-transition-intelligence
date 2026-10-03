import pandas as pd

FILE = "data/processed/eia923_generation_2001_2025.csv"

print("Loading dataset...")

df = pd.read_csv(
    FILE,
    parse_dates=["period"]
)

print("\n=== BASIC CHECKS ===")

print(f"Rows: {len(df):,}")
print(f"Unique plants: {df['plant_code'].nunique():,}")

print(
    "Period range:",
    df["period"].min(),
    "to",
    df["period"].max()
)

print(
    f"Missing generation: "
    f"{df['generation_mwh'].isna().sum():,}"
)

print(
    f"Exact duplicate rows: "
    f"{df.duplicated().sum():,}"
)


print("\n=== KEY DUPLICATE CHECK ===")

key_columns = [
    "period",
    "plant_code",
    "fuel_code",
    "prime_mover"
]

key_duplicates = df.duplicated(
    subset=key_columns,
    keep=False
)

print(
    f"Rows involved in key duplicates: "
    f"{key_duplicates.sum():,}"
)


print("\n=== YEAR COVERAGE ===")

year_counts = (
    df.assign(
        year=df["period"].dt.year
    )
    .groupby("year")
    .size()
)

print(year_counts.to_string())


print("\n=== MONTH COVERAGE ===")

month_coverage = (
    df.assign(
        year=df["period"].dt.year,
        month=df["period"].dt.month
    )
    .groupby("year")["month"]
    .nunique()
)

print(month_coverage.to_string())


print("\n=== MISSING GENERATION BY YEAR ===")

missing_by_year = (
    df.assign(
        year=df["period"].dt.year
    )
    .groupby("year")["generation_mwh"]
    .apply(lambda x: x.isna().sum())
)

print(missing_by_year.to_string())


print("\n=== NEGATIVE GENERATION ===")

negative = df[
    df["generation_mwh"] < 0
]

print(
    f"Negative generation rows: "
    f"{len(negative):,}"
)

if len(negative) > 0:
    print(
        negative[
            [
                "period",
                "plant_code",
                "plant_name",
                "fuel_code",
                "prime_mover",
                "generation_mwh"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


print("\n=== VALIDATION COMPLETE ===")