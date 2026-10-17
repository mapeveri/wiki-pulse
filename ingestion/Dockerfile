# Build context: repository root
#   docker build -f ingestion/Dockerfile -t wikipulse/ingestion .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY ingestion/pyproject.toml ./ingestion/pyproject.toml
COPY ingestion/src ./ingestion/src
RUN pip install ./ingestion

# Default topics file; can be overridden with --topics-file.
COPY ingestion/topics.txt /app/topics.txt

ENTRYPOINT ["wikipulse-ingest"]
CMD ["--help"]
