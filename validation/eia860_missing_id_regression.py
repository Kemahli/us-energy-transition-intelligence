from pathlib import Path
from zipfile import ZipFile
import tempfile

import pandas as pd
from dbfread import DBF


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

TARGET_PLANTS = [
    10012,
    7549,
]


def inspect_raw(year):

    year2 = str(year)[-2:]

    zip_path = (
        RAW_DIR
        / f"eia860{year}.zip"
    )

    filename = (
        f"GENY{year2}.dbf"
    )

    with ZipFile(
        zip_path,
        "r"
    ) as z:

        actual = None

        for name in z.namelist():

            if name.lower() == filename.lower():
                actual = name
                break

        if actual is None:
            raise FileNotFoundError(filename)

        with tempfile.TemporaryDirectory(
            ignore_cleanup_errors=True
        ) as temp_dir:

            path = z.extract(
                actual,
                path=temp_dir
            )

            table = DBF(
                path,
                load=True,
                char_decode_errors="ignore"
            )

            raw = pd.DataFrame(
                iter(table)
            )

    target = raw[
        raw["PLNTCODE"].isin(
            TARGET_PLANTS
        )
    ].copy()

    print("\n" + "=" * 100)
    print(f"RAW DBF {year}")
    print("=" * 100)

    for _, row in target.iterrows():

        print(
            "Plant:",
            row["PLNTCODE"],
            "| GENCODE repr:",
            repr(row["GENCODE"]),
            "| STATUS:",
            row["STATUS"],
            "| NAMEPLATE:",
            row["NAMEPLATE"]
        )


def inspect_csv(year):

    path = (
        PROCESSED_DIR
        / f"eia860_generators_{year}.csv"
    )

    print("\n" + "=" * 100)
    print(f"CSV {year} - DEFAULT PANDAS READ")
    print("=" * 100)

    default_df = pd.read_csv(
        path,
        low_memory=False
    )

    target_default = default_df[
        default_df["plant_code"].isin(
            TARGET_PLANTS
        )
    ]

    print(
        target_default[
            [
                "plant_code",
                "generator_id",
                "status",
                "nameplate_capacity_mw",
            ]
        ].to_string(
            index=False
        )
    )

    print("\n" + "=" * 100)
    print(f"CSV {year} - PRESERVE 'NA' STRINGS")
    print("=" * 100)

    safe_df = pd.read_csv(
        path,
        low_memory=False,
        keep_default_na=False,
        na_values=[""]
    )

    target_safe = safe_df[
        safe_df["plant_code"].isin(
            TARGET_PLANTS
        )
    ]

    print(
        target_safe[
            [
                "plant_code",
                "generator_id",
                "status",
                "nameplate_capacity_mw",
            ]
        ].to_string(
            index=False
        )
    )


for year in [
    2001,
    2002,
]:

    inspect_raw(year)
    inspect_csv(year)


print(
    "\n=== NA STRING CHECK COMPLETE ==="
)