# Data Source Audit

This document tracks the public datasets considered for the U.S. Power & Energy Transition Intelligence Platform.

The objective is to identify each dataset's analytical role, grain, historical coverage, update frequency, join keys, and refresh suitability before ingestion begins.

## Core Data Sources

| Source | Dataset | Analytical Role | Grain | History | Update Frequency | Likely Join Keys | Planned Use |
|---|---|---|---|---|---|---|---|
| EIA | EIA-923 Power Plant Operations | Electricity generation, fuel consumption, fuel cost | Plant × Month × Fuel / Prime Mover | Long historical coverage | Monthly / Annual | Plant ID, Date, Fuel | Core generation fact table |
| EIA | EIA-860 / 860M Generator Data | Capacity, technology, plant characteristics, planned additions, retirements | Generator | Long historical coverage | Annual + Monthly preliminary | Plant ID, Generator ID | Capacity and asset structure |
| EIA | EIA-861M Retail Sales & Prices | Retail electricity sales, revenue, and prices by customer sector | State × Sector × Month | Multi-decade | Monthly | State, Sector, Date | Residential / commercial / industrial price analysis |
| EPA | GHGRP Power Plant Emissions | Facility-level greenhouse gas emissions | Facility × Year | 2011+ | Annual | Facility ID, Plant / Facility Name, Geography | Emissions fact table |
| EPA | GHGRP Parent Company Data | Ownership structure for reporting facilities | Facility × Parent Company | Multi-year | Annual | Facility ID, Parent Company | Facility-to-company mapping |
| FRED | Selected Energy and Macro Series | Energy prices and macroeconomic context | Series × Date | Series dependent | Daily / Weekly / Monthly / Quarterly | Date, Series ID | Economic context and trend analysis |

## Planned Fact Tables

### FactGeneration
Expected source:
- EIA-923

Potential fields:
- Date
- Plant ID
- Fuel type
- Prime mover / technology
- Net generation
- Fuel consumption
- Fuel cost

### FactCapacity
Expected source:
- EIA-860
- EIA-860M

Potential fields:
- Plant ID
- Generator ID
- Capacity MW
- Technology
- Fuel
- Operating status
- Operating date
- Retirement date
- Planned capacity status

### FactRetailPrices
Expected source:
- EIA-861M

Potential fields:
- Date
- State
- Customer sector
- Electricity sales
- Revenue
- Average retail price

Customer sectors to preserve separately:
- Residential
- Commercial
- Industrial
- Transportation
- Total

### FactEmissions
Expected source:
- EPA GHGRP

Potential fields:
- Reporting year
- Facility ID
- Facility name
- State
- CO2 emissions
- Total reported GHG emissions

### FactMacro
Expected source:
- FRED API

Potential series:
- Natural gas prices
- Crude oil prices
- CPI
- Federal Funds Rate
- Treasury yields
- Industrial production
- Other energy-related economic indicators where analytically justified

## Planned Dimension Tables

Potential dimensions:

- DimDate
- DimPlant
- DimGenerator
- DimFuel
- DimTechnology
- DimGeography
- DimCustomerSector
- DimMacroSeries
- DimParentCompany

## Key Modeling Challenges

The project is expected to require careful handling of:

- Different data grains
- Different update frequencies
- Plant and facility identifier mismatches
- Generator-level versus plant-level records
- Monthly versus annual observations
- Fuel category standardization
- Technology classification
- Geographic mapping
- Facility-to-parent-company mapping
- Missing values
- Revised historical observations
- Source schema changes

## Refresh Design Goal

Each source should ultimately be classified into one of the following refresh patterns:

1. Monthly automated refresh
2. Annual automated refresh
3. Periodic metadata refresh
4. Manual-only source if automation is not practical

The final design should minimize manual intervention while preserving reproducibility and data quality.
