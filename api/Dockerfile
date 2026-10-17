# Build context: repository root
#   docker build -f api/Dockerfile -t wikipulse/api .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY api/pyproject.toml ./api/pyproject.toml
COPY api/src ./api/src
RUN pip install ./api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
