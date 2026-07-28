# Compliance Guide — Stock Pipeline

## Overview
The pipeline implements compliance checks for 4 regulatory
frameworks covering financial data management.

## Compliance Frameworks

### CF001 — SOX (Sarbanes-Oxley)
Applies to: Public company financial data
Requirements:
- audit_trail: All data access logged
- data_integrity: No unauthorized modifications
- access_control: Role-based access enforced
- retention_7_years: Data kept for 7 years

### CF002 — GDPR
Applies to: EU user data or data subjects
Requirements:
- pii_protection: No PII in pipeline data
- data_minimization: Only necessary data collected
- right_to_erasure: Data deletion capability
- consent_tracking: User consent recorded

### CF003 — FINRA
Applies to: Broker-dealer financial data
Requirements:
- trade_reporting: All trades reported
- audit_trail: Complete audit log
- data_retention_6_years: 6-year retention
- supervisory_controls: Oversight documented

### CF004 — INTERNAL
Applies to: All pipeline data
Requirements:
- data_classification: All datasets classified
- quality_gates: Quality checks passing
- sla_compliance: SLAs being met
- documentation: ADRs and runbooks current

## Compliance Certificate
Auto-generated when framework score = 100%:
```json
{
  "certified": true,
  "framework": "CF004",
  "date": "2026-07-28",
  "certificate_id": "CERT-CF004-20260728"
}
```

## Audit Categories (8 types)

| Category | Examples |
|---|---|
| data_access | Reading S3 files, querying DB |
| data_modification | Writing to S3, DB inserts |
| pipeline_execution | Airflow task runs |
| model_training | ML model retraining |
| secret_access | Reading from secrets manager |
| compliance_check | Running compliance reports |
| schema_change | Adding/removing fields |
| config_change | Updating feature flags |

## Suspicious Activity Detection
Triggers:
- 3+ failed access attempts by same actor
- Access outside business hours (before 6 AM or after 10 PM)

Action: Review audit logs and investigate

## Running Compliance Checks
```bash
# Full compliance report
python -c "
from ingestion.compliance_reporter import generate_compliance_report
import os, datetime
result = generate_compliance_report(
    os.getenv('AWS_BUCKET_NAME'),
    datetime.datetime.now().strftime('%Y/%m/%d')
)
for fw, data in result.get('frameworks', {}).items():
    print(f'{fw}: {data.get(\"score_pct\", 0):.1f}%')
"
```
