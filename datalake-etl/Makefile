PYTHON ?= python3
DBT ?= $(HOME)/.local/bin/dbt

DS ?= 2026-06-05
LAKE_ROOT ?= ./lake
export LAKE_ROOT DS DBT_PROFILES_DIR := $(CURDIR)/dbt
export PYTHONPATH := $(CURDIR)
export DBT_DUCKDB_PATH := $(CURDIR)/duckdb/local.duckdb
export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: help setup fixtures ingest bronze silver gold test all clean docker-all

help:
	@echo "Targets:"
	@echo "  make setup      Install Python deps"
	@echo "  make fixtures   Generate local sample staging data"
	@echo "  make ingest     Run thin Python ingest (staging/)"
	@echo "  make bronze     Land staging -> bronze Parquet"
	@echo "  make silver     dbt run --select silver.*"
	@echo "  make gold       dbt run --select gold.*"
	@echo "  make test       pytest + dbt test"
	@echo "  make all        Full local pipeline"
	@echo "  make docker-all Run full pipeline in Docker"
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

silver:
	$(DBT) run --project-dir dbt --profiles-dir dbt --select 'silver.*' \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

gold:
	$(DBT) run --project-dir dbt --profiles-dir dbt --select 'gold.*' \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

test:
	$(PYTHON) -m pytest tests/ -q
	$(DBT) test --project-dir dbt --profiles-dir dbt \
		--vars '{"ds": "$(DS)", "lake_root": "$(LAKE_ROOT)"}'

all: fixtures ingest bronze silver gold test

docker-all:
	DS=$(DS) docker compose run --rm etl all

clean:
	rm -rf lake staging duckdb/*.duckdb dbt/target dbt/logs dbt/.user.yml
