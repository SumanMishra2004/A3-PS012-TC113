.PHONY: help validate lab-up lab-down scan evaluate report demo clean install lint test

help:
	@echo "A3-PS012-TC113 — DNS Resolver Exposure Assessment Tool"
	@echo ""
	@echo "Available targets:"
	@echo "  install          Install dependencies"
	@echo "  validate         Validate configuration files"
	@echo "  lab-up           Bring up Docker lab environment"
	@echo "  lab-down         Bring down Docker lab"
	@echo "  scan             Run DNS probe scan"
	@echo "  evaluate         Evaluate results against ground truth"
	@echo "  report           Generate reports (JSON, MD, HTML, CSV)"
	@echo "  demo             Full end-to-end demo (lab-up → scan → evaluate → report)"
	@echo "  lint             Run linters (pylint, mypy)"
	@echo "  test             Run test suite"
	@echo "  clean            Clean up artifacts"

install:
	pip install -e .

validate:
	python -m dnsprobe validate-config

lab-up:
	cd lab && docker-compose up -d

lab-down:
	cd lab && docker-compose down

scan:
	python -m dnsprobe scan --targets configs/targets.yaml --settings configs/settings.yaml --seed 42 --repeat 3 --out reports/run1

evaluate:
	python -m dnsprobe evaluate --results reports/run1/results.json --targets configs/targets.yaml

report:
	python -m dnsprobe report --results reports/run1/results.json --format html,md,json,csv

demo: lab-up scan evaluate report
	@echo "✓ Demo complete. Reports in reports/run1/"

lint:
	pylint src/dnsprobe/
	mypy src/dnsprobe/

test:
	pytest tests/ -v --cov=src/dnsprobe

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .coverage .pytest_cache .mypy_cache
	rm -rf reports/*
