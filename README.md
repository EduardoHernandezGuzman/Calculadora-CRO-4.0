# Calculadora CRO 4.0 — A/B Testing

Aplicación web para analizar experimentos A/B orientados a **CRO (Conversion Rate Optimization)** con enfoques **bayesiano** y **frecuentista**.

## Motores disponibles

| Motor | Distribución | Session ID |
|---|---|---|
| Bayesiano [0,1] | Beta-Binomial | ❌ / ✅ |
| Bayesiano [0,∞] | Gamma-Poisson | ❌ / ✅ |
| Frecuentista | Bootstrap | ❌ / ✅ |

## Arquitectura

```
backend/                 → API REST (FastAPI)
├── api/routes.py        → Endpoints: /analyze, /engines, /health
├── api/schemas.py       → Modelos Pydantic
├── core/engine_router.py → Enrutador de motores
├── core/config.py       → Configuración (OpenAI key)
└── engines/             → 6 motores de cálculo
frontend/                → SPA (HTML + CSS + JS vanilla)
├── index.html           → Página principal con wizard y calculadora
├── css/styles.css       → Sistema de diseño completo
└── js/                  → Lógica del frontend
```

Cada motor devuelve una estructura homogénea: `summary`, `figures`, `pdf_bytes`, `log_text`, `comparisons`.

## Funcionalidades

- Wizard guiado paso a paso para configurar el análisis
- Interpretación con IA vía OpenAI (opcional) — la API key se puede introducir directamente en la interfaz o mediante variable de entorno
- Exportación a PDF (opcional)
- Diseño responsive con identidad visual de VML THE COCKTAIL
- Sin dependencias de frameworks JS — HTML, CSS y JS vanilla

## Requisitos

```
fastapi uvicorn python-multipart pydantic-settings pandas matplotlib seaborn numpy openai pymc
```

## Ejecutar

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Abrir en el navegador: http://localhost:8000

## Variables de entorno

| Variable | Descripción |
|---|---|
| `OPENAI_API_KEY` | API key de OpenAI para la interpretación con IA |
