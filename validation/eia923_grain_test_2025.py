from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")
ARCHIVE = RAW_DIR / "f923_2025.zip"

SHEET_NAME = "Page 1 Generation and Fuel Data"
YEAR = 2025

MONTH_MAP = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12
}


def normalize(col):
    col = str(col).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", col)


def detect_header(path):
    raw = pd.read_excel(
        path,
        sheet_name=SHEET_NAME,
        header=None,
        nrows=15,
        engine="calamine"
    )

    for i in range(len(raw)):
        vals = [
            str(v).lower().replace(" ", "")
            for v in raw.iloc[i]
        ]

        if "plantid" in vals:
            return i

    raise ValueError("Header not found")


with ZipFile(ARCHIVE, "r") as z:

    excel_name = [
        n for n in z.namelist()
        if "Schedules_2_3_4_5" in n
        and n.lower().endswith((".xls", ".xlsx"))
    ][0]

    with tempfile.TemporaryDirectory() as temp_dir:

        path = z.extract(
            excel_name,
            path=temp_dir
        )

        header = detect_header(path)

        df = pd.read_excel(
            path,
            sheet_name=SHEET_NAME,
            header=header,
            engine="calamine"
        )


df.columns = [
    normalize(c)
    for c in df.columns
]


netgen_cols = {}

for col in df.columns:

    upper = col.upper()

    if not upper.startswith("NETGEN"):
        continue

    remainder = upper.replace("NETGEN", "").strip()

    if remainder in MONTH_MAP:
        netgen_cols[MONTH_MAP[remainder]] = col


if len(netgen_cols) != 12:
    raise ValueError(
        f"Expected 12 Netgen columns, found {len(netgen_cols)}"
    )


id_cols = [
    "Plant Id",
    "Plant Name",
    "Plant State",
    "Combined Heat And Power Plant",
    "Nuclear Unit Id",
    "Operator Id",
    "EIA Sector Number",
    "Sector Name",
    "Reported Prime Mover",
    "Reported Fuel Type Code",
    "MER Fuel Type Code",
    "Respondent Frequency",
    "Physical Unit Label"
]


work = df[
    id_cols + list(netgen_cols.values())
].copy()


work = work.rename(
    columns={
        original: month
        for month, original in netgen_cols.items()
    }
)


long = work.melt(
    id_vars=id_cols,
    value_vars=list(range(1, 13)),
    var_name="month",
    value_name="generation_mwh"
)


long["period"] = pd.to_datetime(
    {
        "year": YEAR,
        "month": long["month"],
        "day": 1
    }
)


long["generation_mwh"] = pd.to_numeric(
    long["generation_mwh"],
    errors="coerce"
)


base = [
    "period",
    "Plant State",
    "Plant Id",
    "Reported Fuel Type Code",
    "Reported Prime Mover"
]


tests = {
    "A_base": base,

    "B_plus_mer_fuel": base + [
        "MER Fuel Type Code"
    ],

    "C_plus_sector": base + [
        "MER Fuel Type Code",
        "EIA Sector Number"
    ],

    "D_plus_respondent_frequency": base + [
        "MER Fuel Type Code",
        "EIA Sector Number",
        "Respondent Frequency"
    ],

    "E_plus_chp": base + [
        "MER Fuel Type Code",
        "EIA Sector Number",
        "Respondent Frequency",
        "Combined Heat And Power Plant"
    ],

    "F_plus_nuclear_unit": base + [
        "MER Fuel Type Code",
        "EIA Sector Number",
        "Respondent Frequency",
        "Combined Heat And Power Plant",
        "Nuclear Unit Id"
    ]
}


print("\n=== 2025 GRAIN TEST ===")

for name, key in tests.items():

    duplicated = long.duplicated(
        subset=key,
        keep=False
    )

    groups = (
        long[duplicated]
        .groupby(
            key,
            dropna=False
        )
        .size()
    )

    print("\n" + name)

    print(
        f"Rows involved in duplicate keys: "
        f"{duplicated.sum():,}"
    )

    print(
        f"Duplicate key groups: "
        f"{len(groups):,}"
    )

    if len(groups) > 0:
        print(
            f"Max rows in one group: "
            f"{groups.max()}"
        )


final_key = tests[
    "F_plus_nuclear_unit"
]

remaining = long[
    long.duplicated(
        subset=final_key,
        keep=False
    )
].copy()


print("\n=== REMAINING DUPLICATES UNDER RICHEST KEY ===")

print(
    f"Remaining rows: "
    f"{len(remaining):,}"
)

if len(remaining) > 0:
    print(
        remaining[
            final_key
            + [
                "Plant Name",
                "Sector Name",
                "Physical Unit Label",
                "generation_mwh"
            ]
        ]
        .sort_values(final_key)
        .head(50)
        .to_string(index=False)
    )


print("\n=== TEST COMPLETE ===")