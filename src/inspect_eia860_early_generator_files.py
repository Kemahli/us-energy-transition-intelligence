from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd

try:
    from dbfread import DBF
except ImportError:
    DBF = None


RAW_DIR = Path("data/raw")

CASES = {
    2001: [
        "GENY01.dbf",
        "PRGENY01.dbf",
    ],
    2002: [
        "GENY02.dbf",
        "PRGENY02.dbf",
        "PCGENY02.dbf",
    ],
    2004: [
        "GenY04.xls",
        "PRGenY04.xls",
        "PCGenY04.xls",
    ],
}


def inspect_dbf(path):
    if DBF is None:
        print("dbfread not installed")
        return

    table = DBF(
        path,
        load=False
    )

    print("\nFIELDS:")

    for field in table.fields:
        print(field.name)

    print("\nFIRST 3 RECORDS:")

    for i, record in enumerate(table):
        print(dict(record))

        if i >= 2:
            break


def inspect_excel(path):
    xl = pd.ExcelFile(
        path,
        engine="calamine"
    )

    print("\nSHEETS:")
    print(xl.sheet_names)

    for sheet in xl.sheet_names:

        print("\n" + "-" * 80)
        print(f"SHEET: {sheet}")
        print("-" * 80)

        raw = pd.read_excel(
            path,
            sheet_name=sheet,
            header=None,
            nrows=5,
            engine="calamine"
        )

        print(
            raw.to_string(
                index=True,
                header=False
            )
        )


for year, filenames in CASES.items():

    print("\n" + "=" * 100)
    print(f"YEAR {year}")
    print("=" * 100)

    zip_path = RAW_DIR / f"eia860{year}.zip"

    with ZipFile(zip_path, "r") as z:

        for filename in filenames:

            print("\n" + "#" * 100)
            print(f"FILE: {filename}")
            print("#" * 100)

            if filename not in z.namelist():
                print("FILE NOT FOUND")
                continue

            with tempfile.TemporaryDirectory(
                ignore_cleanup_errors=True
            ) as temp_dir:

                path = z.extract(
                    filename,
                    path=temp_dir
                )

                if filename.lower().endswith(".dbf"):
                    inspect_dbf(path)

                else:
                    inspect_excel(path)


print(
    "\n=== EARLY GENERATOR FILE INSPECTION COMPLETE ==="
)