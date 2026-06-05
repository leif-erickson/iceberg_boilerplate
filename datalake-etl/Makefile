PYTHON ?= python3
DBT ?= $(HOME)/.local/bin/dbt
DBT_OL ?= $(HOME)/.local/bin/dbt-ol

DS ?= 2026-06-05
LAKE_ROOT ?= ./lake
export LAKE_ROOT DS DBT_PROFILES_DIR := $(CURDIR)/dbt
export PYTHONPATH := $(CURDIR)
export DBT_DUCKDB_PATH := $(CURDIR)/duckdb/local.duckdb
export OPENLINEAGE_CONFIG ?= quality/openlineage/openlineage.local.yml
export OPENLINEAGE_NAMESPACE ?= datalake-etl
export PROMETHEUS_PUSHGATEWAY_URL ?= http://localhost:9091
export PATH := $(HOME)/.local/bin:$(PATH)

STAGES := fixtures ingest bronze gx-bronze silver gx-silver gold-dimensional gold-denormalized test

.PHONY: help setup all prefect test gold lineage observability-up observability-down docker-all clean $(STAGES)

help:
	@echo "Targets:"
	@echo "  make setup              Install Python deps"
	@echo "  make all                Full pipeline (CLI + metrics)"
	@echo "  make prefect            Run via Prefect flow"
	@echo "  make observability-up   Prometheus + Grafana + Pushgateway + Prefect UI"
	@echo "  make observability-down Stop observability stack"
	@echo "  make lineage            Tail OpenLineage events"
	@echo ""
	@echo "Vars: DS=$(DS)  LAKE_ROOT=$(LAKE_ROOT)"

setup:
	pip install -r requirements.txt

$(STAGES):
	$(PYTHON) scripts/run_pipeline.py $@

gold:
	$(PYTHON) scripts/run_pipeline.py gold

all:
	$(PYTHON) scripts/run_pipeline.py all

prefect:
	$(PYTHON) orchestration/flows/medallion_flow.py

test:
	$(PYTHON) scripts/run_pipeline.py test

lineage:
	@test -f lineage/events.ndjson && tail -5 lineage/events.ndjson || echo "No lineage events yet."

observability-up:
	docker compose -f compose.observability.yml up -d pushgateway prometheus grafana prefect-server

observability-down:
	docker compose -f compose.observability.yml down

docker-all:
	DS=$(DS) docker compose run --rm etl all

clean:
	rm -rf lake staging lineage duckdb/*.duckdb dbt/target dbt/logs dbt/.user.yml
