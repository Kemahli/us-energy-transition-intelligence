from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")

YEARS = [2002, 2024]

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
    files = [
        name for name in z.namelist()
        if name.lower().endswith((".xls", ".xlsx"))
    ]

    candidates = []

    for name in files:
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
        values = [
            str(v).lower().replace(" ", "")
            for v in raw.iloc[i]
        ]

        if "plantid" in values:
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

    return result


for year in YEARS:

    print("\n" + "=" * 100)
    print(f"YEAR {year}")
    print("=" * 100)

    archive = get_archive(year)

    with ZipFile(archive, "r") as z:

        workbook = choose_workbook(z)

        print(f"Workbook: {workbook}")

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

    plant = find_col(
        df.columns,
        ["Plant ID", "Plant Id"]
    )

    state = find_col(
        df.columns,
        ["State", "Plant State"]
    )

    fuel = find_col(
        df.columns,
        ["Reported Fuel Type Code"]
    )

    prime = find_col(
        df.columns,
        ["Reported Prime Mover"]
    )

    fuel_group = find_col(
        df.columns,
        [
            "AER Fuel Type Code",
            "MER Fuel Type Code"
        ]
    )

    sector = find_col(
        df.columns,
        ["EIA Sector Number"]
    )

    nuclear = find_col(
        df.columns,
        [
            "Nuclear Unit I.D.",
            "Nuclear Unit Id"
        ]
    )

    netgen = identify_netgen(
        df.columns
    )

    # All source identifier columns before monthly measures
    first_netgen_or_quantity = min(
        [
            df.columns.get_loc(col)
            for col in netgen.values()
        ]
    )

    identifier_columns = list(
        df.columns[:first_netgen_or_quantity]
    )

    work = df[
        identifier_columns
        + list(netgen.values())
    ].copy()

    work = work.rename(
        columns={
            original: month
            for month, original in netgen.items()
        }
    )

    long = work.melt(
        id_vars=identifier_columns,
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

    universal_key = [
        "period",
        state,
        plant,
        fuel,
        prime,
        fuel_group,
        sector,
        nuclear
    ]

    duplicate_mask = long.duplicated(
        subset=universal_key,
        keep=False
    )

    dup = long[
        duplicate_mask
    ].copy()

    print(
        f"\nRows under investigation: "
        f"{len(dup):,}"
    )

    groups = (
        dup.groupby(
            universal_key,
            dropna=False
        )
        .size()
        .reset_index(name="row_count")
    )

    print(
        f"Duplicate groups: "
        f"{len(groups):,}"
    )

    # --------------------------------------------------
    # Which remaining identifier columns split duplicates?
    # --------------------------------------------------

    extra_columns = [
        col
        for col in identifier_columns
        if col not in universal_key
    ]

    print(
        "\n=== CANDIDATE COLUMN DIFFERENCES ==="
    )

    candidate_results = []

    for col in extra_columns:

        variation = (
            dup.groupby(
                universal_key,
                dropna=False
            )[col]
            .nunique(
                dropna=False
            )
        )

        groups_split = int(
            (variation > 1).sum()
        )

        if groups_split > 0:

            candidate_results.append(
                (
                    col,
                    groups_split
                )
            )

    candidate_results.sort(
        key=lambda x: x[1],
        reverse=True
    )

    for col, groups_split in candidate_results:

        print(
            f"{col}: differs in "
            f"{groups_split:,} duplicate groups"
        )


    # --------------------------------------------------
    # Show first sample groups with all identifiers
    # --------------------------------------------------

    print(
        "\n=== RAW DUPLICATE SAMPLE ==="
    )

    sample_keys = groups[
        universal_key
    ].head(5)

    samples = dup.merge(
        sample_keys,
        on=universal_key,
        how="inner"
    )

    display_columns = (
        universal_key
        + [
            col
            for col, _ in candidate_results
        ]
        + ["generation_mwh"]
    )

    display_columns = list(
        dict.fromkeys(display_columns)
    )

    print(
        samples[
            display_columns
        ]
        .sort_values(
            universal_key
        )
        .to_string(index=False)
    )


print("\n=== DIAGNOSIS COMPLETE ===")