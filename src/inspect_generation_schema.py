from pathlib import Path
from zipfile import ZipFile
import pandas as pd
import tempfile

RAW_DIR = Path("data/raw")

archives = {
    2024: {
        "archive": "f923_2024.zip",
        "keyword": "Schedules_2_3_4_5"
    },
    2010: {
        "archive": "f923_2010.zip",
        "keyword": "SCHEDULES 2_3_4_5"
    },
    2007: {
        "archive": "f906920_2007.zip",
        "keyword": "f906920_2007"
    },
}

SHEET_NAME = "Page 1 Generation and Fuel Data"

for year, config in archives.items():

    print("\n" + "=" * 100)
    print(f"YEAR: {year}")
    print("=" * 100)

    archive_path = RAW_DIR / config["archive"]
    keyword = config["keyword"].lower()

    with ZipFile(archive_path, "r") as z:

        excel_name = [
            name for name in z.namelist()
            if keyword in name.lower()
            and name.lower().endswith((".xls", ".xlsx"))
        ][0]

        with tempfile.TemporaryDirectory() as temp_dir:

            extracted_path = z.extract(
                excel_name,
                path=temp_dir
            )

            raw = pd.read_excel(
                extracted_path,
                sheet_name=SHEET_NAME,
                header=None,
                nrows=12
            )

            print("\nFIRST 12 ROWS, FIRST 12 COLUMNS:")
            print(
                raw.iloc[:, :12]
                .to_string(index=True, header=False)
            )

            header_row = None

            for i in range(len(raw)):

                row_values = (
                    raw.iloc[i]
                    .astype(str)
                    .str.strip()
                    .tolist()
                )

                normalized = [
                    value.lower().replace(" ", "")
                    for value in row_values
                ]

                if "plantid" in normalized:
                    header_row = i
                    break

            print(f"\nDetected header row: {header_row}")

            if header_row is None:
                print("Could not detect header")
                continue

            df = pd.read_excel(
                extracted_path,
                sheet_name=SHEET_NAME,
                header=header_row,
                nrows=5
            )

            print("\nCOLUMNS:")

            for i, col in enumerate(df.columns):
                print(f"{i:02d}: {repr(col)}")