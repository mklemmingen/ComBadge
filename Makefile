# ComBadge Testing Framework Makefile

.PHONY: help install test test-unit test-integration test-performance test-all
.PHONY: test-fast test-slow test-coverage test-parallel lint format type-check
.PHONY: security-scan clean test-reports benchmark load-test profile

# Default target
help: ## Show this help message
	@echo "ComBadge Testing Framework"
	@echo "=========================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install all dependencies
	pip install -e .
	pip install -r requirements-test.txt

install-dev: ## Install development dependencies
	pip install -e ".[dev]"
	pre-commit install

# Quick testing
test-fast: ## Run fast unit tests only
	pytest tests/unit/ -m "not slow" --tb=short -q

test-unit: ## Run all unit tests
	pytest tests/unit/ -v --cov=src/combadge --cov-report=term-missing

test-integration: ## Run integration tests
	pytest tests/integration/ -v --tb=short

test-performance: ## Run performance benchmarks
	pytest tests/performance/ -v --tb=short -m "not slow"

test-load: ## Run load tests
	pytest tests/performance/test_load_testing.py -v

# Comprehensive testing
test: test-unit test-integration ## Run unit and integration tests

test-all: ## Run all tests including performance
	pytest --cov=src/combadge --cov-report=html --cov-report=term-missing

test-slow: ## Run all tests including slow ones
	pytest --cov=src/combadge --cov-report=html -m ""

# Parallel testing
test-parallel: ## Run tests in parallel
	pytest -n auto --cov=src/combadge --cov-report=html

test-parallel-fast: ## Run fast tests in parallel
	pytest tests/unit/ -n auto -m "not slow" --tb=short

# Coverage reporting
test-coverage: ## Generate detailed coverage report
	pytest --cov=src/combadge --cov-report=html --cov-report=xml --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

coverage-report: ## Open coverage report in browser
	python -m webbrowser htmlcov/index.html

# Code quality
lint: ## Run linting checks
	ruff check src/ tests/
	ruff format --check src/ tests/

format: ## Format code
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check: ## Run type checking
	mypy src/combadge --ignore-missing-imports

# Security
security-scan: ## Run security scans
	bandit -r src/combadge
	safety check
	semgrep --config=auto src/

security-report: ## Generate security report
	bandit -r src/combadge -f json -o security-report.json || true
	safety check --json --output safety-report.json || true
	@echo "Security reports generated: security-report.json, safety-report.json"

# Performance testing
benchmark: ## Run performance benchmarks
	pytest tests/performance/test_nlp_performance.py -v --benchmark-only

benchmark-compare: ## Compare benchmarks
	pytest tests/performance/ --benchmark-compare --benchmark-compare-fail=mean:10%

profile: ## Profile application performance
	python -m cProfile -o profile.stats -m pytest tests/performance/test_nlp_performance.py::test_intent_classification_response_time
	python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"

profile-memory: ## Profile memory usage
	python -m memory_profiler tests/performance/test_system_benchmarks.py

# Load testing with Locust
load-test-ui: ## Start Locust UI for load testing
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

load-test-headless: ## Run headless load test
	locust -f tests/performance/locustfile.py --host=http://localhost:8000 \
		--users 50 --spawn-rate 2 --run-time 60s --headless

# Test reporting
test-reports: ## Generate comprehensive test reports
	pytest --html=test-report.html --self-contained-html \
		--junit-xml=test-results.xml \
		--cov=src/combadge --cov-report=html

test-allure: ## Generate Allure test reports
	pytest --alluredir=allure-results
	allure serve allure-results

# Specific test categories
test-nlp: ## Test NLP components only
	pytest tests/unit/test_intelligence/ tests/integration/test_nlp_pipeline_integration.py -v

test-api: ## Test API components only
	pytest tests/unit/test_api/ -v

test-fleet: ## Test fleet processing components
	pytest tests/unit/test_fleet/ -v

test-ui: ## Test UI components
	pytest tests/unit/test_ui/ tests/integration/test_ui_approval_workflow.py -v

test-email: ## Test email processing
	pytest -k "email" -v

test-templates: ## Test template system
	pytest -k "template" -v

# Test environment management
test-env-setup: ## Set up test environment
	@echo "Setting up test environment..."
	mkdir -p logs temp test-data
	cp config/.env.example .env.test

test-env-clean: ## Clean test environment
	rm -rf logs/* temp/* test-data/*
	rm -f .env.test

# CI/CD helpers
ci-test: ## Run tests as in CI (GitHub Actions)
	pytest tests/unit/ --cov=src/combadge --cov-report=xml --junit-xml=test-results.xml
	pytest tests/integration/ --junit-xml=integration-results.xml

ci-quality: ## Run quality checks as in CI
	ruff check src/ tests/
	mypy src/combadge --ignore-missing-imports
	bandit -r src/combadge --severity-level medium

# Development helpers
test-watch: ## Watch for changes and run tests
	pytest-watch -- tests/unit/ -x -v

test-debug: ## Run tests with debugging enabled
	pytest --pdb --tb=long -s

test-verbose: ## Run tests with maximum verbosity
	pytest -vv --tb=long --capture=no

test-failed: ## Re-run only failed tests
	pytest --lf -v

test-new: ## Run only tests for new/modified code
	pytest --testmon -v

# Cleanup
clean: ## Clean up generated files
	rm -rf __pycache__/ .pytest_cache/ .coverage htmlcov/ coverage.xml
	rm -rf test-results.xml test-report.html allure-results/
	rm -rf .mypy_cache/ .ruff_cache/
	rm -rf build/ dist/ *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

clean-all: clean ## Clean everything including test data
	rm -rf temp/ logs/ test-data/
	rm -f security-report.json safety-report.json profile.stats

# Documentation
test-docs: ## Test documentation examples
	python -m doctest src/combadge/*.py -v

# Database testing (if applicable)
test-db-setup: ## Set up test database
	@echo "Setting up test database..."
	# Add database setup commands here

test-db-teardown: ## Tear down test database
	@echo "Tearing down test database..."
	# Add database cleanup commands here

# Docker testing
test-docker: ## Run tests in Docker container
	docker build -t combadge-test -f Dockerfile.test .
	docker run --rm combadge-test

# Stress testing
stress-test: ## Run stress tests
	pytest tests/performance/test_load_testing.py::TestLoadTesting::test_stress_scenario -v

endurance-test: ## Run endurance tests
	pytest tests/performance/test_load_testing.py::TestLoadTesting::test_endurance_scenario -v

# Test data management
test-data-generate: ## Generate fresh test data
	python scripts/generate_test_data.py

test-data-validate: ## Validate test data integrity
	python scripts/validate_test_data.py

# Quick checks
check: lint type-check test-fast ## Run quick quality checks

verify: test-unit test-integration ## Verify core functionality

validate: test-all security-scan ## Full validation suite

# Help for specific test types
test-help: ## Show detailed testing help
	@echo ""
	@echo "ComBadge Testing Guide"
	@echo "====================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make install     - Install all dependencies"
	@echo "  make test-fast   - Run quick unit tests"
	@echo "  make test        - Run comprehensive tests"
	@echo ""
	@echo "Test Categories:"
	@echo "  Unit Tests       - Fast, isolated component tests"
	@echo "  Integration      - Component interaction tests"
	@echo "  Performance      - Benchmarks and load tests"
	@echo "  Security         - Security vulnerability scans"
	@echo ""
	@echo "Development Workflow:"
	@echo "  1. make test-fast         # Quick feedback"
	@echo "  2. make lint              # Code quality"
	@echo "  3. make test-integration  # Component interactions"
	@echo "  4. make test-performance  # Performance validation"
	@echo ""
	@echo "CI/CD Commands:"
	@echo "  make ci-test      - Run CI test suite"
	@echo "  make ci-quality   - Run CI quality checks"
	@echo ""

# Default target points to help
.DEFAULT_GOAL := help