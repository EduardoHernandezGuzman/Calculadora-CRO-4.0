# -*- coding: utf-8 -*-
"""
Varios_diseno_frecuentista.py

Adaptación desde Colab a módulo reutilizable (Streamlit).
- Mantiene la lógica: Bootstrap sobre datos agregados + IC + gráfico + IA opcional.
- Elimina dependencias de Google Drive / rutas fijas.
"""

from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
try:
    import streamlit as st
except Exception:
    st = None  # FastAPI app: streamlit es opcional
from matplotlib.backends.backend_pdf import PdfPages

from backend.core.experiment_groups import (
    STATUS_WINNER,
    detect_aggregate_groups,
    make_comparison_record,
    mark_best_comparison,
)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

import warnings

warnings.filterwarnings("ignore", "Glyph .* missing from font")
sns.set(style="whitegrid")


def interpretar_resultados_con_ia(
    resultados: Any, api_key: Optional[str] = None
) -> str:
    """
    Función opcional que envía los resultados a ChatGPT para obtener
    una interpretación en lenguaje natural (como si fuera un Director de CRO).
    Si no hay API key, simplemente devuelve un mensaje de error.
    """
    if OpenAI is None:
        return "❌ La librería 'openai' no está instalada en este entorno."

    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "❌ OPENAI_API_KEY no está configurada en secrets o entorno."

    client = OpenAI(api_key=api_key)

    items = resultados if isinstance(resultados, list) else [resultados]
    data_blocks = []
    for item in items:
        variant = item.get("variant", "B")
        m1, m2 = item["media_real_g1"], item["media_real_g2"]
        ci_rel_low, ci_rel_high = item["ci_relativo_centrado"]
        data_blocks.append(
            f"""COMPARATIVA A vs {variant}:
Grupo Control (A):
Visitas Acumuladas = {item['n_g1']}
Conversiones Acumuladas = {int(item['conv_g1'])}
Tasa Media = {m1:.4f}

Grupo Variante ({variant}):
Visitas Acumuladas = {item['n_g2']}
Conversiones Acumuladas = {int(item['conv_g2'])}
Tasa Media = {m2:.4f}

UPLIFT (MEJORA) ESTIMADO: {item['uplift_%']:.2f}%
NIVEL DE SIGNIFICANCIA DE QUE {variant} > A: {item['precision_b_mejor'] * 100:.2f}%
IC centrado 95%: [{ci_rel_low:.2f}%, {ci_rel_high:.2f}%]
Límite inferior (escenario conservador): > {item['ci_relativo_derecha_izq']:.2f}%
Límite superior (escenario optimista): < {item['ci_relativo_izquierda_der']:.2f}%"""
        )

    prompt = f"""
Eres un Director de CRO. Analiza los resultados de un test A/B y proporciona una recomendación clara de negocio basada en inferencia frecuentista.

IMPORTANTE:
No uses la palabra "probabilidad". Usa siempre "NIVEL DE SIGNIFICANCIA".
Lenguaje claro, ejecutivo y sin fórmulas.

DATOS DEL TEST:
{chr(10).join(data_blocks)}

REGLAS DE DECISIÓN:

Significancia estadística (regla del cero):
Si el intervalo de confianza incluye el 0% → el resultado no es concluyente.

Nivel de significancia:
Si el nivel de significancia de superioridad es > 95% → considerar ganador sólido.

Gestión de riesgo:
Traduce el peor y mejor escenario del intervalo a impacto real de negocio.

ESTRUCTURA DE RESPUESTA:

DICTAMEN
Conclusión clara: ¿B gana, pierde o no hay evidencia suficiente?

ANÁLISIS DE RIESGO
Qué puede pasar en el peor y mejor escenario (impacto negocio).

ACCIÓN RECOMENDADA
¿Implementar variante, mantener control o seguir testeando?
Justificación breve y directa.
""".strip()

    # Llamamos a ChatGPT con el prompt armado arriba
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un Director de CRO experto en experimentación y análisis frecuentista.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"❌ Nota: Error de conexión con la API de OpenAI: {e}"


class AnalisisBootstrapAgregado:
    """
    Motor de análisis frecuentista mediante Bootstrap.
    Toma los datos agregados (visitas y conversiones de A y B)
    y remuestrea muchas veces para estimar la distribución de las tasas de conversión.
    """

    def __init__(self, n_iteraciones: int = 10000):
        # Número de remuestreos Bootstrap (por defecto 10,000)
        self.n_iter = int(n_iteraciones)
        self.resultados: Dict[str, Any] = {}
        self.distribuciones_medias: Dict[str, np.ndarray] = {}
        self.distribuciones_uplift_rel: Optional[np.ndarray] = None

    def analizar(
        self,
        n_a: int,
        conv_a: int,
        n_b: int,
        conv_b: int,
        variant: str = "B",
    ):
        """
        Paso 1: Convertir los datos agregados en vectores de 0s y 1s.
        Ejemplo: si n_a=100 y conv_a=30, creamos un vector con 30 unos y 70 ceros.
        """
        data_a = np.array([1] * int(conv_a) + [0] * int(n_a - conv_a))
        data_b = np.array([1] * int(conv_b) + [0] * int(n_b - conv_b))

        print(f"🔄 Iniciando Bootstrap con {self.n_iter} iteraciones...")

        # Preparar arrays vacíos para guardar los resultados de cada remuestreo
        medias_a = np.zeros(self.n_iter)
        medias_b = np.zeros(self.n_iter)
        diferencias_ba = np.zeros(self.n_iter)

        # --- BUCLE DE BOOTSTRAP ---
        # Remuestreamos con reemplazo muchas veces para simular
        # cómo se comportarían las tasas si repitiéramos el experimento.
        for i in range(self.n_iter):
            # En cada iteración, cogemos una muestra aleatoria CON reemplazo
            # del mismo tamaño que los datos originales y calculamos su media.
            # Esto nos da una "versión simulada" de la tasa de conversión.
            m_a = np.mean(np.random.choice(data_a, size=len(data_a), replace=True))
            m_b = np.mean(np.random.choice(data_b, size=len(data_b), replace=True))

            # Guardamos las tasas simuladas y su diferencia (B - A)
            medias_a[i] = m_a
            medias_b[i] = m_b
            diferencias_ba[i] = m_b - m_a

        # Almacenamos las distribuciones completas para usarlas después en los gráficos
        self.distribuciones_medias["A"] = medias_a
        self.distribuciones_medias["B"] = medias_b
        self.distribuciones_medias["diferencia"] = diferencias_ba

        # --- NIVEL DE SIGNIFICANCIA ---
        # ¿Qué porcentaje de las simulaciones mostraron B > A?
        # Si es >95%, decimos que B es significativamente mejor que A.
        precision_b_mejor = float(np.mean(diferencias_ba > 0))

        # --- INTERVALO DE CONFIANZA de la DIFERENCIA ABSOLUTA (B - A) ---
        # Ordenamos las 10,000 diferencias simuladas y cogemos:
        #   - el percentil 2.5  (límite inferior del IC 95%)
        #   - el percentil 97.5 (límite superior del IC 95%)
        # Esto nos da el rango donde está el verdadero valor de la diferencia
        # con un 95% de confianza.
        ci_low = float(np.percentile(diferencias_ba, 2.5))
        ci_high = float(np.percentile(diferencias_ba, 97.5))

        # --- TASAS OBSERVADAS (reales, sin simular) ---
        # Son las tasas que vimos realmente en el experimento.
        m_a_obs = conv_a / n_a if n_a != 0 else 0.0
        m_b_obs = conv_b / n_b if n_b != 0 else 0.0

        se_control = float(np.sqrt(m_a_obs * (1 - m_a_obs) / n_a)) if n_a else 0.0
        se_variante = float(np.sqrt(m_b_obs * (1 - m_b_obs) / n_b)) if n_b else 0.0
        se_diferencia = float(np.sqrt(se_control**2 + se_variante**2))
        z_score = float((m_b_obs - m_a_obs) / se_diferencia) if se_diferencia else 0.0
        uplift_pct = (
            float((m_b_obs - m_a_obs) / m_a_obs * 100)
            if m_a_obs != 0
            else 0.0
        )

        # --- UPLIFT RELATIVO y sus INTERVALOS DE CONFIANZA ---
        # El uplift relativo = (diferencia / tasa de A) * 100
        # Nos dice el % de mejora (o empeoramiento) respecto a A.
        if m_a_obs != 0:
            # Convertimos cada diferencia simulada a porcentaje relativo
            uplift_rel = (diferencias_ba / m_a_obs) * 100

            # IC CENTRADO (Two-Tailed): del percentil 2.5 al 97.5
            # Es el rango simétrico donde esperamos que esté el uplift real.
            ci_rel_centrado = np.percentile(uplift_rel, [2.5, 97.5]).astype(float)

            # COLA DERECHA (One-Tailed, límite inferior):
            #   percentil 5.0 → "¿Cuál es el mínimo uplift que podemos esperar
            #   con un 95% de confianza?" (solo nos importa el límite de abajo).
            ci_rel_derecha_izq = float(np.percentile(uplift_rel, 5.0))

            # COLA IZQUIERDA (One-Tailed, límite superior):
            #   percentil 95.0 → "¿Cuál es el máximo riesgo/empeoramiento
            #   que podemos esperar con un 95% de confianza?"
            ci_rel_izquierda_der = float(np.percentile(uplift_rel, 95.0))
        else:
            # Si la tasa de A es 0, no podemos calcular porcentajes
            uplift_rel = np.zeros_like(diferencias_ba)
            ci_rel_centrado = np.array([0.0, 0.0], dtype=float)
            ci_rel_derecha_izq = 0.0
            ci_rel_izquierda_der = 0.0

        self.distribuciones_uplift_rel = uplift_rel

        # Guardamos todos los resultados en un diccionario para usarlos después
        self.resultados = {
            "control": "A",
            "variant": variant,
            "n_g1": int(n_a),
            "n_g2": int(n_b),
            "conv_g1": int(conv_a),
            "conv_g2": int(conv_b),
            "media_real_g1": float(m_a_obs),
            "media_real_g2": float(m_b_obs),
            "uplift_%": uplift_pct,
            "se_control": se_control,
            "se_variante": se_variante,
            "se_diferencia": se_diferencia,
            "z_score": z_score,
            "precision_b_mejor": precision_b_mejor,
            "ci_diferencia": (ci_low, ci_high),
            "ci_relativo_centrado": (
                float(ci_rel_centrado[0]),
                float(ci_rel_centrado[1]),
            ),
            "ci_relativo_derecha_izq": float(ci_rel_derecha_izq),
            "ci_relativo_izquierda_der": float(ci_rel_izquierda_der),
        }

    def generar_reporte(self, pdf: Optional[PdfPages] = None):
        """
        Genera un reporte por consola o PDF con los resultados del análisis.
        """
        r = self.resultados
        variant = r["variant"]

        # === RESULTADOS POR CONSOLA ===
        print("\n" + "=" * 50)
        print(f"{f'ANÁLISIS DE PRECISIÓN {variant} vs A':^50}")
        print("=" * 50)
        print(
            f"{'Diseño A':<20} | Visitas: {r['n_g1']:>8} | Convs: {int(r['conv_g1']):>6}"
        )
        print(
            f"{f'Diseño {variant}':<20} | Visitas: {r['n_g2']:>8} | Convs: {int(r['conv_g2']):>6}"
        )
        print("-" * 50)
        print(
            f"NIVEL DE SIGNIFICANCIA DE QUE {variant} > A: {r['precision_b_mejor'] * 100:.2f}%"
        )
        print(
            f"IC CENTRADO (UPLIFT): [{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]"
        )
        print(
            f"COLA DERECHA (IC 95% IZQUIERDA): > {r['ci_relativo_derecha_izq']:.2f}%"
        )
        print(
            f"COLA IZQUIERDA (IC 95% DERECHA): < {r['ci_relativo_izquierda_der']:.2f}%"
        )
        print("=" * 50)

        # === PÁGINA DE TEXTO DEL PDF (si se genera) ===
        # Pinta los mismos resultados en una hoja dentro del PDF
        if pdf:
            fig_t = plt.figure(figsize=(8, 6))
            txt = (
                f"REPORTE DE NIVEL DE SIGNIFICANCIA (DATOS AGREGADOS)\n\n"
                f"Métricas de Control (A):\n"
                f"Visitas: {r['n_g1']} | Conversiones: {int(r['conv_g1'])}.\n\n"
                f"Métricas de Variante ({variant}):\n"
                f"Visitas: {r['n_g2']} | Conversiones: {int(r['conv_g2'])}.\n\n"
                f"--------------------------------------------\n"
                f"Tasa Conv. A: {r['media_real_g1']:.4%}\n"
                f"Tasa Conv. B: {r['media_real_g2']:.4%}\n\n"
                f"NIVEL DE SIGNIFICANCIA DE QUE {variant} > A: {r['precision_b_mejor'] * 100:.2f}%\n\n"
                f"INTERVALOS DEL UPLIFT RELATIVO:\n"
                f"IC Centrado: [{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]\n"
                f"Cola derecha (IC 95% izquierda): > {r['ci_relativo_derecha_izq']:.2f}%\n"
                f"Cola izquierda (IC 95% derecha): < {r['ci_relativo_izquierda_der']:.2f}%\n"
            )
            fig_t.text(
                0.5,
                0.5,
                txt,
                family="monospace",
                fontsize=11,
                ha="center",
                va="center",
                bbox=dict(facecolor="white", alpha=0.8, edgecolor="black", pad=15),
            )
            pdf.savefig(fig_t)
            plt.close(fig_t)

        # === GRÁFICO DE LA DISTRIBUCIÓN DE LA DIFERENCIA (B - A) ===
        # Muestra un histograma con todos los valores simulados de la diferencia
        # para visualizar dónde cae la mayor parte de la masa probabilística.
        fig = plt.figure(figsize=(10, 6))
        sns.histplot(
            self.distribuciones_medias["diferencia"],
            color="skyblue",
            kde=True,
            element="step",
        )
        # Línea roja discontinua en 0: marca "sin diferencia" (B = A)
        plt.axvline(0, color="red", linestyle="--", label="Sin diferencia")
        # Líneas verdes punteadas: límites del IC 95% de la diferencia absoluta
        plt.axvline(
            r["ci_diferencia"][0],
            color="green",
            linestyle=":",
            label=f"Lím. Izq: {r['ci_diferencia'][0]:.4f}",
        )
        plt.axvline(
            r["ci_diferencia"][1],
            color="green",
            linestyle=":",
            label=f"Lím. Der: {r['ci_diferencia'][1]:.4f}",
        )
        plt.title(f"Precisión del Uplift: Distribución de la diferencia ({variant} - A)")
        plt.xlabel("Diferencia de Tasas de Conversión")
        plt.legend(loc="upper right")

        if pdf:
            pdf.savefig(fig)

        return fig


def _build_comparisons(
    results: List[Dict[str, Any]], interval_type: str
) -> List[Dict[str, Any]]:
    comparisons = []
    for r in results:
        uplift = float(r["uplift_%"])
        precision = float(r["precision_b_mejor"])
        direction = "positive" if uplift > 0 else "negative" if uplift < 0 else "neutral"

        if interval_type == "derecha":
            evidence = precision
            favorable = uplift > 0
            significant = evidence > 0.95 and float(r["ci_relativo_derecha_izq"]) > 0
            interval = [float(r["ci_relativo_derecha_izq"]), None]
            interval_name = "right_95"
        elif interval_type == "izquierda":
            evidence = 1 - precision
            favorable = uplift < 0
            significant = evidence > 0.95 and float(r["ci_relativo_izquierda_der"]) < 0
            interval = [None, float(r["ci_relativo_izquierda_der"])]
            interval_name = "left_95"
        else:
            evidence = precision
            favorable = uplift > 0
            significant = (
                evidence > 0.95
                and float(r["ci_relativo_centrado"][0]) > 0
            )
            interval = [
                float(r["ci_relativo_centrado"][0]),
                float(r["ci_relativo_centrado"][1]),
            ]
            interval_name = "centered_95"

        comparisons.append(
            make_comparison_record(
                variant=r["variant"],
                control_value=float(r["media_real_g1"]),
                variant_value=float(r["media_real_g2"]),
                uplift_pct=uplift,
                difference=float(r["media_real_g2"] - r["media_real_g1"]),
                evidence_name="level_of_significance",
                evidence_value=evidence,
                interval_name=interval_name,
                interval=interval,
                favorable=favorable,
                significant=significant,
                metrics={
                    "direction": direction,
                    "precision_variant_better": precision,
                    "ci_centered_pct": list(r["ci_relativo_centrado"]),
                    "ci_right_floor_pct": float(r["ci_relativo_derecha_izq"]),
                    "ci_left_ceiling_pct": float(r["ci_relativo_izquierda_der"]),
                    "z_score": float(r["z_score"]),
                    "se_control": float(r["se_control"]),
                    "se_variante": float(r["se_variante"]),
                    "se_diferencia": float(r["se_diferencia"]),
                },
            )
        )

    winners = [
        item for item in comparisons
        if item["comparison_status"] == STATUS_WINNER
    ]
    candidates = winners or [item for item in comparisons if item["favorable"]]
    if not candidates:
        return mark_best_comparison(comparisons, None, winner=False)
    best = max(candidates, key=lambda item: item["evidence"]["value"])
    return mark_best_comparison(comparisons, best["variant"], winner=bool(winners))


def _summary_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "control": "A",
        "variant": r["variant"],
        "n_visitas_A": r["n_g1"],
        "n_visitas_B": r["n_g2"],
        "conv_A": r["conv_g1"],
        "conv_B": r["conv_g2"],
        "tasa_A": r["media_real_g1"],
        "tasa_B": r["media_real_g2"],
        "uplift_%": r["uplift_%"],
        "se_control": r["se_control"],
        "se_variante": r["se_variante"],
        "se_diferencia": r["se_diferencia"],
        "z_score": r["z_score"],
        "precision_B_mejor": r["precision_b_mejor"],
        "ci_diff_low": r["ci_diferencia"][0],
        "ci_diff_high": r["ci_diferencia"][1],
        "ci_uplift_center_low": r["ci_relativo_centrado"][0],
        "ci_uplift_center_high": r["ci_relativo_centrado"][1],
        "ci_right_95_left": r["ci_relativo_derecha_izq"],
        "ci_left_95_right": r["ci_relativo_izquierda_der"],
    }


def run(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Función principal que orquesta todo el análisis:
      1. Lee los datos de un DataFrame
      2. Ejecuta el Bootstrap
      3. Genera reporte (consola, PDF, gráfico)
      4. Opcionalmente pide interpretación a ChatGPT
    """
    config = config or {}
    n_iteraciones = int(config.get("n_iteraciones", 10000))
    generate_figures = bool(config.get("generate_figures", True))
    generate_pdf = bool(config.get("generate_pdf", False)) and generate_figures
    include_ai = bool(config.get("include_ai", False))
    openai_api_key = config.get("openai_api_key", "")
    interval_type = str(config.get("freq_interval_type", "centrado"))
    layout = detect_aggregate_groups(df.columns)

    total_v_a = int(df[layout.visit_columns["A"]].sum())
    total_c_a = int(df[layout.value_columns["A"]].sum())
    analyses = []
    for variant in layout.variants:
        analysis = AnalisisBootstrapAgregado(n_iteraciones=n_iteraciones)
        analysis.analizar(
            total_v_a,
            total_c_a,
            int(df[layout.visit_columns[variant]].sum()),
            int(df[layout.value_columns[variant]].sum()),
            variant=variant,
        )
        analyses.append(analysis)

    figures: List[Any] = []
    pdf_bytes: Optional[bytes] = None

    # === GENERAMOS REPORTE (consola y opcionalmente PDF) ===
    if generate_pdf:
        bio = io.BytesIO()
        with PdfPages(bio) as pdf:
            for analysis in analyses:
                fig_diff = analysis.generar_reporte(pdf)
                if fig_diff is not None:
                    figures.append(fig_diff)
        pdf_bytes = bio.getvalue()
    elif generate_figures:
        for analysis in analyses:
            fig_diff = analysis.generar_reporte(pdf=None)
            if fig_diff is not None:
                figures.append(fig_diff)

    # === INTERPRETACIÓN CON IA (opcional) ===
    log_text = ""
    if include_ai:
        log_text = interpretar_resultados_con_ia(
            [analysis.resultados for analysis in analyses], api_key=openai_api_key
        )

    results = [analysis.resultados for analysis in analyses]
    summary = pd.DataFrame([_summary_row(result) for result in results])
    comparisons = _build_comparisons(results, interval_type)

    return {
        "summary": summary,
        "figures": figures,
        "pdf_bytes": pdf_bytes,
        "log_text": log_text,
        "comparisons": comparisons,
    }
