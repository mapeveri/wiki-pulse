# Build context: repository root
#   docker build -f dbt/Dockerfile -t wikipulse/dbt .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY dbt/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY dbt/dbt_project.yml ./dbt/dbt_project.yml
COPY dbt/macros ./dbt/macros
COPY dbt/models ./dbt/models
# Env-var driven profile so the same image works locally and in Kubernetes.
COPY dbt/profiles.example.yml ./dbt/profiles.yml

WORKDIR /app/dbt

ENTRYPOINT ["dbt"]
CMD ["--help"]
