from pathlib import Path
from zipfile import ZipFile
import io
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

EIA_860_PAGE = "https://www.eia.gov/electricity/data/eia860/"

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def find_annual_zip_links():
    print("Reading official EIA-860 page...")

    response = SESSION.get(
        EIA_860_PAGE,
        timeout=120
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]

        match = re.search(
            r"eia860(\d{4})\.zip",
            href,
            flags=re.IGNORECASE
        )

        if match:
            year = int(match.group(1))

            if href.startswith("http"):
                url = href
            else:
                url = requests.compat.urljoin(
                    EIA_860_PAGE,
                    href
                )

            links[year] = url

    return dict(
        sorted(links.items())
    )


def download_zip(year, url):
    local_path = (
        RAW_DIR
        / f"eia860{year}.zip"
    )

    if local_path.exists():
        return local_path

    print(f"Downloading {year}...")

    response = SESSION.get(
        url,
        timeout=180
    )

    response.raise_for_status()

    local_path.write_bytes(
        response.content
    )

    return local_path


def inspect_archive(year, zip_path):
    result = {
        "year": year,
        "generator_workbook": None,
        "sheets": None,
        "status": None
    }

    try:
        with ZipFile(zip_path, "r") as z:

            files = z.namelist()

            generator_candidates = [
                name
                for name in files
                if name.lower().endswith(
                    (".xls", ".xlsx")
                )
                and (
                    "3_1_generator" in name.lower()
                    or "generator" in name.lower()
                )
            ]

            # Prefer the normal Schedule 3.1 generator workbook
            preferred = [
                name
                for name in generator_candidates
                if "3_1_generator" in name.lower()
            ]

            if preferred:
                generator_file = preferred[0]

            elif generator_candidates:
                generator_file = generator_candidates[0]

            else:
                result["status"] = "NO GENERATOR WORKBOOK"
                return result

            result[
                "generator_workbook"
            ] = generator_file

            with z.open(generator_file) as f:
                data = f.read()

            excel_buffer = io.BytesIO(data)

            try:
                xl = pd.ExcelFile(
                    excel_buffer,
                    engine="calamine"
                )

                result["sheets"] = " | ".join(
                    xl.sheet_names
                )

                result["status"] = "OK"

            except Exception as exc:
                result["status"] = (
                    f"EXCEL READ ERROR: {exc}"
                )

    except Exception as exc:
        result["status"] = (
            f"ZIP ERROR: {exc}"
        )

    return result


def main():
    links = find_annual_zip_links()

    print("\n=== ANNUAL ZIP LINKS FOUND ===")

    if not links:
        print("No annual EIA-860 ZIP links found.")
        return

    for year, url in links.items():
        print(
            f"{year}: {url}"
        )

    print(
        f"\nYears found: "
        f"{min(links)}-{max(links)}"
    )

    print(
        f"Total years: "
        f"{len(links)}"
    )

    results = []

    print(
        "\n=== DOWNLOADING / INSPECTING ARCHIVES ==="
    )

    for year, url in links.items():

        print("\n" + "=" * 80)
        print(f"YEAR {year}")
        print("=" * 80)

        try:
            zip_path = download_zip(
                year,
                url
            )

            result = inspect_archive(
                year,
                zip_path
            )

        except Exception as exc:
            result = {
                "year": year,
                "generator_workbook": None,
                "sheets": None,
                "status": (
                    f"DOWNLOAD ERROR: {exc}"
                )
            }

        print(
            f"Generator workbook: "
            f"{result['generator_workbook']}"
        )

        print(
            f"Sheets: "
            f"{result['sheets']}"
        )

        print(
            f"Status: "
            f"{result['status']}"
        )

        results.append(result)

    results_df = pd.DataFrame(
        results
    )

    print("\n" + "=" * 100)
    print("EIA-860 HISTORICAL ARCHIVE SUMMARY")
    print("=" * 100)

    print(
        results_df.to_string(
            index=False
        )
    )

    print(
        "\nYears with inspection problems:"
    )

    problems = results_df[
        results_df["status"] != "OK"
    ]

    if len(problems) == 0:
        print("NONE")
    else:
        print(
            problems.to_string(
                index=False
            )
        )


if __name__ == "__main__":
    main()