from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd

ZIP_PATH = Path("data/raw/eia8602025.zip")
WORKBOOK = "3_1_Generator_Y2025.xlsx"

SHEETS = [
    "Operable",
    "Proposed",
    "Retired and Canceled"
]


def clean_string(series):
    return (
        series
        .astype("string")
        .str.strip()
        .replace({
            "": pd.NA,
            ".": pd.NA
        })
    )


all_valid = []


with ZipFile(ZIP_PATH, "r") as z:

    with tempfile.TemporaryDirectory(
        ignore_cleanup_errors=True
    ) as temp_dir:

        path = z.extract(
            WORKBOOK,
            path=temp_dir
        )

        for sheet in SHEETS:

            df = pd.read_excel(
                path,
                sheet_name=sheet,
                header=1,
                engine="calamine"
            )

            df["Plant Code"] = pd.to_numeric(
                df["Plant Code"],
                errors="coerce"
            ).astype("Int64")

            df["Generator ID"] = clean_string(
                df["Generator ID"]
            )

            print("\n" + "=" * 90)
            print(sheet)
            print("=" * 90)

            missing_key = df[
                df["Plant Code"].isna()
                | df["Generator ID"].isna()
            ].copy()

            print(
                f"Rows with missing Plant Code or Generator ID: "
                f"{len(missing_key):,}"
            )

            if len(missing_key) > 0:

                cols = [
                    "Utility ID",
                    "Utility Name",
                    "Plant Code",
                    "Plant Name",
                    "State",
                    "Generator ID",
                    "Technology",
                    "Prime Mover",
                    "Status",
                    "Nameplate Capacity (MW)"
                ]

                print(
                    missing_key[cols]
                    .to_string(index=False)
                )

            completely_empty = df[
                df.notna().sum(axis=1) == 0
            ]

            print(
                f"\nCompletely empty rows: "
                f"{len(completely_empty):,}"
            )

            valid = df[
                df["Plant Code"].notna()
                & df["Generator ID"].notna()
            ].copy()

            valid["source_sheet"] = sheet

            all_valid.append(
                valid[
                    [
                        "Plant Code",
                        "Generator ID",
                        "Plant Name",
                        "State",
                        "Technology",
                        "Prime Mover",
                        "Status",
                        "Nameplate Capacity (MW)",
                        "source_sheet"
                    ]
                ]
            )


combined = pd.concat(
    all_valid,
    ignore_index=True
)


key = [
    "Plant Code",
    "Generator ID"
]

dup = combined[
    combined.duplicated(
        subset=key,
        keep=False
    )
].copy()


print("\n" + "=" * 90)
print("VALID RECORD CROSS-SHEET TEST")
print("=" * 90)

if len(dup) == 0:

    print(
        "No Plant Code × Generator ID overlaps "
        "across valid records."
    )

else:

    groups = (
        dup.groupby(
            key,
            dropna=False
        )["source_sheet"]
        .nunique()
    )

    multi_sheet = groups[
        groups > 1
    ]

    print(
        f"Keys appearing in multiple sheets: "
        f"{len(multi_sheet):,}"
    )

    if len(multi_sheet) > 0:

        keys = (
            multi_sheet
            .reset_index()[key]
        )

        sample = dup.merge(
            keys,
            on=key,
            how="inner"
        )

        print(
            sample.sort_values(
                key + ["source_sheet"]
            )
            .head(50)
            .to_string(index=False)
        )


print("\n=== DIAGNOSIS COMPLETE ===")