from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

RAW_PATH = Path(
    "data/raw/eia861m_sales_revenue_2010_current.xlsx"
)

OUTPUT_PATH = Path(
    "data/processed/fact_retail_prices_2010_current.csv"
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


# =============================================================================
# CONSTANTS
# =============================================================================

SECTORS = [
    "Residential",
    "Commercial",
    "Industrial",
    "Transportation",
    "Total",
]


# =============================================================================
# LOAD SOURCE
# =============================================================================

def load_monthly_states():

    raw = pd.read_excel(
        RAW_PATH,
        sheet_name="Monthly-States",
        header=None,
        engine="calamine"
    )

    sector_row = raw.iloc[0]
    metric_row = raw.iloc[1]
    header_row = raw.iloc[2]

    columns = []

    current_sector = None

    for i in range(
        raw.shape[1]
    ):

        sector_value = (
            sector_row.iloc[i]
        )

        metric_value = (
            metric_row.iloc[i]
        )

        header_value = (
            header_row.iloc[i]
        )

        # -------------------------------------------------------------
        # First four columns are identifiers
        # -------------------------------------------------------------

        if i < 4:

            columns.append(
                str(
                    header_value
                ).strip()
            )

            continue

        # -------------------------------------------------------------
        # Detect sector group
        # -------------------------------------------------------------

        if pd.notna(
            sector_value
        ):

            sector_text = (
                str(
                    sector_value
                )
                .strip()
                .title()
            )

            if sector_text in SECTORS:

                current_sector = (
                    sector_text
                )

        if current_sector is None:

            raise RuntimeError(
                f"Could not identify sector "
                f"for source column {i}"
            )

        metric_text = (
            str(
                metric_value
            )
            .strip()
        )

        columns.append(
            f"{current_sector}_{metric_text}"
        )

    df = raw.iloc[
        3:
    ].copy()

    df.columns = columns

    # -------------------------------------------------------------
    # Keep only true monthly state records
    # -------------------------------------------------------------

    df = df[
        df["Year"].notna()
        & df["Month"].notna()
        & df["State"].notna()
    ].copy()

    # -------------------------------------------------------------
    # Types
    # -------------------------------------------------------------

    df["Year"] = (
        pd.to_numeric(
            df["Year"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["Month"] = (
        pd.to_numeric(
            df["Month"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["State"] = (
        df["State"]
        .astype("string")
        .str.strip()
    )

    df["Data Status"] = (
        df["Data Status"]
        .astype("string")
        .str.strip()
    )

    # -------------------------------------------------------------
    # Explicit grain validation
    # -------------------------------------------------------------

    key = [
        "Year",
        "Month",
        "State",
    ]

    duplicates = df.duplicated(
        subset=key,
        keep=False
    )

    if duplicates.any():

        duplicate_rows = df.loc[
            duplicates,
            key
        ]

        raise RuntimeError(
            "Historical Monthly-States "
            "contains duplicate "
            "Year × Month × State rows.\n"
            + duplicate_rows
            .head(50)
            .to_string(
                index=False
            )
        )

    return df


# =============================================================================
# WIDE TO LONG
# =============================================================================

def reshape_to_long(
    wide
):

    frames = []

    for sector in SECTORS:

        revenue_col = (
            f"{sector}_Revenue"
        )

        sales_col = (
            f"{sector}_Sales"
        )

        customers_col = (
            f"{sector}_Customers"
        )

        price_col = (
            f"{sector}_Price"
        )

        required = [
            revenue_col,
            sales_col,
            customers_col,
            price_col,
        ]

        missing = [
            col
            for col in required
            if col not in wide.columns
        ]

        if missing:

            raise RuntimeError(
                f"Missing columns for "
                f"{sector}: {missing}"
            )

        frame = pd.DataFrame(
            {
                "year":
                    wide["Year"],

                "month":
                    wide["Month"],

                "state":
                    wide["State"],

                "sector":
                    sector,

                "data_status":
                    wide[
                        "Data Status"
                    ],

                "revenue_thousand_dollars":
                    wide[
                        revenue_col
                    ],

                "sales_mwh":
                    wide[
                        sales_col
                    ],

                "customers":
                    wide[
                        customers_col
                    ],

                "price_cents_per_kwh":
                    wide[
                        price_col
                    ],
            }
        )

        frames.append(
            frame
        )

    long_df = pd.concat(
        frames,
        ignore_index=True
    )

    return long_df


# =============================================================================
# CLEAN TYPES
# =============================================================================

def clean_long(
    df
):

    df = df.copy()

    df["year"] = (
        pd.to_numeric(
            df["year"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["month"] = (
        pd.to_numeric(
            df["month"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["state"] = (
        df["state"]
        .astype("string")
        .str.strip()
    )

    df["sector"] = (
        df["sector"]
        .astype("string")
        .str.strip()
    )

    df["data_status"] = (
        df["data_status"]
        .astype("string")
        .str.strip()
    )

    numeric_columns = [
        "revenue_thousand_dollars",
        "sales_mwh",
        "customers",
        "price_cents_per_kwh",
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # -------------------------------------------------------------
    # Period
    # -------------------------------------------------------------

    df["period"] = pd.to_datetime(
        {
            "year":
                df["year"],

            "month":
                df["month"],

            "day":
                1,
        },
        errors="coerce"
    )

    # -------------------------------------------------------------
    # Column order
    # -------------------------------------------------------------

    df = df[
        [
            "period",
            "year",
            "month",
            "state",
            "sector",
            "data_status",
            "revenue_thousand_dollars",
            "sales_mwh",
            "customers",
            "price_cents_per_kwh",
        ]
    ]

    return df


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    df
):

    print(
        "\n"
        + "=" * 100
    )

    print(
        "EIA-861M RETAIL PRICE "
        "PIPELINE VALIDATION"
    )

    print(
        "=" * 100
    )

    print(
        f"Rows: "
        f"{len(df):,}"
    )

    print(
        f"Period: "
        f"{df['period'].min()} "
        f"to "
        f"{df['period'].max()}"
    )

    print(
        f"States: "
        f"{df['state'].nunique():,}"
    )

    print(
        f"Sectors: "
        f"{df['sector'].nunique():,}"
    )

    print(
        "\nSector counts:"
    )

    print(
        df[
            "sector"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # -------------------------------------------------------------
    # Expected long-format grain
    # -------------------------------------------------------------

    key = [
        "period",
        "state",
        "sector",
    ]

    duplicate_mask = (
        df.duplicated(
            subset=key,
            keep=False
        )
    )

    print(
        "\nDuplicate "
        "Period × State × Sector rows: "
        f"{duplicate_mask.sum():,}"
    )

    if duplicate_mask.any():

        print(
            "\nDuplicate sample:"
        )

        print(
            df.loc[
                duplicate_mask,
                key
            ]
            .sort_values(
                key
            )
            .head(
                50
            )
            .to_string(
                index=False
            )
        )

    # -------------------------------------------------------------
    # Missing values
    # -------------------------------------------------------------

    print(
        "\nMissing values:"
    )

    for col in [
        "period",
        "state",
        "sector",
        "revenue_thousand_dollars",
        "sales_mwh",
        "customers",
        "price_cents_per_kwh",
    ]:

        print(
            f"{col}: "
            f"{df[col].isna().sum():,}"
        )

    # -------------------------------------------------------------
    # Data status
    # -------------------------------------------------------------

    print(
        "\nData Status counts:"
    )

    print(
        df[
            "data_status"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # -------------------------------------------------------------
    # Coverage by year
    # -------------------------------------------------------------

    yearly = (
        df.groupby(
            "year"
        )
        .agg(
            rows=(
                "period",
                "size"
            ),

            months=(
                "month",
                "nunique"
            ),

            states=(
                "state",
                "nunique"
            ),

            sectors=(
                "sector",
                "nunique"
            ),
        )
    )

    print(
        "\nCoverage by year:"
    )

    print(
        yearly.to_string()
    )

    # -------------------------------------------------------------
    # Price consistency
    #
    # Revenue is thousand dollars.
    # sales_mwh × 1000 = kWh
    #
    # cents/kWh =
    # revenue_thousand_dollars * 1000 dollars
    # × 100 cents
    # / (sales_mwh × 1000 kWh)
    #
    # simplifies to:
    # revenue_thousand_dollars * 100
    # / sales_mwh
    # -------------------------------------------------------------

    calculable = df[
        df["revenue_thousand_dollars"].notna()
        & df["sales_mwh"].notna()
        & (
            df[
                "sales_mwh"
            ] != 0
        )
        & df[
            "price_cents_per_kwh"
        ].notna()
    ].copy()

    calculable[
        "calculated_price"
    ] = (
        calculable[
            "revenue_thousand_dollars"
        ]
        * 100
        / calculable[
            "sales_mwh"
        ]
    )

    calculable[
        "price_abs_diff"
    ] = (
        calculable[
            "calculated_price"
        ]
        - calculable[
            "price_cents_per_kwh"
        ]
    ).abs()

    print(
        "\nPrice consistency:"
    )

    print(
        "Rows compared: "
        f"{len(calculable):,}"
    )

    print(
        "Max absolute difference "
        "(cents/kWh): "
        f"{calculable['price_abs_diff'].max()}"
    )

    print(
        "Rows difference > 0.01 "
        "cents/kWh: "
        f"{(
            calculable[
                'price_abs_diff'
            ] > 0.01
        ).sum():,}"
    )

    # -------------------------------------------------------------
    # Latest period sample
    # -------------------------------------------------------------

    latest_period = (
        df["period"].max()
    )

    latest = df[
        df["period"]
        == latest_period
    ].copy()

    print(
        "\nLatest period:"
        f" {latest_period}"
    )

    print(
        f"Latest rows: "
        f"{len(latest):,}"
    )

    print(
        "\nLatest Massachusetts sample:"
    )

    ma = latest[
        latest["state"]
        == "MA"
    ]

    print(
        ma[
            [
                "period",
                "state",
                "sector",
                "sales_mwh",
                "customers",
                "price_cents_per_kwh",
                "data_status",
            ]
        ]
        .to_string(
            index=False
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print(
        "Loading EIA-861M "
        "Monthly-States..."
    )

    wide = (
        load_monthly_states()
    )

    print(
        f"Source rows: "
        f"{len(wide):,}"
    )

    print(
        "Reshaping wide sector "
        "groups to long format..."
    )

    long_df = (
        reshape_to_long(
            wide
        )
    )

    long_df = (
        clean_long(
            long_df
        )
    )

    validate(
        long_df
    )

    long_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        "\nSaved:"
    )

    print(
        OUTPUT_PATH
    )

    print(
        "\n=== EIA-861M RETAIL "
        "PRICE INGESTION COMPLETE ==="
    )


if __name__ == "__main__":
    main()