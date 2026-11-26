VENV := .venv
PY := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

.PHONY: help test venv clean

help:
	@echo "test   Run the Home Assistant test suite (creates the venv if needed)"
	@echo "venv   Create .venv and install the development dependencies"

test: $(VENV)
	$(PYTEST)

venv: $(VENV)

$(VENV):
	uv python install 3.14
	uv venv --python 3.14 $(VENV)
	uv pip install --python $(PY) -r requirements-dev.txt

clean:
	rm -rf .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
