# Calculadora CRO 4.0 - A/B Testing

Aplicación web para analizar experimentos con un control A y hasta cuatro variantes B, C, D y E. Utiliza enfoques bayesianos y frecuentistas orientados a CRO (Conversion Rate Optimization) e incluye entrada manual, carga de CSV en el flujo bayesiano, gráficos, interpretación opcional con IA y exportación a PDF.

Todas las comparaciones se realizan exclusivamente contra el control: A vs B, A vs C, A vs D y A vs E. No se calculan comparaciones entre variantes.

## Motores disponibles

El backend conecta ocho combinaciones de motor y unidad de análisis:

| Enfoque | Método | Sin Session ID | Con Session ID |
|---|---|---:|---:|
| Bayesiano, conversiones únicas `[0,1]` | Beta-Binomial | Sí | Sí |
| Bayesiano, conversiones múltiples `[0,∞]` | Gamma-Poisson | Sí | Sí |
| Frecuentista | Bootstrap | Sí | Sí |
| Frecuentista analítico | z-test de proporciones / t-test de Welch | Sí | Sí |

Los contrastes frecuentistas permiten hipótesis de dos colas o de una cola, tanto derecha como izquierda.

El selector de la interfaz muestra únicamente **Enfoque Bayesiano** y **Enfoque Frecuentista (p-value)**. Bootstrap se conserva para compatibilidad interna y de API, pero no es seleccionable desde el frontend. En Bayesiano, el asistente permite elegir con o sin Session ID antes de seleccionar conversiones únicas o múltiples. En Frecuentista, la pantalla de Session ID se omite, `session_id` se fija a `false` y se continúa directamente con el tipo de hipótesis.

En el menú lateral frecuentista se muestran únicamente dos desplegables informativos: **Nivel de significancia (95%)** y **Poder estadístico (80%)**. Estos valores son explicativos y no modifican los umbrales, el tamaño muestral ni la configuración enviada a los motores.

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

### Despliegue en Render

El repositorio incluye [`render.yaml`](render.yaml) para desplegar el backend y el frontend como un único Web Service. La configuración utiliza Python 3.13.5 y el backend no interactivo `Agg` de Matplotlib.

Configuración equivalente para crear el servicio manualmente desde el panel de Render:

- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/health`
- **Instance Type:** `Free`

Variables de entorno:

| Variable | Valor | Obligatoria |
|---|---|---|
| `PYTHON_VERSION` | `3.13.5` | Sí |
| `MPLBACKEND` | `Agg` | Sí |
| `MPLCONFIGDIR` | `/tmp/matplotlib` | Recomendada |
| `OPENAI_API_KEY` | Secreto configurado en Render | Solo para interpretación con IA |

No guardes el valor de `OPENAI_API_KEY` en el repositorio. Si no se configura, los análisis siguen funcionando con la interpretación de IA desactivada.

El sistema de archivos de las instancias gratuitas de Render es efímero. Esta aplicación procesa CSV, gráficos y PDF en memoria y no necesita almacenamiento persistente. Las instancias gratuitas pueden suspenderse tras periodos de inactividad, por lo que la primera petición posterior puede tardar más en responder. Para reducir tiempo de CPU, memoria y tamaño de respuesta puede desactivarse **Generar gráficos**; esta opción también desactiva el PDF.

## Formatos de entrada

El formato depende de la unidad de análisis seleccionada. Los nombres de las columnas distinguen mayúsculas, espacios y tildes.

- A es siempre el control y es obligatorio.
- Debe existir al menos una variante.
- B, C, D y E son opcionales; solo se incluyen las variantes disponibles.
- Se admiten experimentos A/B, A/B/C, A/B/C/D y A/B/C/D/E.

En la interfaz, el enfoque bayesiano permite cargar CSV o introducir datos manualmente, tanto con Session ID como sin él. El enfoque frecuentista p-value muestra únicamente entrada manual y utiliza el motor sin Session ID. La API conserva la aceptación de CSV y los motores con Session ID para compatibilidad.

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

La entrada manual está disponible en todos los flujos visibles de la interfaz y utiliza el mismo contrato que un CSV:

- A es obligatorio.
- B se muestra inicialmente; C-E pueden añadirse y eliminarse. Las variantes ocultas, eliminadas o vacías no se envían.
- Sin Session ID se genera internamente una fila agregada con visitas y conversiones.
- Con Session ID se generan `Día`, `SessionID` y las columnas canónicas `Conversiones X`.

En conversiones únicas `[0,1]`, las conversiones no pueden superar las visitas o sesiones. En conversiones múltiples `[0,∞]`, una sesión puede registrar más de una conversión y el total puede superar el número de visitas.

## Interpretación de resultados

La interfaz muestra una tarjeta principal por comparación A vs variante y destaca como máximo una:

- **Ganadora**: la comparación seleccionada cumple todos los criterios estadísticos vigentes del motor.
- **Mejor candidata**: es la comparación favorable con mayor evidencia, pero todavía no cumple todos los criterios de ganadora.
- **Sin ganador concluyente**: no existe una variante que cumpla los criterios necesarios.

Una comparación puede ser individualmente concluyente sin recibir el destacado principal cuando otra variante tiene mayor evidencia.

El control A también puede ser ganador. En el frecuentista bilateral, el signo de una diferencia significativa determina si gana A o la variante. En los cuatro motores bayesianos, una probabilidad de superioridad de la variante igual o superior al 95 % declara ganadora a la variante; una probabilidad igual o inferior al 5 % declara ganador al control A.

Los cuatro motores bayesianos añaden `reverse_comparison` a cada A vs variante. La interfaz muestra junto a la tarjeta principal una tarjeta inversa B vs A, C vs A, etc., que contiene únicamente la probabilidad de que A supere a la variante y el ganador absoluto. Estas tarjetas son informativas: no participan en `is_best`, no duplican el resumen y no generan comparaciones entre variantes.

### Gráficos y PDF

La opción **Generar gráficos** está activada por defecto. Cuando está activa, los motores bayesianos procesan y conservan todo el historial, pero crean únicamente las figuras correspondientes al último estado acumulado. Por tanto, el número de gráficos depende de los grupos y comparaciones, no del número de días del CSV. Los motores frecuentistas ya generan figuras finales por comparación.

Cuando se desactiva, no se crean figuras Matplotlib/Seaborn, `figures` se devuelve vacío o `null` y la pestaña Gráficos se oculta. El resumen histórico, SRM, comparaciones, ganador, intervalos, salida tipo consola e interpretación con IA no cambian. En esta versión el PDF requiere gráficos: desactivar los gráficos desmarca y deshabilita también la generación de PDF.

### Comparaciones múltiples

La calculadora no aplica Bonferroni, Holm, FDR ni otra corrección por comparaciones múltiples. Cada A vs variante reutiliza exactamente el cálculo A/B original para conservar la compatibilidad histórica.

Al analizar varias variantes aumenta el riesgo global de falsos positivos. Los resultados deben interpretarse teniendo en cuenta el número de comparaciones y el coste de una decisión incorrecta.

### Chequeo SRM

Cada análisis incluye un chequeo global SRM (Sample Ratio Mismatch) independiente del motor estadístico. SRM comprueba mediante chi-cuadrado si el reparto de muestra entre todos los grupos detectados coincide con el reparto esperado; no mide diferencias de conversión.

En esta versión el reparto esperado es uniforme y se utiliza `alpha = 0.01`. Se muestra “Se detectó SRM” únicamente cuando `p_value < alpha`. El aviso es informativo: no bloquea ni modifica el análisis, las comparaciones o la selección de variante.

- Sin Session ID, la muestra es la suma de `Visitas X`.
- Con Session ID, la muestra es el número de valores no nulos en `Conversiones X` o en las columnas heredadas `A`, `B`, etc.
- Los valores cero cuentan como observaciones y los `NaN` no se cuentan.
- No se deduplican valores de `SessionID`; cada fila se considera una observación.

Antes de ejecutar SRM o un motor, la API valida que las columnas obligatorias no tengan vacíos, que visitas y conversiones sean enteros finitos y no negativos, y que los valores binarios sean 0 o 1. En Beta-Binomial y Frecuentista las conversiones no pueden superar las visitas; Gamma-Poisson permite superarlas porque representa conteos múltiples. Las variantes por sesión completamente vacías se ignoran. Los `SessionID` duplicados no se deduplican: la política vigente considera cada fila una observación independiente.

SRM todavía no se incluye en los prompts de IA ni en el PDF. Una futura versión podría incorporar ratios esperadas configurables y añadir el resultado a esos informes sin cambiar los cálculos de los motores.

## Archivos de ejemplo

- `examples/bayes_sin_session_abc.csv`
- `examples/bayes_con_session_abc.csv`
- `examples/frecuentista_sin_session_abcde.csv`
- `examples/frecuentista_con_session_abc.csv`

Todos contienen datos sintéticos válidos para pruebas y llamadas directas a la API. La interfaz muestra carga de CSV en los flujos bayesianos con y sin Session ID; los ejemplos frecuentistas sirven también para validar los motores conservados en backend.

## Pruebas

La batería no requiere dependencias adicionales:

```bash
MPLBACKEND=Agg venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
node --check frontend/js/calculator.js
node --check frontend/js/wizard.js
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
| `config` | JSON con las opciones de ejecución |

Opciones principales de `config`:

| Opción | Descripción |
|---|---|
| `generate_figures` | Genera únicamente los gráficos del resultado final. Por defecto es `true` |
| `generate_pdf` | Genera el PDF cuando es `true`; requiere `generate_figures=true` |
| `include_ai` | Solicita una única interpretación conjunta cuando es `true` |
| `openai_api_key` | Clave opcional para la interpretación con IA |
| `num_samples` | Número de muestras para motores bayesianos |
| `n_iteraciones` | Número de iteraciones para Bootstrap |
| `freq_interval_type` | Contraste frecuentista: `centrado`, `derecha` o `izquierda` |
| `session_id` | Indica si el CSV utiliza el formato por sesión |

`session_id` debe coincidir con el motor seleccionado y con las columnas del CSV. Si no se envía, se infiere a partir del motor para mantener la compatibilidad con clientes anteriores. Una contradicción entre configuración, motor y formato de datos devuelve un error `400` claro y no ejecuta el análisis.

La respuesta puede incluir `summary`, `figures`, `pdf_bytes`, `log_text`, `comparisons` y `srm`.

`comparisons` contiene un registro ligero y serializable por cada A vs variante, con tasas o medias, uplift, evidencia, intervalo, `comparison_winner`, estado estadístico, `selection_label` e `is_best`. Como máximo un registro puede tener `is_best=true`. En los cuatro motores bayesianos, cada registro incluye además un bloque ligero `reverse_comparison`; nunca se añade como un elemento independiente de la colección.

`srm` contiene el resultado global del reparto de muestra:

```json
{
  "has_srm": false,
  "alpha": 0.01,
  "chi2": 0.0,
  "p_value": 1.0,
  "degrees_of_freedom": 1,
  "total_sample": 20000,
  "groups": ["A", "B"],
  "sample_counts": {"A": 10000, "B": 10000},
  "expected_counts": {"A": 10000.0, "B": 10000.0},
  "expected_ratios": {"A": 0.5, "B": 0.5},
  "observed_ratios": {"A": 0.5, "B": 0.5}
}
```

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
examples/                 # CSV sintéticos de ejemplo
tests/                    # Tests unittest y smoke tests frontend
```
