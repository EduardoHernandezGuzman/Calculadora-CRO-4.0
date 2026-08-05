# -*- coding: utf-8 -*-
"""
Frecuentista (Bootstrap) con Session ID
Adaptación del notebook de Colab para integrarlo en el proyecto.

- Expone run(df, config) -> dict con: summary, figures, pdf_bytes, log_text
- Mantiene la lógica de bootstrap + gráficos + (opcional) interpretación IA.
"""

from __future__ import annotations

import io
import os
import warnings
from typing import Any, Dict, List, Optional

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
    detect_session_groups,
    make_comparison_record,
    mark_best_comparison,
)

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

warnings.filterwarnings("ignore")
sns.set(style="whitegrid")


def _safe_openai_client(api_key: Optional[str] = None) -> Optional["OpenAI"]:
    if OpenAI is None:
        return None

    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def interpretar_resultados_con_ia(
    resultados: Any, api_key: Optional[str] = None
) -> str:
    client = _safe_openai_client(api_key=api_key)
    if client is None:
        return ""

    items = resultados if isinstance(resultados, list) else [resultados]
    data_blocks = []
    for item in items:
        variant = item["g2"]
        ci_rel_low, ci_rel_high = item["ci_relativo_centrado"]
        data_blocks.append(
            f"""TEST A/{variant}: Control (A) vs Variante ({variant})
MUESTRAS: A: {item['n_g1']} filas | {variant}: {item['n_g2']} filas
CONVERSIONES: A: {item['conv_g1']} | {variant}: {item['conv_g2']}
TASA CONTROL: {item['media_real_g1']:.4f}
TASA VARIANTE {variant}: {item['media_real_g2']:.4f}
UPLIFT: {item['uplift_%']:.2f}%
NIVEL DE SIGNIFICANCIA DE QUE {variant} > A: {item['precision_b_mejor'] * 100:.2f}%
IC centrado: [{ci_rel_low:.2f}%, {ci_rel_high:.2f}%]
Cola derecha: > {item['ci_relativo_derecha_izq']:.2f}%
Cola izquierda: < {item['ci_relativo_izquierda_der']:.2f}%"""
        )

    prompt = f"""
Eres un Director de CRO. Analiza estos resultados de un test A/B.
IMPORTANTE: No uses la palabra "probabilidad", usa siempre "NIVEL DE SIGNIFICANCIA".

DATOS DEL TEST:
{chr(10).join(data_blocks)}

TU MISIÓN:
Interpreta si B es mejor que A para un directivo.

REGLAS DE DECISIÓN:
1) Significancia: Si el intervalo de confianza cruza el 0%, no es concluyente.
2) Nivel de significancia: Si el nivel de significancia de superioridad es > 95%, es un ganador sólido.

ESTRUCTURA:
🎯 DICTAMEN
📊 ANÁLISIS DE RIESGO
🚀 ACCIÓN RECOMENDADA
""".strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en A/B testing que habla siempre de nivel de significancia.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return ""


class AnalisisBootstrap:
    def __init__(self, n_iteraciones: int = 10000):
        self.n_iter = int(n_iteraciones)
        self.resultados: Dict[str, Any] = {}
        self.distribuciones_medias: Dict[str, np.ndarray] = {}
        self.distribucion_uplift_rel: Optional[np.ndarray] = None

    def analizar(self, datos_raw: Dict[str, np.ndarray]) -> None:
        grupos = list(datos_raw.keys())
        if len(grupos) < 2:
            raise ValueError("Se necesitan al menos 2 columnas/grupos para analizar (A y B).")

        g1_name, g2_name = grupos[0], grupos[1]

        data1 = np.array(datos_raw[g1_name], dtype=float)
        data2 = np.array(datos_raw[g2_name], dtype=float)

        n_g1, n_g2 = len(data1), len(data2)
        conv_g1, conv_g2 = np.sum(data1), np.sum(data2)

        print(f"🔄 Bootstrapping en curso ({self.n_iter} iteraciones)...")

        medias_g1 = np.zeros(self.n_iter)
        medias_g2 = np.zeros(self.n_iter)
        diferencias_ba = np.zeros(self.n_iter)

        for i in range(self.n_iter):
            muestra_1 = np.random.choice(data1, size=n_g1, replace=True)
            muestra_2 = np.random.choice(data2, size=n_g2, replace=True)

            m1, m2 = np.mean(muestra_1), np.mean(muestra_2)
            medias_g1[i], medias_g2[i] = m1, m2
            diferencias_ba[i] = m2 - m1

        self.distribuciones_medias[g1_name] = medias_g1
        self.distribuciones_medias[g2_name] = medias_g2
        self.distribuciones_medias["diferencia"] = diferencias_ba

        precision_b_mejor = float(np.mean(diferencias_ba > 0))

        ci_low = float(np.percentile(diferencias_ba, 2.5))
        ci_high = float(np.percentile(diferencias_ba, 97.5))

        m1_obs = float(np.mean(data1))
        m2_obs = float(np.mean(data2))

        se_control = float(np.sqrt(m1_obs * (1 - m1_obs) / n_g1)) if n_g1 else 0.0
        se_variante = float(np.sqrt(m2_obs * (1 - m2_obs) / n_g2)) if n_g2 else 0.0
        se_diferencia = float(np.sqrt(se_control**2 + se_variante**2))
        z_score = float((m2_obs - m1_obs) / se_diferencia) if se_diferencia else 0.0
        uplift_pct = (
            float((m2_obs - m1_obs) / m1_obs * 100)
            if m1_obs != 0
            else 0.0
        )

        if m1_obs != 0:
            uplift_rel = (diferencias_ba / m1_obs) * 100
            ci_rel_centrado = np.percentile(uplift_rel, [2.5, 97.5]).astype(float)
            ci_rel_derecha_izq = float(np.percentile(uplift_rel, 5.0))
            ci_rel_izquierda_der = float(np.percentile(uplift_rel, 95.0))
        else:
            uplift_rel = np.zeros_like(diferencias_ba)
            ci_rel_centrado = np.array([0.0, 0.0], dtype=float)
            ci_rel_derecha_izq = 0.0
            ci_rel_izquierda_der = 0.0

        self.distribucion_uplift_rel = uplift_rel

        ganador = (
            g2_name
            if (precision_b_mejor > 0.95 and ci_low > 0)
            else (g1_name if (precision_b_mejor < 0.05 and ci_high < 0) else None)
        )

        self.resultados = {
            "g1": g1_name,
            "g2": g2_name,
            "n_g1": n_g1,
            "n_g2": n_g2,
            "conv_g1": conv_g1,
            "conv_g2": conv_g2,
            "media_real_g1": m1_obs,
            "media_real_g2": m2_obs,
            "uplift_%": uplift_pct,
            "se_control": se_control,
            "se_variante": se_variante,
            "se_diferencia": se_diferencia,
            "z_score": z_score,
            "precision_b_mejor": precision_b_mejor,
            "ci_diferencia": (ci_low, ci_high),
            "ci_relativo_centrado": (float(ci_rel_centrado[0]), float(ci_rel_centrado[1])),
            "ci_relativo_derecha_izq": float(ci_rel_derecha_izq),
            "ci_relativo_izquierda_der": float(ci_rel_izquierda_der),
            "ganador": ganador,
        }

    def generar_reporte(self, pdf: Optional[PdfPages] = None) -> List[plt.Figure]:
        if not self.resultados:
            return []

        r = self.resultados
        figs: List[plt.Figure] = []

        print("\n" + "=" * 40)
        print(f"{'MÉTRICAS DEL TEST':^40}")
        print("=" * 40)
        print(f"{r['g1']} (A): {r['n_g1']} filas | {int(r['conv_g1'])} convs | Media: {r['media_real_g1']:.4f}")
        print(f"{r['g2']} (B): {r['n_g2']} filas | {int(r['conv_g2'])} convs | Media: {r['media_real_g2']:.4f}")
        print("-" * 40)
        print(f"{'NIVEL DE SIGNIFICANCIA DE QUE B > A: ' + f'{r['precision_b_mejor']*100:.2f}%':^40}")
        print(f"{'IC CENTRADO (UPLIFT): ' + f'[{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]':^40}")
        print(f"{'COLA DERECHA (IC 95% IZQUIERDA): ' + f'> {r['ci_relativo_derecha_izq']:.2f}%':^40}")
        print(f"{'COLA IZQUIERDA (IC 95% DERECHA): ' + f'< {r['ci_relativo_izquierda_der']:.2f}%':^40}")
        print("=" * 40)

        if pdf:
            fig_t = plt.figure(figsize=(8, 6))
            txt = (
                f"REPORTE DE NIVEL DE SIGNIFICANCIA BOOTSTRAP\n\n"
                f"{r['g1']} (Control): {r['n_g1']} filas, {int(r['conv_g1'])} conversiones\n"
                f"{r['g2']} (Variante): {r['n_g2']} filas, {int(r['conv_g2'])} conversiones\n\n"
                f"Tasa de conversión A: {r['media_real_g1']:.4f}\n"
                f"Tasa de conversión B: {r['media_real_g2']:.4f}\n\n"
                f"NIVEL DE SIGNIFICANCIA DE QUE B > A: {r['precision_b_mejor']*100:.2f}%\n"
                f"IC centrado: [{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]\n"
                f"Cola derecha (IC 95% izquierda): > {r['ci_relativo_derecha_izq']:.2f}%\n"
                f"Cola izquierda (IC 95% derecha): < {r['ci_relativo_izquierda_der']:.2f}%\n\n"
                f"RESULTADO: {r['ganador'] if r['ganador'] else 'Sin diferencia estadísticamente precisa'}"
            )
            fig_t.text(
                0.5,
                0.5,
                txt,
                family="monospace",
                fontsize=11,
                ha="center",
                va="center",
                bbox=dict(facecolor="none", edgecolor="black", pad=10),
            )
            pdf.savefig(fig_t)
            plt.close(fig_t)

        fig1 = plt.figure(figsize=(10, 5))
        sns.kdeplot(self.distribuciones_medias[r["g1"]], fill=True, color="gray", label=f"A: {r['g1']}")
        sns.kdeplot(self.distribuciones_medias[r["g2"]], fill=True, color="blue", label=f"B: {r['g2']}")
        plt.title("Precisión de Distribución de Medias")
        plt.xlabel("Conversión Media")
        plt.legend()
        if pdf is not None:
            pdf.savefig(fig1)
        figs.append(fig1)

        fig2 = plt.figure(figsize=(10, 5))
        sns.histplot(self.distribuciones_medias["diferencia"], color="skyblue", kde=True)
        plt.axvline(0, color="red", linestyle="--", label="Punto de No Diferencia")
        ci_izq, ci_der = r["ci_diferencia"]
        plt.axvline(ci_izq, color="green", linestyle=":", label=f"Lím. Izq: {ci_izq:.4f}")
        plt.axvline(ci_der, color="green", linestyle=":", label=f"Lím. Der: {ci_der:.4f}")
        plt.title("Contraste de Precisión: Diferencia (B - A)")
        plt.legend()
        if pdf is not None:
            pdf.savefig(fig2)
        figs.append(fig2)

        return figs


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
            significant = evidence > 0.95 and float(r["ci_relativo_centrado"][0]) > 0
            interval = [
                float(r["ci_relativo_centrado"][0]),
                float(r["ci_relativo_centrado"][1]),
            ]
            interval_name = "centered_95"

        comparisons.append(
            make_comparison_record(
                variant=r["g2"],
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

    winners = [item for item in comparisons if item["comparison_status"] == STATUS_WINNER]
    candidates = winners or [item for item in comparisons if item["favorable"]]
    if not candidates:
        return mark_best_comparison(comparisons, None, winner=False)
    best = max(candidates, key=lambda item: item["evidence"]["value"])
    return mark_best_comparison(comparisons, best["variant"], winner=bool(winners))


def _summary_row(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "control": "A", "variant": r["g2"],
        "grupo_A_col": r["g1"], "grupo_B_col": r["g2"],
        "n_A": r["n_g1"], "n_B": r["n_g2"],
        "conv_A": float(r["conv_g1"]), "conv_B": float(r["conv_g2"]),
        "media_A": float(r["media_real_g1"]), "media_B": float(r["media_real_g2"]),
        "uplift_%": float(r["uplift_%"]),
        "se_control": float(r["se_control"]), "se_variante": float(r["se_variante"]),
        "se_diferencia": float(r["se_diferencia"]), "z_score": float(r["z_score"]),
        "precision_B_mejor": float(r["precision_b_mejor"]),
        "ci_diff_low": float(r["ci_diferencia"][0]), "ci_diff_high": float(r["ci_diferencia"][1]),
        "ci_uplift_center_low": float(r["ci_relativo_centrado"][0]),
        "ci_uplift_center_high": float(r["ci_relativo_centrado"][1]),
        "ci_right_95_left": float(r["ci_relativo_derecha_izq"]),
        "ci_left_95_right": float(r["ci_relativo_izquierda_der"]),
        "ganador": r["ganador"] or "",
    }


def run(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or {}
    n_iteraciones = int(config.get("n_iteraciones", 10000))
    generate_figures = bool(config.get("generate_figures", True))
    generate_pdf = bool(config.get("generate_pdf", False)) and generate_figures
    include_ai = bool(config.get("include_ai", False))
    openai_api_key = config.get("openai_api_key", "")
    interval_type = str(config.get("freq_interval_type", "centrado"))
    layout = detect_session_groups(df.columns)
    control_values = df[layout.value_columns["A"]].dropna().values
    analyses = []
    for variant in layout.variants:
        analysis = AnalisisBootstrap(n_iteraciones=n_iteraciones)
        analysis.analizar({
            "A": control_values,
            variant: df[layout.value_columns[variant]].dropna().values,
        })
        analyses.append(analysis)

    pdf_bytes: Optional[bytes] = None
    figs: List[plt.Figure] = []

    if generate_pdf:
        buffer = io.BytesIO()
        with PdfPages(buffer) as pdf:
            for analysis in analyses:
                figs.extend(analysis.generar_reporte(pdf))
            if include_ai:
                texto_ia = interpretar_resultados_con_ia(
                    [analysis.resultados for analysis in analyses], api_key=openai_api_key
                )
                if texto_ia:
                    fig_ia = plt.figure(figsize=(8.27, 11.69))
                    fig_ia.clf()
                    fig_ia.text(0.05, 0.95, texto_ia, va="top", family="monospace", fontsize=10)
                    plt.axis("off")
                    pdf.savefig(fig_ia)
                    figs.append(fig_ia)
        pdf_bytes = buffer.getvalue()
        buffer.close()
    elif generate_figures:
        for analysis in analyses:
            figs.extend(analysis.generar_reporte(pdf=None))

    results = [analysis.resultados for analysis in analyses]
    summary = pd.DataFrame([_summary_row(result) for result in results])
    comparisons = _build_comparisons(results, interval_type)

    log_text = ""
    if include_ai:
        log_text = interpretar_resultados_con_ia(results, api_key=openai_api_key)

    return {
        "summary": summary,
        "figures": figs,
        "pdf_bytes": pdf_bytes,
        "log_text": log_text,
        "comparisons": comparisons,
    }
