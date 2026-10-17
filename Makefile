SHELL := /bin/bash
VENV := .venv
PIP := $(VENV)/bin/pip
DBT := $(VENV)/bin/dbt
INGEST := $(VENV)/bin/wikipulse-ingest

START ?=
END ?=

.DEFAULT_GOAL := help

.PHONY: help setup up down reset ingest crawl transform dbt-test api dashboard test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create the venv, install Python deps and dbt, fetch Go/Node deps
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ./ingestion -e "./api[dev]" -r dbt/requirements.txt
	cp -n dbt/profiles.example.yml dbt/profiles.yml || true
	cd crawler && go mod download
	cd dashboard && npm install

up: ## Start ClickHouse
	docker compose up -d clickhouse

down: ## Stop ClickHouse
	docker compose down

reset: ## Stop ClickHouse and delete its volume (drops all data)
	docker compose down -v

ingest: ## Load Wikimedia Pageviews; needs START=YYYYMMDD END=YYYYMMDD
	$(INGEST) pageviews --start $(START) --end $(END)

crawl: ## Crawl article content metrics into ClickHouse
	cd crawler && go run . --topics-file ../ingestion/topics.txt

transform: ## Build the dbt models (staging + marts)
	$(DBT) run --project-dir dbt --profiles-dir dbt

dbt-test: ## Run the dbt data tests
	$(DBT) test --project-dir dbt --profiles-dir dbt

api: ## Run the metrics API with reload
	$(VENV)/bin/uvicorn api.main:app --reload --port 8000

dashboard: ## Run the dashboard dev server
	cd dashboard && npm run dev

test: ## Run the API and crawler tests
	$(VENV)/bin/pytest api/tests -q
	cd crawler && go test ./...

lint: ## Lint Python and Go code
	$(VENV)/bin/ruff check ingestion api
	cd crawler && go vet ./...

clean: ## Remove build artifacts
	rm -rf dbt/target dbt/dbt_packages
	cd dashboard && rm -rf dist
