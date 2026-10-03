from pathlib import Path
from zipfile import ZipFile

RAW_DIR = Path("data/raw")

YEARS = range(2001, 2009)


for year in YEARS:

    zip_path = (
        RAW_DIR
        / f"eia860{year}.zip"
    )

    print("\n" + "=" * 100)
    print(f"YEAR {year}")
    print("=" * 100)

    if not zip_path.exists():
        print(f"Missing ZIP: {zip_path}")
        continue

    with ZipFile(zip_path, "r") as z:

        files = z.namelist()

        print(
            f"Files in archive: "
            f"{len(files)}"
        )

        for name in files:
            print(name)


print("\n=== EARLY ARCHIVE INSPECTION COMPLETE ===")