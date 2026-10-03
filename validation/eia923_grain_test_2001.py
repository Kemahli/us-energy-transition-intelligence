from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")
ARCHIVE = RAW_DIR / "f906920_2001.zip"

SHEET_NAME = "Page 1 Generation and Fuel Data"
YEAR = 2001

MONTH_MAP = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12
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
        if n.lower().endswith((".xls", ".xlsx"))
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


# --------------------------------------------------
# Identify monthly generation columns
# --------------------------------------------------

netgen_cols = {}

for col in df.columns:

    upper = col.upper()

    if not upper.startswith("NETGEN_"):
        continue

    month = upper.replace("NETGEN_", "")

    if month in MONTH_MAP:
        netgen_cols[MONTH_MAP[month]] = col


if len(netgen_cols) != 12:
    raise ValueError(
        f"Expected 12 Netgen columns, found {len(netgen_cols)}"
    )


# --------------------------------------------------
# Preserve candidate identifier columns
# --------------------------------------------------

id_cols = [
    "Plant ID",
    "Plant Name",
    "State",
    "Combined Heat & Power Plant",
    "Nuclear Unit I.D.",
    "Operator ID",
    "EIA Sector Number",
    "Sector Name",
    "Reported Prime Mover",
    "Reported Fuel Type Code",
    "AER Fuel Type Code",
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


# --------------------------------------------------
# Candidate grain tests
# --------------------------------------------------

base = [
    "period",
    "State",
    "Plant ID",
    "Reported Fuel Type Code",
    "Reported Prime Mover"
]

tests = {
    "A_base": base,

    "B_plus_aer_fuel": base + [
        "AER Fuel Type Code"
    ],

    "C_plus_sector": base + [
        "AER Fuel Type Code",
        "EIA Sector Number"
    ],

    "D_plus_chp": base + [
        "AER Fuel Type Code",
        "EIA Sector Number",
        "Combined Heat & Power Plant"
    ],

    "E_plus_nuclear_unit": base + [
        "AER Fuel Type Code",
        "EIA Sector Number",
        "Combined Heat & Power Plant",
        "Nuclear Unit I.D."
    ],

    "F_plus_operator": base + [
        "AER Fuel Type Code",
        "EIA Sector Number",
        "Combined Heat & Power Plant",
        "Nuclear Unit I.D.",
        "Operator ID"
    ]
}


print("\n=== 2001 GRAIN TEST ===")

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


# --------------------------------------------------
# Inspect remaining duplicates under richest key
# --------------------------------------------------

final_key = tests[
    "F_plus_operator"
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