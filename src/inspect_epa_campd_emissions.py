import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

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


PARAMS = {
    "api_key": EPA_API_KEY,
    "year": 2025,
    "month": [1],
}


# =============================================================================
# REQUEST
# =============================================================================

def fetch_json(
    url,
    params
):

    query = urlencode(
        params,
        doseq=True
    )

    full_url = (
        url
        + "?"
        + query
    )

    safe_url = full_url.replace(
        EPA_API_KEY,
        "***API_KEY***"
    )

    print(
        "=" * 110
    )

    print(
        "REQUEST"
    )

    print(
        "=" * 110
    )

    print(
        safe_url
    )

    request = Request(
        full_url,
        headers={
            "Accept":
                "application/json",

            "User-Agent":
                "us-energy-transition-intelligence/1.0",
        }
    )

    try:

        with urlopen(
            request,
            timeout=120
        ) as response:

            body = (
                response.read()
                .decode(
                    "utf-8"
                )
            )

            print(
                "\nHTTP STATUS:"
            )

            print(
                response.status
            )

            return json.loads(
                body
            )

    except HTTPError as exc:

        print(
            "\nHTTP ERROR:"
        )

        print(
            exc.code,
            exc.reason
        )

        error_body = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace"
            )
        )

        print(
            "\nERROR BODY:"
        )

        print(
            error_body
        )

        raise


# =============================================================================
# INSPECTION
# =============================================================================

def inspect_payload(
    payload
):

    print(
        "\n"
        + "=" * 110
    )

    print(
        "PAYLOAD SUMMARY"
    )

    print(
        "=" * 110
    )

    print(
        "Python type:",
        type(
            payload
        ).__name__
    )

    records = None

    if isinstance(
        payload,
        list
    ):

        records = payload

    elif isinstance(
        payload,
        dict
    ):

        print(
            "\nTop-level keys:"
        )

        for key in (
            payload.keys()
        ):

            print(
                f"  {key}"
            )

        for candidate in [
            "items",
            "data",
            "results",
            "records",
        ]:

            value = (
                payload.get(
                    candidate
                )
            )

            if isinstance(
                value,
                list
            ):

                records = value

                break

        if records is None:

            print(
                "\nRAW PAYLOAD:"
            )

            print(
                json.dumps(
                    payload,
                    indent=2
                )[:15000]
            )

            return

    else:

        print(
            payload
        )

        return

    print(
        f"\nRecords returned: "
        f"{len(records):,}"
    )

    if not records:
        return

    print(
        "\nFIRST RECORD:"
    )

    print(
        json.dumps(
            records[0],
            indent=2
        )
    )

    fields = set()

    for record in records:

        if isinstance(
            record,
            dict
        ):

            fields.update(
                record.keys()
            )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "FIELDS"
    )

    print(
        "=" * 110
    )

    for field in sorted(
        fields
    ):

        print(
            field
        )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "POSSIBLE EMISSIONS / LOAD FIELDS"
    )

    print(
        "=" * 110
    )

    keywords = [
        "co2",
        "so2",
        "nox",
        "heat",
        "load",
        "time",
        "op",
    ]

    for field in sorted(
        fields
    ):

        field_lower = (
            field.lower()
        )

        if not any(
            keyword in field_lower
            for keyword in keywords
        ):

            continue

        sample_values = []

        for record in records:

            if not isinstance(
                record,
                dict
            ):

                continue

            value = record.get(
                field
            )

            if value not in (
                None,
                ""
            ):

                sample_values.append(
                    value
                )

            if len(
                sample_values
            ) >= 5:

                break

        print(
            f"{field}: "
            f"{sample_values}"
        )

    print(
        "\n"
        + "=" * 110
    )

    print(
        "FIRST 10 RECORDS"
    )

    print(
        "=" * 110
    )

    candidate_fields = [
        "year",
        "month",
        "stateCode",
        "facilityId",
        "facilityName",
        "unitId",
        "grossLoad",
        "steamLoad",
        "heatInput",
        "so2Mass",
        "co2Mass",
        "noxMass",
    ]

    for i, record in enumerate(
        records[:10],
        start=1
    ):

        if not isinstance(
            record,
            dict
        ):

            continue

        selected = {
            key:
                record.get(
                    key
                )
            for key in candidate_fields
            if key in record
        }

        print(
            f"{i}: "
            + json.dumps(
                selected,
                default=str
            )
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    payload = fetch_json(
        BASE_URL,
        PARAMS
    )

    inspect_payload(
        payload
    )

    print(
        "\n=== EPA CAMPD STREAMING "
        "MONTHLY FACILITY INSPECTION "
        "COMPLETE ==="
    )


if __name__ == "__main__":
    main()