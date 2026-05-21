# Этап 1: Сборка зависимостей
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY req.txt .

RUN pip install --no-cache-dir --user -r req.txt


# Этап 2: Финальный образ
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY . .

WORKDIR /app/adaptive_tasks
