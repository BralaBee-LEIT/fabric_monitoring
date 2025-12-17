# Changelog

All notable changes to this project will be documented in this file.

## 0.3.1 (December 2024) - Smart Merge Fix Release

### Fixed
- **Star Schema Builder** now correctly reads from CSV files with Smart Merge enriched data
  - Changed data source from parquet to `activities_master_*.csv` files
  - Fixed NaN handling in `classify_user_type()`, `extract_domain_from_upn()`, and `build_from_activities()` 
  - Fixed NaT datetime handling in fact table building
  - Failure data (is_failed=1) now properly captured from Smart Merge correlation

### Changed
- Notebook auto-selects CSV file with failure data when multiple files available
- Added Failure Analysis cell to notebook for Smart Merge validation

---

## 0.3.0 (January 2025) - Star Schema Analytics Release

### Added
- **Star Schema Builder** - Kimball-style dimensional model for analytics
  - 7 dimension tables (dim_date, dim_time, dim_workspace, dim_item, dim_user, dim_activity_type, dim_status)
  - 2 fact tables (fact_activity, fact_daily_metrics)
  - Incremental loading with high-water mark tracking
  - SCD Type 2 support for slowly changing dimensions
  - Delta Lake DDL generation for Fabric deployment
  - Validated with 1M+ activity records
- New CLI entry point: `usf-star-schema`
- Makefile targets: `star-schema`, `star-schema-ddl`, `star-schema-describe`
- Fabric deployment guide (`docs/FABRIC_DEPLOYMENT.md`)
- Ready-to-use Fabric notebook (`notebooks/Fabric_Star_Schema_Builder.ipynb`)

### Changed
- Updated documentation to reflect v0.3.0 features
- Enhanced README with star schema feature documentation
- Updated WIKI with star schema notebook guide

## 0.2.0 (December 2024) - Advanced Analytics Release

### Added
- Monitor Hub analysis pipeline with Smart Merge duration recovery
- Workspace access enforcement CLI (`assess`/`enforce`) with targets + suppressions
- Lineage extraction inventory for Mirrored Databases
- Safe-by-default pytest configuration (integration tests opt-in)
- CONTRIBUTING.md with development guidelines
- SECURITY.md with security policy
