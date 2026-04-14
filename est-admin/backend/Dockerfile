FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y docker.io docker-compose && rm -rf /var/lib/apt/lists/*

COPY main.py .

ENV CONFIG_BASE_DIR=/app/configs/base
ENV CONFIG_INSTANCES_DIR=/app/configs/instances
ENV COMPOSE_DIR=/app/compose

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
