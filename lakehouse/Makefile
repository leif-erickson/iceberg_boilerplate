PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

DS ?= 2026-06-05
export LAKE_ROOT ?= $(CURDIR)/lake
export PYTHONPATH := $(CURDIR)
export OPENLINEAGE_CONFIG ?= lakehouse/openlineage.yml
export OPENLINEAGE_NAMESPACE ?= lakehouse
export DAGSTER_HOME ?= $(CURDIR)/dagster_home

.PHONY: help setup run sodacl test dagster-dev clean

help:
	@echo "Targets:"
	@echo "  make setup        Create venv + install deps"
	@echo "  make run          Run pipeline (orders) -> Iceberg"
	@echo "  make sodacl       Regenerate governance/soda/orders.yml from the contract"
	@echo "  make test         Run pytest"
	@echo "  make dagster-dev  Launch Dagster UI (http://localhost:3000)"

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

run:
	$(BIN)/python -m lakehouse.cli run orders data/raw/orders.csv --ds $(DS)

sodacl:
	$(BIN)/python -m lakehouse.cli sodacl orders --out governance/soda/orders.yml

test:
	$(BIN)/python -m pytest

dagster-dev:
	mkdir -p $(DAGSTER_HOME)
	$(BIN)/dagster dev -m dagster_project -h 0.0.0.0 -p 3000

clean:
	rm -rf lake lineage dagster_home
