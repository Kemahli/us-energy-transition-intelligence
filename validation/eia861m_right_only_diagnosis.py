from pathlib import Path

import pandas as pd


HIST_PATH = Path(
    "data/raw/eia861m_sales_revenue_2010_current.xlsx"
)

CURRENT_PATH = Path(
    "data/raw/eia861m_sales_2026.xlsx"
)


def load_historical():

    raw = pd.read_excel(
        HIST_PATH,
        sheet_name="Monthly-States",
        header=None,
        engine="calamine"
    )

    df = raw.iloc[3:, :4].copy()

    df.columns = [
        "Year",
        "Month",
        "State",
        "Data Status",
    ]

    df["Year"] = pd.to_numeric(
        df["Year"],
        errors="coerce"
    )

    df["Month"] = pd.to_numeric(
        df["Month"],
        errors="coerce"
    )

    df["State"] = (
        df["State"]
        .astype("string")
        .str.strip()
    )

    df = df[
        df["Year"].notna()
        & df["Month"].notna()
        & df["State"].notna()
    ].copy()

    return df


def load_current():

    raw = pd.read_excel(
        CURRENT_PATH,
        sheet_name="Sales Ultimate Cust. -States",
        header=None,
        engine="calamine"
    )

    df = raw.iloc[3:].copy()

    df = df.iloc[:, :7]

    df.columns = [
        "Year",
        "Month",
        "Utility Number",
        "Utility Name",
        "State",
        "Ownership",
        "Data Status",
    ]

    df["Year"] = pd.to_numeric(
        df["Year"],
        errors="coerce"
    )

    df["Utility Number"] = pd.to_numeric(
        df["Utility Number"],
        errors="coerce"
    )

    df["State"] = (
        df["State"]
        .astype("string")
        .str.strip()
    )

    return df


hist = load_historical()

current = load_current()

current_total = current[
    current["Utility Number"] == 88888
].copy()


merged = current_total.merge(
    hist[
        [
            "Year",
            "Month",
            "State",
        ]
    ],
    on=[
        "Year",
        "Month",
        "State",
    ],
    how="left",
    indicator=True
)


right_only = merged[
    merged["_merge"] == "left_only"
].copy()


print("=" * 100)
print("CURRENT STATE TOTAL ROWS NOT IN HISTORICAL MONTHLY-STATES")
print("=" * 100)

print(
    f"Rows: {len(right_only):,}"
)

print()

print(
    right_only[
        [
            "Year",
            "Month",
            "State",
            "Utility Number",
            "Utility Name",
            "Data Status",
        ]
    ].to_string(
        index=False
    )
)

print(
    "\nRaw Month representations:"
)

for value in right_only["Month"]:

    print(
        repr(value)
    )


print(
    "\n=== RIGHT-ONLY DIAGNOSIS COMPLETE ==="
)