# Runbook — Stock Pipeline

This document covers operational procedures for the AI-powered stock price pipeline.

---

## Alert Response Procedures

### 🚨 Anomaly Alert Response
1. Check Slack for ticker and anomaly label (SPIKE/DROP/VOLUME)
2. Verify in dashboard: http://localhost:8503
3. Check raw data: aws s3 ls s3://bucket/raw/stocks/YYYY/MM/DD/TICKER/
4. If data corruption: run rollback script
   python scripts/rollback_pipeline.py --ticker AAPL --step prices --version-id abc12345
5. If genuine anomaly: no action needed — pipeline handles automatically

### ⚠️ Quality Warning Response
1. Check quality score in Slack message
2. Run quality scorer:
   python -c "from ingestion.quality_scorer import run_quality_scoring; import os, datetime; print(run_quality_scoring(os.getenv('AWS_BUCKET_NAME'), datetime.datetime.now().strftime('%Y/%m/%d')))"
3. Identify which dimension is failing (completeness, accuracy, etc.)
4. Check S3 for missing files if completeness issue
5. Re-run affected pipeline step if needed

### ❌ Pipeline Failure Response
1. Check Airflow UI: http://localhost:8080
2. Find failed task and check logs
3. Common fixes:
   - API timeout: re-run task manually in Airflow
   - S3 permission: check AWS credentials in .env
   - DB connection: check POSTGRES_HOST in .env
4. After fix: clear failed task and re-run in Airflow

---

## Weekly Maintenance Schedule

### Every Monday
- Check GitHub Actions — all green?
- Review Slack alerts from past week
- Check S3 storage quota

### Every Sunday (automated via cron)
- Run S3 optimizer (dry_run=True first!)
- Run health scorer
- Generate weekly quality trend report

### Monthly
- Review ADRs — any decisions to update?
- Update project-stats.md with current counts
- Review AWS costs in Cost Explorer
- Rotate secrets (90-day policy)

### Commands for Weekly Maintenance

```bash
# Check all systems
python scripts/health_check.py

# Run S3 optimization (dry run)
python -c "from ingestion.s3_optimizer import run_s3_optimization; import os; print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"

# Check resource usage
python -c "from ingestion.resource_manager import run_resource_check; import os; print(run_resource_check(os.getenv('AWS_BUCKET_NAME')))"
```

---

## Configuration Validation

### Before Every Pipeline Run
```bash
python scripts/validate_secrets.py
```

### Expected Output (all green)
```
=== REQUIRED SECRETS ===
  AWS            ✅ ok
  PostgreSQL     ✅ ok
  Snowflake      ✅ ok

=== OPTIONAL SECRETS ===
  OpenAI         ✅ ok
  Slack          ✅ ok
  Email          ⚠️  missing: SMTP_HOST, SMTP_USER (not required)
```

### If Required Secret Missing
```
ERROR: Required secrets are missing — pipeline cannot run
```
Fix: Add the missing variable to `.env` and re-run `validate_secrets.py`.

### Config Summary (safe to share — never shows secrets)
```bash
python -c "from ingestion.config_manager import get_config_summary; print(get_config_summary())"
# Output: {"tickers": ["AAPL", ...], "region": "us-east-1", "chaos_enabled": false}
```

---

## Quality Gate Procedures

### When a Gate Blocks the Pipeline
1. Check which gate failed in Slack alert
2. Run gate check manually:
```python
from ingestion.quality_gate import run_quality_gates
metrics = {'hours_since_update': 30, 'completeness_pct': 95.0,
           'quality_score': 88.0, 'anomaly_rate_pct': 5.0,
           'prediction_accuracy_pct': 75.0}
print(run_quality_gates(metrics, 'AAPL'))
```
3. Check auto remediation history:
```python
from ingestion.auto_remediation import get_remediation_history
import os
print(get_remediation_history('AAPL', os.getenv('AWS_BUCKET_NAME')))
```
4. Fix underlying issue (see Alert Response Procedures above)
5. Re-run blocked pipeline step in Airflow

### Common Gate Failures
- **G001 freshness_gate**: Yahoo Finance API rate limit hit → wait 1 hour
- **G002 completeness_gate**: S3 upload failed → check AWS credentials
- **G005 prediction_accuracy_gate**: Model drift → trigger retraining
