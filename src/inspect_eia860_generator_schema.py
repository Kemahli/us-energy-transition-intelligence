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


with ZipFile(ZIP_PATH, "r") as z:

    with tempfile.TemporaryDirectory(
        ignore_cleanup_errors=True
    ) as temp_dir:

        excel_path = z.extract(
            WORKBOOK,
            path=temp_dir
        )

        for sheet in SHEETS:

            print("\n" + "=" * 100)
            print(f"SHEET: {sheet}")
            print("=" * 100)

            raw = pd.read_excel(
                excel_path,
                sheet_name=sheet,
                header=None,
                nrows=15,
                engine="calamine"
            )

            print("\n=== FIRST 15 RAW ROWS ===")
            print(
                raw.to_string(
                    index=True,
                    header=False
                )
            )

            print("\n=== POSSIBLE HEADER ROWS ===")

            for i in range(len(raw)):

                non_null = raw.iloc[i].notna().sum()

                if non_null >= 5:
                    print(
                        f"Row {i}: "
                        f"{raw.iloc[i].tolist()}"
                    )


print("\n=== INSPECTION COMPLETE ===")