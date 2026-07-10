# Calculadora CRO 4.0 - A/B Testing

Aplicación web para analizar experimentos A/B orientados a CRO (Conversion Rate Optimization) mediante modelos bayesianos y frecuentistas. Incluye un asistente para configurar el análisis, carga de CSV, entrada manual para modelos frecuentistas, gráficos, interpretación opcional con IA y exportación a PDF.

## Motores disponibles

La aplicación conecta ocho combinaciones de motor y unidad de análisis:

| Enfoque | Método | Sin Session ID | Con Session ID |
|---|---|---:|---:|
| Bayesiano, conversiones únicas `[0,1]` | Beta-Binomial | Sí | Sí |
| Bayesiano, conversiones múltiples `[0,∞]` | Gamma-Poisson | Sí | Sí |
| Frecuentista | Bootstrap | Sí | Sí |
| Frecuentista analítico | z-test de proporciones / t-test de Welch | Sí | Sí |

Los contrastes frecuentistas permiten hipótesis de dos colas o de una cola, tanto derecha como izquierda.

## Requisitos

- Python 3 con soporte para entornos virtuales (`venv`).
- `make`, recomendado para ejecutar los comandos del proyecto.
- Conexión a Internet durante la primera instalación de dependencias.

Las dependencias de Python están declaradas en `requirements.txt`.

## Ejecución

Desde la raíz del repositorio:

```bash
make dev
```

La primera ejecución crea el entorno virtual `venv`, actualiza `pip`, instala las dependencias y arranca Uvicorn con recarga automática. La aplicación queda disponible en:

```text
http://localhost:8000
```

Para detener el servidor, pulsa `Ctrl+C`.

### Comandos Make

| Comando | Descripción |
|---|---|
| `make help` | Muestra los comandos disponibles |
| `make venv` | Crea el entorno virtual e instala las dependencias |
| `make install` | Instala o actualiza las dependencias |
| `make dev` | Arranca el servidor con recarga automática |
| `make run` | Alias de `make dev` |
| `make serve` | Arranca el servidor sin recarga automática |
| `make freeze` | Guarda las versiones instaladas en `requirements.txt` |
| `make clean` | Elimina cachés de Python |
| `make clean-all` | Elimina cachés y el entorno virtual |

También puede arrancarse con el script incluido:

```bash
./run.sh
```

O manualmente:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Formatos de entrada

El formato depende de la unidad de análisis seleccionada. Los nombres de las columnas distinguen mayúsculas, espacios y tildes.

### Datos agregados, sin Session ID

Los modelos agregados esperan una fila por día con estas columnas:

```csv
Día,Visitas A,Visitas B,Conversiones A,Conversiones B
1,100,95,5,8
2,110,105,6,7
```

Los motores frecuentistas también permiten introducir manualmente los totales de usuarios o sesiones y conversiones desde la interfaz.

### Datos por sesión

Los motores bayesianos con Session ID esperan `Día` y una columna `Conversiones X` por variante. Cada fila representa una sesión; los valores son `0/1` para conversiones únicas o un conteo para conversiones múltiples.

```csv
Día,Conversiones A,Conversiones B
1,0,
1,1,
1,,0
1,,1
```

Los motores frecuentistas con Session ID trabajan con las dos primeras columnas del CSV como muestras A y B. Admiten valores binarios o continuos y celdas vacías cuando las muestras tienen distinta longitud.

```csv
A,B
0,1
1,0
0,
```

## Interpretación con IA

La interpretación mediante OpenAI es opcional. La clave se puede introducir en el campo de la interfaz o configurar en un archivo `.env` en la raíz:

```dotenv
OPENAI_API_KEY=sk-...
```

También se puede exportar como variable de entorno. No es necesaria para ejecutar los análisis estadísticos sin IA.

## API

FastAPI expone los siguientes endpoints:

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/health` | Comprueba el estado del servicio |
| `GET` | `/api/engines` | Lista los motores disponibles |
| `POST` | `/api/analyze` | Ejecuta un análisis a partir de un CSV |

`POST /api/analyze` recibe `multipart/form-data` con:

| Campo | Contenido |
|---|---|
| `file` | Archivo CSV |
| `engine_key` | Identificador devuelto por `/api/engines` |
| `config` | JSON con opciones como `generate_pdf`, `include_ai` y `openai_api_key` |

La respuesta puede incluir `summary`, `figures`, `pdf_bytes`, `log_text` y `comparisons`.

## Arquitectura

```text
backend/
├── api/                 # Rutas y esquemas de FastAPI
├── core/                # Configuración y selección de motores
├── engines/             # Ocho motores estadísticos
└── main.py              # Aplicación FastAPI y montaje del frontend
frontend/
├── css/                 # Estilos
├── js/                  # Wizard, cliente API y calculadora
└── index.html            # SPA servida por FastAPI
```
