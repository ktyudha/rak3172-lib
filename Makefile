VENV := .venv

ifeq ($(OS),Windows_NT)
    PYTHON := python
    BIN := $(VENV)/Scripts
else
    PYTHON := python3
    BIN := $(VENV)/bin
endif

PYTHON_VENV := $(BIN)/python
RAK := $(BIN)/rak3172

.PHONY: help
help:
	@echo "Available commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install   Create virtualenv & install the package (editable)"
	@echo "  make env       Create .env from .env.example (if missing), then edit it"
	@echo "  make init      Check .env and configure the module with it (do this once)"
	@echo ""
	@echo "LoRa modes:"
	@echo "  make run       Start what .env says (LORA_MODE / LORA_ROLE)"
	@echo "  make ports     List serial ports"
	@echo "  make gateway   Run P2P gateway   (settings from .env)"
	@echo "  make node      Run P2P node      (MESSAGE=hello INTERVAL=10)"
	@echo "  make otaa      Run LoRaWAN OTAA node (keys from .env)"
	@echo "  make abp       Run LoRaWAN ABP node  (keys from .env)"
	@echo ""
	@echo "Research experiments (Alice/Bob/Eve):"
	@echo "  make bob       Run Bob (gateway) - LORA_ADDRESS=1"
	@echo "  make alice     Run Alice (node) - LORA_ADDRESS=2"
	@echo "  make eve       Run Eve (listener) - LORA_ADDRESS=3"
	@echo "  make bob-csv CSV_FILE=path   Run Bob with custom CSV output"
	@echo "  make alice-csv CSV_FILE=path Run Alice with custom CSV output"
	@echo ""
	@echo "Maintenance:"
	@echo "  make freeze    Update requirements.txt"
	@echo "  make clean     Remove virtual environment"

.PHONY: install
install:
	$(PYTHON) -m venv $(VENV)
	$(PYTHON_VENV) -m pip install --upgrade pip
	$(PYTHON_VENV) -m pip install -e .

.PHONY: env
env:
	@test -f .env || cp .env.example .env && echo ".env ready - edit it, then run: make init"

.PHONY: init
init:
	$(RAK) init

.PHONY: run
run:
	$(RAK) run

.PHONY: ports
ports:
	$(RAK) ports

.PHONY: gateway
gateway:
	$(RAK) gateway

MESSAGE ?= hello
INTERVAL ?= 10

.PHONY: node
node:
	$(RAK) node --message "$(MESSAGE)" --interval $(INTERVAL)

.PHONY: otaa
otaa:
	$(RAK) otaa --message "$(MESSAGE)" --interval $(INTERVAL)

.PHONY: abp
abp:
	$(RAK) abp --message "$(MESSAGE)" --interval $(INTERVAL)

.PHONY: freeze
freeze:
	$(PYTHON_VENV) -m pip freeze > requirements.txt

.PHONY: clean
clean:
	rm -rf $(VENV) *.egg-info

# Research experiments: Alice, Bob, Eve
.PHONY: bob
bob:
	@test -f .env || (echo "Error: .env not found. Run: make env" && exit 1)
	LORA_ADDRESS=1 $(PYTHON_VENV) features/bob.py

.PHONY: alice
alice:
	@test -f .env || (echo "Error: .env not found. Run: make env" && exit 1)
	LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 $(PYTHON_VENV) features/alice.py

.PHONY: eve
eve:
	@test -f .env || (echo "Error: .env not found. Run: make env" && exit 1)
	LORA_ADDRESS=3 $(PYTHON_VENV) features/eve.py

.PHONY: bob-csv
bob-csv:
	@test -f .env || (echo "Error: .env not found. Run: make env" && exit 1)
	LORA_ADDRESS=1 CSV_FILE=$(CSV_FILE) $(PYTHON_VENV) features/bob.py

.PHONY: alice-csv
alice-csv:
	@test -f .env || (echo "Error: .env not found. Run: make env" && exit 1)
	LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 CSV_FILE=$(CSV_FILE) $(PYTHON_VENV) features/alice.py
