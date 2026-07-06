# Slack Setup Guide — Stock Pipeline

## Overview
The pipeline sends 6 types of Slack alerts:
- 🚨 Anomaly detected (red/danger)
- 📈 Prediction ready (green/good)
- ❌ Pipeline failure (red/danger)
- ⚠️ Quality warning (yellow/warning)
- 📊 Daily summary (green/good)
- 💡 Market insights (green/good)

## Setup Steps
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Stock Pipeline Bot"
4. Select your workspace
5. Click "Incoming Webhooks" → Toggle ON
6. Click "Add New Webhook to Workspace"
7. Select your #alerts channel
8. Copy the webhook URL

## Add to .env
SLACK_WEBHOOK_URL=<paste-your-webhook-url-here>

## Alert Examples

### Anomaly Alert (red)
🚨 Anomaly Detected: AAPL
Label: SPIKE
Price: $185.50
Score: -0.45
Date: 2026-07-04

### Daily Summary (green)
📊 Daily Pipeline Summary
Tickers processed: 5
Anomalies found: 2
Predictions made: 5
Avg quality score: 92.5%

## Disabling Alerts
Simply remove SLACK_WEBHOOK_URL from .env
All alert functions return False gracefully when not configured
