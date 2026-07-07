# Cost Optimization Guide — Stock Pipeline

## S3 Storage Costs
Based on AWS S3 Standard pricing (us-east-1):

| Storage Class | Cost/GB/Month |
|---|---|
| Standard | $0.023 |
| Standard-IA | $0.0125 |
| Glacier | $0.004 |
| Glacier Deep Archive | $0.00099 |

## Retention Policies
| Prefix | Retention | Reason |
|---|---|---|
| raw/stocks/ | 90 days | Needed for backfill |
| processed/anomalies/ | 180 days | ML training data |
| processed/predictions/ | 90 days | Model evaluation |
| processed/sentiment/ | 30 days | Short-lived value |
| cache/ | 7 days | Refreshed frequently |
| audit/ | Indefinite | Compliance requirement |
| lineage/ | Indefinite | Data governance |
| models/registry/ | Indefinite | ML artifacts |

## Running Cost Optimization

```bash
# Step 1: Preview (always do this first!)
python -c "from ingestion.s3_optimizer import run_s3_optimization; import os; print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"

# Step 2: Review the report
# Check: reports/s3_optimization/YYYY/MM/DD/report.json in S3

# Step 3: Execute deletion (only after reviewing!)
python -c "from ingestion.s3_optimizer import run_s3_optimization; import os; print(run_s3_optimization(os.getenv('AWS_BUCKET_NAME'), dry_run=False))"
```

## Estimated Monthly Savings
Running the optimizer weekly on a 6-month-old pipeline:
- Delete expired cache (7 days): ~$0.50/month
- Delete old sentiment (30 days): ~$1.20/month
- Glacier archive old raw data: ~$8.50/month
- Total estimated savings: ~$10/month

## Best Practices
- Always dry_run=True first
- Review deletion report before executing
- Never delete audit/ or lineage/ prefixes
- Run optimizer every Sunday at 2 AM (cron)
- Monitor S3 costs in AWS Cost Explorer monthly
