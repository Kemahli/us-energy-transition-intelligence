import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
from dotenv import load_dotenv


# =============================================================================
# CONFIG
# =============================================================================

load_dotenv()

EPA_API_KEY = os.getenv("EPA_API_KEY")

if not EPA_API_KEY:
    raise RuntimeError(
        "EPA_API_KEY not found in .env"
    )


EPA_URL = (
    "https://api.epa.gov/easey/"
    "streaming-services/emissions/"
    "apportioned/monthly/by-facility"
)

EIA_CAPACITY_PATH = Path(
    "data/processed/fact_capacity_generators_2001_2025.csv"
)

YEAR = 2025

MONTHS = [
    1,
    2,
    3,
]


# =============================================================================
# EPA DOWNLOAD
# =============================================================================

def fetch_epa_month(
    year,
    month
):

    params = {
        "api_key": EPA_API_KEY,
        "year": year,
        "month": [month],
    }

    query = urlencode(
        params,
        doseq=True
    )

    url = (
        EPA_URL
        + "?"
        + query
    )

    safe_url = url.replace(
        EPA_API_KEY,
        "***API_KEY***"
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        f"EPA REQUEST - "
        f"{year}-{month:02d}"
    )

    print(
        "=" * 110
    )

    print(
        safe_url
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

    with urlopen(
        request,
        timeout=180
    ) as response:

        payload = json.loads(
            response.read()
            .decode(
                "utf-8"
            )
        )

    if not isinstance(
        payload,
        list
    ):
        raise RuntimeError(
            f"Unexpected EPA response "
            f"for month {month}"
        )

    print(
        f"Records returned: "
        f"{len(payload):,}"
    )

    return pd.DataFrame(
        payload
    )


def fetch_epa():

    frames = []

    for month in MONTHS:

        frame = fetch_epa_month(
            YEAR,
            month
        )

        frames.append(
            frame
        )

    combined = pd.concat(
        frames,
        ignore_index=True
    )

    return combined


# =============================================================================
# NAME NORMALIZATION
# =============================================================================

def normalize_name(
    value
):

    if pd.isna(
        value
    ):
        return ""

    text = str(
        value
    ).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =============================================================================
# LOAD EIA
# =============================================================================

def load_eia():

    if not EIA_CAPACITY_PATH.exists():

        raise FileNotFoundError(
            f"Missing file: "
            f"{EIA_CAPACITY_PATH}"
        )

    df = pd.read_csv(
        EIA_CAPACITY_PATH,
        keep_default_na=False,
        na_values=[""]
    )

    df["report_year"] = pd.to_numeric(
        df["report_year"],
        errors="coerce"
    )

    df["plant_code"] = pd.to_numeric(
        df["plant_code"],
        errors="coerce"
    )

    df = df[
        df["report_year"] == YEAR
    ].copy()

    plants = (
        df[
            [
                "plant_code",
                "plant_name",
                "state",
            ]
        ]
        .dropna(
            subset=[
                "plant_code"
            ]
        )
        .drop_duplicates()
    )

    code_counts = (
        plants.groupby(
            "plant_code"
        )
        .size()
    )

    ambiguous_codes = (
        code_counts[
            code_counts > 1
        ]
    )

    print(
        "\nEIA plant codes with multiple "
        "name/state combinations:"
    )

    print(
        len(
            ambiguous_codes
        )
    )

    plant_codes = set(
        plants[
            "plant_code"
        ]
        .astype(
            int
        )
        .tolist()
    )

    return (
        plants,
        plant_codes
    )


# =============================================================================
# MAIN VALIDATION
# =============================================================================

def main():

    epa = fetch_epa()

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA CAMPD SAMPLE SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        f"Rows: "
        f"{len(epa):,}"
    )

    print(
        f"Facilities: "
        f"{epa['facilityId'].nunique():,}"
    )

    print(
        f"Months: "
        f"{sorted(epa['month'].unique())}"
    )

    print(
        "\nMissing values:"
    )

    for col in [
        "facilityId",
        "facilityName",
        "stateCode",
        "year",
        "month",
        "grossLoad",
        "steamLoad",
        "so2Mass",
        "co2Mass",
        "noxMass",
        "heatInput",
    ]:

        print(
            f"{col}: "
            f"{epa[col].isna().sum():,}"
        )

    # -----------------------------------------------------------------
    # GRAIN TEST
    # -----------------------------------------------------------------

    grain = [
        "year",
        "month",
        "facilityId",
    ]

    duplicate_mask = (
        epa.duplicated(
            subset=grain,
            keep=False
        )
    )

    print(
        "\nDuplicate "
        "Year × Month × Facility ID rows: "
        f"{duplicate_mask.sum():,}"
    )

    if duplicate_mask.any():

        print(
            "\nDuplicate sample:"
        )

        print(
            epa.loc[
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

    # -----------------------------------------------------------------
    # FACILITY IDENTITY STABILITY
    # -----------------------------------------------------------------

    facility_identity = (
        epa[
            [
                "facilityId",
                "facilityName",
                "stateCode",
            ]
        ]
        .drop_duplicates()
    )

    identity_counts = (
        facility_identity.groupby(
            "facilityId"
        )
        .size()
    )

    unstable = (
        identity_counts[
            identity_counts > 1
        ]
    )

    print(
        "\nFacility IDs with multiple "
        "name/state combinations:"
    )

    print(
        len(
            unstable
        )
    )

    if len(
        unstable
    ) > 0:

        print(
            facility_identity[
                facility_identity[
                    "facilityId"
                ].isin(
                    unstable.index
                )
            ]
            .sort_values(
                "facilityId"
            )
            .head(
                50
            )
            .to_string(
                index=False
            )
        )

    # -----------------------------------------------------------------
    # EIA COMPARISON
    # -----------------------------------------------------------------

    eia_plants, eia_codes = (
        load_eia()
    )

    epa["facilityId"] = pd.to_numeric(
        epa["facilityId"],
        errors="coerce"
    )

    epa_facilities = (
        epa[
            [
                "facilityId",
                "facilityName",
                "stateCode",
            ]
        ]
        .dropna(
            subset=[
                "facilityId"
            ]
        )
        .drop_duplicates()
    )

    epa_facilities[
        "facilityId"
    ] = (
        epa_facilities[
            "facilityId"
        ]
        .astype(
            int
        )
    )

    epa_facilities[
        "id_in_eia"
    ] = (
        epa_facilities[
            "facilityId"
        ]
        .isin(
            eia_codes
        )
    )

    matched = (
        epa_facilities[
            epa_facilities[
                "id_in_eia"
            ]
        ]
    )

    unmatched = (
        epa_facilities[
            ~epa_facilities[
                "id_in_eia"
            ]
        ]
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA FACILITY ID VS EIA PLANT CODE"
    )

    print(
        "=" * 110
    )

    print(
        f"EPA facilities tested: "
        f"{len(epa_facilities):,}"
    )

    print(
        f"Facility IDs found as EIA Plant Code: "
        f"{len(matched):,}"
    )

    print(
        f"Facility IDs not found in EIA 2025: "
        f"{len(unmatched):,}"
    )

    print(
        f"ID match rate: "
        f"{(
            len(matched)
            / len(epa_facilities)
            * 100
        ):.2f}%"
    )

    if len(
        unmatched
    ) > 0:

        print(
            "\nFirst unmatched EPA facilities:"
        )

        print(
            unmatched[
                [
                    "facilityId",
                    "facilityName",
                    "stateCode",
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
    # MATCHED ID NAME + STATE CHECK
    # -----------------------------------------------------------------

    eia_reference = (
        eia_plants[
            [
                "plant_code",
                "plant_name",
                "state",
            ]
        ]
        .drop_duplicates(
            subset=[
                "plant_code"
            ],
            keep="first"
        )
        .copy()
    )

    eia_reference[
        "plant_code"
    ] = (
        eia_reference[
            "plant_code"
        ]
        .astype(
            int
        )
    )

    comparison = matched.merge(
        eia_reference,
        left_on="facilityId",
        right_on="plant_code",
        how="left"
    )

    comparison[
        "epa_name_normalized"
    ] = (
        comparison[
            "facilityName"
        ]
        .apply(
            normalize_name
        )
    )

    comparison[
        "eia_name_normalized"
    ] = (
        comparison[
            "plant_name"
        ]
        .apply(
            normalize_name
        )
    )

    comparison[
        "state_match"
    ] = (
        comparison[
            "stateCode"
        ]
        == comparison[
            "state"
        ]
    )

    comparison[
        "exact_normalized_name_match"
    ] = (
        comparison[
            "epa_name_normalized"
        ]
        == comparison[
            "eia_name_normalized"
        ]
    )

    print(
        "\nState matches for matched IDs:"
    )

    print(
        comparison[
            "state_match"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print(
        "\nExact normalized plant-name matches:"
    )

    print(
        comparison[
            "exact_normalized_name_match"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    state_mismatch = (
        comparison[
            ~comparison[
                "state_match"
            ]
        ]
    )

    if len(
        state_mismatch
    ) > 0:

        print(
            "\nSTATE MISMATCH SAMPLE:"
        )

        print(
            state_mismatch[
                [
                    "facilityId",
                    "facilityName",
                    "stateCode",
                    "plant_name",
                    "state",
                ]
            ]
            .head(
                50
            )
            .to_string(
                index=False
            )
        )

    name_mismatch = (
        comparison[
            ~comparison[
                "exact_normalized_name_match"
            ]
        ]
    )

    print(
        "\nName mismatch count:"
    )

    print(
        len(
            name_mismatch
        )
    )

    if len(
        name_mismatch
    ) > 0:

        print(
            "\nNAME MISMATCH SAMPLE:"
        )

        print(
            name_mismatch[
                [
                    "facilityId",
                    "facilityName",
                    "plant_name",
                    "stateCode",
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
    # BARRY CONTROL
    # -----------------------------------------------------------------

    print(
        "\n"
        + "=" * 110
    )

    print(
        "BARRY CONTROL"
    )

    print(
        "=" * 110
    )

    print(
        comparison[
            comparison[
                "facilityId"
            ] == 3
        ][
            [
                "facilityId",
                "facilityName",
                "stateCode",
                "plant_code",
                "plant_name",
                "state",
            ]
        ]
        .to_string(
            index=False
        )
    )

    print(
        "\n=== EPA CAMPD × EIA PLANT ID "
        "VALIDATION COMPLETE ==="
    )


if __name__ == "__main__":
    main()