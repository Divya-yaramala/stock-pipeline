FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir streamlit plotly pandas psycopg2-binary yfinance

COPY dashboard/ ./dashboard/

EXPOSE 8503

CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8503", "--server.address=0.0.0.0"]
