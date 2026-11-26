VENV := .venv
PY := $(VENV)/bin/python
BIN := $(VENV)/bin
PKG := custom_components.skycrophd_hdmi_switch_infrared

.PHONY: help test lint typecheck check venv clean

help:
	@echo "test       Run the Home Assistant test suite with coverage (fails under 95%)"
	@echo "lint       ruff check + ruff format --check"
	@echo "typecheck  mypy --strict on the integration"
	@echo "check      lint + typecheck + test"
	@echo "venv       Create .venv and install the development dependencies"

test: $(VENV)
	$(BIN)/pytest --cov=$(PKG) --cov-report=term-missing --cov-fail-under=95

lint: $(VENV)
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck: $(VENV)
	$(BIN)/mypy custom_components

check: lint typecheck test

venv: $(VENV)

$(VENV):
	uv python install 3.14
	uv venv --python 3.14 $(VENV)
	uv pip install --python $(PY) -r requirements-dev.txt

clean:
	rm -rf .pytest_cache .mypy_cache .coverage
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
