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

## EIA-860 Annual Electric Generator Data

### Purpose

EIA-860 provides annual generator-level information for U.S. electric power plants.

The dataset is used in this project for:

- installed and operable generating capacity
- proposed capacity
- retired capacity
- canceled or indefinitely postponed projects
- generator technology
- prime mover
- energy source
- operating dates
- retirement dates
- plant and generator identifiers

The historical ingestion currently covers 2001 through 2025.

### Historical Source Coverage

Official annual EIA-860 archives were identified for every year from 2001 through 2025.

The source structure changes substantially over time.

#### 2001-2003

DBF-based files.

Primary generator files:

- GENYxx.dbf: existing generator inventory
- PRGENYxx.dbf: proposed generator inventory
- PCGENYxx.dbf: proposed changes to existing generators, where available

PCGEN is not treated as normal generator inventory because the official layout describes it as proposed changes to existing generators.

Examples of modification statuses include:

- fuel conversion
- repowering
- capability increase
- capability decrease
- deactivation
- reactivation
- scheduled retirement
- ownership change

#### 2004-2008

Older Excel-based structure.

Primary files:

- GenYxx.xls: existing generator inventory
- PRGenYxx.xls: proposed generator inventory
- PCGenYxx.xls: proposed changes to existing generators, where available

The existing generator file may contain retired generators. Therefore, source file membership alone is not sufficient to determine analytical capacity status.

#### 2009-2010

Generator information is stored in one workbook with sheets such as:

- Exist
- Prop
- Ret_IP

#### 2011-2012

Transitional workbook structure using modern-style sheet names such as:

- Operable
- Proposed
- Retired and Canceled

#### 2013-2025

Modern workbook structure:

- Operable
- Proposed
- Retired and Canceled

The primary workbook is typically:

3_1_Generator_Y<year>.xlsx

### Canonical Historical Output

The historical pipeline creates:

data/processed/fact_capacity_generators_2001_2025.csv

Current output:

- 628,446 rows
- 2001-2025 coverage
- 19,517 unique Plant Codes
- 43,250 unique observed Plant Code x Generator ID combinations
- 22 true missing Generator ID records
- 2 flagged duplicate source-key rows

No generator records are silently removed because of a missing Generator ID.

### Generator Identity

Plant Code x Generator ID is used as the primary natural generator identity candidate when Generator ID is present.

However:

- valid EIA records can have missing Generator IDs
- "NA" can be a legitimate Generator ID string
- pandas default CSV parsing interprets "NA" as a missing value

Therefore, downstream CSV readers must preserve literal "NA" values.

Example safe CSV loading approach:

    pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""]
    )

Missing Generator ID records remain in the dataset and are explicitly flagged.

### Source Record Types

The canonical dataset preserves source semantics using:

source_record_type

Values include:

- existing
- operable
- proposed
- retired_canceled

These describe where the record came from in the historical EIA-860 structure.

### Analytical Capacity Classification

A separate field:

capacity_bucket

is used for analytical interpretation.

Values:

- operable
- planned
- retired
- canceled_or_postponed
- other

This distinction prevents retired or canceled capacity from being accidentally included in current installed-capacity measures.

The pipeline also includes:

operable_capacity_flag

This flag identifies generator records that belong to the operable fleet for capacity analysis.

### Status Handling

Examples of operable-fleet statuses include:

- OP
- SB
- OS
- OA
- BU

Examples of retired/canceled statuses include:

- RE
- CN
- IP

Proposed generator statuses such as:

- P
- L
- T
- TS
- U
- V

are retained as planned capacity unless the source status explicitly indicates cancellation or indefinite postponement.

Original EIA status values are always preserved.

### 2025 Validation Control

The 2025 historical parser output matches the directly inspected source workbook structure:

- Operable: 27,918 records
- Proposed: 2,850 records
- Retired and Canceled: 5,805 records

Nameplate capacity:

- Operable: 1,376,742.0 MW
- Proposed: 326,487.9 MW
- Retired and Canceled: 335,223.7 MW

The analytical breakdown is:

- Operable: 1,376,742.0 MW
- Planned: 326,487.9 MW
- Retired: 212,117.6 MW
- Canceled or postponed: 123,106.1 MW

Retired and canceled capacity are therefore excluded from operable-capacity KPIs.

### Duplicate Handling

The historical source contains two records in 2001 sharing the same candidate source key:

- Plant Code 1146
- Generator ID HMU
- Status SB

The canonical values are identical.

These records are not silently deleted.

Instead, the pipeline preserves both source rows and flags them using:

duplicate_source_key_flag

Source row provenance is retained using:

source_row_number

### Missing Generator IDs

Some valid EIA generator records do not contain a Generator ID.

These records are preserved and identified using:

missing_generator_id_flag

A specific validation also identified historical generator IDs equal to the literal string "NA".

These must not be confused with missing values.

### Important Analytical Rule

Capacity values in the full 2001-2025 table must not be summed across all years and interpreted as national installed capacity.

Each year is an annual generator snapshot.

For national capacity at a particular point in time:

1. select one report year
2. use the appropriate analytical capacity bucket or flag
3. aggregate generator capacity within that annual snapshot

### Current Status

Historical EIA-860 generator and capacity ingestion:

DONE + VALIDATED

Remaining EIA-860 related work:

- optional ingestion of proposed changes to existing generators from historical PCGEN files
- optional EIA-860M monthly incremental refresh layer
- later dimensional modeling for DimGenerator, DimPlant, technology, fuel, and geography


## EIA-861M Monthly Retail Sales, Revenue, Customers, and Prices

### Purpose

EIA-861M provides monthly state-level retail electricity data.

This project uses the source for:

- retail electricity sales
- retail revenue
- customer counts
- published average retail electricity prices
- sector-level electricity market analysis

The historical workbook currently covers 2010 through the latest published 2026 month.

### Source Structure

The primary historical workbook is:

`data/raw/eia861m_sales_revenue_2010_current.xlsx`

The analytical source sheet is:

`Monthly-States`

The source is stored in wide format.

Each row represents:

`Year × Month × State`

Sector groups are stored as repeated column blocks:

- Residential
- Commercial
- Industrial
- Transportation
- Total

Each sector contains:

- Revenue
- Sales
- Customers
- Price

### Source Grain Validation

The `Monthly-States` sheet contains:

- 10,149 source rows
- 2010 through July 2026
- 51 state/DC codes
- 0 duplicate `Year × Month × State` rows

Coverage:

- 2010-2025: 612 source rows per year
- 2026: 357 source rows through July

### Canonical Analytical Grain

The ingestion pipeline converts the wide source into long format.

Canonical grain:

`Period × State × Sector`

Sectors:

- Residential
- Commercial
- Industrial
- Transportation
- Total

The canonical output is:

`data/processed/fact_retail_prices_2010_current.csv`

Current output:

- 50,745 rows
- 2010-01 through 2026-07
- 51 state/DC codes
- 5 sectors
- 0 duplicate `Period × State × Sector` rows
- 0 missing values in core analytical fields

### Current Workbook Reconciliation

The current utility-level workbook includes special records such as:

- Utility Number `0`: State Adjustment
- Utility Number `88888`: State Total
- State code `US`: national total

The historical `Monthly-States` sheet is used directly as the authoritative state aggregate layer.

Utility-level rows are not re-aggregated to reconstruct state totals.

A controlled 2026 comparison between historical state aggregates and current `State Total` rows found:

- 357 matching state-month records
- exact customer-count agreement
- maximum revenue difference of about 0.055 thousand dollars
- maximum sales difference of about 0.501 MWh

The additional 7 current records were U.S. national total rows and are not part of the 51-state/DC grain.

### Published Total Sector

The source includes a published `Total` sector.

This value is preserved directly.

It is not reconstructed by summing Residential, Commercial, Industrial, and Transportation.

Source-level comparisons show small differences between reported Total revenue/sales and recomputed component sums.

### Retail Price Handling

The published EIA price field is preserved as:

`price_cents_per_kwh`

A derived revenue-to-sales price is used only for validation.

The validation formula is:

`revenue_thousand_dollars × 100 / sales_mwh`

Across 46,350 nonzero-sales records:

- 82 rows differed by more than 0.01 cents/kWh
- all 82 were Transportation records
- only 4 differed by more than 0.05 cents/kWh
- only 1 differed by more than 0.10 cents/kWh
- maximum difference was approximately 0.154 cents/kWh

The differing records were all very low-volume Transportation observations.

Because the source does not explicitly establish the cause of these differences, the published EIA price is retained rather than overwritten by the derived calculation.

### Zero-Sales Records

There are 4,395 zero-sales rows.

All are in the Transportation sector.

For these rows, the published price is 0.0 cents/kWh.

These records are retained as valid source observations.

### Current Status

Historical EIA-861M state-level retail sales, revenue, customer, and price ingestion:

**DONE + VALIDATED**

Remaining EIA-861M related work:

- refresh/update strategy for newly published months
- optional utility-level analysis
- later dimensional integration with geography and date tables

---

## EPA CAMPD Monthly Facility Emissions

### Source

EPA Clean Air Markets Program Data (CAMPD) API

Endpoint used:

`https://api.epa.gov/easey/streaming-services/emissions/apportioned/monthly/by-facility`

Historical coverage used in this project:

- January 2001 through December 2025

The API was queried one month at a time to avoid multi-month request instability and to handle rate-limit behavior safely.

### Source Grain

Validated source grain:

`Year × Month × Facility ID`

Equivalent project analytical grain:

`Period × Facility ID`

Historical ingestion results:

- 407,535 rows
- 1,814 unique facilities
- 51 state / territory codes
- 0 duplicate `Period × Facility ID` rows
- 0 missing identifiers

The facility identifier, facility name, state code, year, and month were complete across the processed dataset.

### Fields Retained

The processed emissions fact includes:

- `period`
- `year`
- `month`
- `state`
- `facility_id`
- `facility_name`
- `eia_plant_code_candidate`
- `gross_load_mwh`
- `steam_load_klb`
- `heat_input_mmbtu`
- `so2_mass_tons`
- `co2_mass_tons`
- `nox_mass_tons`
- `has_reported_measures`

EPA-reported units used in the project:

- Gross Load = MWh
- Steam Load = thousand lb
- Heat Input = mmBtu
- SO2 Mass = short tons
- CO2 Mass = short tons
- NOx Mass = short tons

### Missing-Value Semantics

Missing measure values are preserved as missing.

They are not converted to zero.

A record with all six analytical measures missing does not automatically mean:

- zero generation
- zero emissions
- retired facility
- inactive facility

Historical diagnosis showed:

- 49,486 rows with all measures missing
- 12.14% of all facility-month rows
- 8 facilities always all-missing
- 1,592 facilities partially all-missing
- 214 facilities never all-missing

Several facilities showed valid reported values both before and after all-missing months. Therefore, all-measure null records are retained as source records rather than interpreted as zero activity.

The field `has_reported_measures` is defined as:

- `True`: at least one retained analytical measure is non-null
- `False`: all retained analytical measures are null

Final counts:

- `True`: 358,049
- `False`: 49,486

### Negative Values

The historical audit found zero negative observations in:

- `gross_load_mwh`
- `steam_load_klb`
- `heat_input_mmbtu`
- `so2_mass_tons`
- `co2_mass_tons`
- `nox_mass_tons`

No rows were altered based on this result.

### Facility Identity Stability

Across the 2001-2025 CAMPD history:

- 0 Facility IDs had multiple facility-name/state combinations

The source facility identifier was therefore retained as the primary facility identifier for the emissions fact.

### EPA Facility ID and EIA Plant Code

A controlled 2025 comparison was performed between EPA CAMPD `facilityId` and EIA plant identifiers.

Against EIA-860:

- EPA facilities tested: 1,253
- Facility IDs found as EIA Plant Code: 1,228
- Match rate: 98.00%
- All 1,228 matched IDs had matching state codes

Against EIA-923:

- EPA facilities tested: 1,253
- Found in EIA-923 2025: 1,220
- 2025 match rate: 97.37%
- Found somewhere in EIA-923 2001-2025: 1,236
- Never found in EIA-923 2001-2025: 17

This provides strong empirical evidence that EPA `facilityId` generally corresponds to EIA `plant_code`.

However, this relationship is not treated as universal.

The processed emissions fact therefore retains:

- `facility_id`
- `eia_plant_code_candidate`

with `eia_plant_code_candidate` currently equal to `facility_id`.

EPA facilities that do not exist in EIA-923 are retained rather than dropped.

Plant names are not used as the join key because naming differences are common across EPA and EIA sources.

State is used as a validation field rather than part of the primary join.

### Ingestion Strategy

Production script:

`src/epa_campd_monthly_ingestion.py`

The pipeline:

1. queries one year-month at a time
2. stores each successful API response in a local raw JSON cache
3. retries temporary API failures
4. preserves null measures
5. validates returned year and month
6. combines all monthly batches
7. validates `Period × Facility ID` uniqueness
8. writes the processed historical fact

Raw cache pattern:

`data/raw/epa_campd_monthly_facility_YYYY_MM.json`

Processed output:

`data/processed/fact_emissions_monthly_2001_2025.csv`

The raw and processed data files are excluded from Git.

### Rate Limiting

During historical ingestion, the API periodically returned:

`HTTP 429 Too Many Requests`

The ingestion script handles this using retry delays.

Successful monthly responses are cached, so rerunning the pipeline does not re-download already completed months.

### Validation Scripts

EPA validation and diagnosis scripts:

- `src/inspect_epa_campd_emissions.py`
- `src/epa_campd_finalize.py`
- `validation/epa_campd_eia_plant_id_validation.py`
- `validation/epa_campd_unmatched_facility_diagnosis.py`
- `validation/epa_campd_eia923_plant_id_validation.py`
- `validation/epa_campd_all_missing_diagnosis.py`

### Current Status

EPA CAMPD monthly facility historical ingestion:

`DONE + VALIDATED`

Remaining EPA-related work:

- incremental refresh for post-2025 months
- final EPA-to-EIA crosswalk policy for Power BI
- emissions-intensity calculations using matched EIA-923 generation
- Power BI model integration

