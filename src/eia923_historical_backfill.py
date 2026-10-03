from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd
import re

RAW_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")

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


def normalize_column_name(column):
    column = str(column)
    column = column.replace("\n", " ")
    column = column.strip()
    column = re.sub(r"\s+", " ", column)
    return column


def get_archive_path(year):
    if year <= 2007:
        return RAW_DIR / f"f906920_{year}.zip"

    return RAW_DIR / f"f923_{year}.zip"


def choose_generation_workbook(zip_file):
    excel_files = [
        name for name in zip_file.namelist()
        if name.lower().endswith((".xls", ".xlsx"))
    ]

    candidates = []

    for name in excel_files:
        lower_name = name.lower()

        if "schedule_8" in lower_name:
            continue

        if "schedule 8" in lower_name:
            continue

        if "source" in lower_name and "disposition" in lower_name:
            continue

        if "nonutility" in lower_name:
            continue

        candidates.append(name)

    for name in candidates:
        lower_name = name.lower()

        if (
            "2_3_4_5" in lower_name
            or "eia923december" in lower_name
            or "f906920" in lower_name
        ):
            return name

    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(
        f"Could not uniquely identify generation workbook: {candidates}"
    )


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


def find_column(columns, candidates):
    normalized_lookup = {
        normalize_column_name(col).lower(): col
        for col in columns
    }

    for candidate in candidates:
        candidate_normalized = candidate.lower()

        if candidate_normalized in normalized_lookup:
            return normalized_lookup[candidate_normalized]

    return None


def identify_netgen_columns(columns):
    result = {}

    for col in columns:
        normalized = normalize_column_name(col).upper()

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
            f"Expected 12 monthly Netgen columns, found {len(result)}"
        )

    return result


def clean_string_column(series):
    return (
        series
        .astype("string")
        .str.strip()
        .replace({
            "": pd.NA,
            ".": pd.NA,
            "nan": pd.NA
        })
    )


def parse_year(year):
    archive_path = get_archive_path(year)

    print("\n" + "=" * 70)
    print(f"Processing {year}")
    print("=" * 70)

    if not archive_path.exists():
        raise FileNotFoundError(
            f"Missing archive: {archive_path}"
        )

    with ZipFile(archive_path, "r") as z:
        excel_name = choose_generation_workbook(z)

        print(f"Workbook: {excel_name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            excel_path = z.extract(
                excel_name,
                path=temp_dir
            )

            header_row = detect_header(excel_path)

            print(f"Detected header row: {header_row}")
            print("Reading generation sheet...")

            df = pd.read_excel(
                excel_path,
                sheet_name=SHEET_NAME,
                header=header_row,
                engine="calamine"
            )

            print("Generation sheet loaded.")

    df.columns = [
        normalize_column_name(col)
        for col in df.columns
    ]

    plant_col = find_column(
        df.columns,
        ["Plant ID", "Plant Id"]
    )

    plant_name_col = find_column(
        df.columns,
        ["Plant Name"]
    )

    state_col = find_column(
        df.columns,
        ["State", "Plant State"]
    )

    fuel_col = find_column(
        df.columns,
        ["Reported Fuel Type Code"]
    )

    prime_mover_col = find_column(
        df.columns,
        ["Reported Prime Mover"]
    )

    fuel_group_col = find_column(
        df.columns,
        [
            "AER Fuel Type Code",
            "MER Fuel Type Code"
        ]
    )

    sector_col = find_column(
        df.columns,
        ["EIA Sector Number"]
    )

    sector_name_col = find_column(
        df.columns,
        ["Sector Name"]
    )

    nuclear_col = find_column(
        df.columns,
        [
            "Nuclear Unit I.D.",
            "Nuclear Unit Id"
        ]
    )

    chp_col = find_column(
        df.columns,
        [
            "Combined Heat & Power Plant",
            "Combined Heat And Power Plant"
        ]
    )

    physical_unit_col = find_column(
        df.columns,
        ["Physical Unit Label"]
    )

    operator_id_col = find_column(
        df.columns,
        ["Operator ID", "Operator Id"]
    )

    operator_name_col = find_column(
        df.columns,
        ["Operator Name"]
    )

    required_columns = {
        "plant": plant_col,
        "plant_name": plant_name_col,
        "state": state_col,
        "fuel": fuel_col,
        "prime_mover": prime_mover_col,
        "fuel_group": fuel_group_col,
        "sector": sector_col,
        "nuclear": nuclear_col,
        "chp": chp_col,
        "physical_unit": physical_unit_col
    }

    missing_required = [
        name
        for name, col in required_columns.items()
        if col is None
    ]

    if missing_required:
        raise ValueError(
            f"{year}: missing required columns: {missing_required}"
        )

    netgen_columns = identify_netgen_columns(
        df.columns
    )

    id_columns = [
        plant_col,
        plant_name_col,
        state_col,
        fuel_col,
        prime_mover_col,
        fuel_group_col,
        sector_col,
        nuclear_col,
        chp_col,
        physical_unit_col
    ]

    optional_columns = []

    if sector_name_col is not None:
        optional_columns.append(sector_name_col)

    if operator_id_col is not None:
        optional_columns.append(operator_id_col)

    if operator_name_col is not None:
        optional_columns.append(operator_name_col)

    source_columns = (
        id_columns
        + optional_columns
        + list(netgen_columns.values())
    )

    generation_df = df[
        source_columns
    ].copy()

    rename_months = {
        original_col: month_number
        for month_number, original_col
        in netgen_columns.items()
    }

    generation_df = generation_df.rename(
        columns=rename_months
    )

    long_df = generation_df.melt(
        id_vars=id_columns + optional_columns,
        value_vars=list(range(1, 13)),
        var_name="month",
        value_name="generation_mwh"
    )

    long_df["generation_mwh"] = pd.to_numeric(
        long_df["generation_mwh"],
        errors="coerce"
    )

    long_df["period"] = pd.to_datetime(
        {
            "year": year,
            "month": long_df["month"],
            "day": 1
        }
    )

    rename_map = {
        plant_col: "plant_code",
        plant_name_col: "plant_name",
        state_col: "state",
        fuel_col: "fuel_code",
        prime_mover_col: "prime_mover",
        fuel_group_col: "fuel_group_code",
        sector_col: "eia_sector_number",
        nuclear_col: "nuclear_unit_id",
        chp_col: "chp_flag",
        physical_unit_col: "physical_unit"
    }

    if sector_name_col is not None:
        rename_map[sector_name_col] = "sector_name"

    if operator_id_col is not None:
        rename_map[operator_id_col] = "operator_id"

    if operator_name_col is not None:
        rename_map[operator_name_col] = "operator_name"

    long_df = long_df.rename(
        columns=rename_map
    )

    string_columns = [
        "plant_name",
        "state",
        "fuel_code",
        "prime_mover",
        "fuel_group_code",
        "nuclear_unit_id",
        "chp_flag",
        "physical_unit"
    ]

    if "sector_name" in long_df.columns:
        string_columns.append("sector_name")

    if "operator_name" in long_df.columns:
        string_columns.append("operator_name")

    for col in string_columns:
        long_df[col] = clean_string_column(
            long_df[col]
        )

    long_df["plant_code"] = pd.to_numeric(
        long_df["plant_code"],
        errors="coerce"
    ).astype("Int64")

    long_df["eia_sector_number"] = pd.to_numeric(
        long_df["eia_sector_number"],
        errors="coerce"
    ).astype("Int64")

    if "operator_id" in long_df.columns:
        long_df["operator_id"] = pd.to_numeric(
            long_df["operator_id"],
            errors="coerce"
        ).astype("Int64")

    final_columns = [
        "period",
        "state",
        "plant_code",
        "plant_name",
        "fuel_code",
        "prime_mover",
        "fuel_group_code",
        "eia_sector_number",
        "nuclear_unit_id",
        "chp_flag",
        "physical_unit"
    ]

    if "sector_name" in long_df.columns:
        final_columns.append("sector_name")

    if "operator_id" in long_df.columns:
        final_columns.append("operator_id")

    if "operator_name" in long_df.columns:
        final_columns.append("operator_name")

    final_columns.append(
        "generation_mwh"
    )

    long_df = long_df[
        final_columns
    ]

    grain_key = [
        "period",
        "state",
        "plant_code",
        "fuel_code",
        "prime_mover",
        "fuel_group_code",
        "eia_sector_number",
        "nuclear_unit_id",
        "chp_flag",
        "physical_unit"
    ]

    duplicate_mask = long_df.duplicated(
        subset=grain_key,
        keep=False
    )

    duplicate_rows = int(
        duplicate_mask.sum()
    )

    if duplicate_rows > 0:
        raise ValueError(
            f"{year}: final grain validation failed. "
            f"{duplicate_rows:,} rows involved in duplicate keys."
        )

    output_file = (
        OUTPUT_DIR
        / f"eia923_generation_{year}.csv"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    long_df.to_csv(
        output_file,
        index=False
    )

    print(f"Source rows: {len(df):,}")
    print(f"Output rows: {len(long_df):,}")
    print(
        f"Plants: "
        f"{long_df['plant_code'].nunique():,}"
    )
    print(
        f"Missing generation: "
        f"{long_df['generation_mwh'].isna().sum():,}"
    )
    print(
        f"Duplicate grain rows: "
        f"{duplicate_rows:,}"
    )
    print(f"Saved: {output_file}")

    return long_df


def main():
    all_years = []

    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):
        year_df = parse_year(year)
        all_years.append(year_df)

    print("\nCombining all years...")

    combined = pd.concat(
        all_years,
        ignore_index=True
    )

    grain_key = [
        "period",
        "state",
        "plant_code",
        "fuel_code",
        "prime_mover",
        "fuel_group_code",
        "eia_sector_number",
        "nuclear_unit_id",
        "chp_flag",
        "physical_unit"
    ]

    duplicate_mask = combined.duplicated(
        subset=grain_key,
        keep=False
    )

    duplicate_rows = int(
        duplicate_mask.sum()
    )

    if duplicate_rows > 0:
        raise ValueError(
            "Combined dataset failed final grain validation: "
            f"{duplicate_rows:,} duplicate rows."
        )

    combined_file = (
        OUTPUT_DIR
        / "fact_generation_2001_2025.csv"
    )

    combined.to_csv(
        combined_file,
        index=False
    )

    print("\n" + "=" * 70)
    print("FINAL HISTORICAL GENERATION BUILD COMPLETE")
    print("=" * 70)

    print(
        f"Combined rows: "
        f"{len(combined):,}"
    )

    print(
        "Period range:",
        combined["period"].min(),
        "to",
        combined["period"].max()
    )

    print(
        f"Unique plants: "
        f"{combined['plant_code'].nunique():,}"
    )

    print(
        f"Missing generation values: "
        f"{combined['generation_mwh'].isna().sum():,}"
    )

    print(
        f"Duplicate grain rows: "
        f"{duplicate_rows:,}"
    )

    print(
        f"Final dataset: "
        f"{combined_file}"
    )


if __name__ == "__main__":
    main()