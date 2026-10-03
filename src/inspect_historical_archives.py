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

for year, config in archives.items():

    archive_path = RAW_DIR / config["archive"]
    keyword = config["keyword"].lower()

    print("\n" + "=" * 80)
    print(f"YEAR: {year}")
    print(f"ARCHIVE: {config['archive']}")
    print("=" * 80)

    with ZipFile(archive_path, "r") as z:

        matches = [
            name for name in z.namelist()
            if keyword in name.lower()
            and name.lower().endswith((".xls", ".xlsx"))
        ]

        if not matches:
            print("No matching workbook found")
            continue

        for excel_name in matches:

            print(f"\nFILE: {excel_name}")

            with tempfile.TemporaryDirectory() as temp_dir:

                extracted_path = z.extract(
                    excel_name,
                    path=temp_dir
                )

                try:
                    with pd.ExcelFile(extracted_path) as xls:

                        print("SHEETS:")

                        for sheet in xls.sheet_names:
                            print(f"  - {sheet}")

                except Exception as e:
                    print(f"Could not inspect: {e}")