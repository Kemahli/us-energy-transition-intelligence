import pandas as pd

FILE = "data/processed/eia923_generation_2001_2025.csv"

print("Loading dataset...")

df = pd.read_csv(
    FILE,
    parse_dates=["period"]
)

df["year"] = df["period"].dt.year


print("\n=== HIGH / SPECIAL PLANT IDS ===")

special = df[
    df["plant_code"] >= 99990
].copy()

print(
    f"Rows with plant_code >= 99990: "
    f"{len(special):,}"
)

print("\nPlant IDs:")

print(
    special[
        [
            "plant_code",
            "plant_name"
        ]
    ]
    .drop_duplicates()
    .sort_values("plant_code")
    .to_string(index=False)
)


print("\n=== SPECIAL RECORDS BY YEAR ===")

print(
    special
    .groupby("year")
    .size()
    .to_string()
)


print("\n=== SPECIAL GENERATION BY YEAR ===")

special_gen = (
    special
    .groupby("year")["generation_mwh"]
    .sum(min_count=1)
)

print(
    special_gen.to_string()
)


print("\n=== TOTAL GENERATION BY YEAR ===")

total_gen = (
    df.groupby("year")["generation_mwh"]
    .sum(min_count=1)
)

print(
    total_gen.to_string()
)


print("\n=== SPECIAL SHARE OF GENERATION ===")

share = (
    special_gen
    / total_gen
    * 100
)

print(
    share.to_string()
)


print("\n=== SAMPLE SPECIAL RECORDS ===")

print(
    special[
        [
            "period",
            "plant_code",
            "plant_name",
            "state",
            "fuel_code",
            "prime_mover",
            "generation_mwh"
        ]
    ]
    .head(50)
    .to_string(index=False)
)


print("\n=== DIAGNOSIS COMPLETE ===")