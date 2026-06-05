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
export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: help setup fixtures ingest bronze gx-bronze silver gx-silver gold gold-dimensional gold-denormalized test all clean docker-all lineage

help:
	@echo "Targets:"
	@echo "  make setup              Install Python deps"
	@echo "  make fixtures           Sample staging data"
	@echo "  make ingest             Thin Python -> staging/"
	@echo "  make bronze             DuckDB SQL -> bronze/"
	@echo "  make gx-bronze          Great Expectations on bronze"
	@echo "  make silver             dbt run silver.*"
	@echo "  make gx-silver          Great Expectations on silver"
	@echo "  make gold               dbt run dimensional + denormalized marts"
	@echo "  make gold-dimensional   Kimball-style dim + fact"
	@echo "  make gold-denormalized  Wide / summary marts"
	@echo "  make test               pytest + dbt test"
	@echo "  make lineage            Show local OpenLineage events file"
	@echo "  make all                Full pipeline"
	@echo ""
	@echo "Vars: DS=$(DS)  LAKE_ROOT=$(LAKE_ROOT)"

setup:
	pip install -r requirements.txt

fixtures:
	$(PYTHON) scripts/seed_fixtures.py --ds $(DS)

ingest:
	$(PYTHON) ingest/orders_api.py --ds $(DS) --lake-root $(LAKE_ROOT)

bronze:
	$(PYTHON) scripts/run_bronze.py --ds $(DS) --lake-root $(LAKE_ROOT)

gx-bronze:
	$(PYTHON) scripts/run_gx.py bronze --ds $(DS) --lake-root $(LAKE_ROOT)

silver:
	$(DBT_OL) run --project-dir dbt --profiles-dir dbt --select 'silver.*' \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

gx-silver:
	$(PYTHON) scripts/run_gx.py silver --ds $(DS) --lake-root $(LAKE_ROOT)

gold-dimensional:
	$(DBT_OL) run --project-dir dbt --profiles-dir dbt --select 'tag:dimensional' \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

gold-denormalized:
	$(DBT_OL) run --project-dir dbt --profiles-dir dbt --select 'tag:denormalized' \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

gold: gold-dimensional gold-denormalized

test:
	$(PYTHON) -m pytest tests/ -q
	$(DBT) test --project-dir dbt --profiles-dir dbt \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

lineage:
	@test -f lineage/events.ndjson && tail -5 lineage/events.ndjson || echo "No lineage events yet. Run make bronze or make silver."

all: fixtures ingest bronze gx-bronze silver gx-silver gold test

docker-all:
	DS=$(DS) docker compose run --rm etl all

clean:
	rm -rf lake staging lineage duckdb/*.duckdb dbt/target dbt/logs dbt/.user.yml
