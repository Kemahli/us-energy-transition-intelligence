import pandas as pd

FILE = "data/processed/eia923_generation_2001_2025.csv"

print("Loading dataset...")

df = pd.read_csv(
    FILE,
    parse_dates=["period"]
)

key = [
    "period",
    "plant_code",
    "fuel_code",
    "prime_mover"
]

df["year"] = df["period"].dt.year


# --------------------------------------------------
# 1. Duplicate groups
# --------------------------------------------------

group_sizes = (
    df.groupby(
        key,
        dropna=False
    )
    .size()
    .reset_index(name="row_count")
)

duplicate_groups = group_sizes[
    group_sizes["row_count"] > 1
]

print("\n=== DUPLICATE GROUP SUMMARY ===")

print(
    f"Duplicate key groups: "
    f"{len(duplicate_groups):,}"
)

print(
    f"Maximum rows in one key group: "
    f"{duplicate_groups['row_count'].max()}"
)

print("\nGroup size distribution:")

print(
    duplicate_groups["row_count"]
    .value_counts()
    .sort_index()
    .to_string()
)


# --------------------------------------------------
# 2. Duplicates by year
# --------------------------------------------------

duplicate_rows = df.merge(
    duplicate_groups[key],
    on=key,
    how="inner"
)

print("\n=== DUPLICATE ROWS BY YEAR ===")

print(
    duplicate_rows
    .groupby("year")
    .size()
    .to_string()
)


# --------------------------------------------------
# 3. Are duplicate generation values identical?
# --------------------------------------------------

generation_variation = (
    duplicate_rows
    .groupby(
        key,
        dropna=False
    )["generation_mwh"]
    .agg(
        row_count="size",
        unique_generation="nunique",
        min_generation="min",
        max_generation="max"
    )
    .reset_index()
)

same_value_groups = generation_variation[
    generation_variation["unique_generation"] <= 1
]

different_value_groups = generation_variation[
    generation_variation["unique_generation"] > 1
]

print("\n=== GENERATION VALUE CHECK ===")

print(
    f"Duplicate groups with same generation value: "
    f"{len(same_value_groups):,}"
)

print(
    f"Duplicate groups with different generation values: "
    f"{len(different_value_groups):,}"
)


# --------------------------------------------------
# 4. Sample problematic groups
# --------------------------------------------------

print("\n=== SAMPLE GROUPS WITH DIFFERENT VALUES ===")

print(
    different_value_groups
    .head(20)
    .to_string(index=False)
)


# --------------------------------------------------
# 5. Show full rows for first few groups
# --------------------------------------------------

if len(different_value_groups) > 0:

    sample_keys = different_value_groups[
        key
    ].head(5)

    sample_rows = df.merge(
        sample_keys,
        on=key,
        how="inner"
    )

    print("\n=== FULL SAMPLE ROWS ===")

    print(
        sample_rows[
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
        .sort_values(key)
        .to_string(index=False)
    )


print("\n=== DIAGNOSIS COMPLETE ===")