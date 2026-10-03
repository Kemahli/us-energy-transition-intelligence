from pathlib import Path
import tempfile
import urllib.request

import pandas as pd


RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)


HISTORICAL_URL = (
    "https://www.eia.gov/electricity/data/eia861m/"
    "xls/sales_revenue.xlsx"
)

CURRENT_2026_URL = (
    "https://www.eia.gov/electricity/data/eia861m/"
    "xls/sales_ult_cust_2026.xlsx"
)


HISTORICAL_PATH = (
    RAW_DIR
    / "eia861m_sales_revenue_2010_current.xlsx"
)

CURRENT_2026_PATH = (
    RAW_DIR
    / "eia861m_sales_2026.xlsx"
)


def download_file(url, path):

    if path.exists():

        print(
            f"Already exists: {path}"
        )

        return

    print(
        f"Downloading:\n{url}"
    )

    urllib.request.urlretrieve(
        url,
        path
    )

    print(
        f"Saved: {path}"
    )


def inspect_workbook(path, label):

    print("\n" + "=" * 110)
    print(label)
    print("=" * 110)

    xl = pd.ExcelFile(
        path,
        engine="calamine"
    )

    print("\nSHEETS:")

    for sheet in xl.sheet_names:
        print(
            f"  - {sheet}"
        )

    for sheet in xl.sheet_names:

        print("\n" + "-" * 110)
        print(
            f"SHEET: {sheet}"
        )
        print("-" * 110)

        raw = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            nrows=12,
            engine="calamine"
        )

        print(
            "\nFIRST 12 RAW ROWS:"
        )

        print(
            raw.to_string(
                index=True,
                header=False
            )
        )

        print(
            "\nPOSSIBLE HEADER SEARCH:"
        )

        header_candidates = []

        for idx, row in raw.iterrows():

            row_text = (
                row.astype("string")
                .fillna("")
                .str.lower()
                .tolist()
            )

            combined = " | ".join(
                row_text
            )

            keywords = [
                "year",
                "month",
                "state",
                "sector",
                "revenue",
                "sales",
                "customers",
            ]

            hits = sum(
                keyword in combined
                for keyword in keywords
            )

            if hits >= 3:

                header_candidates.append(
                    idx
                )

        print(
            f"Header candidates: "
            f"{header_candidates}"
        )

        for header_row in header_candidates:

            try:

                df = pd.read_excel(
                    path,
                    sheet_name=sheet,
                    header=header_row,
                    engine="calamine"
                )

                print(
                    "\nColumns using "
                    f"header={header_row}:"
                )

                for col in df.columns:
                    print(
                        f"  {col}"
                    )

                print(
                    "\nShape:"
                )

                print(
                    df.shape
                )

                print(
                    "\nFIRST 5 DATA ROWS:"
                )

                print(
                    df.head(
                        5
                    ).to_string(
                        index=False
                    )
                )

            except Exception as exc:

                print(
                    f"Could not parse "
                    f"header={header_row}: "
                    f"{exc}"
                )


def inspect_candidate_grain(path):

    print("\n" + "=" * 110)
    print("HISTORICAL WORKBOOK GRAIN TEST")
    print("=" * 110)

    xl = pd.ExcelFile(
        path,
        engine="calamine"
    )

    for sheet in xl.sheet_names:

        raw = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            nrows=15,
            engine="calamine"
        )

        header_row = None

        for idx, row in raw.iterrows():

            values = (
                row.astype("string")
                .fillna("")
                .str.lower()
            )

            text = " | ".join(
                values.tolist()
            )

            if (
                "state" in text
                and "sector" in text
                and (
                    "sales" in text
                    or "revenue" in text
                )
            ):

                header_row = idx
                break

        if header_row is None:
            continue

        df = pd.read_excel(
            path,
            sheet_name=sheet,
            header=header_row,
            engine="calamine"
        )

        normalized = {
            str(col)
            .strip()
            .lower()
            .replace("\n", " "): col
            for col in df.columns
        }

        print("\n" + "-" * 110)
        print(
            f"SHEET: {sheet}"
        )
        print(
            f"Detected header row: "
            f"{header_row}"
        )

        print(
            f"Rows: {len(df):,}"
        )

        print(
            "\nNORMALIZED COLUMN NAMES:"
        )

        for col in normalized:
            print(
                f"  {col}"
            )

        possible_grain_cols = []

        for candidate in [
            "year",
            "month",
            "state",
            "sector",
            "industry sector category",
            "data status",
        ]:

            for normalized_name, original_name in normalized.items():

                if candidate == normalized_name:
                    possible_grain_cols.append(
                        original_name
                    )

        print(
            "\nCandidate grain columns:"
        )

        print(
            possible_grain_cols
        )

        if possible_grain_cols:

            valid = df[
                possible_grain_cols
            ].copy()

            duplicate_count = (
                valid.duplicated(
                    keep=False
                )
                .sum()
            )

            print(
                "Duplicate rows using candidate "
                f"grain: {duplicate_count:,}"
            )

            if duplicate_count > 0:

                dup = df[
                    valid.duplicated(
                        keep=False
                    )
                ]

                print(
                    "\nDuplicate sample:"
                )

                cols = (
                    possible_grain_cols
                    + [
                        col
                        for col in df.columns
                        if col
                        not in possible_grain_cols
                    ][:5]
                )

                print(
                    dup[
                        cols
                    ]
                    .head(
                        30
                    )
                    .to_string(
                        index=False
                    )
                )


def main():

    download_file(
        HISTORICAL_URL,
        HISTORICAL_PATH
    )

    download_file(
        CURRENT_2026_URL,
        CURRENT_2026_PATH
    )

    inspect_workbook(
        HISTORICAL_PATH,
        "EIA-861M SALES & REVENUE "
        "2010-CURRENT"
    )

    inspect_workbook(
        CURRENT_2026_PATH,
        "EIA-861M SALES & REVENUE "
        "2026"
    )

    inspect_candidate_grain(
        HISTORICAL_PATH
    )

    print(
        "\n=== EIA-861M SALES SCHEMA "
        "INSPECTION COMPLETE ==="
    )


if __name__ == "__main__":
    main()