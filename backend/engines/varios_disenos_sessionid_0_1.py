# -*- coding: utf-8 -*-
"""
Motor Bayesiano [0,1] CON Session ID (datos por sesión, agregación por día).

Entradas esperadas (mínimo):
- Columna "Día"
- Columnas "Conversiones A", "Conversiones B", ... (valores 0/1 o NaN)
"""

from __future__ import annotations

import os
import warnings
from collections import defaultdict
from io import BytesIO
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
    ExperimentGroups,
    detect_session_groups,
    make_comparison_record,
    mark_best_comparison,
)

warnings.filterwarnings("ignore", "Glyph .* missing from font")
sns.set(style="whitegrid")


def _interpretar_con_ia(resultados_ultimo_dia: Dict[str, Any], api_key: Optional[str] = None) -> str:
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        return "Interpretación IA no configurada (falta OPENAI_API_KEY en secrets o entorno)."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except Exception as e:
        return f"[IA] No disponible (no se pudo importar OpenAI): {e}"

    resumen_grupos: List[str] = []
    comparativas: List[str] = []

    for k, v in resultados_ultimo_dia.items():
        if isinstance(v, dict) and "media" in v:
            visitas_acum = resultados_ultimo_dia.get(f"acum_visitas_{k}", "N/A")
            conv_acum = resultados_ultimo_dia.get(f"acum_clicks_{k}", "N/A")
            resumen_grupos.append(
                f"Grupo {k}: Visitas Acumuladas={visitas_acum}, "
                f"Conversiones Acumuladas={conv_acum}, "
                f"Tasa Media={v['media']:.4f}, "
                f"IC95%=[{v['ci'][0]:.4f}, {v['ci'][1]:.4f}]"
            )

        if str(k).startswith("A_vs_") and isinstance(v, dict):
            variant = str(k).split("_vs_", 1)[1]
            comparativas.append(
                f"COMPARATIVA {k}:\n"
                f"- Probabilidad de que {variant} supere al control A: {v['prob_mejor']*100:.2f}%\n"
                f"- Uplift Medio Estimado: {v['uplift_media']*100:.2f}%\n"
                f"- IC CENTRADO 95%: [{v['ci_centered'][0]*100:.2f}%, {v['ci_centered'][1]*100:.2f}%]\n"
                f"- IC SUELO: > {v['ci_right'][0]*100:.2f}%\n"
                f"- IC TECHO: < {v['ci_left'][1]*100:.2f}%"
            )

    prompt = f"""
Eres un experto Senior en Estadística Bayesiana y Experimentación (A/B Testing). Tu trabajo es interpretar los resultados y dar una recomendación de negocio.

Instrucciones:
- Contempla objetivo de MAXIMIZAR o MINIMIZAR la métrica (da ambas interpretaciones).
- Regla del cero: si el intervalo de uplift incluye 0% => no hay diferencia concluyente.
- Gestión de riesgo: traduce el peor caso (suelo/techo) a lenguaje de negocio.
- Recomendación: detener el test o continuar.

DATOS DEL ÚLTIMO DÍA:
{chr(10).join(resumen_grupos)}

COMPARATIVAS:
{chr(10).join(comparativas)}

Lenguaje claro, ejecutivo y sin fórmulas.
""".strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un analista senior de CRO."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[IA] Error llamando a OpenAI: {e}"


class ConversionBayesBeta:
    def __init__(self, priors: Dict[str, Tuple[float, float]]):
        self.priors = priors.copy()
        self.historial: List[Dict[str, Any]] = []
        self.acumulados = defaultdict(lambda: {"clicks": 0.0, "visitas": 0.0})

    def actualizar_con_datos(
        self,
        datos: Dict[str, Tuple[float, float]],
        raw_data: Optional[pd.DataFrame] = None,
        dia: Optional[str] = None,
        num_samples: int = 100000,
    ) -> None:
        resultados: Dict[str, Any] = {
            "dia": dia or f"Día {len(self.historial)+1}",
            "raw_data": raw_data,
        }

        muestras: Dict[str, np.ndarray] = {}
        grupos = list(datos.keys())

        for grupo in grupos:
            alpha0, beta0 = self.priors.get(grupo, (1.0, 1.0))
            visitas_dia, clicks_dia = datos[grupo]

            self.acumulados[grupo]["clicks"] += float(clicks_dia)
            self.acumulados[grupo]["visitas"] += float(visitas_dia)

            total_visitas = self.acumulados[grupo]["visitas"]
            total_clicks = self.acumulados[grupo]["clicks"]
            total_fracasos = total_visitas - total_clicks

            alpha_post = alpha0 + total_clicks
            beta_post = beta0 + total_fracasos

            muestras_array = np.random.beta(
                a=alpha_post,
                b=beta_post,
                size=int(num_samples),
            ).astype(np.float64)

            muestras[grupo] = muestras_array

            mean = float(np.mean(muestras_array))
            std = float(np.std(muestras_array))
            ci = np.percentile(muestras_array, [2.5, 97.5]).astype(np.float64)

            resultados[f"acum_visitas_{grupo}"] = int(total_visitas)
            resultados[f"acum_clicks_{grupo}"] = int(total_clicks)

            resultados[grupo] = {
                "media": mean,
                "std": std,
                "ci": ci,
                "muestras": muestras_array,
            }

        control = "A"
        control_samples = muestras[control]
        for variant in grupos:
            if variant == control:
                continue
            variant_samples = muestras[variant]

            uplift_samples = np.where(
                control_samples != 0,
                (variant_samples - control_samples) / control_samples,
                0.0,
            )
            diff_samples = variant_samples - control_samples

            prob_mejor = float(np.mean(diff_samples > 0))
            mean_uplift = float(np.mean(uplift_samples))
            std_uplift = float(np.std(uplift_samples))

            ci_centered = np.percentile(uplift_samples, [2.5, 97.5]).astype(np.float64)
            ci_right = np.percentile(uplift_samples, [5.0, 100.0]).astype(np.float64)
            ci_left = np.percentile(uplift_samples, [0.0, 95.0]).astype(np.float64)

            resultados[f"A_vs_{variant}"] = {
                "uplift_media": mean_uplift,
                "uplift_std": std_uplift,
                "ci_centered": ci_centered,
                "ci_right": ci_right,
                "ci_left": ci_left,
                "prob_mejor": prob_mejor,
                "ganador": variant if prob_mejor >= 0.95 else None,
                "diff": diff_samples,
            }

        self.historial.append(resultados)


def _fig_histograma_raw(
    dia: str, raw_data: pd.DataFrame, groups: List[str]
) -> Optional[plt.Figure]:
    if raw_data is None or raw_data.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    plotted = False

    for group in groups:
        column = f"Conversiones {group}"
        if column not in raw_data.columns:
            continue
        s = raw_data[column].dropna()
        if len(s) > 0:
            sns.histplot(
                s,
                label=f"Grupo {group}",
                kde=False,
                element="step",
                alpha=0.4,
                discrete=True,
                ax=ax,
            )
            plotted = True

    if not plotted:
        plt.close(fig)
        return None

    ax.set_title(f"{dia} - Distribución Real (0=No conv, 1=Conv)")
    ax.set_xlabel("Valor de Conversión")
    ax.set_ylabel("Frecuencia (Sesiones)")
    ax.legend()
    return fig


def _fig_posteriors_beta(dia: str, paso: Dict[str, Any], grupos: List[str]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    for grupo in grupos:
        muestras = paso[grupo]["muestras"]
        sns.kdeplot(muestras, label=f"Grupo {grupo}", fill=True, ax=ax)
    ax.set_title(f"{dia} - Incertidumbre Tasa Conversión (Modelo Beta)")
    ax.set_xlabel("Tasa de Conversión Estimada")
    ax.legend()
    return fig


def _fig_diff(
    dia: str, stats: Dict[str, Any], control: str, variant: str
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    diff = stats["diff"]
    sns.histplot(diff, stat="density", element="step", alpha=0.3, label="Histograma", ax=ax)
    sns.kdeplot(diff, fill=True, alpha=0.4, label="Densidad", ax=ax)
    ax.axvline(0, linestyle="--", label="Ref (0)")
    ax.set_title(f"{dia} - Diferencia Absoluta ({variant} - {control})")
    ax.set_xlabel("Diferencia en Tasa de Conversión")
    ax.legend()
    return fig


def _build_beta_priors(
    expected_priors: Optional[Dict[str, Tuple[float, float]]],
    grupos: List[str],
) -> Dict[str, Tuple[float, float]]:
    if not expected_priors:
        return {g: (1.0, 1.0) for g in grupos}

    priors: Dict[str, Tuple[float, float]] = {}
    for g in grupos:
        conv, visitas = expected_priors.get(g, (0.0, 0.0))
        alpha0 = float(conv) + 1.0
        beta0 = float(visitas - conv) + 1.0 if visitas >= conv else 1.0
        priors[g] = (alpha0, beta0)

    return priors


def _aggregate_by_day_sessionid(
    df: pd.DataFrame,
    layout: ExperimentGroups,
) -> List[Tuple[Any, pd.DataFrame, Dict[str, Tuple[int, int]]]]:
    if "Día" not in df.columns:
        raise ValueError("Falta la columna 'Día' en el CSV.")

    dias_unicos = sorted(df["Día"].dropna().unique())
    out: List[Tuple[Any, pd.DataFrame, Dict[str, Tuple[int, int]]]] = []

    for dia_val in dias_unicos:
        df_dia = df[df["Día"] == dia_val].copy()
        datos_agregados: Dict[str, Tuple[int, int]] = {}

        for g in layout.groups:
            col = layout.value_columns[g]
            visitas = int(df_dia[col].count())
            conv = float(df_dia[col].sum(skipna=True))
            datos_agregados[g] = (visitas, int(conv))

        out.append((dia_val, df_dia, datos_agregados))

    return out


def _build_lightweight_comparisons(
    paso: Dict[str, Any], variants: Tuple[str, ...]
) -> List[Dict[str, Any]]:
    comparisons = []
    for variant in variants:
        stats = paso[f"A_vs_{variant}"]
        probability_variant_better = float(stats["prob_mejor"])
        favorable = float(stats["uplift_media"]) > 0
        comparison_winner = None
        if probability_variant_better >= 0.95:
            comparison_winner = variant
        elif probability_variant_better <= 0.05:
            comparison_winner = "A"
        significant = comparison_winner is not None
        record = make_comparison_record(
            variant=variant,
            control_value=float(paso["A"]["media"]),
            variant_value=float(paso[variant]["media"]),
            uplift_pct=float(stats["uplift_media"]) * 100,
            difference=float(np.mean(stats["diff"])),
            evidence_name="probability_superiority",
            evidence_value=float(stats["prob_mejor"]),
            interval_name="centered_95",
            interval=[
                float(stats["ci_centered"][0]) * 100,
                float(stats["ci_centered"][1]) * 100,
            ],
            favorable=favorable,
            significant=significant,
            comparison_winner=comparison_winner,
            metrics={
                "uplift_std_pct": float(stats["uplift_std"]) * 100,
                "ci_floor_pct": [
                    float(stats["ci_right"][0]) * 100,
                    float(stats["ci_right"][1]) * 100,
                ],
                "ci_ceiling_pct": [
                    float(stats["ci_left"][0]) * 100,
                    float(stats["ci_left"][1]) * 100,
                ],
            },
        )
        control_samples = np.asarray(paso["A"]["muestras"], dtype=float)
        variant_samples = np.asarray(paso[variant]["muestras"], dtype=float)
        reverse_difference_samples = control_samples - variant_samples
        reverse_uplift_samples = np.divide(
            reverse_difference_samples,
            variant_samples,
            out=np.zeros_like(reverse_difference_samples),
            where=variant_samples != 0,
        )
        reverse_interval = np.percentile(reverse_uplift_samples, [2.5, 97.5])
        reverse_values = (
            float(np.mean(reverse_uplift_samples) * 100),
            float(np.mean(reverse_difference_samples)),
            float(np.mean(control_samples > variant_samples)),
            float(reverse_interval[0] * 100),
            float(reverse_interval[1] * 100),
        )
        if not all(np.isfinite(value) for value in reverse_values):
            raise ValueError("La comparación bayesiana inversa contiene valores no finitos.")
        record["reverse_comparison"] = {
            "reference": variant,
            "compared": "A",
            "reference_value": float(paso[variant]["media"]),
            "compared_value": float(paso["A"]["media"]),
            "uplift_pct": reverse_values[0],
            "difference": reverse_values[1],
            "evidence": {
                "name": "probability_superiority",
                "value": reverse_values[2],
            },
            "interval": {
                "name": "centered_95",
                "low": reverse_values[3],
                "high": reverse_values[4],
            },
            "comparison_winner": comparison_winner,
            "comparison_status": record["comparison_status"],
            "is_best": False,
        }
        comparisons.append(record)

    winners = [
        item for item in comparisons
        if item["comparison_winner"] == item["variant"]
    ]
    if not winners and any(item["comparison_winner"] == "A" for item in comparisons):
        return mark_best_comparison(comparisons, None, winner=False)
    candidates = winners or [item for item in comparisons if item["favorable"]]
    if not candidates:
        return mark_best_comparison(comparisons, None, winner=False)
    best = max(candidates, key=lambda item: item["evidence"]["value"])
    return mark_best_comparison(comparisons, best["variant"], winner=bool(winners))


def run(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or {}
    num_samples = int(config.get("num_samples", 20000))
    generate_figures = bool(config.get("generate_figures", True))
    generate_pdf = bool(config.get("generate_pdf", False)) and generate_figures
    include_ai = bool(config.get("include_ai", False))
    openai_api_key = config.get("openai_api_key", "")
    expected_priors = config.get("expected_priors")

    layout = detect_session_groups(df.columns)
    grupos = list(layout.groups)

    priors = _build_beta_priors(expected_priors, grupos)
    modelo = ConversionBayesBeta(priors=priors)
    agregados = _aggregate_by_day_sessionid(df, layout)

    figures: List[plt.Figure] = []
    log_parts: List[str] = []
    summary_rows: List[Dict[str, Any]] = []

    for dia_val, df_dia_raw, datos_agregados in agregados:
        dia_label = f"Día {int(dia_val)}" if str(dia_val).isdigit() else f"Día {dia_val}"

        modelo.actualizar_con_datos(
            datos=datos_agregados,
            raw_data=df_dia_raw,
            dia=dia_label,
            num_samples=num_samples,
        )

        paso = modelo.historial[-1]
        grupos_stats = [
            g for g in paso if isinstance(paso.get(g), dict) and "media" in paso[g]
        ]

        for g in grupos_stats:
            total_visitas = int(paso.get(f"acum_visitas_{g}", 0))
            total_conv = int(paso.get(f"acum_clicks_{g}", 0))

            visitas_dia, conv_dia = datos_agregados[g]
            tasa_obs = (conv_dia / visitas_dia) if visitas_dia > 0 else 0.0

            summary_rows.append(
                {
                    "dia": dia_label,
                    "grupo": g,
                    "media": float(paso[g]["media"]),
                    "ci_low": float(paso[g]["ci"][0]),
                    "ci_high": float(paso[g]["ci"][1]),
                    "visitas": int(visitas_dia),
                    "conversiones": int(conv_dia),
                    "tasa_observada": float(tasa_obs),
                    "acum_visitas": total_visitas,
                    "acum_conversiones": total_conv,
                }
            )

        if generate_figures:
            f0 = _fig_histograma_raw(dia_label, df_dia_raw, grupos_stats)
            if f0 is not None:
                figures.append(f0)

            figures.append(_fig_posteriors_beta(dia_label, paso, grupos_stats))

            comparaciones = [
                k for k in paso.keys()
                if isinstance(k, str) and k.startswith("A_vs_")
            ]
            for clave in comparaciones:
                stats = paso[clave]
                control, variant = clave.split("_vs_")
                figures.append(_fig_diff(dia_label, stats, control, variant))

    summary_df = pd.DataFrame(summary_rows)
    comparisons = (
        _build_lightweight_comparisons(modelo.historial[-1], layout.variants)
        if modelo.historial
        else []
    )

    pdf_bytes: Optional[bytes] = None
    if generate_pdf:
        buffer = BytesIO()
        with PdfPages(buffer) as pdf:
            for fig in figures:
                pdf.savefig(fig)
        buffer.seek(0)
        pdf_bytes = buffer.read()

    if include_ai:
        if modelo.historial:
            log_parts.append("🤖 Interpretación IA (último día):")
            log_parts.append(_interpretar_con_ia(modelo.historial[-1], api_key=openai_api_key))
        else:
            log_parts.append("[IA] No hay historial para interpretar.")

    return {
        "summary": summary_df,
        "figures": figures,
        "pdf_bytes": pdf_bytes,
        "log_text": "\n\n".join(log_parts) if log_parts else "",
        "comparisons": comparisons,
    }
