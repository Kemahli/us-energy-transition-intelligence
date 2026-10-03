from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")

YEAR = 2001
ARCHIVE = RAW_DIR / "f906920_2001.zip"
SHEET_NAME = "Page 1 Generation and Fuel Data"

TEST_PLANTS = [
    145,
    148,
    437,
    438,
    563,
    861,
]


def normalize_column_name(column):
    column = str(column)
    column = column.replace("\n", " ")
    column = column.strip()
    column = re.sub(r"\s+", " ", column)
    return column


def detect_header(excel_path):
    raw = pd.read_excel(
        excel_path,
        sheet_name=SHEET_NAME,
        header=None,
        nrows=15,
        engine="calamine"
    )

    for i in range(len(raw)):
        values = [
            str(value).lower().replace(" ", "")
            for value in raw.iloc[i].tolist()
        ]

        if "plantid" in values:
            return i

    raise ValueError("Could not detect header row")


with ZipFile(ARCHIVE, "r") as z:

    excel_files = [
        name for name in z.namelist()
        if name.lower().endswith((".xls", ".xlsx"))
    ]

    excel_name = excel_files[0]

    print(f"Workbook: {excel_name}")

    with tempfile.TemporaryDirectory() as temp_dir:

        excel_path = z.extract(
            excel_name,
            path=temp_dir
        )

        header_row = detect_header(excel_path)

        df = pd.read_excel(
            excel_path,
            sheet_name=SHEET_NAME,
            header=header_row,
            engine="calamine"
        )


# Normalize column names only for easier display
rename_map = {
    col: normalize_column_name(col)
    for col in df.columns
}

df = df.rename(columns=rename_map)


plant_col = [
    col for col in df.columns
    if col.lower().replace(" ", "") == "plantid"
][0]


sample = df[
    df[plant_col].isin(TEST_PLANTS)
].copy()


id_columns = [
    col for col in sample.columns[:19]
]

print("\n=== IDENTIFIER COLUMNS ===")

for i, col in enumerate(id_columns):
    print(f"{i:02d}: {col}")


print("\n=== RAW SOURCE ROWS FOR TEST PLANTS ===")

print(
    sample[
        id_columns
    ]
    .sort_values(
        by=[plant_col]
    )
    .to_string(index=False)
)


print("\n=== DIFFERENCE PROFILE WITHIN EACH PLANT ===")

for plant in TEST_PLANTS:

    plant_rows = sample[
        sample[plant_col] == plant
    ]

    print("\n" + "=" * 70)
    print(f"PLANT {plant}")
    print("=" * 70)

    for col in id_columns:

        values = (
            plant_rows[col]
            .drop_duplicates()
            .tolist()
        )

        if len(values) > 1:
            print(
                f"{col}: {values}"
            )