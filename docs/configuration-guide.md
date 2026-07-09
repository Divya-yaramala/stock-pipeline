# Configuration Guide — Stock Pipeline

## Overview
All configuration loaded from environment variables.
Never hardcode credentials in code!

## Quick Validation
```bash
python scripts/validate_secrets.py
```

## Configuration Classes

### AWSConfig
| Env Var | Required | Default | Description |
|---|---|---|---|
| AWS_ACCESS_KEY_ID | ✅ | - | AWS access key |
| AWS_SECRET_ACCESS_KEY | ✅ | - | AWS secret key |
| AWS_BUCKET_NAME | ✅ | - | S3 bucket name |
| AWS_REGION | ❌ | us-east-1 | AWS region |

### SnowflakeConfig
| Env Var | Required | Default | Description |
|---|---|---|---|
| SNOWFLAKE_ACCOUNT | ✅ | - | Account identifier |
| SNOWFLAKE_USER | ✅ | - | Username |
| SNOWFLAKE_PASSWORD | ✅ | - | Password |
| SNOWFLAKE_WAREHOUSE | ❌ | STOCK_PIPELINE_WH | Warehouse name |
| SNOWFLAKE_DATABASE | ❌ | STOCK_PIPELINE_DB | Database name |

### PostgresConfig
| Env Var | Required | Default | Description |
|---|---|---|---|
| POSTGRES_HOST | ✅ | - | Database host |
| POSTGRES_PORT | ❌ | 5432 | Database port |
| POSTGRES_USER | ✅ | - | Username |
| POSTGRES_PASSWORD | ✅ | - | Password |
| POSTGRES_DB | ✅ | - | Database name |

### PipelineConfig (Optional)
| Env Var | Required | Default | Description |
|---|---|---|---|
| OPENAI_API_KEY | ❌ | - | For GPT insights |
| SLACK_WEBHOOK_URL | ❌ | - | For Slack alerts |
| NEWS_API_KEY | ❌ | - | For news sentiment |
| SMTP_HOST | ❌ | - | For email reports |
| KAFKA_BOOTSTRAP_SERVERS | ❌ | - | For streaming |
| CHAOS_ENABLED | ❌ | false | Chaos engineering |

## .env File Template
Copy `.env.example` to `.env` and fill in values:
```bash
cp .env.example .env
```

## Security Best Practices
- Never commit `.env` to git (already in `.gitignore`)
- Rotate secrets every 90 days
- Use AWS IAM roles in production instead of keys
- Store production secrets in AWS Secrets Manager
