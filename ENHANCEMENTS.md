# Future Enhancements & Gap Analysis

This document outlines identified gaps and recommended enhancements for the Microsoft Fabric Monitoring & Governance System.

## 1. Automated Alerting

**Current State:**
The system generates comprehensive CSV reports but relies on manual review or downstream ingestion to identify issues.

**Gap:**
No real-time or push-based notification system for critical failures or compliance violations.

**Recommendation:**
Implement a notification module that can send alerts via:
- **Microsoft Teams Webhooks**: Post summary cards to a dedicated channel when `failed_activities` exceed a threshold.
- **Email (SMTP/Graph API)**: Send daily executive summaries to stakeholders.
- **Azure Monitor**: Push metrics to Azure Monitor for dashboarding and alerting.

## 2. Infrastructure as Code (IaC)

**Current State:**
The project is a collection of Python scripts and a Makefile, suitable for local execution or a VM.

**Gap:**
No formal definition for cloud deployment (e.g., Azure Function, Container Instance).

**Recommendation:**
Create deployment artifacts:
- **Dockerfile**: Containerize the application for consistent execution.
- **Bicep/Terraform Templates**: Define Azure resources (e.g., Azure Container Instance, Logic App trigger, Key Vault) to host the solution.
- **GitHub Actions/Azure DevOps Pipeline**: Automate the build and deployment process.

## 3. Scalable Pagination for Large Tenants

**Current State:**
The `_fetch_powerbi_workspaces` method uses `$skip` pagination.

**Gap:**
For tenants with a very large number of workspaces (e.g., >10,000), `$skip` pagination becomes progressively slower and may hit timeout limits.

**Recommendation:**
Migrate to the **Power BI Admin "Scanner" API** (Admin Scan) for workspace inventory.
- **Pros**: Asynchronous, highly scalable, returns detailed metadata (lineage, artifact state).
- **Cons**: More complex implementation (initiate scan -> poll status -> retrieve result).

## 4. Advanced Lineage & Impact Analysis

**Current State:**
Basic lineage extraction for Mirrored Databases is implemented.

**Gap:**
Limited visibility into downstream dependencies (e.g., which Power BI reports break if a Lakehouse table changes).

**Recommendation:**
Expand `extract_lineage.py` to leverage the full Fabric Scanner API response to build a complete graph of:
`DataSource -> Lakehouse -> Semantic Model -> Report -> Dashboard`

## 5. Data Persistence

**Current State:**
Data is exported to local CSV files.

**Gap:**
No centralized database for long-term trend analysis beyond the 28-day API limit.

**Recommendation:**
Implement a "Sink" pattern to write results to:
- **Azure SQL Database**
- **Fabric Lakehouse (Delta Tables)**
- **Azure Blob Storage (Parquet)**

This would enable building a Power BI report *on top of* the monitoring data for self-monitoring.
