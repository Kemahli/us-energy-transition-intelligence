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


all_sheets = []


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

            df["Generator ID"] = clean_string(
                df["Generator ID"]
            )

            df["Plant Code"] = pd.to_numeric(
                df["Plant Code"],
                errors="coerce"
            ).astype("Int64")

            df["source_sheet"] = sheet

            print("\n" + "=" * 80)
            print(f"SHEET: {sheet}")
            print("=" * 80)

            print(
                f"Rows: {len(df):,}"
            )

            print(
                f"Unique plants: "
                f"{df['Plant Code'].nunique():,}"
            )

            print(
                f"Missing Plant Code: "
                f"{df['Plant Code'].isna().sum():,}"
            )

            print(
                f"Missing Generator ID: "
                f"{df['Generator ID'].isna().sum():,}"
            )

            key = [
                "Plant Code",
                "Generator ID"
            ]

            duplicated = df.duplicated(
                subset=key,
                keep=False
            )

            duplicate_rows = int(
                duplicated.sum()
            )

            print(
                f"Duplicate key rows: "
                f"{duplicate_rows:,}"
            )

            if duplicate_rows > 0:

                groups = (
                    df[duplicated]
                    .groupby(
                        key,
                        dropna=False
                    )
                    .size()
                    .reset_index(
                        name="row_count"
                    )
                )

                print(
                    f"Duplicate groups: "
                    f"{len(groups):,}"
                )

                print(
                    "\nDuplicate sample:"
                )

                print(
                    df[duplicated][
                        [
                            "Plant Code",
                            "Plant Name",
                            "State",
                            "Generator ID",
                            "Technology",
                            "Prime Mover",
                            "Status",
                            "Nameplate Capacity (MW)"
                        ]
                    ]
                    .sort_values(key)
                    .head(30)
                    .to_string(index=False)
                )

            print(
                "\nStatus counts:"
            )

            print(
                df["Status"]
                .value_counts(
                    dropna=False
                )
                .to_string()
            )

            print(
                "\nTotal nameplate capacity (MW):"
            )

            print(
                pd.to_numeric(
                    df["Nameplate Capacity (MW)"],
                    errors="coerce"
                ).sum()
            )

            all_sheets.append(
                df[
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
                ].copy()
            )


combined = pd.concat(
    all_sheets,
    ignore_index=True
)


print("\n" + "=" * 80)
print("CROSS-SHEET KEY TEST")
print("=" * 80)

key = [
    "Plant Code",
    "Generator ID"
]

cross_duplicates = combined.duplicated(
    subset=key,
    keep=False
)

cross = combined[
    cross_duplicates
].copy()

print(
    f"Rows sharing Plant Code × Generator ID "
    f"across combined sheets: {len(cross):,}"
)

if len(cross) > 0:

    groups = (
        cross.groupby(
            key,
            dropna=False
        )["source_sheet"]
        .nunique()
    )

    multi_sheet_keys = groups[
        groups > 1
    ]

    print(
        f"Keys appearing in more than one sheet: "
        f"{len(multi_sheet_keys):,}"
    )

    if len(multi_sheet_keys) > 0:

        multi_sheet_df = (
            multi_sheet_keys
            .reset_index()[key]
        )

        sample = cross.merge(
            multi_sheet_df,
            on=key,
            how="inner"
        )

        print(
            "\nCross-sheet overlap sample:"
        )

        print(
            sample[
                [
                    "Plant Code",
                    "Plant Name",
                    "State",
                    "Generator ID",
                    "Technology",
                    "Prime Mover",
                    "Status",
                    "Nameplate Capacity (MW)",
                    "source_sheet"
                ]
            ]
            .sort_values(
                key + ["source_sheet"]
            )
            .head(50)
            .to_string(index=False)
        )


print("\n=== TEST COMPLETE ===")