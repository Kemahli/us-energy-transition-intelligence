from pathlib import Path
import pandas as pd

DATA_PATH = Path(
    "data/processed/fact_capacity_generators_2001_2025.csv"
)

df = pd.read_csv(
    DATA_PATH,
    dtype={
        "generator_id": "string",
        "status": "string",
        "source_sheet": "string",
        "source_file": "string",
    }
)


print("=" * 100)
print("EIA-860 CAPACITY SEMANTICS DIAGNOSIS")
print("=" * 100)


# ------------------------------------------------------------------
# 1. Missing generator IDs
# ------------------------------------------------------------------

missing_gen = df[
    df["generator_id"].isna()
].copy()

print("\n" + "=" * 100)
print("MISSING GENERATOR IDs")
print("=" * 100)

print(
    f"Rows with missing Generator ID: "
    f"{len(missing_gen):,}"
)

if len(missing_gen) > 0:

    cols = [
        "report_year",
        "record_type",
        "plant_code",
        "plant_name",
        "state",
        "generator_id",
        "status",
        "technology",
        "prime_mover",
        "nameplate_capacity_mw",
        "source_file",
        "source_sheet",
    ]

    print(
        missing_gen[
            cols
        ].to_string(
            index=False
        )
    )


# ------------------------------------------------------------------
# 2. Duplicate natural keys within year and record type
# ------------------------------------------------------------------

valid = df[
    df["plant_code"].notna()
    & df["generator_id"].notna()
].copy()

key = [
    "report_year",
    "record_type",
    "plant_code",
    "generator_id",
]

dup = valid[
    valid.duplicated(
        subset=key,
        keep=False
    )
].copy()

print("\n" + "=" * 100)
print("DUPLICATE KEY DIAGNOSIS")
print("=" * 100)

print(
    f"Duplicate rows: "
    f"{len(dup):,}"
)

if len(dup) > 0:

    cols = [
        "report_year",
        "record_type",
        "plant_code",
        "plant_name",
        "state",
        "generator_id",
        "status",
        "prime_mover",
        "nameplate_capacity_mw",
        "summer_capacity_mw",
        "winter_capacity_mw",
        "source_file",
        "source_sheet",
    ]

    print(
        dup[
            cols
        ]
        .sort_values(key)
        .to_string(
            index=False
        )
    )

    print(
        "\nAre duplicate rows exact duplicates "
        "across canonical columns?"
    )

    exact_dups = dup.duplicated(
        keep=False
    )

    print(
        f"Exact duplicate rows: "
        f"{exact_dups.sum():,}"
    )


# ------------------------------------------------------------------
# 3. Source-sheet composition by year
# ------------------------------------------------------------------

print("\n" + "=" * 100)
print("SOURCE SHEET COMPOSITION")
print("=" * 100)

for year in [
    2001,
    2004,
    2009,
    2013,
    2025,
]:

    sample = df[
        df["report_year"] == year
    ]

    print(
        f"\nYEAR {year}"
    )

    print(
        sample.groupby(
            [
                "source_sheet",
                "status",
            ],
            dropna=False
        )
        .size()
        .to_string()
    )


# ------------------------------------------------------------------
# 4. Capacity totals by status for selected years
# ------------------------------------------------------------------

print("\n" + "=" * 100)
print("NAMEPLATE CAPACITY BY STATUS")
print("=" * 100)

for year in [
    2001,
    2004,
    2009,
    2013,
    2025,
]:

    sample = df[
        df["report_year"] == year
    ]

    capacity = (
        sample.groupby(
            [
                "record_type",
                "status",
            ],
            dropna=False
        )[
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
        .sort_values(
            ascending=False
        )
    )

    print(
        f"\nYEAR {year}"
    )

    print(
        capacity.to_string()
    )


# ------------------------------------------------------------------
# 5. 2025 explicit sheet-level totals
# ------------------------------------------------------------------

year_2025 = df[
    df["report_year"] == 2025
].copy()

print("\n" + "=" * 100)
print("2025 SOURCE-SHEET CAPACITY")
print("=" * 100)

sheet_capacity = (
    year_2025.groupby(
        "source_sheet",
        dropna=False
    )[
        "nameplate_capacity_mw"
    ]
    .agg(
        ["count", "sum"]
    )
)

print(
    sheet_capacity.to_string()
)


print("\n=== DIAGNOSIS COMPLETE ===")