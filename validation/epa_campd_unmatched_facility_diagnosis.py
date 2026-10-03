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

EIA_PATH = Path(
    "data/processed/fact_capacity_generators_2001_2025.csv"
)


# =============================================================================
# EPA JANUARY 2025 FACILITIES
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

    df = pd.DataFrame(payload)

    return (
        df[
            [
                "facilityId",
                "facilityName",
                "stateCode",
            ]
        ]
        .drop_duplicates()
    )


# =============================================================================
# EIA FULL HISTORY
# =============================================================================

def load_eia():

    df = pd.read_csv(
        EIA_PATH,
        keep_default_na=False,
        na_values=[""],
        low_memory=False
    )

    df["report_year"] = pd.to_numeric(
        df["report_year"],
        errors="coerce"
    )

    df["plant_code"] = pd.to_numeric(
        df["plant_code"],
        errors="coerce"
    )

    plants = (
        df[
            [
                "report_year",
                "plant_code",
                "plant_name",
                "state",
            ]
        ]
        .dropna(
            subset=["plant_code"]
        )
        .drop_duplicates()
    )

    plants["plant_code"] = (
        plants["plant_code"]
        .astype(int)
    )

    return plants


# =============================================================================
# MAIN
# =============================================================================

def main():

    epa = load_epa()
    eia = load_eia()

    eia_2025_codes = set(
        eia.loc[
            eia["report_year"] == 2025,
            "plant_code"
        ].tolist()
    )

    epa["in_eia_2025"] = (
        epa["facilityId"]
        .isin(eia_2025_codes)
    )

    unmatched = (
        epa[
            ~epa["in_eia_2025"]
        ]
        .copy()
    )

    print("=" * 110)
    print("EPA FACILITIES NOT FOUND IN EIA-860 2025")
    print("=" * 110)

    print(
        f"Unmatched facilities: "
        f"{len(unmatched):,}"
    )

    all_eia_codes = set(
        eia["plant_code"].tolist()
    )

    unmatched[
        "found_any_eia860_year"
    ] = (
        unmatched["facilityId"]
        .isin(all_eia_codes)
    )

    print(
        "\nFound somewhere in "
        "EIA-860 2001-2025:"
    )

    print(
        unmatched[
            "found_any_eia860_year"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    results = []

    for _, row in unmatched.iterrows():

        facility_id = int(
            row["facilityId"]
        )

        history = (
            eia[
                eia["plant_code"]
                == facility_id
            ]
            .sort_values(
                "report_year"
            )
        )

        if len(history) == 0:

            results.append(
                {
                    "facility_id":
                        facility_id,

                    "epa_name":
                        row["facilityName"],

                    "epa_state":
                        row["stateCode"],

                    "found_in_eia860":
                        False,

                    "first_eia_year":
                        pd.NA,

                    "last_eia_year":
                        pd.NA,

                    "latest_eia_name":
                        pd.NA,

                    "latest_eia_state":
                        pd.NA,
                }
            )

            continue

        latest = history.iloc[-1]

        results.append(
            {
                "facility_id":
                    facility_id,

                "epa_name":
                    row["facilityName"],

                "epa_state":
                    row["stateCode"],

                "found_in_eia860":
                    True,

                "first_eia_year":
                    int(
                        history[
                            "report_year"
                        ].min()
                    ),

                "last_eia_year":
                    int(
                        history[
                            "report_year"
                        ].max()
                    ),

                "latest_eia_name":
                    latest[
                        "plant_name"
                    ],

                "latest_eia_state":
                    latest[
                        "state"
                    ],
            }
        )

    result = pd.DataFrame(
        results
    )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "UNMATCHED FACILITY HISTORY"
    )

    print(
        "=" * 110
    )

    print(
        result.to_string(
            index=False
        )
    )

    # -----------------------------------------------------------------
    # State consistency for historical matches
    # -----------------------------------------------------------------

    historical_matches = result[
        result[
            "found_in_eia860"
        ]
    ].copy()

    if len(
        historical_matches
    ) > 0:

        historical_matches[
            "state_match"
        ] = (
            historical_matches[
                "epa_state"
            ]
            == historical_matches[
                "latest_eia_state"
            ]
        )

        print(
            "\n"
            + "=" * 110
        )

        print(
            "STATE CONSISTENCY FOR "
            "HISTORICAL MATCHES"
        )

        print(
            "=" * 110
        )

        print(
            historical_matches[
                "state_match"
            ]
            .value_counts(
                dropna=False
            )
            .to_string()
        )

    # -----------------------------------------------------------------
    # Completely absent IDs
    # -----------------------------------------------------------------

    absent = result[
        ~result[
            "found_in_eia860"
        ]
    ]

    print(
        "\n"
        + "=" * 110
    )

    print(
        "EPA IDs NEVER FOUND IN "
        "EIA-860 2001-2025"
    )

    print(
        "=" * 110
    )

    print(
        f"Count: "
        f"{len(absent):,}"
    )

    if len(
        absent
    ) > 0:

        print()

        print(
            absent[
                [
                    "facility_id",
                    "epa_name",
                    "epa_state",
                ]
            ]
            .to_string(
                index=False
            )
        )

    print(
        "\n=== EPA CAMPD UNMATCHED "
        "FACILITY DIAGNOSIS COMPLETE ==="
    )


if __name__ == "__main__":
    main()