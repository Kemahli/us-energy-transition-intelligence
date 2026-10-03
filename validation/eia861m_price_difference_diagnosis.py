from pathlib import Path

import pandas as pd


PATH = Path(
    "data/processed/fact_retail_prices_2010_current.csv"
)


df = pd.read_csv(
    PATH,
    parse_dates=["period"]
)


# =============================================================================
# CALCULATE IMPLIED PRICE
# =============================================================================

valid = df[
    df["sales_mwh"].notna()
    & df["revenue_thousand_dollars"].notna()
    & df["price_cents_per_kwh"].notna()
    & (df["sales_mwh"] != 0)
].copy()


valid["calculated_price"] = (
    valid["revenue_thousand_dollars"]
    * 100
    / valid["sales_mwh"]
)


valid["price_abs_diff"] = (
    valid["calculated_price"]
    - valid["price_cents_per_kwh"]
).abs()


# =============================================================================
# SUMMARY
# =============================================================================

print("=" * 110)
print("EIA-861M PRICE DIFFERENCE DIAGNOSIS")
print("=" * 110)

print(
    f"Rows compared: {len(valid):,}"
)

print(
    f"Max absolute difference: "
    f"{valid['price_abs_diff'].max():.6f}"
)

print(
    f"Rows > 0.01: "
    f"{(valid['price_abs_diff'] > 0.01).sum():,}"
)

print(
    f"Rows > 0.05: "
    f"{(valid['price_abs_diff'] > 0.05).sum():,}"
)

print(
    f"Rows > 0.10: "
    f"{(valid['price_abs_diff'] > 0.10).sum():,}"
)


# =============================================================================
# BY YEAR
# =============================================================================

problem = valid[
    valid["price_abs_diff"] > 0.01
].copy()


print("\n" + "=" * 110)
print("ROWS > 0.01 BY YEAR")
print("=" * 110)

print(
    problem["year"]
    .value_counts()
    .sort_index()
    .to_string()
)


# =============================================================================
# BY SECTOR
# =============================================================================

print("\n" + "=" * 110)
print("ROWS > 0.01 BY SECTOR")
print("=" * 110)

print(
    problem["sector"]
    .value_counts()
    .to_string()
)


# =============================================================================
# YEAR × SECTOR
# =============================================================================

print("\n" + "=" * 110)
print("ROWS > 0.01 BY YEAR × SECTOR")
print("=" * 110)

year_sector = (
    problem.groupby(
        ["year", "sector"]
    )
    .size()
    .unstack(
        fill_value=0
    )
)

print(
    year_sector.to_string()
)


# =============================================================================
# TOP DIFFERENCES
# =============================================================================

print("\n" + "=" * 110)
print("TOP 40 ABSOLUTE PRICE DIFFERENCES")
print("=" * 110)

columns = [
    "period",
    "state",
    "sector",
    "data_status",
    "revenue_thousand_dollars",
    "sales_mwh",
    "price_cents_per_kwh",
    "calculated_price",
    "price_abs_diff",
]

top = (
    valid.sort_values(
        "price_abs_diff",
        ascending=False
    )
    .head(40)
)

print(
    top[
        columns
    ].to_string(
        index=False
    )
)


# =============================================================================
# SALES SIZE OF PROBLEM ROWS
# =============================================================================

print("\n" + "=" * 110)
print("SALES SIZE FOR DIFFERENCE > 0.01")
print("=" * 110)

if len(problem) > 0:

    print(
        problem["sales_mwh"]
        .describe()
        .to_string()
    )


# =============================================================================
# ZERO-SALES RECORDS
# =============================================================================

zero_sales = df[
    df["sales_mwh"] == 0
].copy()

print("\n" + "=" * 110)
print("ZERO-SALES ROWS")
print("=" * 110)

print(
    f"Zero-sales rows: "
    f"{len(zero_sales):,}"
)

print("\nBy sector:")

print(
    zero_sales[
        "sector"
    ]
    .value_counts()
    .to_string()
)

print("\nPrice values on zero-sales rows:")

print(
    zero_sales[
        "price_cents_per_kwh"
    ]
    .value_counts(
        dropna=False
    )
    .head(20)
    .to_string()
)


print(
    "\n=== PRICE DIFFERENCE DIAGNOSIS COMPLETE ==="
)