from pathlib import Path

import pandas as pd


PATH = Path(
    "data/processed/fact_emissions_monthly_2001_2025.csv"
)


df = pd.read_csv(
    PATH,
    parse_dates=["period"],
    low_memory=False
)


MEASURES = [
    "gross_load_mwh",
    "steam_load_klb",
    "heat_input_mmbtu",
    "so2_mass_tons",
    "co2_mass_tons",
    "nox_mass_tons",
]


df["all_measures_missing"] = (
    df[MEASURES]
    .isna()
    .all(axis=1)
)


print("=" * 110)
print("EPA CAMPD ALL-MEASURES-MISSING DIAGNOSIS")
print("=" * 110)

print(
    f"Total rows: "
    f"{len(df):,}"
)

print(
    f"All-measures-missing rows: "
    f"{df['all_measures_missing'].sum():,}"
)

print(
    f"Share: "
    f"{(
        df['all_measures_missing'].mean()
        * 100
    ):.2f}%"
)


# =============================================================================
# BY YEAR
# =============================================================================

print("\n" + "=" * 110)
print("ALL-MISSING BY YEAR")
print("=" * 110)

year_summary = (
    df.groupby("year")
    .agg(
        total_rows=(
            "facility_id",
            "size"
        ),
        all_missing_rows=(
            "all_measures_missing",
            "sum"
        ),
    )
)

year_summary["missing_share_pct"] = (
    year_summary["all_missing_rows"]
    / year_summary["total_rows"]
    * 100
)

print(
    year_summary.to_string()
)


# =============================================================================
# FACILITY-LEVEL PATTERN
# =============================================================================

facility_summary = (
    df.groupby(
        [
            "facility_id",
            "facility_name",
            "state",
        ]
    )
    .agg(
        total_months=(
            "period",
            "size"
        ),
        all_missing_months=(
            "all_measures_missing",
            "sum"
        ),
        first_period=(
            "period",
            "min"
        ),
        last_period=(
            "period",
            "max"
        ),
    )
    .reset_index()
)

facility_summary[
    "missing_share_pct"
] = (
    facility_summary[
        "all_missing_months"
    ]
    / facility_summary[
        "total_months"
    ]
    * 100
)


print("\n" + "=" * 110)
print("FACILITY MISSING-PATTERN COUNTS")
print("=" * 110)

fully_missing = facility_summary[
    facility_summary[
        "all_missing_months"
    ]
    == facility_summary[
        "total_months"
    ]
]

partially_missing = facility_summary[
    (
        facility_summary[
            "all_missing_months"
        ] > 0
    )
    & (
        facility_summary[
            "all_missing_months"
        ]
        < facility_summary[
            "total_months"
        ]
    )
]

never_missing = facility_summary[
    facility_summary[
        "all_missing_months"
    ] == 0
]


print(
    f"Facilities always all-missing: "
    f"{len(fully_missing):,}"
)

print(
    f"Facilities partially all-missing: "
    f"{len(partially_missing):,}"
)

print(
    f"Facilities never all-missing: "
    f"{len(never_missing):,}"
)


# =============================================================================
# ALWAYS-MISSING FACILITIES
# =============================================================================

print("\n" + "=" * 110)
print("TOP ALWAYS-ALL-MISSING FACILITIES")
print("=" * 110)

print(
    fully_missing[
        [
            "facility_id",
            "facility_name",
            "state",
            "total_months",
            "first_period",
            "last_period",
        ]
    ]
    .sort_values(
        "total_months",
        ascending=False
    )
    .head(50)
    .to_string(
        index=False
    )
)


# =============================================================================
# PARTIAL-MISSING FACILITIES
# =============================================================================

print("\n" + "=" * 110)
print("TOP PARTIALLY-MISSING FACILITIES")
print("=" * 110)

print(
    partially_missing[
        [
            "facility_id",
            "facility_name",
            "state",
            "total_months",
            "all_missing_months",
            "missing_share_pct",
            "first_period",
            "last_period",
        ]
    ]
    .sort_values(
        [
            "all_missing_months",
            "total_months",
        ],
        ascending=False
    )
    .head(50)
    .to_string(
        index=False
    )
)


# =============================================================================
# TRANSITION EXAMPLES
# =============================================================================

print("\n" + "=" * 110)
print("SAMPLE PARTIAL FACILITY MONTH PATTERNS")
print("=" * 110)

sample_ids = (
    partially_missing[
        "facility_id"
    ]
    .head(5)
    .tolist()
)

for facility_id in sample_ids:

    sample = df[
        df[
            "facility_id"
        ] == facility_id
    ].copy()

    print(
        f"\nFacility {facility_id}: "
        f"{sample['facility_name'].iloc[0]}"
    )

    print(
        sample[
            [
                "period",
                "all_measures_missing",
                "gross_load_mwh",
                "heat_input_mmbtu",
                "co2_mass_tons",
            ]
        ]
        .tail(36)
        .to_string(
            index=False
        )
    )


print(
    "\n=== ALL-MEASURES-MISSING "
    "DIAGNOSIS COMPLETE ==="
)