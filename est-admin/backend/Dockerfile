FROM python:3.11-slim

WORKDIR /app

# 使用清华/阿里云源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y docker.io docker-compose && rm -rf /var/lib/apt/lists/*

COPY main.py .

ENV CONFIG_BASE_DIR=/app/configs/base
ENV CONFIG_INSTANCES_DIR=/app/configs/instances
ENV COMPOSE_DIR=/app/compose

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
