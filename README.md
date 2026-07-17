# Calculadora CRO 4.0 - A/B Testing

Aplicación web para analizar experimentos con un control A y hasta cuatro variantes B, C, D y E. Utiliza modelos bayesianos y frecuentistas orientados a CRO (Conversion Rate Optimization) e incluye carga de CSV, entrada manual, gráficos, interpretación opcional con IA y exportación a PDF.

Todas las comparaciones se realizan exclusivamente contra el control: A vs B, A vs C, A vs D y A vs E. No se calculan comparaciones entre variantes.

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

- A es siempre el control y es obligatorio.
- Debe existir al menos una variante.
- B, C, D y E son opcionales; solo se incluyen las variantes disponibles.
- Se admiten experimentos A/B, A/B/C, A/B/C/D y A/B/C/D/E.

### Datos agregados, sin Session ID

Cada grupo utilizado necesita las columnas `Visitas X` y `Conversiones X`. Las variantes no utilizadas no deben incluirse.

Ejemplo A/B:

```csv
Día,Visitas A,Conversiones A,Visitas B,Conversiones B
1,100,5,95,8
2,110,6,105,7
```

Ejemplo A/B/C:

```csv
Día,Visitas A,Conversiones A,Visitas B,Conversiones B,Visitas C,Conversiones C
1,100,20,100,24,100,18
```

Ejemplo A/B/C/D/E:

```csv
Día,Visitas A,Conversiones A,Visitas B,Conversiones B,Visitas C,Conversiones C,Visitas D,Conversiones D,Visitas E,Conversiones E
1,1000,200,1000,230,1000,180,1000,250,1000,210
```

### Datos por sesión

El formato recomendado para todos los motores con Session ID utiliza `Día`, `SessionID` y una columna `Conversiones X` por grupo. Cada fila pertenece a un único grupo; las columnas de los demás grupos deben estar vacías o contener `NaN`.

```csv
Día,SessionID,Conversiones A,Conversiones B,Conversiones C
1,A-001,1,,
1,A-002,0,,
1,B-001,,1,
1,B-002,,0,
1,C-001,,,1
```

Los motores frecuentistas con Session ID conservan compatibilidad con el formato heredado `A,B`, pero no debe mezclarse con el formato canónico `Conversiones A...E`.

### Entrada manual

La entrada manual está disponible en los ocho motores y utiliza el mismo contrato que un CSV:

- A es obligatorio.
- B-E son opcionales y las variantes vacías no se envían.
- Sin Session ID se genera internamente una fila agregada con visitas y conversiones.
- Con Session ID se generan `Día`, `SessionID` y las columnas canónicas `Conversiones X`.

En conversiones únicas `[0,1]`, las conversiones no pueden superar las visitas o sesiones. En conversiones múltiples `[0,∞]`, una sesión puede registrar más de una conversión y el total puede superar el número de visitas.

## Interpretación de resultados

La interfaz muestra una tarjeta por comparación A vs variante y destaca como máximo una:

- **Ganadora**: la comparación seleccionada cumple todos los criterios estadísticos vigentes del motor.
- **Mejor candidata**: es la comparación favorable con mayor evidencia, pero todavía no cumple todos los criterios de ganadora.
- **Sin ganador concluyente**: no existe una variante que cumpla los criterios necesarios.

Una comparación puede ser individualmente concluyente sin recibir el destacado principal cuando otra variante tiene mayor evidencia.

### Comparaciones múltiples

La calculadora no aplica Bonferroni, Holm, FDR ni otra corrección por comparaciones múltiples. Cada A vs variante reutiliza exactamente el cálculo A/B original para conservar la compatibilidad histórica.

Al analizar varias variantes aumenta el riesgo global de falsos positivos. Los resultados deben interpretarse teniendo en cuenta el número de comparaciones y el coste de una decisión incorrecta.

## Archivos de ejemplo

- `examples/bayes_sin_session_abc.csv`
- `examples/bayes_con_session_abc.csv`
- `examples/frecuentista_sin_session_abcde.csv`
- `examples/frecuentista_con_session_abc.csv`

Todos contienen datos sintéticos y pueden cargarse directamente desde la interfaz.

## Pruebas

La batería no requiere dependencias adicionales:

```bash
MPLBACKEND=Agg venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --check frontend/js/calculator.js
node tests/frontend_smoke.js
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
