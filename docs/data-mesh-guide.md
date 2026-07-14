# Data Mesh Guide — Stock Pipeline

## Overview
The stock pipeline implements data mesh principles with
5 data products across 4 domains.

## Data Products

| Product | Domain | Owner | SLA | Consumers |
|---|---|---|---|---|
| DP001 stock_prices | market_data | data_engineering | 25h | ml_team, analytics |
| DP002 anomaly_signals | ml_insights | ml_team | 26h | trading, risk |
| DP003 price_forecasts | ml_insights | ml_team | 27h | trading, portfolio |
| DP004 market_sentiment | nlp_insights | data_engineering | 28h | trading, research |
| DP005 portfolio_analytics | analytics | analytics_team | 29h | executives |

## Domains
- market_data: Raw and processed price data
- ml_insights: ML model outputs (anomalies + forecasts)
- nlp_insights: NLP outputs (sentiment + insights)
- analytics: Business analytics and KPIs

## Event Bus Events

| Event | Trigger | Consumers |
|---|---|---|
| data_ingested | After Yahoo Finance fetch | ML pipeline |
| anomaly_detected | After Isolation Forest | Slack, trading |
| prediction_generated | After Prophet forecast | Dashboard, API |
| quality_gate_passed | Gate check passes | Next stage |
| quality_gate_blocked | Gate check fails | Remediation |
| sla_met | SLA deadline met | Reporter |
| sla_missed | SLA deadline missed | Alerts |
| model_retrain_triggered | Drift detected | ML pipeline |
| pipeline_completed | Full pipeline done | Summary |
| pipeline_failed | Any stage fails | Alerting |

## Data Mesh Commands

```bash
# Register all products
python -c "from ingestion.data_product_manager import run_data_mesh_registration; import os; run_data_mesh_registration(os.getenv('AWS_BUCKET_NAME'))"

# View domain summary
python -c "from ingestion.data_product_manager import get_domain_summary; import os; import json; print(json.dumps(get_domain_summary(os.getenv('AWS_BUCKET_NAME')), indent=2))"
```
