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
	@echo "  make install   Create virtualenv & install the package (editable)"
	@echo "  make env       Create .env from .env.example (if missing), then edit it"
	@echo "  make init      Check .env and configure the module with it (do this once)"
	@echo "  make run       Start what .env says (LORA_MODE / LORA_ROLE)"
	@echo "  make ports     List serial ports"
	@echo "  make gateway   Run P2P gateway   (settings from .env)"
	@echo "  make node      Run P2P node      (MESSAGE=hello INTERVAL=10)"
	@echo "  make otaa      Run LoRaWAN OTAA node (keys from .env)"
	@echo "  make abp       Run LoRaWAN ABP node  (keys from .env)"
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
