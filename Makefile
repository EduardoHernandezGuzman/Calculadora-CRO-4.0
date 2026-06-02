# ============================================================
#  Calculadora CRO 4.0 — Makefile
# ============================================================

# Configuración
VENV       := venv
PYTHON     := python3
BIN        := $(VENV)/bin
PIP        := $(BIN)/pip
UVICORN    := $(BIN)/uvicorn
APP        := backend.main:app
HOST       := 0.0.0.0
PORT       := 8000

.DEFAULT_GOAL := help

# ------------------------------------------------------------
#  Ayuda
# ------------------------------------------------------------
.PHONY: help
help: ## Muestra esta ayuda
	@echo "Calculadora CRO 4.0 — comandos disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ------------------------------------------------------------
#  Entorno e instalación
# ------------------------------------------------------------
$(VENV)/bin/activate: requirements.txt
	@echo "Creando entorno virtual..."
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate

.PHONY: venv
venv: $(VENV)/bin/activate ## Crea el entorno virtual

.PHONY: install
install: $(VENV)/bin/activate ## Instala/actualiza las dependencias
	$(PIP) install -r requirements.txt

.PHONY: freeze
freeze: ## Congela las dependencias instaladas a requirements.txt
	$(PIP) freeze > requirements.txt

# ------------------------------------------------------------
#  Ejecución
# ------------------------------------------------------------
.PHONY: dev
dev: $(VENV)/bin/activate ## Arranca el servidor en modo desarrollo (con reload)
	@echo "Servidor en http://localhost:$(PORT)"
	$(UVICORN) $(APP) --reload --host $(HOST) --port $(PORT)

.PHONY: run
run: dev ## Alias de 'dev'

.PHONY: serve
serve: $(VENV)/bin/activate ## Arranca el servidor en modo producción (sin reload)
	@echo "Servidor en http://localhost:$(PORT)"
	$(UVICORN) $(APP) --host $(HOST) --port $(PORT)

# ------------------------------------------------------------
#  Limpieza
# ------------------------------------------------------------
.PHONY: clean
clean: ## Elimina cachés de Python (__pycache__, .pyc)
	find . -path ./$(VENV) -prune -o -type d -name '__pycache__' -exec rm -rf {} +
	find . -path ./$(VENV) -prune -o -type f -name '*.py[cod]' -delete

.PHONY: clean-all
clean-all: clean ## Elimina cachés y el entorno virtual
	rm -rf $(VENV)
