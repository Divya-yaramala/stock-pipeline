# Feature Flags Guide — Stock Pipeline

## Overview
Feature flags allow enabling/disabling pipeline features
without code changes or redeployment.

## Default Flags

| Flag | Default | When to Change |
|---|---|---|
| enable_gpt_insights | ✅ True | Disable to save OpenAI costs |
| enable_kafka_streaming | ❌ False | Enable when Kafka is running |
| enable_chaos_engineering | ❌ False | NEVER enable in production |
| enable_ensemble_models | ✅ True | Disable for faster runs |
| enable_news_sentiment | ✅ True | Disable if no NEWS_API_KEY |
| enable_slack_alerts | ✅ True | Disable if no SLACK_WEBHOOK |
| enable_email_reports | ✅ True | Disable if no SMTP config |
| enable_snowflake_sync | ✅ True | Disable if no Snowflake creds |
| enable_auto_remediation | ✅ True | Disable for manual control |
| enable_ab_testing | ❌ False | Enable for model experiments |

## Common Flag Scenarios

### Development Environment
Disable expensive features for local dev:
```bash
python -c "from ingestion.feature_flag_manager import disable_flag; import os; disable_flag('enable_gpt_insights', os.getenv('AWS_BUCKET_NAME'))"
python -c "from ingestion.feature_flag_manager import disable_flag; import os; disable_flag('enable_snowflake_sync', os.getenv('AWS_BUCKET_NAME'))"
```

### Testing Environment
Enable chaos engineering for resilience testing:
```bash
python -c "from ingestion.feature_flag_manager import enable_flag; import os; enable_flag('enable_chaos_engineering', os.getenv('AWS_BUCKET_NAME'))"
```

### Production Environment
All flags at defaults — run audit to verify:
```bash
python -c "from ingestion.feature_flag_manager import run_flag_audit; import os; print(run_flag_audit(os.getenv('AWS_BUCKET_NAME')))"
```

## Flag Audit Output
```json
{
  "total": 10,
  "enabled": 7,
  "disabled": 3,
  "overridden": ["enable_kafka_streaming"]
}
```
