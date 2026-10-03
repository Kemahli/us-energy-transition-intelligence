from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd

RAW_DIR = Path("data/raw")

CASES = {
    2001: {
        "file": "GENY01.dbf",
        "type": "dbf"
    },
    2004: {
        "file": "GenY04.xls",
        "type": "excel"
    },
    2009: {
        "file": "GeneratorY09.xls",
        "type": "excel"
    },
    2013: {
        "file": "3_1_Generator_Y2013.xlsx",
        "type": "excel"
    },
    2025: {
        "file": "3_1_Generator_Y2025.xlsx",
        "type": "excel"
    }
}


def inspect_excel(path):
    xl = pd.ExcelFile(
        path,
        engine="calamine"
    )

    print("Sheets:")
    for sheet in xl.sheet_names:
        print(f"  - {sheet}")

    for sheet in xl.sheet_names[:3]:

        print("\n" + "-" * 80)
        print(f"SHEET: {sheet}")
        print("-" * 80)

        raw = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            nrows=8,
            engine="calamine"
        )

        print(
            raw.to_string(
                index=True,
                header=False
            )
        )


def inspect_dbf(path):
    try:
        from dbfread import DBF
    except ImportError:
        print(
            "dbfread is not installed."
        )
        print(
            "Run: pip install dbfread"
        )
        return

    table = DBF(
        path,
        load=False
    )

    print("\nDBF fields:")

    for field in table.fields:
        print(
            f"{field.name} | "
            f"type={field.type} | "
            f"length={field.length}"
        )

    print("\nFirst 5 records:")

    for i, record in enumerate(table):

        print(dict(record))

        if i >= 4:
            break


for year, config in CASES.items():

    print("\n" + "=" * 100)
    print(f"YEAR {year}")
    print("=" * 100)

    zip_path = (
        RAW_DIR
        / f"eia860{year}.zip"
    )

    if not zip_path.exists():
        print(
            f"Missing ZIP: {zip_path}"
        )
        continue

    with ZipFile(zip_path, "r") as z:

        target = config["file"]

        if target not in z.namelist():
            print(
                f"Expected file not found: {target}"
            )
            print("Available files:")

            for name in z.namelist():
                print(name)

            continue

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            path = z.extract(
                target,
                path=temp_dir
            )

            print(
                f"File: {target}"
            )

            if config["type"] == "dbf":
                inspect_dbf(path)

            else:
                inspect_excel(path)


print(
    "\n=== SCHEMA ERA INSPECTION COMPLETE ==="
)