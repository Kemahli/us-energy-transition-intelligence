# Data Source Audit

This document tracks the public datasets considered for the U.S. Power & Energy Transition Intelligence Platform.

The objective is to identify each dataset's analytical role, grain, historical coverage, update frequency, join keys, refresh suitability, and expected role in the Power BI model before large-scale ingestion begins.

---

## Core Data Sources

| Source | Dataset | Analytical Role | Grain | History | Update Frequency | Likely Join Keys | Planned Use |
|---|---|---|---|---|---|---|---|
| EIA | EIA-923 Power Plant Operations | Electricity generation, fuel consumption, plant operations | Plant × Month × Fuel × Prime Mover | API route from 2001 onward; historical files may extend further | Monthly / Annual | Plant ID, Period, Fuel, Prime Mover | Core generation fact table |
| EIA | EIA-860 / 860M Generator Data | Capacity, technology, generator status, planned additions, retirements | Generator | Long historical coverage | Annual + Monthly preliminary | Plant ID, Generator ID | Capacity and asset structure |
| EIA | EIA-861M Retail Sales & Prices | Retail electricity sales, revenue, and prices by customer sector | State × Sector × Month | Multi-decade | Monthly | State, Sector, Date | Residential / commercial / industrial / total retail price analysis |
| EPA | GHGRP Power Plant Emissions | Facility-level greenhouse gas emissions | Facility × Year | 2011+ | Annual | Facility ID, Plant / Facility Name, Geography | Emissions fact table |
| EPA | GHGRP Parent Company Data | Ownership structure for reporting facilities | Facility × Parent Company | Multi-year | Annual | Facility ID, Parent Company | Facility-to-company mapping |
| FRED | Selected Energy and Macro Series | Energy prices and macroeconomic context | Series × Date | Series dependent | Daily / Weekly / Monthly / Quarterly | Date, Series ID | Economic context and trend analysis |

---
## EIA-923 Power Plant Operations

### Role in the Project

EIA-923 is the primary operational source for historical U.S. electricity generation and fuel-use data.

The generation layer is used to build the project's historical `FactGeneration` dataset.

Primary historical coverage used in the project:

- 2001 through 2025
- Monthly observations
- Annual EIA-923 / predecessor archives
- Official EIA Excel workbooks

The production historical dataset is stored locally as:

`data/processed/fact_generation_2001_2025.csv`

Raw EIA archives are not committed to GitHub.

---

### Historical Source Architecture

Historical data is downloaded from official EIA annual archives.

Archive naming differs by period:

- 2001-2007: `f906920_YEAR.zip`
- 2008 onward: `f923_YEAR.zip`

The generation sheet is generally:

`Page 1 Generation and Fuel Data`

Workbook structure changes across years.

Examples:

- Older files generally use header row 7.
- Modern files generally use header row 5.
- Older files use `AER Fuel Type Code`.
- Modern files use `MER Fuel Type Code`.
- Monthly generation fields appear with different naming conventions across eras.

The ingestion pipeline therefore detects and normalizes schema differences instead of assuming a single fixed workbook layout.

---

### Validated Historical Grain

Initial testing showed that the simplified grain:

`Period × Plant × Reported Fuel × Prime Mover`

is not sufficient across the full historical dataset.

The final validated source grain is:

`Period`
× `State`
× `Plant ID`
× `Reported Fuel Type Code`
× `Reported Prime Mover`
× `AER/MER Fuel Type Code`
× `EIA Sector Number`
× `Nuclear Unit ID`
× `Combined Heat and Power Flag`
× `Physical Unit Label`

This grain was tested independently against every annual file from 2001 through 2025.

Final validation result:

- 25 years tested
- 25 years passed
- 0 duplicate grain rows in every year
- 0 duplicate grain rows in the combined historical dataset

Some components are only required in particular periods, but preserving the full validated source grain provides a consistent cross-era structure.

---

### Why the Additional Grain Fields Matter

Several fields that initially appeared secondary were found to distinguish legitimate source rows.

#### AER / MER Fuel Type Code

Older files may contain multiple rows with the same reported fuel code but different AER fuel classifications.

Modern files use the corresponding MER fuel classification field.

These are normalized into:

`fuel_group_code`

The original historical distinction is preserved rather than discarded.

#### EIA Sector Number

The same plant and fuel combination can appear in different EIA sectors.

Sector must therefore be preserved at the fact-source level.

#### State

Special EIA records can reuse the same plant identifier across multiple states.

State is therefore part of the validated key.

#### Nuclear Unit ID

Modern nuclear generation can contain separate unit-level rows under the same plant.

Without Nuclear Unit ID, legitimate rows collapse into duplicate keys.

#### Combined Heat and Power Flag

Some modern source rows differ only by CHP classification.

The CHP flag is therefore preserved.

#### Physical Unit Label

Older files, especially 2002-2003, contain otherwise identical records that differ by physical unit.

Physical Unit Label is required to preserve those source rows correctly.

---

### Special Plant ID 99999

The dataset contains records with:

- Plant ID: `99999`
- Plant Name: `State-Fuel Level Increment`

These records appear across the historical period and are not ordinary physical power plants.

The same Plant ID may appear in multiple states, which is one reason State must be included in the source grain.

These records are preserved in the source-level dataset.

They must not be interpreted as normal plant entities in plant-level analysis.

A later analytical layer may separate physical plants from adjustment / state-level records depending on the reporting requirement.

They are not deleted during ingestion.

---

### Missing Generation Values

Missing generation values are preserved as missing.

They are not automatically converted to zero.

This distinction was validated using the 2025 Barry plant sample:

- The annual source contained a missing June value.
- The API omitted that plant-fuel-period observation rather than reporting zero.
- Explicit zero values also exist elsewhere in the data.

Therefore:

`missing ≠ zero`

This rule is enforced throughout the historical ingestion pipeline.

---

### Negative Generation Values

Negative generation observations exist in the official source data.

They are preserved during ingestion.

Negative generation is not automatically treated as a data error because it can reflect operational or accounting behavior such as station use, pumping, or other source-defined reporting conditions.

Any analytical exclusion or reinterpretation must be explicitly justified later.

---

### Historical Pipeline

The production historical pipeline is:

1. Download official EIA annual archives.
2. Identify the correct generation workbook.
3. Detect the workbook header row.
4. Normalize historical and modern column names.
5. Identify all 12 monthly net generation columns.
6. Preserve validated source-grain identifiers.
7. Convert annual wide-format data into monthly long format.
8. Standardize field names and data types.
9. Preserve missing and negative generation values.
10. Validate uniqueness at the full historical grain.
11. Save yearly processed files.
12. Combine all years into the historical generation fact dataset.

Production script:

`src/eia923_historical_backfill.py`

Historical archive downloader:

`src/download_eia923_history.py`

---

### Final Historical Dataset

Final build results:

- Period: January 2001 through December 2025
- Rows: 3,687,312
- Unique Plant IDs: 16,430
- Missing generation observations: 130,948
- Duplicate grain rows: 0

Final file:

`data/processed/fact_generation_2001_2025.csv`

The processed dataset is excluded from GitHub because of its size and can be rebuilt from the official source archives using the production pipeline.

---

### Validation Framework

The historical generation layer was validated through multiple stages.

Validation scripts include:

- `validation/eia923_historical_validation.py`
- `validation/eia923_full_validation.py`
- `validation/eia923_duplicate_diagnosis.py`
- `validation/eia923_raw_grain_diagnosis.py`
- `validation/eia923_grain_test_2001.py`
- `validation/eia923_grain_test_2025.py`
- `validation/eia923_remaining_grain_diagnosis.py`
- `validation/eia923_special_record_diagnosis.py`
- `validation/eia923_universal_grain_validation.py`

Validation included:

- comparison between historical Excel data and EIA API output for a controlled plant sample
- month coverage checks
- missing-value checks
- negative-generation inspection
- duplicate diagnosis
- raw source-grain investigation
- cross-era schema testing
- full 2001-2025 grain uniqueness validation

The controlled Barry plant comparison matched API generation values within the API's display / rounding precision.

---

### API Role

The EIA API route explored for plant-level operational data is:

`/v2/electricity/facility-fuel/data/`

The API includes dimensions such as:

- period
- plant
- fuel
- prime mover
- state

and measures such as:

- net generation
- gross generation
- total fuel consumption
- total fuel consumption in Btu

The API contains both detailed rows and aggregate / subtotal rows.

Therefore API data must not be summed blindly.

For the historical project layer, official annual archives are used as the authoritative backfill source.

The intended future architecture is:

`Annual historical files`
+
`Recent monthly API updates`
→ `standardization and reconciliation`
→ `FactGeneration`

The API incremental-refresh layer will be designed only after the historical fact structure is stable.

---

### Current Status

Historical EIA-923 generation ingestion:

`DONE + VALIDATED`

Remaining EIA-923 work:

- design API-based incremental update logic
- reconcile API grain with the historical canonical grain
- formalize treatment of special adjustment records in analytical models
- incorporate fuel-consumption measures if needed for later analysis