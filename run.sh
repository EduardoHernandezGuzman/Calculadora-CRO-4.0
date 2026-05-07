#!/usr/bin/env bash
set -e

echo "=== Calculadora CRO 4.0 ==="
echo ""

# Verificar e instalar dependencias
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Instalando dependencias..."
pip install -q -r requirements.txt

echo ""
echo "Iniciando servidor..."
echo "Abrir en: http://localhost:8000"
echo ""

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
