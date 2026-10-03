from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")

START_YEAR = 2001
END_YEAR = 2025

SHEET_NAME = "Page 1 Generation and Fuel Data"

SHORT_MONTHS = {
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

FULL_MONTHS = {
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


def get_archive(year):
    if year <= 2007:
        return RAW_DIR / f"f906920_{year}.zip"

    return RAW_DIR / f"f923_{year}.zip"


def choose_workbook(z):
    excel_files = [
        name for name in z.namelist()
        if name.lower().endswith((".xls", ".xlsx"))
    ]

    candidates = []

    for name in excel_files:
        lower = name.lower()

        if "schedule_8" in lower:
            continue

        if "schedule 8" in lower:
            continue

        if "source" in lower and "disposition" in lower:
            continue

        if "nonutility" in lower:
            continue

        candidates.append(name)

    for name in candidates:
        lower = name.lower()

        if (
            "2_3_4_5" in lower
            or "eia923december" in lower
            or "f906920" in lower
        ):
            return name

    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(
        f"Could not identify workbook: {candidates}"
    )


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


def find_col(columns, candidates):
    lookup = {
        normalize(col).lower(): col
        for col in columns
    }

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def identify_netgen(columns):
    result = {}

    for col in columns:
        normalized = normalize(col).upper()

        if not normalized.startswith("NETGEN"):
            continue

        remainder = normalized.replace(
            "NETGEN",
            ""
        ).strip(" _")

        if remainder in SHORT_MONTHS:
            result[SHORT_MONTHS[remainder]] = col

        elif remainder in FULL_MONTHS:
            result[FULL_MONTHS[remainder]] = col

    if len(result) != 12:
        raise ValueError(
            f"Expected 12 Netgen columns, found {len(result)}"
        )

    return result


results = []


for year in range(
    START_YEAR,
    END_YEAR + 1
):

    print("\n" + "=" * 70)
    print(f"Testing {year}")
    print("=" * 70)

    archive = get_archive(year)

    with ZipFile(archive, "r") as z:

        workbook = choose_workbook(z)

        with tempfile.TemporaryDirectory() as temp_dir:

            path = z.extract(
                workbook,
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

    plant_col = find_col(
        df.columns,
        ["Plant ID", "Plant Id"]
    )

    state_col = find_col(
        df.columns,
        ["State", "Plant State"]
    )

    fuel_col = find_col(
        df.columns,
        ["Reported Fuel Type Code"]
    )

    prime_col = find_col(
        df.columns,
        ["Reported Prime Mover"]
    )

    sector_col = find_col(
        df.columns,
        ["EIA Sector Number"]
    )

    nuclear_col = find_col(
        df.columns,
        [
            "Nuclear Unit I.D.",
            "Nuclear Unit Id"
        ]
    )

    fuel_group_col = find_col(
        df.columns,
        [
            "AER Fuel Type Code",
            "MER Fuel Type Code"
        ]
    )

    chp_col = find_col(
        df.columns,
        [
            "Combined Heat & Power Plant",
            "Combined Heat And Power Plant"
        ]
    )

    physical_unit_col = find_col(
        df.columns,
        ["Physical Unit Label"]
    )

    required = {
        "plant": plant_col,
        "state": state_col,
        "fuel": fuel_col,
        "prime": prime_col,
        "sector": sector_col,
        "nuclear": nuclear_col,
        "fuel_group": fuel_group_col,
        "chp": chp_col,
        "physical_unit": physical_unit_col
    }

    missing_required = [
        name
        for name, col in required.items()
        if col is None
    ]

    if missing_required:
        print(
            f"Missing columns: {missing_required}"
        )

        results.append(
            {
                "year": year,
                "duplicate_rows": None,
                "duplicate_groups": None,
                "max_group_size": None,
                "status": "MISSING COLUMNS"
            }
        )

        continue

    netgen = identify_netgen(
        df.columns
    )

    id_cols = [
        state_col,
        plant_col,
        fuel_col,
        prime_col,
        fuel_group_col,
        sector_col,
        nuclear_col,
        chp_col,
        physical_unit_col
    ]

    work = df[
        id_cols + list(netgen.values())
    ].copy()

    work = work.rename(
        columns={
            original: month
            for month, original in netgen.items()
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
            "year": year,
            "month": long["month"],
            "day": 1
        }
    )

    key = [
        "period",
        state_col,
        plant_col,
        fuel_col,
        prime_col,
        fuel_group_col,
        sector_col,
        nuclear_col,
        chp_col,
        physical_unit_col
    ]

    duplicated = long.duplicated(
        subset=key,
        keep=False
    )

    duplicate_rows = int(
        duplicated.sum()
    )

    if duplicate_rows > 0:

        duplicate_groups = (
            long[duplicated]
            .groupby(
                key,
                dropna=False
            )
            .size()
        )

        group_count = len(
            duplicate_groups
        )

        max_group = int(
            duplicate_groups.max()
        )

    else:
        group_count = 0
        max_group = 0

    print(
        f"Duplicate rows: {duplicate_rows:,}"
    )

    print(
        f"Duplicate groups: {group_count:,}"
    )

    print(
        f"Maximum group size: {max_group}"
    )

    results.append(
        {
            "year": year,
            "duplicate_rows": duplicate_rows,
            "duplicate_groups": group_count,
            "max_group_size": max_group,
            "status": (
                "PASS"
                if duplicate_rows == 0
                else "FAIL"
            )
        }
    )


results_df = pd.DataFrame(
    results
)


print("\n" + "=" * 70)
print("UNIVERSAL GRAIN VALIDATION SUMMARY")
print("=" * 70)

print(
    results_df.to_string(
        index=False
    )
)


failed = results_df[
    results_df["status"] != "PASS"
]


print("\nYears failing universal grain:")

if len(failed) == 0:
    print("NONE")
else:
    print(
        failed[
            [
                "year",
                "status",
                "duplicate_rows",
                "duplicate_groups"
            ]
        ]
        .to_string(index=False)
    )


print("\n=== VALIDATION COMPLETE ===")