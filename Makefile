.PHONY: help install setup-db run-etl run-dbt test clean format lint all

help:
	@echo "Irish Housing Data Platform - Available Commands"
	@echo "=================================================="
	@echo "install      - Install Python dependencies"
	@echo "setup-db     - Create database tables"
	@echo "run-etl      - Run full ETL pipeline"
	@echo "run-dbt      - Run dbt transformations"
	@echo "test         - Run all tests"
	@echo "clean        - Clean temporary files"
	@echo "format       - Format Python code"
	@echo "lint         - Lint Python code"
	@echo "all          - Run full pipeline (ETL + dbt)"

install:
	pip install -r requirements.txt
	cd dbt && dbt deps

setup-db:
	@echo "Creating database tables..."
	@echo "Make sure to run: psql -h $$DB_HOST -U $$DB_USER -d $$DB_NAME -f sql/create_raw_tables.sql"

run-etl:
	python -m etl.main

run-dbt:
	cd dbt && dbt run --profiles-dir . && dbt test --profiles-dir .

test:
	pytest -v
	cd dbt && dbt test --profiles-dir .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf dbt/target
	rm -rf dbt/dbt_packages
	rm -rf dbt/logs

format:
	black etl/
	isort etl/

lint:
	flake8 etl/ --max-line-length=100
	black --check etl/

all: run-etl run-dbt
	@echo "✅ Full pipeline complete!"
