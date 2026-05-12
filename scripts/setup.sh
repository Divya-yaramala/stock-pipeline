#!/usr/bin/env bash
# setup.sh — Bootstrap the stock-pipeline project environment
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Stock Price Pipeline Setup ==="

# 1. Create .env from example if it doesn't exist
if [ ! -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    echo "Created .env from .env.example — edit it with your credentials before continuing."

    # Auto-generate Fernet and secret keys
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "REPLACE_ME")
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "REPLACE_ME")

    sed -i "s|REPLACE_WITH_GENERATED_FERNET_KEY|$FERNET_KEY|" "$ROOT_DIR/.env"
    sed -i "s|REPLACE_WITH_GENERATED_SECRET_KEY|$SECRET_KEY|" "$ROOT_DIR/.env"
    echo "Auto-generated AIRFLOW_FERNET_KEY and AIRFLOW_SECRET_KEY."
else
    echo ".env already exists — skipping."
fi

# 2. Remind user about required credentials
echo ""
echo "Before running 'docker compose up', set the following in .env:"
echo "  AWS_ACCESS_KEY_ID"
echo "  AWS_SECRET_ACCESS_KEY"
echo "  S3_BUCKET"
echo "  POSTGRES_PASSWORD"
echo ""

# 3. Check Docker is available
if ! command -v docker &>/dev/null; then
    echo "ERROR: docker not found. Install Docker Desktop and try again."
    exit 1
fi

echo "=== Setup complete. Run: docker compose up --build -d ==="
