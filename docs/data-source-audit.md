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

# EIA-923 Power Plant Operations

## Role in Project

Primary operational source for plant-level electricity generation and fuel use.

## Provider

U.S. Energy Information Administration (EIA)

## Source

Form EIA-923

## API Route

```text
/v2/electricity/facility-fuel/data/
