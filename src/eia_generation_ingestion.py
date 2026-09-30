import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("EIA_API_KEY")

if not API_KEY:
    raise ValueError("EIA_API_KEY not found in .env file")

# EIA endpoint
url = "https://api.eia.gov/v2/electricity/facility-fuel/data/"

params = {
    "api_key": API_KEY,
    "frequency": "monthly",
    "data[0]": "generation",
    "data[1]": "gross-generation",
    "data[2]": "total-consumption-btu",
    "facets[plantCode][]": "3",
    "start": "2025-01",
    "end": "2025-12",
    "length": 500
}

response = requests.get(url, params=params)
response.raise_for_status()

json_data = response.json()

rows = json_data["response"]["data"]

df = pd.DataFrame(rows)

output_path = "data/raw/eia_barry_2025.csv"
df.to_csv(output_path, index=False)

print("Download complete")
print(f"Rows: {len(df)}")
print(f"Periods found: {sorted(df['period'].unique())}")
print(f"Saved to: {output_path}")