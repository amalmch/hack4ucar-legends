
FROM python:3.11-slim

WORKDIR /app

# System deps for Prophet, PyTorch, ReportLab, psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p saved_models exports logs/audit

EXPOSE 5001

CMD ["python", "app.py"]
