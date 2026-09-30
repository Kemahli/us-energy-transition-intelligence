# us-energy-transition-intelligence
A refreshable Power BI analytics platform for U.S. power generation, capacity, emissions, and energy transition trends.

## Project Objective
The goal of this project is to build a multi-source, refreshable analytics platform using public U.S. energy data.

The platform will integrate operational, environmental, and economic datasets to analyze:

- Electricity generation by fuel, technology, geography, and time
- Installed generating capacity
- New capacity additions and plant retirements
- Renewable and fossil generation trends
- Greenhouse gas emissions and emissions intensity
- Electricity and fuel price trends
- Regional differences in the U.S. power system

The final output will be an interactive Power BI report supported by a reproducible data pipeline, dimensional data model, validation workflow, and automated data refresh process.

## Planned Data Sources
- U.S. Energy Information Administration (EIA)
- U.S. Environmental Protection Agency (EPA)
- Federal Reserve Economic Data (FRED)
- Additional public sources where needed

## Planned Technical Stack
- Power BI Desktop
- Power Query
- DAX
- Python
- REST APIs
- Git / GitHub
- GitHub Actions
- Public government datasets

## Project Structure

```text
data/
├── raw/
└── processed/

docs/
powerbi/
src/
validation/
