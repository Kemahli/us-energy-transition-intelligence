import json
import os
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

EIA923_PATH = Path(
    "data/processed/fact_generation_2001_2025.csv"
)


# =============================================================================
# EPA SAMPLE
# =============================================================================

def load_epa():

    params = {
        "api_key": EPA_API_KEY,
        "year": 2025,
        "month": [1],
    }

    url = (
        EPA_URL
        + "?"
        + urlencode(
            params,
            doseq=True
        )
    )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
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
            .decode("utf-8")
        )

    df = pd.DataFrame(
        payload
    )

    facilities = (
        df[
            [
                "facilityId",
                "facilityName",
                "stateCode",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    facilities["facilityId"] = pd.to_numeric(
        facilities["facilityId"],
        errors="coerce"
    )

    facilities = facilities[
        facilities["facilityId"].notna()
    ].copy()

    facilities["facilityId"] = (
        facilities["facilityId"]
        .astype(int)
    )

    return facilities


# =============================================================================
# EIA-923
# =============================================================================

def load_eia923():

    if not EIA923_PATH.exists():

        raise FileNotFoundError(
            f"Missing file: {EIA923_PATH}"
        )

    df = pd.read_csv(
        EIA923_PATH,
        keep_default_na=False,
        na_values=[""],
        low_memory=False
    )

    print(
        "\nEIA-923 columns:"
    )

    print(
        list(df.columns)
    )

    # -------------------------------------------------------------
    # Detect likely year field
    # -------------------------------------------------------------

    if "period" in df.columns:

        df["period"] = pd.to_datetime(
            df["period"],
            errors="coerce"
        )

        df["report_year_check"] = (
            df["period"].dt.year
        )

    elif "year" in df.columns:

        df["report_year_check"] = (
            pd.to_numeric(
                df["year"],
                errors="coerce"
            )
        )

    else:

        raise RuntimeError(
            "Could not find period/year "
            "column in EIA-923 file."
        )

    # -------------------------------------------------------------
    # Detect plant ID field
    # -------------------------------------------------------------

    plant_id_candidates = [
        "plant_id",
        "plant_code",
        "plant id",
        "plant code",
    ]

    plant_id_col = None

    normalized = {
        str(col).strip().lower():
            col
        for col in df.columns
    }

    for candidate in plant_id_candidates:

        if candidate in normalized:

            plant_id_col = (
                normalized[candidate]
            )

            break

    if plant_id_col is None:

        raise RuntimeError(
            "Could not detect EIA-923 plant ID column."
        )

    print(
        f"\nDetected plant ID column: "
        f"{plant_id_col}"
    )

    df[plant_id_col] = pd.to_numeric(
        df[plant_id_col],
        errors="coerce"
    )

    df_2025 = df[
        df["report_year_check"] == 2025
    ].copy()

    plant_ids_2025 = set(
        df_2025[
            plant_id_col
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    all_plant_ids = set(
        df[
            plant_id_col
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    return (
        plant_ids_2025,
        all_plant_ids,
        plant_id_col
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    epa = load_epa()

    (
        eia923_2025_ids,
        eia923_all_ids,
        plant_id_col,
    ) = load_eia923()

    epa["in_eia923_2025"] = (
        epa["facilityId"]
        .isin(
            eia923_2025_ids
        )
    )

    epa[
        "in_eia923_any_year"
    ] = (
        epa["facilityId"]
        .isin(
            eia923_all_ids
        )
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA CAMPD FACILITY ID "
        "VS EIA-923 PLANT ID"
    )

    print(
        "=" * 110
    )

    print(
        f"EPA facilities tested: "
        f"{len(epa):,}"
    )

    print(
        f"Found in EIA-923 2025: "
        f"{epa['in_eia923_2025'].sum():,}"
    )

    print(
        f"Not found in EIA-923 2025: "
        f"{(~epa['in_eia923_2025']).sum():,}"
    )

    print(
        f"2025 match rate: "
        f"{(
            epa['in_eia923_2025'].mean()
            * 100
        ):.2f}%"
    )

    print(
        "\nFound somewhere in "
        "EIA-923 2001-2025:"
    )

    print(
        epa[
            "in_eia923_any_year"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # -------------------------------------------------------------
    # Facilities absent from 2025
    # -------------------------------------------------------------

    unmatched_2025 = epa[
        ~epa[
            "in_eia923_2025"
        ]
    ].copy()

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA FACILITIES NOT FOUND "
        "IN EIA-923 2025"
    )

    print(
        "=" * 110
    )

    print(
        unmatched_2025[
            [
                "facilityId",
                "facilityName",
                "stateCode",
                "in_eia923_any_year",
            ]
        ]
        .to_string(
            index=False
        )
    )

    # -------------------------------------------------------------
    # Completely absent from EIA-923 history
    # -------------------------------------------------------------

    absent_all = epa[
        ~epa[
            "in_eia923_any_year"
        ]
    ].copy()

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA FACILITIES NEVER FOUND "
        "IN EIA-923 2001-2025"
    )

    print(
        "=" * 110
    )

    print(
        f"Count: "
        f"{len(absent_all):,}"
    )

    if len(
        absent_all
    ) > 0:

        print()

        print(
            absent_all[
                [
                    "facilityId",
                    "facilityName",
                    "stateCode",
                ]
            ]
            .to_string(
                index=False
            )
        )

    # -------------------------------------------------------------
    # Previously interesting IDs
    # -------------------------------------------------------------

    ids_to_check = [
        302,
        330,
        1594,
        3604,
        7258,
        7762,
        7765,
        10619,
        50030,
        50607,
        55120,
        55248,
        59073,
        70454,
        880004,
        880006,
        880007,
        880023,
        880025,
        880041,
        880067,
        880079,
        880100,
        880102,
        880107,
    ]

    diagnostic = epa[
        epa["facilityId"]
        .isin(
            ids_to_check
        )
    ].copy()

    print(
        "\n"
        + "=" * 110
    )

    print(
        "PREVIOUS EIA-860 "
        "UNMATCHED FACILITIES"
    )

    print(
        "=" * 110
    )

    print(
        diagnostic[
            [
                "facilityId",
                "facilityName",
                "stateCode",
                "in_eia923_2025",
                "in_eia923_any_year",
            ]
        ]
        .sort_values(
            "facilityId"
        )
        .to_string(
            index=False
        )
    )

    print(
        "\n=== EPA CAMPD × EIA-923 "
        "PLANT ID VALIDATION COMPLETE ==="
    )


if __name__ == "__main__":
    main()