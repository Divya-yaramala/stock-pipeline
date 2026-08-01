# Model Deployment Guide — Stock Pipeline

## Overview
The pipeline implements a structured 3-environment
deployment pipeline for all ML models.

## Deployment Environments

### Development (E001)
- Min accuracy: 60%
- Purpose: Initial model testing
- Auto-promote: No (manual review required)
- Who deploys: ML engineers

### Staging (E002)
- Min accuracy: 65%
- Purpose: Integration testing with real data
- Auto-promote: No (QA review required)
- Who deploys: Senior ML engineers

### Production (E003)
- Min accuracy: 70%
- Purpose: Live predictions for dashboard and API
- Auto-promote: No (approval required)
- Who deploys: Tech lead only

## Promotion Path
Development → Staging → Production

Each promotion:
1. Check accuracy meets target environment threshold
2. Create new deployment record
3. Mark previous deployment as superseded
4. Update active deployment pointer

## Rollback Procedure
If production model degrades:
1. Run rollback_deployment()
2. Previous version automatically restored
3. New deployment record created with status "rollback"
4. Alert sent via Slack

## Serving Endpoints
Each model gets an endpoint per environment:
- anomaly_detector (dev): port 8080
- anomaly_detector (staging): port 8081
- anomaly_detector (prod): port 8082

## Models Currently Deployed
| Model | Dev | Staging | Prod |
|---|---|---|---|
| anomaly_detector | v2.1.0 | v2.0.0 | v1.9.0 |
| price_predictor | v1.5.0 | v1.4.0 | v1.3.0 |
| ensemble_model | v3.0.0 | v2.9.0 | v2.8.0 |

## Deployment Commands
```python
# Create development deployment
python -c "
from ingestion.model_deployment_manager import create_deployment
import os
dep_id = create_deployment(
    'anomaly_detector', 'v2.1.0', 'development',
    {'accuracy': 0.85, 'rmse': 2.3},
    os.getenv('AWS_BUCKET_NAME')
)
print('Created:', dep_id)
"

# Check all deployments
python -c "
from ingestion.model_deployment_manager import run_deployment_check
import os
result = run_deployment_check(os.getenv('AWS_BUCKET_NAME'))
print('Total deployments:', result['total_deployments'])
for env, data in result['environments'].items():
    print(f'  {env}: {data}')
"
```
