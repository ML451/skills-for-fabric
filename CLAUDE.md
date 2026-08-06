# Microsoft Fabric Development Instructions

> **Update Check**: At session start, check for skills-for-fabric updates by reading the remote `package.json` version from `https://github.com/microsoft/skills-for-fabric` (via `git fetch origin main --quiet && git show origin/main:package.json` or GitHub API with authentication) and comparing with the local `package.json` version (currently pinned at `0.3.5`). Show changelog if update available. `skills/check-updates/SKILL.md` implements this check on request ("check for updates", "what version") — prefer it over ad hoc git/API calls.

This project uses Microsoft Fabric for data engineering, warehousing, and analytics.

## Architecture Mode

- Use the hybrid layering model: **Agents → Skills → Common**.
- Agents live under `agents/` and orchestrate cross-workload work, delegating deep endpoint implementation to the relevant skill(s) under `skills/` (each agent's frontmatter lists its `delegates_to` skills):
  - `FabricDataEngineer.agent.md` — default entry point for cross-workload data engineering (Spark, Warehouse, Pipelines, Lakehouse architecture, data quality).
  - `FabricAdmin.agent.md` — capacity, governance, security, cost, and observability across workloads.
  - `FabricAppDev.agent.md` — full-stack apps on top of Fabric (ODBC/XMLA/REST from Python).
  - `FabricMigrationEngineer.agent.md` — Synapse/HDInsight/Databricks → Fabric migration orchestration; see Migration workload below.
  - `FabricIQ.agent.md` — natural-language Q&A over Power BI reports/semantic models; **read `skills/fabriciq/SKILL.md` in full before calling any FabricIQ MCP tool** (mandatory pre-flight, see the agent's own § Pre-Flight).
- `common/` holds workload-specific reference material shared across the authoring/consumption/operations skill split for the same workload, so the split doesn't duplicate the underlying API/concept docs: `COMMON-CORE.md` / `COMMON-CLI.md` / `ITEM-DEFINITIONS-CORE.md` (cross-workload basics), plus one or two `<WORKLOAD>-CORE.md` files per workload (`SPARK-AUTHORING-CORE.md`, `SPARK-CONSUMPTION-CORE.md`, `SPARK-MONITORING-CORE.md`, `SPARK-NOTEBOOK-AUTHORING-CORE.md`, `SQLDW-AUTHORING-CORE.md`, `SQLDW-CONSUMPTION-CORE.md`, `DATAFLOWS-AUTHORING-CORE.md`, `DATAFLOWS-CONSUMPTION-CORE.md`, `EVENTSTREAM-AUTHORING-CORE.md`, `EVENTSTREAM-CONSUMPTION-CORE.md`, `EVENTHOUSE-AUTHORING-CORE.md`, `EVENTHOUSE-CONSUMPTION-CORE.md`) and a `notebook-authoring/` subfolder (connections, context/param resolution, lakehouse paths/tables, library management, ML workflow, troubleshooting). Skills reference these rather than restating them.
- The marketplace also groups skills into installable bundles under `plugins/` (`fabric-authoring`, `fabric-consumption`, `fabric-operations`, `fabric-skills`, `powerbi-authoring`) — see the root `README.md` for what each bundle contains; this file documents the skills themselves, not the packaging.

## Authentication

All Fabric operations require Azure AD authentication. For development:

```bash
# Login to Azure
az login

# Get token for Fabric REST API
az account get-access-token --resource https://api.fabric.microsoft.com

# Get token for SQL connections (Warehouse, Lakehouse SQL Endpoint)
az account get-access-token --resource https://database.windows.net
```

## Fabric REST APIs

All Fabric operations use the REST APIs documented at:
https://learn.microsoft.com/en-us/rest/api/fabric/articles/

## Developer vs Consumer Patterns

### Developers
- Use **REST APIs** to create/manage artifacts (workspaces, warehouses, lakehouses)
- Use **protocol-specific** connections to access data:
  - ODBC/JDBC for Warehouse queries
  - Spark/PySpark for Lakehouse data
  - XMLA/DAX for Semantic Models
  - KQL for Real-Time Intelligence

### Consumers
- Use **MCP servers** for natural language queries
- Limited to: Semantic Models, Warehouses, Lakehouse SQL Endpoints
- No ODBC/JDBC setup needed - MCP handles connections

## Workloads

### Data Engineering
- **Lakehouse**: Delta tables, Spark, file management
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/lakehouse-overview
  - Authoring skill: `skills/spark-authoring-cli/SKILL.md` — notebook authoring, Lakehouse authoring, Materialized Lake Views, and refresh-friendly Spark patterns.
  - Consumption skill: `skills/spark-consumption-cli/SKILL.md` — interactive PySpark/Spark SQL over Livy sessions: DataFrames, cross-lakehouse joins, Delta time-travel, unstructured/JSON analysis. Use for explicit PySpark/DataFrame/Livy asks, not simple SQL.
  - Operations skill: `skills/mlv-operations-cli/SKILL.md` — MLV refresh scheduling, job monitoring, and cancellation via REST API. Use for "schedule MLV refresh", "trigger refresh", "monitor refresh status".
- **Notebooks**: PySpark notebooks with mssparkutils
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/how-to-use-notebook
- **Spark Jobs**: Production Spark workloads
  - Docs: https://learn.microsoft.com/en-us/fabric/data-engineering/spark-job-definition
  - Operations skill: `skills/spark-operations-cli/SKILL.md` — read-only triage for failed jobs, stuck sessions, performance bottlenecks
- **Medallion Architecture**: end-to-end Bronze/Silver/Gold lakehouse design
  - Skill: `skills/e2e-medallion-architecture/SKILL.md` — multi-layer workspace setup, ingestion-to-analytics pipelines, per-layer Spark config, data quality enforcement.

### Data Warehouse
- **Warehouse**: T-SQL data warehouse
  - Docs: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-warehousing
  - Note: Limited T-SQL surface area - check supported features
  - Authoring skill: `skills/sqldw-authoring-cli/SKILL.md` — DDL, DML, ingestion, schema changes
  - Consumption skill: `skills/sqldw-consumption-cli/SKILL.md` — read-only T-SQL queries
  - Operations skill: `skills/sqldw-operations-cli/SKILL.md` — performance diagnostics, slow queries, query insights

### Data Integration
- **Pipelines**: Orchestration and data movement
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/data-factory-overview
- **Dataflows Gen2**: Low-code transformations with Power Query
  - Docs: https://learn.microsoft.com/en-us/fabric/data-factory/dataflows-gen2-overview
  - Authoring skill: `skills/dataflows-authoring-cli/SKILL.md` — dataflow lifecycle management, Power Query M mashup authoring
  - Consumption skill: `skills/dataflows-consumption-cli/SKILL.md` — read-only dataflow exploration, monitoring, status queries
  - Save-as skill: `skills/dataflows-save-as-authoring-cli/SKILL.md` — Gen1 → Gen2.1 CI/CD save-as: tenant/workspace scans, seven-signal readiness assessment (incremental refresh, BYOSA storage, Power Automate triggers, pipeline dependencies, linked entities, DirectQuery, caller-not-owner), Readiness Snapshot output.
  - Primary CLI tool: `az rest` via Fabric REST API

### Migration
- **Synapse → Fabric**: `skills/synapse-migration/SKILL.md` — mssparkutils→notebookutils (incl. env→runtime namespace change), Linked Services → Data Connections/Shortcuts, Spark Pools/Lake Databases/Notebooks/Spark Job Definitions.
- **HDInsight → Fabric**: `skills/hdinsight-migration/SKILL.md` — HiveContext/standalone SparkContext → pre-instantiated SparkSession, WASB/ABFS → OneLake abfss Shortcuts, Hive DDL → Delta Lake, Oozie workflow mapping.
- **Databricks → Fabric**: `skills/databricks-migration/SKILL.md` — dbutils→notebookutils substitution table, secret scope → Key Vault, widgets → parameter-tagged cells, library installs → Fabric Environments, Unity Catalog three-level namespace → Lakehouse two-level schemas.
- **Data Factory pipelines**: `skills/pipeline-migration/SKILL.md` — Synapse Data Factory → Fabric Data Factory: linked services → Fabric connections, inlined dataset definitions, global parameters → Variable Libraries, SynapseNotebook → TridentNotebook activities. SSIS, SHIR-only, and Databricks activities are parked (not migrated).
- Cross-workload orchestration of any of the above: `agents/FabricMigrationEngineer.agent.md`, which also delegates to `spark-authoring-cli`, `sqldw-authoring-cli`, and `e2e-medallion-architecture` for post-migration infrastructure.

### Real-Time Intelligence
- **Eventstreams**: Real-time data ingestion
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/event-streams/overview
  - Authoring skill: `skills/eventstream-authoring-cli/SKILL.md` — create, configure, deploy Eventstream topologies (sources, operators, destinations)
  - Consumption skill: `skills/eventstream-consumption-cli/SKILL.md` — list, inspect, monitor Eventstreams
  - Primary CLI tool: `az rest` via Fabric REST API
- **Activator**: Alerts, notifications, and automated actions over Fabric data/events
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/data-activator/activator-introduction
  - Authoring skill: `skills/activator-authoring-cli/SKILL.md` — create Activator items, sources, rules, conditions, and actions
  - Consumption skill: `skills/activator-consumption-cli/SKILL.md` — inspect Activator definitions, rules, sources, and actions
  - Primary CLI tool: `az rest` via Fabric REST API
- **Fabric IQ / Ontology (preview)**: Semantic model of entity types, properties, and relationships over Fabric data
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/articles/
  - Authoring skill: `skills/fabriciq-ontology-authoring-cli/SKILL.md` — define entity types, properties (incl. timeseries), relationship types, and bind them to lakehouse/Eventhouse tables via the item-definition REST API
  - Consumption skill: `skills/fabriciq-ontology-consumption-cli/SKILL.md` — read ontology items for agent grounding context and route ontology-backed queries to the matching per-datasource consumption skill
  - Primary CLI tool: `az rest` via Fabric REST API
- **KQL Database / Eventhouse**: Time-series queries with Kusto
  - Docs: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/create-database
  - Authoring skill: `skills/eventhouse-authoring-cli/SKILL.md` — table management, ingestion, policies, materialized views
  - Consumption skill: `skills/eventhouse-consumption-cli/SKILL.md` — read-only KQL queries, schema discovery
  - Primary CLI tool: `az rest` via Kusto REST API (`/v1/rest/query` and `/v1/rest/mgmt`)
  - Token audience: `https://kusto.kusto.windows.net/.default`

### OneLake Catalog Search
- **Catalog Search API**: Cross-workspace item discovery
  - Docs: https://learn.microsoft.com/en-us/rest/api/fabric/core/catalog/search
  - Consumption skill: `skills/search-consumption-cli/SKILL.md` — find items by name, description, workspace name, or type
  - Primary CLI tool: `az rest` via `POST /v1/catalog/search`
  - Token audience: `https://api.fabric.microsoft.com/.default`

### Business Intelligence
- **Semantic Models**: DAX, XMLA, Power BI integration, TMDL
  - Docs: https://learn.microsoft.com/en-us/power-bi/connect-data/service-datasets-understand
  - Authoring skill: `skills/semantic-model-authoring/SKILL.md` — semantic model authoring
  - Consumption skill: `skills/semantic-model-consumption/SKILL.md` — raw DAX queries against semantic models via MCP ExecuteQuery tool
  - FabricIQ skill: `skills/fabriciq/SKILL.md` — multi-step Power BI data analysis (discover, inspect, resolve, generate, execute)
  - ⚠️ **MANDATORY**: Before calling any FabricIQ MCP tool, read `skills/fabriciq/SKILL.md` in full (see [`agents/FabricIQ.agent.md` § Pre-Flight](../agents/FabricIQ.agent.md#pre-flight--mandatory-skill-reading)).
- **Power BI Reports**: PBIR/PBIP report projects, visual design, Desktop validation, and Fabric report item management
  - Docs: https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
  - Skill docs: https://aka.ms/Report_Authoring_skill_LearnDocs
  - Planning skill: `skills/powerbi-report-planning/SKILL.md` — requirements, page plan, approval gate
  - Design skill: `skills/powerbi-report-design/SKILL.md` — archetype routing, layout, theme, accessibility
  - Authoring skill: `skills/powerbi-report-authoring/SKILL.md` — PBIR/PBIP file mechanics, Desktop reload/screenshot
  - Management skill: `skills/powerbi-report-management/SKILL.md` — Fabric report item CRUD via `az rest`

### Data Science
- **Data Agents**: Conversational AI over Fabric data sources
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent
- **Data Agent Evaluation**: Testing and validating Data Agent accuracy
  - Docs: https://learn.microsoft.com/en-us/fabric/data-science/fabric-data-agent-sdk

## Best Practices

### Must
- Use Delta Lake format for Lakehouse tables
- Include time filters in KQL queries (`where Timestamp > ago(...)`)
- Use `has` over `contains` for indexed string search in KQL
- Use idempotent KQL commands (`.create-merge table`, `.create-or-alter function`)
- Handle credentials via environment variables or Key Vault
- Use parameterized notebooks and pipelines

### Prefer
- Medallion architecture (Bronze/Silver/Gold) for data organization
- REST APIs for programmatic management
- Incremental processing over full refreshes
- mssparkutils for Fabric-specific notebook operations

### Avoid
- Hardcoded workspace/item IDs
- SELECT * without LIMIT on large tables
- Long-running transactions in Warehouse
- Unbounded streaming queries
