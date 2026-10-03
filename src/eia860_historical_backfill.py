from pathlib import Path
from zipfile import ZipFile
import tempfile
import re

import pandas as pd
from dbfread import DBF


# =============================================================================
# PATHS / SETTINGS
# =============================================================================

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)

START_YEAR = 2001
END_YEAR = 2025


# =============================================================================
# STATUS SEMANTICS
# =============================================================================

# Statuses representing generators that belong to the existing / operable
# generator fleet in the annual source snapshot.
#
# Important:
# This does NOT mean every unit is actively generating electricity.
# Example:
# SB = standby
# OS = out of service but expected to return
# OA = another operable status used in later data
# BU = backup
#
# These statuses are kept within the "operable" analytical capacity bucket.
OPERABLE_STATUSES = {
    "OP",
    "SB",
    "OS",
    "OA",
    "BU",
}

RETIRED_STATUSES = {
    "RE",
}

CANCELED_OR_POSTPONED_STATUSES = {
    "CN",
    "IP",
}


# =============================================================================
# CANONICAL OUTPUT SCHEMA
# =============================================================================

CANONICAL_COLUMNS = [
    "report_year",

    # Source semantics
    "source_record_type",
    "capacity_bucket",
    "operable_capacity_flag",

    # Identity
    "utility_id",
    "utility_name",
    "plant_code",
    "plant_name",
    "state",
    "county",
    "generator_id",

    # Generator characteristics
    "status",
    "technology",
    "prime_mover",

    # Capacity
    "nameplate_capacity_mw",
    "summer_capacity_mw",
    "winter_capacity_mw",

    # Historical operation dates
    "operating_month",
    "operating_year",

    # Retirement dates
    "retirement_month",
    "retirement_year",

    # Proposed / expected operation date
    "planned_operation_month",
    "planned_operation_year",

    # Planned retirement
    "planned_retirement_month",
    "planned_retirement_year",

    # Energy sources
    "energy_source_1",
    "energy_source_2",
    "energy_source_3",
    "energy_source_4",
    "energy_source_5",
    "energy_source_6",

    # Other useful dimensions
    "sector",
    "sector_name",
    "chp_flag",
    "ownership",

    # Data quality / provenance
    "missing_generator_id_flag",
    "duplicate_source_key_flag",

    "source_file",
    "source_sheet",
    "source_row_number",
]


# =============================================================================
# COLUMN NAME ALIASES ACROSS EIA-860 ERAS
# =============================================================================

COLUMN_ALIASES = {

    "utility_id": [
        "UTILCODE",
        "UTILITY_ID",
        "Utility ID",
    ],

    "utility_name": [
        "UTILNAME",
        "UTILITY_NAME",
        "Utility Name",
    ],

    "plant_code": [
        "PLNTCODE",
        "PLANT_CODE",
        "Plant Code",
    ],

    "plant_name": [
        "PLNTNAME",
        "PLANT_NAME",
        "Plant Name",
    ],

    "state": [
        "STATE",
        "State",
    ],

    "county": [
        "COUNTY",
        "County",
    ],

    "generator_id": [
        "GENCODE",
        "GENERATOR_ID",
        "Generator ID",
    ],

    "status": [
        "STATUS",
        "PROPOSED_STATUS",
        "Status",
    ],

    "technology": [
        "TECHNOLOGY",
        "Technology",
    ],

    "prime_mover": [
        "PRIMEMOVER",
        "PRIME_MOVER",
        "Prime Mover",
    ],

    "nameplate_capacity_mw": [
        "NAMEPLATE",
        "PROPOSED_NAMEPLATE",
        "Nameplate Capacity (MW)",
    ],

    "summer_capacity_mw": [
        "SUMMCAP",
        "SUMMER_CAPABILITY",
        "PROPOSED_SUMMER_CAPABILITY",
        "Summer Capacity (MW)",
    ],

    "winter_capacity_mw": [
        "WINTCAP",
        "WINTER_CAPABILITY",
        "PROPOSED_WINTER_CAPABILITY",
        "Winter Capacity (MW)",
    ],

    "operating_month": [
        "INSVMONTH",
        "OPERATING_MONTH",
        "Operating Month",
    ],

    "operating_year": [
        "INSVYEAR",
        "OPERATING_YEAR",
        "Operating Year",
    ],

    "retirement_month": [
        "RETIREMNTH",
        "RETIREMONTH",
        "RETIREMENT_MONTH",
        "Retirement Month",
    ],

    "retirement_year": [
        "RETIREYEAR",
        "RETIREMENT_YEAR",
        "Retirement Year",
    ],

    "planned_operation_month": [
        "CURMONTH",
        "CURRENT_MONTH",
        "CURRENT MONTH",
        "CURRENT_MONTH",
        "Current Month",
        "CURRENT MONTH",
        "Effective Month",
    ],

    "planned_operation_year": [
        "CURYEAR",
        "CURRENT_YEAR",
        "CURRRENT_YEAR",
        "Current Year",
        "Effective Year",
    ],

    "planned_retirement_month": [
        "PLANNED_RETIREMENT_MONTH",
        "Planned Retirement Month",
    ],

    "planned_retirement_year": [
        "PLANNED_RETIREMENT_YEAR",
        "Planned Retirement Year",
    ],

    "energy_source_1": [
        "ENSOURCE1",
        "ENERGY_SOURCE_1",
        "PROPOSED_ENERGY_SOURCE_1",
        "Energy Source 1",
    ],

    "energy_source_2": [
        "ENSOURCE2",
        "ENERGY_SOURCE_2",
        "PROPOSED_ENERGY_SOURCE_2",
        "Energy Source 2",
    ],

    "energy_source_3": [
        "ENSOURCE3",
        "ENERGY_SOURCE_3",
        "PROPOSED_ENERGY_SOURCE_3",
        "Energy Source 3",
    ],

    "energy_source_4": [
        "ENSOURCE4",
        "ENERGY_SOURCE_4",
        "PROPOSED_ENERGY_SOURCE_4",
        "Energy Source 4",
    ],

    "energy_source_5": [
        "ENSOURCE5",
        "ENERGY_SOURCE_5",
        "PROPOSED_ENERGY_SOURCE_5",
        "Energy Source 5",
    ],

    "energy_source_6": [
        "ENSOURCE6",
        "ENERGY_SOURCE_6",
        "PROPOSED_ENERGY_SOURCE_6",
        "Energy Source 6",
    ],

    "sector": [
        "SECTOR_NUMBER",
        "SECTOR",
        "Sector",
    ],

    "sector_name": [
        "SECTOR_NAME",
        "Sector Name",
    ],

    "chp_flag": [
        "COGEN",
        "COGENERATOR",
        "PROPOSED_COGENERATOR",
        "Associated with Combined Heat and Power System",
    ],

    "ownership": [
        "OWNER",
        "OWNERSHIP",
        "Ownership",
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def normalize_column_name(value):
    """
    Normalize column names only for matching across historical schema eras.
    Original source column names are not modified.
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def clean_string(series):
    """
    Preserve source strings while treating truly blank-like values as missing.
    """

    return (
        series
        .astype("string")
        .str.strip()
        .replace(
            {
                "": pd.NA,
                ".": pd.NA,
                "nan": pd.NA,
                "NaN": pd.NA,
                "None": pd.NA,
            }
        )
    )


def find_source_column(df, aliases):
    """
    Find the first matching source column using normalized,
    case-insensitive matching.
    """

    normalized_lookup = {
        normalize_column_name(col).upper(): col
        for col in df.columns
    }

    for alias in aliases:

        key = normalize_column_name(
            alias
        ).upper()

        if key in normalized_lookup:
            return normalized_lookup[key]

    return None


def find_case_insensitive(names, target):
    """
    Find a ZIP member name without assuming filename case.
    """

    target_lower = target.lower()

    for name in names:

        if name.lower() == target_lower:
            return name

    return None


# =============================================================================
# CAPACITY SEMANTICS
# =============================================================================

def classify_capacity_bucket(
    source_record_type,
    status
):
    """
    Convert source location + source status into an analytical capacity bucket.

    The original source_record_type and status are preserved separately.

    Buckets:
        operable
        planned
        retired
        canceled_or_postponed
        other
    """

    if pd.isna(status):
        status_clean = None
    else:
        status_clean = str(status).strip().upper()

    # -------------------------------------------------------------------------
    # Modern / historical existing fleet
    # -------------------------------------------------------------------------

    if source_record_type in {
        "existing",
        "operable",
    }:

        if status_clean in OPERABLE_STATUSES:
            return "operable"

        if status_clean in RETIRED_STATUSES:
            return "retired"

        if status_clean in CANCELED_OR_POSTPONED_STATUSES:
            return "canceled_or_postponed"

        return "other"

    # -------------------------------------------------------------------------
    # Proposed generator records
    # -------------------------------------------------------------------------

    if source_record_type == "proposed":

        if status_clean in CANCELED_OR_POSTPONED_STATUSES:
            return "canceled_or_postponed"

        if status_clean in RETIRED_STATUSES:
            return "retired"

        # Proposed records with statuses such as:
        # P, L, T, TS, U, V
        # remain planned capacity.
        return "planned"

    # -------------------------------------------------------------------------
    # Explicit retired / canceled sheets
    # -------------------------------------------------------------------------

    if source_record_type == "retired_canceled":

        if status_clean in RETIRED_STATUSES:
            return "retired"

        if status_clean in CANCELED_OR_POSTPONED_STATUSES:
            return "canceled_or_postponed"

        return "other"

    return "other"


def is_operable_capacity(
    source_record_type,
    status
):
    """
    Safe flag for capacity that belongs to the existing / operable fleet.

    Retired, canceled and proposed capacity must never enter this flag.
    """

    if source_record_type not in {
        "existing",
        "operable",
    }:
        return False

    if pd.isna(status):
        return False

    status_clean = str(status).strip().upper()

    return (
        status_clean
        in OPERABLE_STATUSES
    )


# =============================================================================
# CANONICALIZATION
# =============================================================================

def canonicalize(
    df,
    year,
    source_record_type,
    source_file,
    source_sheet
):
    """
    Convert one source table / sheet into the common historical schema.

    No source generator record is silently deduplicated here.
    """

    df = df.copy()

    df.reset_index(
        drop=True,
        inplace=True
    )

    out = pd.DataFrame(
        index=df.index
    )

    out["report_year"] = year

    out["source_record_type"] = (
        source_record_type
    )

    # Provenance row number within the parsed source table.
    # 1-based because it is easier to inspect manually.
    out["source_row_number"] = (
        df.index + 1
    )

    # -------------------------------------------------------------------------
    # Map historical source columns
    # -------------------------------------------------------------------------

    for canonical_name, aliases in COLUMN_ALIASES.items():

        source_col = find_source_column(
            df,
            aliases
        )

        if source_col is None:

            out[canonical_name] = pd.NA

        else:

            out[canonical_name] = (
                df[source_col]
            )

    # -------------------------------------------------------------------------
    # Provenance
    # -------------------------------------------------------------------------

    out["source_file"] = source_file
    out["source_sheet"] = source_sheet

    # -------------------------------------------------------------------------
    # String cleaning
    # -------------------------------------------------------------------------

    string_columns = [
        "utility_name",
        "plant_name",
        "state",
        "county",
        "generator_id",
        "status",
        "technology",
        "prime_mover",
        "energy_source_1",
        "energy_source_2",
        "energy_source_3",
        "energy_source_4",
        "energy_source_5",
        "energy_source_6",
        "sector_name",
        "chp_flag",
        "ownership",
    ]

    for col in string_columns:

        out[col] = clean_string(
            out[col]
        )

    # -------------------------------------------------------------------------
    # Numeric / integer conversion
    # -------------------------------------------------------------------------

    integer_columns = [
        "utility_id",
        "plant_code",

        "operating_month",
        "operating_year",

        "retirement_month",
        "retirement_year",

        "planned_operation_month",
        "planned_operation_year",

        "planned_retirement_month",
        "planned_retirement_year",

        "sector",
    ]

    for col in integer_columns:

        out[col] = pd.to_numeric(
            out[col],
            errors="coerce"
        ).astype("Int64")

    numeric_columns = [
        "nameplate_capacity_mw",
        "summer_capacity_mw",
        "winter_capacity_mw",
    ]

    for col in numeric_columns:

        out[col] = pd.to_numeric(
            out[col],
            errors="coerce"
        )

    # -------------------------------------------------------------------------
    # Remove non-record metadata/footer rows
    #
    # Important:
    # We do NOT require Generator ID because valid EIA records can have
    # missing Generator IDs.
    # -------------------------------------------------------------------------

    meaningful_record = (
        out["plant_code"].notna()
        | out["generator_id"].notna()
        | out["status"].notna()
        | out["nameplate_capacity_mw"].notna()
    )

    out = out[
        meaningful_record
    ].copy()

    # -------------------------------------------------------------------------
    # Analytical semantics
    # -------------------------------------------------------------------------

    out["capacity_bucket"] = [
        classify_capacity_bucket(
            source_record_type=row_source_type,
            status=row_status
        )
        for row_source_type, row_status
        in zip(
            out["source_record_type"],
            out["status"]
        )
    ]

    out["operable_capacity_flag"] = [
        is_operable_capacity(
            source_record_type=row_source_type,
            status=row_status
        )
        for row_source_type, row_status
        in zip(
            out["source_record_type"],
            out["status"]
        )
    ]

    # -------------------------------------------------------------------------
    # Missing-ID audit
    # -------------------------------------------------------------------------

    out["missing_generator_id_flag"] = (
        out["generator_id"].isna()
    )

    # Filled later after all source frames for the year are combined.
    out["duplicate_source_key_flag"] = False

    return out[
        CANONICAL_COLUMNS
    ]


# =============================================================================
# RAW FILE READERS
# =============================================================================

def read_dbf_from_zip(
    zip_file,
    filename,
    temp_dir
):

    path = zip_file.extract(
        filename,
        path=temp_dir
    )

    table = DBF(
        path,
        load=True,
        char_decode_errors="ignore"
    )

    return pd.DataFrame(
        iter(table)
    )


def read_excel_from_zip(
    zip_file,
    filename,
    sheet_name,
    header,
    temp_dir
):

    path = zip_file.extract(
        filename,
        path=temp_dir
    )

    return pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header,
        engine="calamine"
    )


# =============================================================================
# ERA 1: 2001-2003
# DBF
#
# GENYxx   = existing generator inventory
# PRGENYxx = proposed generator inventory
#
# PCGEN is deliberately excluded from this dataset because it represents
# proposed changes to EXISTING generators, not new generator inventory.
# =============================================================================

def parse_2001_2003(
    year,
    zip_path
):

    year2 = str(year)[-2:]

    existing_name = (
        f"GENY{year2}.dbf"
    )

    proposed_name = (
        f"PRGENY{year2}.dbf"
    )

    frames = []

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        names = z.namelist()

        existing_actual = (
            find_case_insensitive(
                names,
                existing_name
            )
        )

        proposed_actual = (
            find_case_insensitive(
                names,
                proposed_name
            )
        )

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            if existing_actual:

                df = read_dbf_from_zip(
                    z,
                    existing_actual,
                    temp_dir
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type="existing",
                        source_file=existing_actual,
                        source_sheet="existing_generator"
                    )
                )

            else:

                print(
                    f"WARNING: existing generator "
                    f"file not found for {year}"
                )

            if proposed_actual:

                df = read_dbf_from_zip(
                    z,
                    proposed_actual,
                    temp_dir
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type="proposed",
                        source_file=proposed_actual,
                        source_sheet="proposed_generator"
                    )
                )

            else:

                print(
                    f"WARNING: proposed generator "
                    f"file not found for {year}"
                )

    return frames


# =============================================================================
# ERA 2: 2004-2008
# OLD EXCEL
#
# GenYxx   = existing generator inventory, including retired records
# PRGenYxx = proposed generators, including canceled/postponed records
#
# PCGenYxx deliberately excluded here for same reason as above.
# =============================================================================

def parse_2004_2008(
    year,
    zip_path
):

    year2 = str(year)[-2:]

    existing_name = (
        f"GenY{year2}.xls"
    )

    proposed_name = (
        f"PRGenY{year2}.xls"
    )

    frames = []

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        names = z.namelist()

        existing_actual = (
            find_case_insensitive(
                names,
                existing_name
            )
        )

        proposed_actual = (
            find_case_insensitive(
                names,
                proposed_name
            )
        )

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            if existing_actual:

                df = read_excel_from_zip(
                    z,
                    existing_actual,
                    sheet_name=0,
                    header=0,
                    temp_dir=temp_dir
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type="existing",
                        source_file=existing_actual,
                        source_sheet="existing_generator"
                    )
                )

            else:

                print(
                    f"WARNING: existing generator "
                    f"file not found for {year}"
                )

            if proposed_actual:

                df = read_excel_from_zip(
                    z,
                    proposed_actual,
                    sheet_name=0,
                    header=0,
                    temp_dir=temp_dir
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type="proposed",
                        source_file=proposed_actual,
                        source_sheet="proposed_generator"
                    )
                )

            else:

                print(
                    f"WARNING: proposed generator "
                    f"file not found for {year}"
                )

    return frames


# =============================================================================
# ERA 3: 2009-2010
#
# Exist  = operable/existing generator fleet
# Prop   = proposed generators
# Ret_IP = retired and indefinitely postponed/canceled-type records
# =============================================================================

def parse_2009_2010(
    year,
    zip_path
):

    if year == 2009:

        workbook_expected = (
            "GeneratorY09.xls"
        )

    else:

        workbook_expected = (
            "GeneratorsY2010.xls"
        )

    frames = []

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        names = z.namelist()

        workbook = (
            find_case_insensitive(
                names,
                workbook_expected
            )
        )

        if workbook is None:

            raise FileNotFoundError(
                f"Generator workbook "
                f"not found for {year}"
            )

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            path = z.extract(
                workbook,
                path=temp_dir
            )

            sheet_map = {
                "Exist": "operable",
                "Prop": "proposed",
                "Ret_IP": "retired_canceled",
            }

            for sheet, source_type in sheet_map.items():

                df = pd.read_excel(
                    path,
                    sheet_name=sheet,
                    header=0,
                    engine="calamine"
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type=source_type,
                        source_file=workbook,
                        source_sheet=sheet
                    )
                )

    return frames


# =============================================================================
# ERA 4: 2011-2012
#
# Sheet names are close to modern EIA-860 but capitalization differs.
# =============================================================================

def parse_2011_2012(
    year,
    zip_path
):

    workbook_expected = (
        f"GeneratorY{year}.xlsx"
    )

    frames = []

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        names = z.namelist()

        workbook = (
            find_case_insensitive(
                names,
                workbook_expected
            )
        )

        if workbook is None:

            raise FileNotFoundError(
                f"Generator workbook "
                f"not found for {year}"
            )

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            path = z.extract(
                workbook,
                path=temp_dir
            )

            xl = pd.ExcelFile(
                path,
                engine="calamine"
            )

            for sheet in xl.sheet_names:

                sheet_lower = (
                    sheet.lower()
                )

                if "operable" in sheet_lower:

                    source_type = (
                        "operable"
                    )

                elif "proposed" in sheet_lower:

                    source_type = (
                        "proposed"
                    )

                elif (
                    "retired" in sheet_lower
                    or "canceled" in sheet_lower
                    or "cancelled" in sheet_lower
                ):

                    source_type = (
                        "retired_canceled"
                    )

                else:

                    continue

                df = pd.read_excel(
                    path,
                    sheet_name=sheet,
                    header=1,
                    engine="calamine"
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type=source_type,
                        source_file=workbook,
                        source_sheet=sheet
                    )
                )

    return frames


# =============================================================================
# ERA 5: 2013-2025
# MODERN EIA-860 GENERATOR WORKBOOK
# =============================================================================

def parse_2013_2025(
    year,
    zip_path
):

    workbook_expected = (
        f"3_1_Generator_Y{year}.xlsx"
    )

    frames = []

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        names = z.namelist()

        workbook = (
            find_case_insensitive(
                names,
                workbook_expected
            )
        )

        if workbook is None:

            raise FileNotFoundError(
                f"Generator workbook "
                f"not found for {year}"
            )

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            path = z.extract(
                workbook,
                path=temp_dir
            )

            sheet_map = {
                "Operable": "operable",
                "Proposed": "proposed",
                "Retired and Canceled": "retired_canceled",
            }

            for sheet, source_type in sheet_map.items():

                df = pd.read_excel(
                    path,
                    sheet_name=sheet,
                    header=1,
                    engine="calamine"
                )

                frames.append(
                    canonicalize(
                        df=df,
                        year=year,
                        source_record_type=source_type,
                        source_file=workbook,
                        source_sheet=sheet
                    )
                )

    return frames


# =============================================================================
# DUPLICATE FLAGGING
# =============================================================================

def add_duplicate_flags(df):
    """
    Flag duplicate source-level generator keys.

    We DO NOT delete duplicate records.

    A record is eligible for the key test only when:
        plant_code exists
        generator_id exists

    Key:
        report_year
        source_record_type
        plant_code
        generator_id

    This keeps different source categories separate.
    """

    df = df.copy()

    df[
        "duplicate_source_key_flag"
    ] = False

    valid_mask = (
        df["plant_code"].notna()
        & df["generator_id"].notna()
    )

    key_columns = [
        "report_year",
        "source_record_type",
        "plant_code",
        "generator_id",
    ]

    duplicated = (
        df.loc[
            valid_mask,
            key_columns
        ]
        .duplicated(
            keep=False
        )
    )

    df.loc[
        duplicated.index,
        "duplicate_source_key_flag"
    ] = duplicated

    return df


# =============================================================================
# VALIDATION REPORT
# =============================================================================

def validate_year(
    year,
    df
):

    print("\n" + "=" * 100)
    print(f"YEAR {year}")
    print("=" * 100)

    print(
        f"Rows: "
        f"{len(df):,}"
    )

    print(
        f"Plants: "
        f"{df['plant_code'].nunique():,}"
    )

    print(
        f"Missing Plant Code: "
        f"{df['plant_code'].isna().sum():,}"
    )

    print(
        f"Missing Generator ID: "
        f"{df['generator_id'].isna().sum():,}"
    )

    print(
        f"Duplicate source-key rows: "
        f"{df['duplicate_source_key_flag'].sum():,}"
    )

    print(
        "\nSource record types:"
    )

    print(
        df[
            "source_record_type"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nCapacity buckets:"
    )

    print(
        df[
            "capacity_bucket"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nStatus counts:"
    )

    print(
        df[
            "status"
        ]
        .value_counts(
            dropna=False
        )
        .head(30)
        .to_string()
    )

    print(
        "\nNameplate capacity by source record type:"
    )

    print(
        df.groupby(
            "source_record_type",
            dropna=False
        )[
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
        .to_string()
    )

    print(
        "\nNameplate capacity by analytical bucket:"
    )

    print(
        df.groupby(
            "capacity_bucket",
            dropna=False
        )[
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
        .to_string()
    )

    operable_capacity = (
        df.loc[
            df[
                "operable_capacity_flag"
            ],
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
    )

    print(
        "\nOperable-fleet nameplate capacity "
        f"(safe analytical flag): "
        f"{operable_capacity:,.1f} MW"
    )

    # -------------------------------------------------------------------------
    # Duplicate details
    # -------------------------------------------------------------------------

    dup = df[
        df[
            "duplicate_source_key_flag"
        ]
    ].copy()

    if len(dup) > 0:

        print(
            "\nDuplicate source-key sample:"
        )

        print(
            dup[
                [
                    "report_year",
                    "source_record_type",
                    "plant_code",
                    "plant_name",
                    "state",
                    "generator_id",
                    "status",
                    "prime_mover",
                    "nameplate_capacity_mw",
                    "source_file",
                    "source_sheet",
                    "source_row_number",
                ]
            ]
            .sort_values(
                [
                    "plant_code",
                    "generator_id",
                ]
            )
            .head(40)
            .to_string(
                index=False
            )
        )


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def main():

    annual_frames = []

    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):

        zip_path = (
            RAW_DIR
            / f"eia860{year}.zip"
        )

        if not zip_path.exists():

            print(
                f"\nMissing ZIP for {year}: "
                f"{zip_path}"
            )

            continue

        print(
            f"\nProcessing EIA-860 "
            f"{year}..."
        )

        # ---------------------------------------------------------------------
        # Select parser by schema era
        # ---------------------------------------------------------------------

        if year <= 2003:

            frames = (
                parse_2001_2003(
                    year,
                    zip_path
                )
            )

        elif year <= 2008:

            frames = (
                parse_2004_2008(
                    year,
                    zip_path
                )
            )

        elif year <= 2010:

            frames = (
                parse_2009_2010(
                    year,
                    zip_path
                )
            )

        elif year <= 2012:

            frames = (
                parse_2011_2012(
                    year,
                    zip_path
                )
            )

        else:

            frames = (
                parse_2013_2025(
                    year,
                    zip_path
                )
            )

        if not frames:

            print(
                f"No generator frames "
                f"produced for {year}"
            )

            continue

        # ---------------------------------------------------------------------
        # Combine all source categories for this year
        # ---------------------------------------------------------------------

        year_df = pd.concat(
            frames,
            ignore_index=True
        )

        year_df = (
            add_duplicate_flags(
                year_df
            )
        )

        # ---------------------------------------------------------------------
        # Validate before saving
        # ---------------------------------------------------------------------

        validate_year(
            year,
            year_df
        )

        # ---------------------------------------------------------------------
        # Save annual canonical file
        # ---------------------------------------------------------------------

        year_path = (
            PROCESSED_DIR
            / f"eia860_generators_{year}.csv"
        )

        year_df.to_csv(
            year_path,
            index=False
        )

        print(
            f"\nSaved: "
            f"{year_path}"
        )

        annual_frames.append(
            year_df
        )

    # =========================================================================
    # FINAL COMBINED DATASET
    # =========================================================================

    if not annual_frames:

        raise RuntimeError(
            "No EIA-860 data "
            "was parsed."
        )

    combined = pd.concat(
        annual_frames,
        ignore_index=True
    )

    # Re-run globally.
    # Key contains report_year, so this remains year-specific.
    combined = (
        add_duplicate_flags(
            combined
        )
    )

    combined_path = (
        PROCESSED_DIR
        / "fact_capacity_generators_2001_2025.csv"
    )

    combined.to_csv(
        combined_path,
        index=False
    )

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================

    print("\n" + "=" * 100)
    print("FINAL COMBINED DATASET")
    print("=" * 100)

    print(
        f"Rows: "
        f"{len(combined):,}"
    )

    print(
        f"Years: "
        f"{combined['report_year'].min()} "
        f"to "
        f"{combined['report_year'].max()}"
    )

    print(
        f"Unique plants: "
        f"{combined['plant_code'].nunique():,}"
    )

    valid_generators = combined[
        combined["plant_code"].notna()
        & combined["generator_id"].notna()
    ]

    unique_generator_keys = (
        valid_generators[
            [
                "plant_code",
                "generator_id",
            ]
        ]
        .drop_duplicates()
        .shape[0]
    )

    print(
        "Unique Plant Code × Generator ID "
        f"keys: {unique_generator_keys:,}"
    )

    print(
        f"Missing Plant Code: "
        f"{combined['plant_code'].isna().sum():,}"
    )

    print(
        f"Missing Generator ID: "
        f"{combined['generator_id'].isna().sum():,}"
    )

    print(
        f"Duplicate source-key rows: "
        f"{combined['duplicate_source_key_flag'].sum():,}"
    )

    print(
        "\nRows by source record type:"
    )

    print(
        combined[
            "source_record_type"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nRows by capacity bucket:"
    )

    print(
        combined[
            "capacity_bucket"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nNameplate capacity by "
        "capacity bucket:"
    )

    print(
        combined.groupby(
            "capacity_bucket",
            dropna=False
        )[
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
        .to_string()
    )

    # =========================================================================
    # 2025 CONTROL CHECK
    # =========================================================================

    latest_year = combined[
        combined[
            "report_year"
        ] == END_YEAR
    ].copy()

    latest_operable_capacity = (
        latest_year.loc[
            latest_year[
                "operable_capacity_flag"
            ],
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
    )

    latest_retired_capacity = (
        latest_year.loc[
            latest_year[
                "capacity_bucket"
            ] == "retired",
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
    )

    latest_planned_capacity = (
        latest_year.loc[
            latest_year[
                "capacity_bucket"
            ] == "planned",
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
    )

    latest_canceled_capacity = (
        latest_year.loc[
            latest_year[
                "capacity_bucket"
            ] == "canceled_or_postponed",
            "nameplate_capacity_mw"
        ]
        .sum(
            min_count=1
        )
    )

    print("\n" + "=" * 100)
    print(f"{END_YEAR} ANALYTICAL CAPACITY CHECK")
    print("=" * 100)

    print(
        f"Operable-fleet nameplate capacity: "
        f"{latest_operable_capacity:,.1f} MW"
    )

    print(
        f"Planned nameplate capacity: "
        f"{latest_planned_capacity:,.1f} MW"
    )

    print(
        f"Retired nameplate capacity: "
        f"{latest_retired_capacity:,.1f} MW"
    )

    print(
        "Canceled / postponed nameplate capacity: "
        f"{latest_canceled_capacity:,.1f} MW"
    )

    print(
        "\nSaved combined dataset:"
    )

    print(
        combined_path
    )


if __name__ == "__main__":
    main()