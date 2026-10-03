from pathlib import Path

import pandas as pd


PATH = Path(
    "data/processed/fact_emissions_monthly_2001_2025.csv"
)


MEASURES = [
    "gross_load_mwh",
    "steam_load_klb",
    "heat_input_mmbtu",
    "so2_mass_tons",
    "co2_mass_tons",
    "nox_mass_tons",
]


def main():

    df = pd.read_csv(
        PATH,
        parse_dates=["period"],
        low_memory=False
    )

    df["has_reported_measures"] = (
        df[MEASURES]
        .notna()
        .any(axis=1)
    )

    print(
        "Rows:",
        f"{len(df):,}"
    )

    print(
        "\nhas_reported_measures:"
    )

    print(
        df[
            "has_reported_measures"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    duplicate_count = (
        df.duplicated(
            subset=[
                "period",
                "facility_id",
            ]
        )
        .sum()
    )

    print(
        "\nDuplicate Period × Facility ID:",
        f"{duplicate_count:,}"
    )

    df.to_csv(
        PATH,
        index=False
    )

    print(
        "\nUpdated:"
    )

    print(
        PATH
    )


if __name__ == "__main__":
    main()