# Storage Guide — Stock Pipeline

## Storage Architecture

### S3 Storage Tiers
| Tier | Storage Class | Cost/GB/Month | When to Use |
|---|---|---|---|
| HOT | STANDARD | $0.023 | Active data < 30 days |
| WARM | STANDARD_IA | $0.0125 | Occasional access 30-90 days |
| COLD | GLACIER | $0.004 | Rare access 90-365 days |
| FROZEN | DEEP_ARCHIVE | $0.00099 | Compliance 1+ years |

### Archival Policies
| Prefix | Archive After | Delete After |
|---|---|---|
| raw/stocks/ | 90 days | 365 days |
| processed/anomalies/ | 180 days | 730 days |
| processed/predictions/ | 90 days | 365 days |
| processed/insights/ | 90 days | 365 days |
| processed/sentiment/ | 30 days | 180 days |
| models/experiments/ | 90 days | 730 days |

### Never Archive or Delete
- audit/ — compliance requirement (indefinite)
- lineage/ — data governance (indefinite)
- models/registry/ — ML artifacts (indefinite)
- data_contracts/ — schema history (indefinite)

## Monthly Cost Estimate
Assuming 6-month-old pipeline with 50GB total data:
- 10GB HOT (recent): $0.23/month
- 20GB WARM (30-90 days): $0.25/month
- 20GB COLD (90+ days): $0.08/month
Total: ~$0.56/month

## Running Archival
```bash
# Step 1: Always preview first!
python -c "from ingestion.data_archiver import run_archival_pipeline; import os; print(run_archival_pipeline(os.getenv('AWS_BUCKET_NAME'), dry_run=True))"

# Step 2: Review the report in S3
# reports/archival/YYYY/MM/DD/report.json

# Step 3: Execute if report looks correct
python -c "from ingestion.data_archiver import run_archival_pipeline; import os; print(run_archival_pipeline(os.getenv('AWS_BUCKET_NAME'), dry_run=False))"
```

## Retrieving Archived Data
```bash
# Glacier retrieval takes 3-5 minutes (Expedited) or 3-5 hours (Standard)
# Request retrieval via AWS Console or CLI:
aws s3api restore-object \
  --bucket your-bucket \
  --key raw/stocks/2026/01/01/AAPL.json \
  --restore-request Days=7,GlacierJobParameters={Tier=Expedited}
```
