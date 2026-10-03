from pathlib import Path

import pandas as pd


HIST_PATH = Path(
    "data/raw/eia861m_sales_revenue_2010_current.xlsx"
)

CURRENT_PATH = Path(
    "data/raw/eia861m_sales_2026.xlsx"
)


# =============================================================================
# HELPERS
# =============================================================================

SECTORS = [
    "Residential",
    "Commercial",
    "Industrial",
    "Transportation",
    "Total",
]


def load_historical_monthly_states():

    # Row 0 = sector group
    # Row 1 = metric name
    # Row 2 = actual units / identity headers
    raw = pd.read_excel(
        HIST_PATH,
        sheet_name="Monthly-States",
        header=None,
        engine="calamine"
    )

    sector_row = raw.iloc[0]
    metric_row = raw.iloc[1]
    header_row = raw.iloc[2]

    columns = []

    current_sector = None

    for i in range(raw.shape[1]):

        sector_value = sector_row.iloc[i]
        metric_value = metric_row.iloc[i]
        header_value = header_row.iloc[i]

        if pd.notna(sector_value):
            sector_text = str(sector_value).strip()

            if sector_text.upper() in {
                "RESIDENTIAL",
                "COMMERCIAL",
                "INDUSTRIAL",
                "TRANSPORTATION",
                "TOTAL",
            }:
                current_sector = sector_text.title()

        if i < 4:
            columns.append(
                str(header_value).strip()
            )
        else:
            metric = str(metric_value).strip()

            columns.append(
                f"{current_sector}_{metric}"
            )

    df = raw.iloc[3:].copy()

    df.columns = columns

    df = df[
        df["Year"].notna()
        & df["Month"].notna()
        & df["State"].notna()
    ].copy()

    df["Year"] = pd.to_numeric(
        df["Year"],
        errors="coerce"
    ).astype("Int64")

    df["Month"] = pd.to_numeric(
        df["Month"],
        errors="coerce"
    ).astype("Int64")

    df["State"] = (
        df["State"]
        .astype("string")
        .str.strip()
    )

    return df


def load_current_states():

    raw = pd.read_excel(
        CURRENT_PATH,
        sheet_name="Sales Ultimate Cust. -States",
        header=None,
        engine="calamine"
    )

    sector_row = raw.iloc[0]
    metric_row = raw.iloc[1]
    header_row = raw.iloc[2]

    columns = []

    current_sector = None

    for i in range(raw.shape[1]):

        sector_value = sector_row.iloc[i]
        metric_value = metric_row.iloc[i]
        header_value = header_row.iloc[i]

        if pd.notna(sector_value):
            sector_text = str(sector_value).strip()

            if sector_text.upper() in {
                "RESIDENTIAL",
                "COMMERCIAL",
                "INDUSTRIAL",
                "TRANSPORTATION",
                "TOTAL",
            }:
                current_sector = sector_text.title()

        if i < 7:
            columns.append(
                str(header_value).strip()
            )
        else:
            metric = str(metric_value).strip()

            columns.append(
                f"{current_sector}_{metric}"
            )

    df = raw.iloc[3:].copy()

    df.columns = columns

    df = df[
        df["Year"].notna()
        & df["Month"].notna()
        & df["State"].notna()
    ].copy()

    df["Year"] = pd.to_numeric(
        df["Year"],
        errors="coerce"
    ).astype("Int64")

    df["Month"] = pd.to_numeric(
        df["Month"],
        errors="coerce"
    ).astype("Int64")

    df["Utility Number"] = pd.to_numeric(
        df["Utility Number"],
        errors="coerce"
    ).astype("Int64")

    df["State"] = (
        df["State"]
        .astype("string")
        .str.strip()
    )

    df["Utility Name"] = (
        df["Utility Name"]
        .astype("string")
        .str.strip()
    )

    return df


# =============================================================================
# LOAD
# =============================================================================

hist = load_historical_monthly_states()
current = load_current_states()


# =============================================================================
# 1. HISTORICAL GRAIN TEST
# =============================================================================

print("=" * 100)
print("HISTORICAL MONTHLY-STATES GRAIN")
print("=" * 100)

print(
    f"Rows: {len(hist):,}"
)

print(
    f"Years: {hist['Year'].min()} "
    f"to {hist['Year'].max()}"
)

print(
    f"States / codes: "
    f"{hist['State'].nunique():,}"
)

key = [
    "Year",
    "Month",
    "State",
]

dup_mask = hist.duplicated(
    subset=key,
    keep=False
)

print(
    f"Duplicate Year × Month × State rows: "
    f"{dup_mask.sum():,}"
)

if dup_mask.any():

    print("\nDuplicate sample:")

    print(
        hist.loc[
            dup_mask,
            key + ["Data Status"]
        ]
        .sort_values(key)
        .head(50)
        .to_string(index=False)
    )


print("\nData Status counts:")

print(
    hist["Data Status"]
    .value_counts(
        dropna=False
    )
    .to_string()
)


# =============================================================================
# 2. DATE COVERAGE
# =============================================================================

coverage = (
    hist.groupby("Year")
    .agg(
        min_month=("Month", "min"),
        max_month=("Month", "max"),
        rows=("Month", "size"),
        states=("State", "nunique"),
    )
)

print("\n" + "=" * 100)
print("HISTORICAL COVERAGE BY YEAR")
print("=" * 100)

print(
    coverage.to_string()
)


# =============================================================================
# 3. CURRENT SPECIAL ROW TYPES
# =============================================================================

print("\n" + "=" * 100)
print("CURRENT 2026 SPECIAL UTILITY ROWS")
print("=" * 100)

special = current[
    current["Utility Number"].isin(
        [0, 88888]
    )
].copy()

print(
    special[
        [
            "Year",
            "Month",
            "State",
            "Utility Number",
            "Utility Name",
            "Data Status",
        ]
    ]
    .head(100)
    .to_string(index=False)
)

print("\nSpecial Utility Number counts:")

print(
    current[
        "Utility Number"
    ]
    .value_counts()
    .loc[
        lambda s:
        s.index.isin(
            [0, 88888]
        )
    ]
    .to_string()
)


# =============================================================================
# 4. RECONCILE HISTORICAL STATE TOTAL VS CURRENT STATE TOTAL
# =============================================================================

hist_2026 = hist[
    hist["Year"] == 2026
].copy()

current_total = current[
    current["Utility Number"] == 88888
].copy()

merged = hist_2026.merge(
    current_total,
    on=[
        "Year",
        "Month",
        "State",
    ],
    how="outer",
    suffixes=(
        "_hist",
        "_current"
    ),
    indicator=True
)


comparisons = []

for sector in SECTORS:

    hist_rev = (
        f"{sector}_Revenue"
    )

    hist_sales = (
        f"{sector}_Sales"
    )

    hist_customers = (
        f"{sector}_Customers"
    )

    current_rev = (
        f"{sector}_Revenue"
    )

    current_sales = (
        f"{sector}_Sales"
    )

    current_customers = (
        f"{sector}_Customers"
    )

    # After merge, same-named metrics receive suffixes.
    pairs = [
        (
            "revenue",
            f"{hist_rev}_hist",
            f"{current_rev}_current",
        ),
        (
            "sales",
            f"{hist_sales}_hist",
            f"{current_sales}_current",
        ),
        (
            "customers",
            f"{hist_customers}_hist",
            f"{current_customers}_current",
        ),
    ]

    for metric, left_col, right_col in pairs:

        if (
            left_col not in merged.columns
            or right_col not in merged.columns
        ):
            continue

        left = pd.to_numeric(
            merged[left_col],
            errors="coerce"
        )

        right = pd.to_numeric(
            merged[right_col],
            errors="coerce"
        )

        diff = (
            left - right
        ).abs()

        comparisons.append(
            {
                "sector": sector,
                "metric": metric,
                "compared_rows": (
                    left.notna()
                    & right.notna()
                ).sum(),
                "max_abs_diff": diff.max(),
                "rows_diff_gt_0_01": (
                    diff > 0.01
                ).sum(),
            }
        )


comparison_df = pd.DataFrame(
    comparisons
)

print("\n" + "=" * 100)
print("2026 HISTORICAL MONTHLY-STATE VS CURRENT STATE TOTAL")
print("=" * 100)

print("\nMerge result:")

print(
    merged["_merge"]
    .value_counts()
    .to_string()
)

print("\nMetric reconciliation:")

print(
    comparison_df.to_string(
        index=False
    )
)


# =============================================================================
# 5. CHECK TOTAL CONSISTENCY INSIDE HISTORICAL WORKBOOK
# =============================================================================

print("\n" + "=" * 100)
print("HISTORICAL INTERNAL TOTAL CHECK")
print("=" * 100)

for metric in [
    "Revenue",
    "Sales",
    "Customers",
]:

    component_cols = [
        f"Residential_{metric}",
        f"Commercial_{metric}",
        f"Industrial_{metric}",
        f"Transportation_{metric}",
    ]

    total_col = (
        f"Total_{metric}"
    )

    components = hist[
        component_cols
    ].apply(
        pd.to_numeric,
        errors="coerce"
    )

    reported_total = pd.to_numeric(
        hist[total_col],
        errors="coerce"
    )

    calculated_total = (
        components.sum(
            axis=1,
            min_count=1
        )
    )

    diff = (
        reported_total
        - calculated_total
    ).abs()

    print(
        f"\n{metric}:"
    )

    print(
        f"Rows compared: "
        f"{diff.notna().sum():,}"
    )

    print(
        f"Max absolute difference: "
        f"{diff.max()}"
    )

    print(
        f"Rows difference > 0.01: "
        f"{(diff > 0.01).sum():,}"
    )


print(
    "\n=== EIA-861M STATE GRAIN "
    "RECONCILIATION COMPLETE ==="
)