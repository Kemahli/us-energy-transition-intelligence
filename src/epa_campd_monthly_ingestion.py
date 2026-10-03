import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
from dotenv import load_dotenv


# =============================================================================
# CONFIG
# =============================================================================

load_dotenv()

EPA_API_KEY = os.getenv(
    "EPA_API_KEY"
)

if not EPA_API_KEY:
    raise RuntimeError(
        "EPA_API_KEY not found in .env"
    )


BASE_URL = (
    "https://api.epa.gov/easey/"
    "streaming-services/emissions/"
    "apportioned/monthly/by-facility"
)


START_YEAR = 2001
END_YEAR = 2025

MONTHS = list(
    range(
        1,
        13
    )
)


RAW_DIR = Path(
    "data/raw"
)

PROCESSED_DIR = Path(
    "data/processed"
)

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_PATH = (
    PROCESSED_DIR
    / "fact_emissions_monthly_2001_2025.csv"
)


REQUEST_PAUSE_SECONDS = 0.15

MAX_RETRIES = 4

RETRY_WAIT_SECONDS = 5


# =============================================================================
# EXPECTED SOURCE FIELDS
# =============================================================================

SOURCE_FIELDS = [
    "stateCode",
    "facilityName",
    "facilityId",
    "year",
    "month",
    "grossLoad",
    "steamLoad",
    "so2Mass",
    "co2Mass",
    "noxMass",
    "heatInput",
]


# =============================================================================
# RAW CACHE PATH
# =============================================================================

def raw_cache_path(
    year,
    month
):

    return (
        RAW_DIR
        / (
            f"epa_campd_monthly_facility_"
            f"{year}_{month:02d}.json"
        )
    )


# =============================================================================
# API REQUEST
# =============================================================================

def request_month(
    year,
    month
):

    params = {
        "api_key":
            EPA_API_KEY,

        "year":
            year,

        "month":
            [month],
    }

    query = urlencode(
        params,
        doseq=True
    )

    url = (
        BASE_URL
        + "?"
        + query
    )

    safe_url = url.replace(
        EPA_API_KEY,
        "***API_KEY***"
    )

    request = Request(
        url,
        headers={
            "Accept":
                "application/json",

            "User-Agent":
                "us-energy-transition-intelligence/1.0",
        }
    )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            print(
                f"Requesting "
                f"{year}-{month:02d} "
                f"(attempt {attempt})"
            )

            with urlopen(
                request,
                timeout=180
            ) as response:

                body = (
                    response.read()
                    .decode(
                        "utf-8"
                    )
                )

            payload = json.loads(
                body
            )

            if not isinstance(
                payload,
                list
            ):

                raise RuntimeError(
                    f"Unexpected EPA payload "
                    f"for {year}-{month:02d}. "
                    f"Expected list, got "
                    f"{type(payload).__name__}"
                )

            print(
                f"  Records: "
                f"{len(payload):,}"
            )

            return payload

        except HTTPError as exc:

            last_error = exc

            try:

                error_body = (
                    exc.read()
                    .decode(
                        "utf-8",
                        errors="replace"
                    )
                )

            except Exception:

                error_body = ""

            print(
                f"  HTTP {exc.code}: "
                f"{exc.reason}"
            )

            if error_body:

                print(
                    f"  EPA response: "
                    f"{error_body[:1000]}"
                )

        except (
            URLError,
            TimeoutError,
            ConnectionError,
        ) as exc:

            last_error = exc

            print(
                f"  Network error: "
                f"{exc}"
            )

        if attempt < MAX_RETRIES:

            wait_seconds = (
                RETRY_WAIT_SECONDS
                * attempt
            )

            print(
                f"  Waiting "
                f"{wait_seconds} seconds "
                f"before retry..."
            )

            time.sleep(
                wait_seconds
            )

    raise RuntimeError(
        f"EPA request failed after "
        f"{MAX_RETRIES} attempts:\n"
        f"{safe_url}\n"
        f"Last error: {last_error}"
    )


# =============================================================================
# DOWNLOAD OR LOAD CACHE
# =============================================================================

def load_or_download_month(
    year,
    month
):

    cache_path = raw_cache_path(
        year,
        month
    )

    if cache_path.exists():

        print(
            f"Cache found: "
            f"{year}-{month:02d}"
        )

        with cache_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            payload = json.load(
                file
            )

        if not isinstance(
            payload,
            list
        ):

            raise RuntimeError(
                f"Invalid cached payload: "
                f"{cache_path}"
            )

        print(
            f"  Cached records: "
            f"{len(payload):,}"
        )

        return payload

    payload = request_month(
        year,
        month
    )

    with cache_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False
        )

    print(
        f"  Saved cache: "
        f"{cache_path}"
    )

    time.sleep(
        REQUEST_PAUSE_SECONDS
    )

    return payload


# =============================================================================
# NORMALIZE MONTH
# =============================================================================

def normalize_month(
    payload,
    requested_year,
    requested_month
):

    if len(
        payload
    ) == 0:

        print(
            f"WARNING: No records for "
            f"{requested_year}-"
            f"{requested_month:02d}"
        )

        return pd.DataFrame(
            columns=SOURCE_FIELDS
        )

    df = pd.DataFrame(
        payload
    )

    missing_columns = [
        col
        for col in SOURCE_FIELDS
        if col not in df.columns
    ]

    if missing_columns:

        raise RuntimeError(
            f"Missing expected EPA fields "
            f"for "
            f"{requested_year}-"
            f"{requested_month:02d}: "
            f"{missing_columns}"
        )

    df = df[
        SOURCE_FIELDS
    ].copy()

    # -----------------------------------------------------------------
    # Validate response period
    # -----------------------------------------------------------------

    returned_years = set(
        pd.to_numeric(
            df["year"],
            errors="coerce"
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    returned_months = set(
        pd.to_numeric(
            df["month"],
            errors="coerce"
        )
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if returned_years != {
        requested_year
    }:

        raise RuntimeError(
            f"Unexpected year values "
            f"for request "
            f"{requested_year}-"
            f"{requested_month:02d}: "
            f"{returned_years}"
        )

    if returned_months != {
        requested_month
    }:

        raise RuntimeError(
            f"Unexpected month values "
            f"for request "
            f"{requested_year}-"
            f"{requested_month:02d}: "
            f"{returned_months}"
        )

    return df


# =============================================================================
# CLEAN TYPES
# =============================================================================

def clean_dataframe(
    df
):

    df = df.copy()

    rename_map = {
        "stateCode":
            "state",

        "facilityName":
            "facility_name",

        "facilityId":
            "facility_id",

        "grossLoad":
            "gross_load_mwh",

        "steamLoad":
            "steam_load_klb",

        "so2Mass":
            "so2_mass_tons",

        "co2Mass":
            "co2_mass_tons",

        "noxMass":
            "nox_mass_tons",

        "heatInput":
            "heat_input_mmbtu",
    }

    df = df.rename(
        columns=rename_map
    )

    # -----------------------------------------------------------------
    # Identifiers
    # -----------------------------------------------------------------

    df["year"] = (
        pd.to_numeric(
            df["year"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["month"] = (
        pd.to_numeric(
            df["month"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["facility_id"] = (
        pd.to_numeric(
            df["facility_id"],
            errors="coerce"
        )
        .astype("Int64")
    )

    df["state"] = (
        df["state"]
        .astype("string")
        .str.strip()
    )

    df["facility_name"] = (
        df["facility_name"]
        .astype("string")
        .str.strip()
    )

    # -----------------------------------------------------------------
    # Numeric measures
    # -----------------------------------------------------------------

    numeric_columns = [
        "gross_load_mwh",
        "steam_load_klb",
        "so2_mass_tons",
        "co2_mass_tons",
        "nox_mass_tons",
        "heat_input_mmbtu",
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # -----------------------------------------------------------------
    # Period
    # -----------------------------------------------------------------

    df["period"] = pd.to_datetime(
        {
            "year":
                df["year"],

            "month":
                df["month"],

            "day":
                1,
        },
        errors="coerce"
    )

    # -----------------------------------------------------------------
    # EIA join candidate
    #
    # We have validated high correspondence between EPA facilityId
    # and EIA plant_code, but retain the original EPA identifier.
    # -----------------------------------------------------------------

    df[
        "eia_plant_code_candidate"
    ] = df[
        "facility_id"
    ]

    # -----------------------------------------------------------------
    # Column order
    # -----------------------------------------------------------------

    df = df[
        [
            "period",
            "year",
            "month",
            "state",
            "facility_id",
            "facility_name",
            "eia_plant_code_candidate",
            "gross_load_mwh",
            "steam_load_klb",
            "heat_input_mmbtu",
            "so2_mass_tons",
            "co2_mass_tons",
            "nox_mass_tons",
        ]
    ]

    return df


# =============================================================================
# VALIDATION
# =============================================================================

def validate(
    df
):

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA CAMPD MONTHLY FACILITY "
        "VALIDATION"
    )

    print(
        "=" * 110
    )

    print(
        f"Rows: "
        f"{len(df):,}"
    )

    print(
        f"Period: "
        f"{df['period'].min()} "
        f"to "
        f"{df['period'].max()}"
    )

    print(
        f"Unique facilities: "
        f"{df['facility_id'].nunique():,}"
    )

    print(
        f"States / codes: "
        f"{df['state'].nunique():,}"
    )

    # -----------------------------------------------------------------
    # Grain
    # -----------------------------------------------------------------

    grain = [
        "period",
        "facility_id",
    ]

    duplicate_mask = (
        df.duplicated(
            subset=grain,
            keep=False
        )
    )

    print(
        "\nDuplicate "
        "Period × Facility ID rows: "
        f"{duplicate_mask.sum():,}"
    )

    if duplicate_mask.any():

        print(
            "\nDuplicate sample:"
        )

        print(
            df.loc[
                duplicate_mask
            ]
            .sort_values(
                grain
            )
            .head(
                50
            )
            .to_string(
                index=False
            )
        )

        raise RuntimeError(
            "Duplicate source grain "
            "detected. No rows were "
            "silently removed."
        )

    # -----------------------------------------------------------------
    # Missing identifiers
    # -----------------------------------------------------------------

    print(
        "\nMissing identifiers:"
    )

    for col in [
        "period",
        "year",
        "month",
        "state",
        "facility_id",
        "facility_name",
    ]:

        print(
            f"{col}: "
            f"{df[col].isna().sum():,}"
        )

    # -----------------------------------------------------------------
    # Missing measures
    # -----------------------------------------------------------------

    print(
        "\nMissing measures:"
    )

    measure_columns = [
        "gross_load_mwh",
        "steam_load_klb",
        "heat_input_mmbtu",
        "so2_mass_tons",
        "co2_mass_tons",
        "nox_mass_tons",
    ]

    for col in measure_columns:

        print(
            f"{col}: "
            f"{df[col].isna().sum():,}"
        )

    # -----------------------------------------------------------------
    # Coverage by year
    # -----------------------------------------------------------------

    yearly = (
        df.groupby(
            "year"
        )
        .agg(
            rows=(
                "facility_id",
                "size"
            ),

            months=(
                "month",
                "nunique"
            ),

            facilities=(
                "facility_id",
                "nunique"
            ),

            states=(
                "state",
                "nunique"
            ),
        )
    )

    print(
        "\nCoverage by year:"
    )

    print(
        yearly.to_string()
    )

    # -----------------------------------------------------------------
    # Facility identity stability
    # -----------------------------------------------------------------

    identity = (
        df[
            [
                "facility_id",
                "facility_name",
                "state",
            ]
        ]
        .drop_duplicates()
    )

    identity_counts = (
        identity.groupby(
            "facility_id"
        )
        .size()
    )

    unstable_ids = (
        identity_counts[
            identity_counts > 1
        ]
    )

    print(
        "\nFacility IDs with multiple "
        "name/state combinations "
        "across history:"
    )

    print(
        f"{len(unstable_ids):,}"
    )

    if len(
        unstable_ids
    ) > 0:

        print(
            "\nIdentity-change sample:"
        )

        print(
            identity[
                identity[
                    "facility_id"
                ]
                .isin(
                    unstable_ids.index
                )
            ]
            .sort_values(
                "facility_id"
            )
            .head(
                100
            )
            .to_string(
                index=False
            )
        )

    # -----------------------------------------------------------------
    # Negative measures
    #
    # Do not alter them. We only audit.
    # -----------------------------------------------------------------

    print(
        "\nNegative-value audit:"
    )

    for col in measure_columns:

        negative_count = (
            df[col] < 0
        ).sum()

        print(
            f"{col}: "
            f"{negative_count:,}"
        )

    # -----------------------------------------------------------------
    # Completely empty metric records
    # -----------------------------------------------------------------

    all_metrics_missing = (
        df[
            measure_columns
        ]
        .isna()
        .all(
            axis=1
        )
    )

    print(
        "\nRows with ALL measures missing: "
        f"{all_metrics_missing.sum():,}"
    )

    if all_metrics_missing.any():

        print(
            "\nAll-measures-missing sample:"
        )

        print(
            df.loc[
                all_metrics_missing,
                [
                    "period",
                    "state",
                    "facility_id",
                    "facility_name",
                ]
            ]
            .head(
                50
            )
            .to_string(
                index=False
            )
        )

    # -----------------------------------------------------------------
    # Latest period sample
    # -----------------------------------------------------------------

    latest_period = (
        df["period"].max()
    )

    latest = df[
        df["period"]
        == latest_period
    ]

    print(
        "\nLatest period: "
        f"{latest_period}"
    )

    print(
        f"Latest period rows: "
        f"{len(latest):,}"
    )

    print(
        "\nBarry latest-period sample:"
    )

    print(
        latest[
            latest[
                "facility_id"
            ] == 3
        ]
        .to_string(
            index=False
        )
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    frames = []

    total_requests = (
        (
            END_YEAR
            - START_YEAR
            + 1
        )
        * len(
            MONTHS
        )
    )

    request_number = 0

    print(
        "=" * 110
    )

    print(
        "EPA CAMPD MONTHLY FACILITY "
        "HISTORICAL INGESTION"
    )

    print(
        "=" * 110
    )

    print(
        f"Years: "
        f"{START_YEAR}-"
        f"{END_YEAR}"
    )

    print(
        f"Months per year: "
        f"{len(MONTHS)}"
    )

    print(
        f"Total year-month batches: "
        f"{total_requests}"
    )

    print()

    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):

        for month in MONTHS:

            request_number += 1

            print(
                "\n"
                + "-" * 110
            )

            print(
                f"[{request_number}/"
                f"{total_requests}] "
                f"{year}-"
                f"{month:02d}"
            )

            print(
                "-" * 110
            )

            payload = (
                load_or_download_month(
                    year,
                    month
                )
            )

            month_df = (
                normalize_month(
                    payload,
                    year,
                    month
                )
            )

            if len(
                month_df
            ) > 0:

                frames.append(
                    month_df
                )

    if not frames:

        raise RuntimeError(
            "No EPA CAMPD records "
            "were retrieved."
        )

    print(
        "\nCombining monthly batches..."
    )

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    combined = clean_dataframe(
        combined
    )

    validate(
        combined
    )

    combined.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(
        "\nSaved processed file:"
    )

    print(
        OUTPUT_PATH
    )

    print(
        "\n=== EPA CAMPD MONTHLY "
        "HISTORICAL INGESTION COMPLETE ==="
    )


if __name__ == "__main__":
    main()