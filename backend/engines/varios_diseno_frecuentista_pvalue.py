"""
Motor frecuentista basado en z-test de proporciones (sin Session ID).
Alternativa determinista al Bootstrap: mismo input siempre da el mismo resultado.
"""
from __future__ import annotations

import os
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from matplotlib.backends.backend_pdf import PdfPages

from backend.core.frequentist_ai_prompt import build_frequentist_ai_prompt

try:
    import streamlit as st
except Exception:
    st = None  # FastAPI app: streamlit es opcional

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


class AnalisisProporciones:
    """
    Z-test de dos proporciones independientes.
    H0: p_B = p_A  |  H1: p_B ≠ p_A (dos colas) o p_B > p_A / p_B < p_A (una cola)
    """

    def __init__(self):
        self.resultados: Dict[str, Any] = {}

    def analizar(self, n_a: int, conv_a: int, n_b: int, conv_b: int) -> None:
        p_a = conv_a / n_a if n_a > 0 else 0.0
        p_b = conv_b / n_b if n_b > 0 else 0.0
        diff = p_b - p_a

        # Proporción conjunta bajo H0 (pooled)
        p_pool = (conv_a + conv_b) / (n_a + n_b) if (n_a + n_b) > 0 else 0.5
        se_test = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
        z_stat = diff / se_test if se_test > 0 else 0.0

        # P-values
        p_two   = float(2 * (1 - stats.norm.cdf(abs(z_stat))))
        p_right = float(1 - stats.norm.cdf(z_stat))   # H1: B > A
        p_left  = float(stats.norm.cdf(z_stat))        # H1: B < A

        # Error estándar para IC (sin pooling)
        se_control = float(np.sqrt(p_a * (1 - p_a) / n_a)) if n_a > 0 else 0.0
        se_variante = float(np.sqrt(p_b * (1 - p_b) / n_b)) if n_b > 0 else 0.0
        se_diferencia = float(np.sqrt(se_control**2 + se_variante**2))
        z_score = float(diff / se_diferencia) if se_diferencia > 0 else 0.0
        se_ci = se_diferencia

        # IC 95% dos colas (z = 1.96)
        ci_diff_low  = diff - 1.96 * se_ci
        ci_diff_high = diff + 1.96 * se_ci

        # IC 95% una cola (z = 1.645)
        ci_right_bound = diff - 1.645 * se_ci  # límite inferior (cola derecha)
        ci_left_bound  = diff + 1.645 * se_ci  # límite superior (cola izquierda)

        # Uplift relativo expresado como % sobre la tasa de A
        if p_a != 0:
            uplift_pct            = diff / p_a * 100
            ci_uplift_center_low  = ci_diff_low  / p_a * 100
            ci_uplift_center_high = ci_diff_high / p_a * 100
            ci_right_95_left      = ci_right_bound / p_a * 100
            ci_left_95_right      = ci_left_bound  / p_a * 100
        else:
            uplift_pct = ci_uplift_center_low = ci_uplift_center_high = 0.0
            ci_right_95_left = ci_left_95_right = 0.0

        self.resultados = {
            "n_g1":    int(n_a),
            "n_g2":    int(n_b),
            "conv_g1": int(conv_a),
            "conv_g2": int(conv_b),
            "tasa_g1": float(p_a),
            "tasa_g2": float(p_b),
            "diferencia":  float(diff),
            "uplift_pct":  float(uplift_pct),
            "z_stat":      float(z_stat),
            "z_score":     z_score,
            "se_control":  se_control,
            "se_variante": se_variante,
            "se_diferencia": se_diferencia,
            "p_value_two":   float(p_two),
            "p_value_right": float(p_right),
            "p_value_left":  float(p_left),
            "ci_diff_low":   float(ci_diff_low),
            "ci_diff_high":  float(ci_diff_high),
            "ci_relativo_centrado":      [float(ci_uplift_center_low), float(ci_uplift_center_high)],
            "ci_relativo_derecha_izq":   float(ci_right_95_left),
            "ci_relativo_izquierda_der": float(ci_left_95_right),
        }

    def imprimir_consola(self) -> None:
        r = self.resultados
        print("=" * 50)
        print("  ANÁLISIS DE PROPORCIONES (Z-TEST)  ".center(50))
        print("=" * 50)
        print(f"{'Diseño A':<20} | Visitas: {r['n_g1']:>8} | Convs: {int(r['conv_g1']):>6}")
        print(f"{'Diseño B':<20} | Visitas: {r['n_g2']:>8} | Convs: {int(r['conv_g2']):>6}")
        print("-" * 50)
        print(f"ESTADÍSTICO Z:          {r['z_stat']:.4f}")
        print(f"P-VALUE (dos colas):    {r['p_value_two']:.4f}")
        print(f"P-VALUE (cola derecha): {r['p_value_right']:.4f}")
        print(f"P-VALUE (cola izquierda): {r['p_value_left']:.4f}")
        print("-" * 50)
        print(f"UPLIFT RELATIVO:        {r['uplift_pct']:.2f}%")
        print(f"IC CENTRADO (UPLIFT):   [{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]")
        print(f"COLA DERECHA (IC 95% IZQUIERDA): > {r['ci_relativo_derecha_izq']:.2f}%")
        print(f"COLA IZQUIERDA (IC 95% DERECHA): < {r['ci_relativo_izquierda_der']:.2f}%")
        print("=" * 50)

    def generar_figuras(self, pdf: Optional[PdfPages] = None) -> List[Any]:
        r = self.resultados
        p_a = r["tasa_g1"]
        p_b = r["tasa_g2"]
        diff = r["diferencia"]

        figs = []

        # --- Figura 1: tasas de conversión ---
        fig1, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(["A (Control)", "B (Variante)"], [p_a * 100, p_b * 100],
                      color=["#6366f1", "#06b6d4"], width=0.45)
        for bar, val in zip(bars, [p_a, p_b]):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.2,
                    f"{val * 100:.2f}%", ha="center", va="bottom", fontweight="bold")
        ax.set_ylabel("Tasa de conversión (%)")
        ax.set_title("Tasas de conversión observadas")
        ax.set_ylim(0, max(p_a, p_b) * 100 * 1.35 + 1)
        sns.despine(ax=ax)
        if pdf:
            pdf.savefig(fig1)
        figs.append(fig1)

        # --- Figura 2: IC de la diferencia ---
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        ci_low  = r["ci_diff_low"]
        ci_high = r["ci_diff_high"]
        ax2.errorbar([0], [diff * 100],
                     yerr=[[(diff - ci_low) * 100], [(ci_high - diff) * 100]],
                     fmt="o", color="#6366f1", capsize=12, capthick=2, markersize=10)
        ax2.axhline(0, color="red", linestyle="--", label="Sin diferencia (H₀)")
        ax2.set_xticks([])
        ax2.set_ylabel("Diferencia de conversión B − A (%)")
        sig_label = "✓ Significativo" if r["p_value_two"] < 0.05 else "✗ No significativo"
        ax2.set_title(
            f"IC 95% diferencia  |  z = {r['z_stat']:.3f}  |  p = {r['p_value_two']:.4f}  |  {sig_label}"
        )
        ax2.legend()
        sns.despine(ax=ax2)
        if pdf:
            pdf.savefig(fig2)
        figs.append(fig2)

        return figs


def interpretar_resultados_con_ia(resultados: Dict[str, Any], api_key: Optional[str] = None) -> str:
    client = _safe_openai_client(api_key=api_key)
    if client is None:
        return ""

    prompt = build_frequentist_ai_prompt(
        resultados,
        n_control_key="n_g1",
        n_variante_key="n_g2",
        conv_control_key="conv_g1",
        conv_variante_key="conv_g2",
        tasa_control_key="tasa_g1",
        tasa_variante_key="tasa_g2",
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except Exception:
        return ""


def run(df: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = config or {}
    generate_pdf    = bool(config.get("generate_pdf", False))
    include_ai      = bool(config.get("include_ai", False))
    openai_api_key  = config.get("openai_api_key", "")

    required = ["Visitas A", "Visitas B", "Conversiones A", "Conversiones B"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {missing}")

    n_a    = int(df["Visitas A"].sum())
    n_b    = int(df["Visitas B"].sum())
    conv_a = int(df["Conversiones A"].sum())
    conv_b = int(df["Conversiones B"].sum())

    analisis = AnalisisProporciones()
    analisis.analizar(n_a, conv_a, n_b, conv_b)
    analisis.imprimir_consola()

    r = analisis.resultados
    figures: List[Any] = []
    pdf_bytes: Optional[bytes] = None
    log_text: Optional[str] = None

    if generate_pdf:
        import io as _io
        buf = _io.BytesIO()
        with PdfPages(buf) as pdf:
            figures = analisis.generar_figuras(pdf=pdf)
            if include_ai:
                texto_ia = interpretar_resultados_con_ia(r, api_key=openai_api_key)
                if texto_ia:
                    fig_ia = plt.figure(figsize=(8.27, 11.69))
                    fig_ia.text(0.1, 0.95, "Interpretación IA", fontsize=16, fontweight="bold", va="top")
                    fig_ia.text(0.1, 0.88, texto_ia, fontsize=10, va="top", wrap=True)
                    pdf.savefig(fig_ia)
                    plt.close(fig_ia)
                    log_text = texto_ia
        buf.seek(0)
        pdf_bytes = buf.read()
    else:
        figures = analisis.generar_figuras()
        if include_ai:
            log_text = interpretar_resultados_con_ia(r, api_key=openai_api_key)

    summary = pd.DataFrame([{
        "n_visitas_A":          r["n_g1"],
        "n_visitas_B":          r["n_g2"],
        "conv_A":               r["conv_g1"],
        "conv_B":               r["conv_g2"],
        "tasa_A":               r["tasa_g1"],
        "tasa_B":               r["tasa_g2"],
        "uplift_%":             r["uplift_pct"],
        "z_stat":               r["z_stat"],
        "z_score":              r["z_score"],
        "se_control":           r["se_control"],
        "se_variante":          r["se_variante"],
        "se_diferencia":        r["se_diferencia"],
        "p_value_two":          r["p_value_two"],
        "p_value_right":        r["p_value_right"],
        "p_value_left":         r["p_value_left"],
        "ci_diff_low":          r["ci_diff_low"],
        "ci_diff_high":         r["ci_diff_high"],
        "ci_uplift_center_low":  r["ci_relativo_centrado"][0],
        "ci_uplift_center_high": r["ci_relativo_centrado"][1],
        "ci_right_95_left":     r["ci_relativo_derecha_izq"],
        "ci_left_95_right":     r["ci_relativo_izquierda_der"],
    }])

    return {
        "summary":   summary,
        "figures":   figures,
        "pdf_bytes": pdf_bytes,
        "log_text":  log_text,
        "comparisons": None,
    }
