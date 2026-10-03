from pathlib import Path
from zipfile import ZipFile
import requests
import pandas as pd
import tempfile

URL = "https://www.eia.gov/electricity/data/eia860/xls/eia8602025.zip"

RAW_DIR = Path("data/raw")
ZIP_PATH = RAW_DIR / "eia8602025.zip"

RAW_DIR.mkdir(parents=True, exist_ok=True)


def download_file():
    if ZIP_PATH.exists():
        print(f"ZIP already exists: {ZIP_PATH}")
        return

    print("Downloading 2025 EIA-860 ZIP...")

    response = requests.get(
        URL,
        timeout=120
    )

    response.raise_for_status()

    ZIP_PATH.write_bytes(
        response.content
    )

    print(f"Saved: {ZIP_PATH}")


def inspect_zip():
    with ZipFile(ZIP_PATH, "r") as z:

        print("\n=== ZIP CONTENTS ===")

        for name in z.namelist():
            print(name)

        excel_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(
                (".xls", ".xlsx")
            )
        ]

        print("\n=== EXCEL FILES ===")

        for name in excel_files:
            print(name)

        with tempfile.TemporaryDirectory() as temp_dir:

            for name in excel_files:

                extracted_path = z.extract(
                    name,
                    path=temp_dir
                )

                try:
                    xl = pd.ExcelFile(
                        extracted_path,
                        engine="calamine"
                    )

                    print(
                        f"\n=== WORKBOOK: {name} ==="
                    )

                    print("Sheets:")

                    for sheet in xl.sheet_names:
                        print(f"  - {sheet}")

                except Exception as exc:
                    print(
                        f"\nCould not inspect {name}: {exc}"
                    )


if __name__ == "__main__":
    download_file()
    inspect_zip()