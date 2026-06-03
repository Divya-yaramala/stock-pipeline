# Loom Video Script — 3 Minute Portfolio Walkthrough

## Video Structure (3 minutes total)

### Intro (0:00 - 0:20)
"Hi, I am Divya Yaramala, a Data Engineer. Today I am walking you through my AI-powered stock price pipeline — a production-grade data engineering project I built over 90 days using Python, Apache Airflow, dbt, Snowflake, and AWS."

### Show GitHub Repo (0:20 - 0:40)
- Open https://github.com/Divya-yaramala/stock-pipeline
- Point to CI/CD badges: "Both CI and Code Quality checks pass on every commit"
- Point to 108 tests badge
- Scroll down to architecture diagram: "The pipeline has 13 steps"
- Mention: "Built with 7 documented architecture decisions"

### Show the Architecture (0:40 - 1:10)
- Point to ASCII architecture diagram
- Explain each layer:
  "Yahoo Finance API feeds raw data into AWS S3"
  "PostgreSQL handles staging with idempotent inserts"
  "dbt transforms raw data into analytics-ready marts"
  "Snowflake is the final warehouse layer"
  "Three AI components run in parallel"

### Show AI Components (1:10 - 1:40)
- "The AI layer has three components"
- "Isolation Forest detects unusual price movements"
- "Facebook Prophet forecasts next 5 days closing prices"
- "GPT-3.5 generates market insight summaries"
- Show the ingestion/ folder with all 15 modules

### Show Code Quality (1:40 - 2:10)
- Open tests/ folder: "14 test files, 108 tests total"
- Open .github/workflows/: "CI runs automatically on every push"
- Open docs/adr/: "7 Architecture Decision Records explaining every major choice"
- "This is how real engineering teams work"

### Show Production Features (2:10 - 2:40)
- "Beyond the basic pipeline I added production patterns"
- Dead letter queue: "Failed records are captured and replayed automatically"
- Data validation: "7-point quality checks with SLA alerting"
- Monitoring: "Per-step metrics and daily reports"
- Slack alerting: "Real-time notifications on failures"

### Closing (2:40 - 3:00)
"This project demonstrates end-to-end data engineering with modern tools and production patterns. I am currently looking for Data Engineer roles. The full code is on GitHub — link in the description."

## Screen Recording Checklist
- [ ] Open GitHub repo in browser
- [ ] Have VSCode open with project files
- [ ] Have terminal ready with pytest results
- [ ] Clear desktop before recording
- [ ] Use 1080p resolution
- [ ] Speak clearly and at moderate pace

## Tools for Recording
- Loom (free at loom.com)
- Or OBS Studio (free)
- Or Windows built-in: Windows + G

## Tips for a Great Recording
- Record in the morning when your energy is high
- Do a practice run first without recording
- Keep browser bookmarks ready for quick navigation
- Close all unnecessary tabs before recording
- Disable notifications during recording
- Speak to the camera like you are explaining to a colleague
- If you make a mistake just keep going — edit later
