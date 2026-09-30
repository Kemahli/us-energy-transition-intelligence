# Project Architecture

## High-Level Architecture

The project is designed as a refreshable analytics pipeline that integrates multiple public U.S. energy datasets into a Power BI semantic model.

```text
EIA API / Files
      │
EPA Data
      │
FRED API
      │
      ▼
Raw Data Layer
      │
      ▼
Cleaning & Transformation
(Python / Power Query)
      │
      ▼
Processed Data Layer
      │
      ▼
Power BI Data Model
      │
      ▼
DAX Measures
      │
      ▼
Interactive Power BI Report
      │
      ▼
Scheduled / Automated Refresh
