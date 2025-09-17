# Makefile: create and manage a Python virtual environment

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
REQ := requirements.txt
FROZEN := requirements-frozen.txt

.PHONY: setup venv install verify clean-venv

# setup: create venv, install requirements, and verify
setup: venv install verify

# create the virtual environment (idempotent)
venv:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
	fi
	@$(PYTHON) -m pip install --upgrade pip setuptools wheel

# install packages from requirements.txt into the venv
install: venv
	@if [ -f "$(REQ)" ]; then \
		$(PIP) install -r $(REQ); \
		echo "Installed from $(REQ)"; \
	else \
		echo "No $(REQ) found, skipping install."; \
	fi

# verify and save a frozen requirements file
verify: install
	@$(PIP) freeze > $(FROZEN)
	@echo "Packages installed. Frozen requirements written to $(FROZEN)."

# remove the virtual environment
clean-venv:
	@rm -rf $(VENV)
	@echo "Removed $(VENV)"

