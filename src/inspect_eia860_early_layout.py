from pathlib import Path
from zipfile import ZipFile
import tempfile
import pandas as pd

RAW_DIR = Path("data/raw")

CASES = {
    2001: [
        "F860 2001 DBF Layout.xls"
    ],
    2002: [
        "Layout.xls",
        "F860 2002 DBF Layout.xls"
    ],
    2004: [
        "Layout.xls"
    ]
}

SEARCH_TERMS = [
    "GENY",
    "PRGEN",
    "PCGEN",
    "generator",
    "status",
    "proposed",
    "retired",
    "cancel",
    "planned",
    "existing",
    "indefinite",
    "postpon",
    "ORGYEAR",
    "CURYEAR",
    "NEWPRIMOV"
]


def inspect_workbook(path, year, filename):

    xl = pd.ExcelFile(
        path,
        engine="calamine"
    )

    print("\nSHEETS:")
    for sheet in xl.sheet_names:
        print(f"  - {sheet}")

    for sheet in xl.sheet_names:

        try:
            df = pd.read_excel(
                path,
                sheet_name=sheet,
                header=None,
                engine="calamine"
            )

        except Exception as exc:
            print(
                f"\nCould not read sheet {sheet}: {exc}"
            )
            continue

        text_df = df.astype("string")

        matching_rows = pd.Series(
            False,
            index=df.index
        )

        for term in SEARCH_TERMS:

            term_match = text_df.apply(
                lambda col:
                col.str.contains(
                    term,
                    case=False,
                    na=False,
                    regex=False
                )
            ).any(axis=1)

            matching_rows = (
                matching_rows
                | term_match
            )

        if matching_rows.any():

            print("\n" + "-" * 100)
            print(
                f"YEAR {year} | FILE {filename} | SHEET {sheet}"
            )
            print("-" * 100)

            indexes = df.index[
                matching_rows
            ].tolist()

            expanded = set()

            for idx in indexes:

                start = max(
                    0,
                    idx - 2
                )

                end = min(
                    len(df),
                    idx + 3
                )

                for nearby in range(
                    start,
                    end
                ):
                    expanded.add(
                        nearby
                    )

            subset = df.loc[
                sorted(expanded)
            ]

            print(
                subset.to_string(
                    index=True,
                    header=False
                )
            )


for year, filenames in CASES.items():

    zip_path = (
        RAW_DIR
        / f"eia860{year}.zip"
    )

    print("\n" + "=" * 110)
    print(f"YEAR {year}")
    print("=" * 110)

    with ZipFile(zip_path, "r") as z:

        for filename in filenames:

            print("\n" + "#" * 110)
            print(
                f"LAYOUT FILE: {filename}"
            )
            print("#" * 110)

            if filename not in z.namelist():

                print("FILE NOT FOUND")
                continue

            with tempfile.TemporaryDirectory(
                ignore_cleanup_errors=True
            ) as temp_dir:

                path = z.extract(
                    filename,
                    path=temp_dir
                )

                inspect_workbook(
                    path,
                    year,
                    filename
                )


print(
    "\n=== EARLY LAYOUT INSPECTION COMPLETE ==="
)