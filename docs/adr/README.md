# Architecture Decision Records

This project follows the practice of Architecture Decision Records (ADRs) to document
the reasoning behind every major technology choice. Each ADR follows the format:
Status, Context, Decision, Reasons, and Consequences. This ensures future engineers
(and interviewers) understand not just WHAT was built but WHY.

Architecture Decision Records (ADRs) capture the key technical decisions made during the design and build of this project. Each ADR documents the context that prompted a decision, the decision itself, the alternatives considered, and the trade-offs accepted. They serve as a permanent record so that future contributors understand not just *what* was built but *why*.

## ADR Index

| # | Title | Status |
|---|-------|--------|
| [001](001-why-airflow-over-prefect.md) | Why Apache Airflow over Prefect | Accepted |
| [002](002-why-snowflake-over-redshift.md) | Why Snowflake over AWS Redshift | Accepted |
| [003](003-why-dbt-for-transformations.md) | Why dbt over custom SQL scripts | Accepted |
| [004](004-why-isolation-forest-for-anomaly-detection.md) | Why Isolation Forest for Anomaly Detection | Accepted |
| 005 | Why Prophet over ARIMA for price prediction | Accepted |
| [006](006-s3-cost-optimization-strategy.md) | S3 Cost Optimization Strategy | Accepted |
| [007](007-typed-config-with-dataclasses.md) | Typed Configuration with Python Dataclasses | Accepted |
| [008](008-ml-model-registry-pattern.md) | ML Model Registry Pattern | Accepted |
| [009](009-html-reports-with-jinja2.md) | HTML Reports with Jinja2 | Accepted |
| [010](010-technical-indicators-from-scratch.md) | Technical Indicators Built from Scratch | Accepted |
| [011](011-keyword-sentiment-vs-nlp.md) | Keyword Sentiment vs NLP Models | Accepted |
| [012](012-data-observability-pattern.md) | Data Observability Pattern | Accepted |
| [013](013-graphql-with-strawberry.md) | GraphQL API with Strawberry | Accepted |
| [014](014-websocket-for-realtime.md) | WebSocket for Real-Time Streaming | Accepted |
| [015](015-s3-caching-vs-redis.md) | S3 Caching vs Redis | Accepted |
| [017](017-data-governance-pattern.md) | Data Governance Pattern | Accepted |
| [018](018-feature-store-pattern.md) | S3-Based Feature Store | Accepted |
| [019](019-automated-testing-framework.md) | Automated Testing Framework | Accepted |
| [020](020-ensemble-models-pattern.md) | Ensemble Models over Single Model | Accepted |
| [021](021-chaos-engineering-pattern.md) | Chaos Engineering Pattern | Accepted |
| [022](022-secrets-management-pattern.md) | Secrets Management Pattern | Accepted |
| [023](023-workflow-management-pattern.md) | Workflow Management Pattern | Accepted |
| [024](024-business-intelligence-metrics.md) | Business Intelligence Metrics | Accepted |
| [025](025-property-based-testing.md) | Property-Based Testing Pattern | Accepted |
| [026](026-incremental-loading-pattern.md) | Incremental Loading with Watermarks | Accepted |
| [027](027-model-drift-detection.md) | Model Drift Detection with PSI | Accepted |
| [028](028-data-lineage-tracking.md) | Data Lineage Tracking | Accepted |
| [029](029-data-dictionary-as-code.md) | Data Dictionary as Code | Accepted |
| [030](030-integration-and-e2e-testing.md) | Integration and E2E Testing Strategy | Accepted |
| [031](031-streamlit-dashboard.md) | Streamlit Real-Time Dashboard | Accepted |
| [032](032-ab-testing-for-ml-models.md) | A/B Testing Framework for ML Models | Accepted |
| [033](033-slack-alerting-integration.md) | Slack Alerting Integration | Accepted |
| [034](034-email-vs-slack-notifications.md) | Email vs Slack for Notifications | Accepted |
| [035](035-s3-lifecycle-management.md) | S3 Lifecycle Management | Accepted |
| [036](036-psutil-for-resource-monitoring.md) | psutil for System Resource Monitoring | Accepted |
| [037](037-typed-config-with-dataclasses.md) | Typed Configuration with Dataclasses | Accepted |
| [038](038-env-based-configuration.md) | Environment-Based Configuration | Accepted |
| [039](039-quality-gates-pattern.md) | Quality Gates Pattern | Accepted |
| [040](040-auto-remediation-pattern.md) | Auto Remediation Pattern | Accepted |
| [041](041-html-health-dashboard.md) | HTML Health Dashboard | Accepted |
| [042](042-realtime-monitoring-pattern.md) | Real-Time Monitoring Pattern | Accepted |
| [043](043-sla-definitions.md) | SLA Definitions for Stock Pipeline | Accepted |
| [044](044-feature-flags-pattern.md) | Feature Flags Pattern | Accepted |
| [045](045-experiment-management.md) | Experiment Management Framework | Accepted |
| [058](058-automl-pipeline.md) | AutoML Pipeline Pattern | Accepted |
| [046](046-data-mesh-pattern.md) | Data Mesh Pattern | Accepted |
| [047](047-event-driven-pipeline.md) | Event-Driven Pipeline Architecture | Accepted |
| [048](048-data-contracts-pattern.md) | Data Contracts Pattern | Accepted |
| [049](049-schema-registry-pattern.md) | Schema Registry Pattern | Accepted |
| [050](050-data-privacy-pattern.md) | Data Privacy and PII Management | Accepted |
| [051](051-pii-masking-strategy.md) | PII Masking Strategy | Accepted |
| [052](052-storage-tiering-strategy.md) | Storage Tiering Strategy | Accepted |
| [053](053-automated-archival-pipeline.md) | Automated Archival Pipeline | Accepted |
| [054](054-api-versioning-strategy.md) | API Versioning Strategy | Accepted |
| [055](055-api-category-organization.md) | API Endpoint Category Organization | Accepted |
| [056](056-test-coverage-strategy.md) | Test Coverage Strategy | Accepted |
| [057](057-performance-benchmarking.md) | Performance Benchmarking Strategy | Accepted |
| [059](059-streaming-analytics-pattern.md) | Streaming Analytics with Sliding Windows | Accepted |
| [060](060-vwap-for-intraday-analysis.md) | VWAP for Intraday Price Analysis | Accepted |
| [061](061-distributed-processing-pattern.md) | Distributed Processing with ThreadPoolExecutor | Accepted |
| [062](062-pipeline-profiling-pattern.md) | Pipeline Profiling and Bottleneck Detection | Accepted |
| [063](063-nlp-without-external-libraries.md) | NLP Without External Libraries | Accepted |
| [064](064-tfidf-from-scratch.md) | TF-IDF Implemented from Scratch | Accepted |
| [065](065-forecast-blending-strategy.md) | Forecast Blending Strategy | Accepted |
| [066](066-volatility-regime-detection.md) | Volatility Regime Detection | Accepted |
| [067](067-market-graph-analysis.md) | Market Graph Analysis for Correlation Detection | Accepted |
| [068](068-sector-rotation-detection.md) | Sector Rotation Detection | Accepted |
| [069](069-var-cvar-risk-metrics.md) | VaR and CVaR for Risk Management | Accepted |
| [070](070-efficient-frontier-optimization.md) | Efficient Frontier Portfolio Optimization | Accepted |
| [071](071-event-driven-workflow-triggers.md) | Event-Driven Workflow Triggers | Accepted |
| [072](072-multi-channel-notifications.md) | Multi-Channel Notification System | Accepted |
| [073](073-self-service-analytics-pattern.md) | Self-Service Analytics Pattern | Accepted |
| [074](074-data-mesh-access-control.md) | Data Mesh Access Control Pattern | Accepted |
| [075](075-compliance-frameworks.md) | Compliance Framework Coverage | Accepted |
| [076](076-audit-trail-strategy.md) | Audit Trail Strategy | Accepted |
| [077](077-predictive-monitoring-pattern.md) | Predictive Monitoring Pattern | Accepted |
| [078](078-health-fingerprinting.md) | Health Fingerprinting for State Change Detection | Accepted |
| [079](079-knowledge-graph-pattern.md) | Knowledge Graph for Domain Knowledge | Accepted |
| [080](080-semantic-search-inverted-index.md) | Semantic Search with Inverted Index | Accepted |
| [081](081-recommendation-engine-pattern.md) | Stock Recommendation Engine | Accepted |
| [082](082-report-generation-strategy.md) | Report Generation Strategy | Accepted |
| [083](083-model-deployment-environments.md) | Model Deployment Environments | Accepted |
| [084](084-serving-infrastructure-pattern.md) | ML Model Serving Infrastructure | Accepted |
| [085](085-pipeline-validation-framework.md) | Pipeline Validation Framework | Accepted |
