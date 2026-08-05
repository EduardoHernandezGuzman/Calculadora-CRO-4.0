# -*- coding: utf-8 -*-
"""
Motor Bayesiano [0,1] SIN session_id (Beta-Binomial) - Multi-grupo

Refactor mínimo para:
- No ejecutar nada al importar (apto para Streamlit)
- Exponer run(df, config) para que la capa visual lo llame
- Mantener ejecución "standalone" vía CLI si se desea
"""

from __future__ import annotations

import io
import os
import warnings
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
    import pymc as pm  # noqa: F401
except Exception:
    pm = None  # type: ignore

warnings.filterwarnings("ignore", "Glyph .* missing from font")
sns.set(style="whitegrid")


def interpretar_con_ia(resultados: Dict[str, Any], api_key: Optional[str] = None) -> str:
    if not api_key:
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "Interpretación IA no configurada (falta OPENAI_API_KEY en secrets o entorno)."

    try:
        from openai import OpenAI
    except Exception:
        return "Interpretación IA no disponible (paquete openai no instalado)."

    client = OpenAI(api_key=api_key)

    resumen_grupos = []
    comparativas = []

    for k, v in resultados.items():
        if isinstance(v, dict) and "media" in v:
            visitas_acum = resultados.get(f"acum_visitas_{k}", "N/A")
            conv_acum = resultados.get(f"acum_clicks_{k}", "N/A")
            resumen_grupos.append(
                f"Grupo {k}: "
                f"Visitas Acumuladas={visitas_acum}, "
                f"Conversiones Acumuladas={conv_acum}, "
                f"Tasa Media={v['media']:.4f}, "
                f"IC95% (Tasa)=[{v['ci'][0]:.4f}, {v['ci'][1]:.4f}]"
            )

        if str(k).startswith("A_vs_") and isinstance(v, dict):
            variant = str(k).split("_vs_", 1)[1]
            comparativas.append(
                f"COMPARATIVA {k}: \n"
                f"- Probabilidad de que {variant} supere al control A: {v['prob_mejor'] * 100:.2f}%\n"
                f"- Uplift Medio Estimado: {v['uplift_media'] * 100:.2f}%\n"
                f"- Intervalo de Credibilidad (CENTRADO 95%): "
                f"[{v['ci_centered'][0] * 100:.2f}%, {v['ci_centered'][1] * 100:.2f}%]\n"
                f"- Intervalo Unilateral (SUELO): > {v['ci_right'][0] * 100:.2f}%\n"
                f"- Intervalo Unilateral (TECHO): < {v['ci_left'][1] * 100:.2f}%"
            )

    prompt = f"""
Eres un experto Senior en Estadística Bayesiana y Experimentación (A/B Testing). Tu trabajo es interpretar los resultados de un experimento y dar una recomendación de negocio.

TUS INSTRUCCIONES CLAVE:

Contexto del Objetivo: Antes de decidir un ganador, contempla que el objetivo puede ser el de MAXIMIZAR la métrica o MINIMIZARLA. Ofrece las dos interpretaciones

Si Minimizar: Buscamos 'Probabilidad A > B' > 95%.
Si Maximizar: Buscamos 'Probabilidad B > A' > 95%.

LA REGLA DEL CERO (Crucial):
Analiza el Intervalo de Credibilidad (IC) del Uplift.
Si el intervalo incluye el 0%: NO hay diferencia concluyente.

Gestión de Riesgo: Traduce el límite 'peor caso' (Suelo/Techo) del intervalo a lenguaje de negocio.

Recomendación: ¿Detener el test o continuar?

DATOS COMPLETOS DEL ÚLTIMO DÍA:
---------------------
{chr(10).join(resumen_grupos)}

COMPARATIVAS DETALLADAS:
{chr(10).join(comparativas)}
---------------------

Lenguaje claro, ejecutivo y sin fórmulas.
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un analista senior de CRO."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content


class ConversionBayesMultiGrupo:
    def __init__(self, priors: Dict[str, Tuple[float, float]]):
        self.priors = priors.copy()
        self.historial: List[Dict[str, Any]] = []
        self.acumulados = {grupo: {"visitas": 0, "conv": 0} for grupo in priors}

    def actualizar_con_datos(
        self,
        datos: Dict[str, Tuple[int, int]],
        dia: Optional[str] = None,
        num_samples: int = 100000,
    ):
        resultados: Dict[str, Any] = {"dia": dia or f"Día {len(self.historial) + 1}"}
        muestras: Dict[str, np.ndarray] = {}
        grupos = list(datos.keys())
        tasas_conversion: Dict[str, float] = {}

        for grupo in grupos:
            alpha0, beta0 = self.priors.get(grupo, (1, 1))
            visitas, conv = datos[grupo]
            alpha_post = alpha0 + conv
            beta_post = beta0 + visitas - conv

            muestras_array = np.random.beta(alpha_post, beta_post, num_samples).astype(
                np.float64
            )
            muestras[grupo] = muestras_array

            mean = alpha_post / (alpha_post + beta_post)
            std = np.sqrt(
                (alpha_post * beta_post)
                / (((alpha_post + beta_post) ** 2) * (alpha_post + beta_post + 1))
            )
            ci = np.percentile(muestras_array, [2.5, 97.5])

            resultados[grupo] = {
                "media": mean,
                "std": std,
                "ci": ci,
                "muestras": muestras_array,
            }

            tasa = conv / visitas if visitas > 0 else 0
            tasas_conversion[grupo] = tasa
            resultados[f"visitas_{grupo}"] = visitas
            resultados[f"conv_{grupo}"] = conv
            resultados[f"tasa_{grupo}"] = tasa

            self.priors[grupo] = (alpha_post, beta_post)
            if grupo not in self.acumulados:
                self.acumulados[grupo] = {"conv": 0, "visitas": 0}
            self.acumulados[grupo]["conv"] += conv
            self.acumulados[grupo]["visitas"] += visitas

            resultados[f"acum_visitas_{grupo}"] = self.acumulados[grupo]["visitas"]
            resultados[f"acum_clicks_{grupo}"] = self.acumulados[grupo]["conv"]

        control = "A"
        control_samples = muestras[control]
        total_control = self.acumulados[control]
        control_rate = (
            total_control["conv"] / total_control["visitas"]
            if total_control["visitas"] > 0
            else 0
        )

        for variant in grupos:
            if variant == control:
                continue
            variant_samples = muestras[variant]
            uplift = (variant_samples - control_samples) / control_samples
            diff = variant_samples - control_samples
            prob_mejor = np.mean(diff > 0)
            mean_uplift = np.mean(uplift)
            std_uplift = np.std(uplift)

            ci_centered = np.percentile(uplift, [2.5, 97.5])
            ci_right = np.percentile(uplift, [5.0, 100.0])
            ci_left = np.percentile(uplift, [0.0, 95.0])
            total_variant = self.acumulados[variant]
            variant_rate = (
                total_variant["conv"] / total_variant["visitas"]
                if total_variant["visitas"] > 0
                else 0
            )
            observed_uplift = (
                (variant_rate - control_rate) / control_rate
                if control_rate > 0
                else None
            )

            resultados[f"A_vs_{variant}"] = {
                "uplift_media": mean_uplift,
                "uplift_std": std_uplift,
                "uplift_ci": ci_centered,
                "ci_centered": ci_centered,
                "ci_right": ci_right,
                "ci_left": ci_left,
                "prob_mejor": prob_mejor,
                "ganador": variant if prob_mejor >= 0.95 else None,
                "diff": diff,
                "uplift1": observed_uplift,
            }

        self.historial.append(resultados)

    def mostrar_resultados_con_graficos(
        self, pdf: Optional[PdfPages] = None, show: bool = False
    ) -> List[plt.Figure]:
        figs: List[plt.Figure] = []

        for paso in self.historial:
            dia = paso["dia"]
            try:
                dia_num = int(str(dia).split()[1])
            except Exception:
                dia_num = None

            lines = [f"🗓️  {dia}"]
            grupos = [g for g in paso if isinstance(paso[g], dict) and "media" in paso[g]]
            for grupo in grupos:
                stats = paso[grupo]
                lines += [
                    f"Grupo {grupo}:",
                    f"  Media esperada: {stats['media'] * 100:.2f}%",
                    f"  Desviación estándar: {stats['std'] * 100:.2f}%",
                    f"  IC 95%: [{stats['ci'][0] * 100:.2f}%, {stats['ci'][1] * 100:.2f}%]",
                ]

            if pdf is not None:
                fig_text = plt.figure(figsize=(8.27, 11.69))
                fig_text.clf()
                fig_text.text(0.01, 0.99, "\n".join(lines), va="top", family="monospace")
                pdf.savefig(fig_text)
                plt.close(fig_text)

            fig1 = plt.figure(figsize=(10, 5))
            for grupo in grupos:
                muestras = paso[grupo]["muestras"]
                sns.kdeplot(muestras, label=f"Grupo {grupo}", fill=True)
            plt.title(f"{dia} - Distribuciones posteriores (Beta)")
            plt.xlabel("Tasa de conversión")
            plt.legend()

            if pdf is not None:
                pdf.savefig(fig1)
            figs.append(fig1)

            if show:
                plt.show()
            plt.close(fig1)

            comparaciones = [k for k in paso if str(k).startswith("A_vs_")]
            for clave in comparaciones:
                stats = paso[clave]
                control, variant = clave.split("_vs_")

                str_cent = f"[{stats['ci_centered'][0] * 100:.2f}%, {stats['ci_centered'][1] * 100:.2f}%]"
                str_right = f"> {stats['ci_right'][0] * 100:.2f}%"
                str_left = f"< {stats['ci_left'][1] * 100:.2f}%"

                comp_lines = [
                    f"\n📈 Uplift ({variant} frente al control {control}):",
                    f"  Media estimada: {stats['uplift_media'] * 100:.2f}%",
                    f"  ---------------------------------------------",
                    f"  1. IC Centrado:   {str_cent} (Estándar)",
                    f"  2. IC Suelo:      {str_right} (Mínimo asegurado 95%)",
                    f"  3. IC Techo:      {str_left} (Máximo riesgo 95%)",
                    f"  ---------------------------------------------",
                    f"  Probabilidad de que {variant} > {control}: {stats['prob_mejor'] * 100:.2f}%",
                ]

                if stats.get("ganador"):
                    if dia_num is not None and dia_num < 6:
                        comp_lines += [
                            "\n⚠️ *Atención:*",
                            "Aún no has alcanzado el día 6.",
                            "Este resultado podría cambiar con más datos.",
                        ]
                    else:
                        comp_lines += [
                            "\n🏆 Resultado final:",
                            f"  Ganador: {variant}",
                            f"  Decisión: Implementar {variant}",
                            f"  Razón: {variant} es mejor con {stats['prob_mejor'] * 100:.2f}% de probabilidad",
                        ]

                if pdf is not None:
                    fig_cmp = plt.figure(figsize=(8.27, 11.69))
                    fig_cmp.clf()
                    fig_cmp.text(
                        0.01,
                        0.99,
                        "\n".join(comp_lines),
                        va="top",
                        family="monospace",
                    )
                    pdf.savefig(fig_cmp)
                    plt.close(fig_cmp)

                fig2 = plt.figure(figsize=(10, 4))
                sns.kdeplot(stats["diff"], label=f"Diferencia ({variant} - {control})", fill=True)
                plt.axvline(0, color="black", linestyle="--")
                plt.title(f"{dia} - Diferencia de conversión: {variant} - {control}")
                plt.xlabel("Diferencia")
                plt.legend()

                if pdf is not None:
                    pdf.savefig(fig2)
                figs.append(fig2)

                if show:
                    plt.show()
                plt.close(fig2)

        return figs


def _build_priors_from_expected(
    expected: Dict[str, Tuple[int, int]]
) -> Dict[str, Tuple[int, int]]:
    priors: Dict[str, Tuple[int, int]] = {}
    for grupo, (conversiones, visitas) in expected.items():
        if not isinstance(conversiones, int) or not isinstance(visitas, int):
            continue
        if conversiones < 0 or visitas < 0:
            continue
        if conversiones > visitas:
            continue
        alfa = conversiones + 1
        beta = (visitas - conversiones) + 1
        priors[grupo] = (alfa, beta)
    return priors


def _extract_daily_data_from_aggregate_row(row: pd.Series) -> Dict[str, Tuple[int, int]]:
    datos: Dict[str, Tuple[int, int]] = {}
    for col in row.index:
        if str(col).startswith("Conversiones "):
            grupo = str(col).replace("Conversiones ", "")
            visitas_col = f"Visitas {grupo}"
            if visitas_col in row.index:
                conv = int(row[col])
                visitas = int(row[visitas_col])
                datos[grupo] = (visitas, conv)
    return datos


def _build_summary_from_historial(historial: List[Dict[str, Any]]) -> pd.DataFrame:
    records = []
    for paso in historial:
        dia = paso.get("dia")
        grupos = [g for g in paso if isinstance(paso[g], dict) and "media" in paso[g]]
        for g in grupos:
            stats = paso[g]
            records.append(
                {
                    "dia": dia,
                    "grupo": g,
                    "media": stats["media"],
                    "ci_low": float(stats["ci"][0]),
                    "ci_high": float(stats["ci"][1]),
                    "visitas": paso.get(f"visitas_{g}"),
                    "conversiones": paso.get(f"conv_{g}"),
                    "tasa_observada": paso.get(f"tasa_{g}"),
                    "acum_visitas": paso.get(f"acum_visitas_{g}"),
                    "acum_conversiones": paso.get(f"acum_clicks_{g}"),
                }
            )
    return pd.DataFrame.from_records(records)


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
            "comparison_winner": record["comparison_winner"],
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
    num_samples = int(config.get("num_samples", 100000))
    generate_pdf = bool(config.get("generate_pdf", False))
    include_ai = bool(config.get("include_ai", False))
    openai_api_key = config.get("openai_api_key", "")
    layout = detect_aggregate_groups(df.columns)

    expected_priors = config.get("expected_priors")
    if not isinstance(expected_priors, dict) or not expected_priors:
        expected_priors = {"A": (1, 1), "B": (1, 1)}

    priors = _build_priors_from_expected(expected_priors)
    for group in layout.groups:
        priors.setdefault(group, (1, 1))

    modelo = ConversionBayesMultiGrupo(priors)

    for _, row in df.iterrows():
        dia = f"Día {int(row['Día'])}" if "Día" in row.index else None
        datos = _extract_daily_data_from_aggregate_row(row)
        if datos:
            modelo.actualizar_con_datos(datos, dia=dia, num_samples=num_samples)

    pdf_bytes: Optional[bytes] = None
    figs: List[plt.Figure] = []
    if generate_pdf:
        buf = io.BytesIO()
        with PdfPages(buf) as pdf:
            figs = modelo.mostrar_resultados_con_graficos(pdf=pdf, show=False)
        pdf_bytes = buf.getvalue()
    else:
        figs = modelo.mostrar_resultados_con_graficos(pdf=None, show=False)

    summary = _build_summary_from_historial(modelo.historial)
    comparisons = (
        _build_lightweight_comparisons(modelo.historial[-1], layout.variants)
        if modelo.historial
        else []
    )

    ai_text: Optional[str] = None
    if include_ai and modelo.historial:
        try:
            ai_text = interpretar_con_ia(modelo.historial[-1], api_key=openai_api_key)
        except Exception as e:
            ai_text = f"No se pudo generar interpretación IA: {e}"

    return {
        "summary": summary,
        "figures": figs,
        "pdf_bytes": pdf_bytes,
        "log_text": ai_text,
        "comparisons": comparisons,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Motor Bayesiano [0,1] sin session_id (agregado por día)"
    )
    parser.add_argument("--csv", required=True, help="Ruta al CSV de entrada")
    parser.add_argument("--pdf", default="", help="Ruta de salida PDF (opcional)")
    parser.add_argument(
        "--samples",
        type=int,
        default=100000,
        help="Número de muestras (default: 100000)",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    cfg = {
        "num_samples": args.samples,
        "generate_pdf": bool(args.pdf),
        "expected_priors": {"A": (1, 1), "B": (1, 1), "C": (1, 1)},
    }

    out = run(df, cfg)

    if args.pdf and out.get("pdf_bytes"):
        with open(args.pdf, "wb") as f:
            f.write(out["pdf_bytes"])
        print(f"✅ PDF guardado en: {args.pdf}")

    print("✅ Ejecutado. Resumen:")
    print(out["summary"].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
