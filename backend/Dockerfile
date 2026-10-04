FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Сид идемпотентный: создаёт демо-данные только если база пустая.
CMD ["sh", "-c", "python -m scripts.seed_demo && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
