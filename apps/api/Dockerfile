FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN useradd --create-home apiuser
USER apiuser
EXPOSE 8000

# Worker-entrypoint kører fra samme image med anden kommando (Technical Master §2).
# PORT sættes af hostingplatformen (Render); lokalt falder den tilbage til 8000.
CMD ["sh", "-c", "exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
