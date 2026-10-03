from pathlib import Path
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

BASE_PAGE = "https://www.eia.gov/electricity/data/eia923/"
RAW_DIR = Path("data/raw")

START_YEAR = 2001
END_YEAR = 2025


def get_download_links():
    print("Reading official EIA download page...")

    response = requests.get(
        BASE_PAGE,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = {}

    for row in soup.find_all("tr"):
        row_text = row.get_text(" ", strip=True)

        year_match = re.match(
            r"(20\d{2})",
            row_text
        )

        if not year_match:
            continue

        year = int(year_match.group(1))

        if not START_YEAR <= year <= END_YEAR:
            continue

        zip_link = None

        for a in row.find_all("a", href=True):
            href = a["href"]

            if href.lower().endswith(".zip"):
                zip_link = urljoin(
                    BASE_PAGE,
                    href
                )
                break

        if zip_link:
            links[year] = zip_link

    return links


def download_file(year, url):
    filename = url.split("/")[-1]
    output_path = RAW_DIR / filename

    if output_path.exists():
        print(
            f"{year}: already exists -> {filename}"
        )
        return

    print(
        f"{year}: downloading {filename}"
    )

    with requests.get(
        url,
        stream=True,
        timeout=120
    ) as response:

        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):
                if chunk:
                    f.write(chunk)

    print(
        f"{year}: saved -> {output_path}"
    )


def main():
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    links = get_download_links()

    print("\nOfficial annual ZIPs found:")

    for year in sorted(links):
        print(
            f"{year}: {links[year]}"
        )

    expected_years = set(
        range(
            START_YEAR,
            END_YEAR + 1
        )
    )

    found_years = set(
        links.keys()
    )

    missing_years = sorted(
        expected_years - found_years
    )

    if missing_years:
        print(
            "\nWARNING: years missing from EIA page:"
        )
        print(missing_years)
        return

    print("\nAll requested years found.")
    print("\nStarting historical downloads...\n")

    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):
        download_file(
            year,
            links[year]
        )

    print(
        "\nHistorical download complete."
    )


if __name__ == "__main__":
    main()