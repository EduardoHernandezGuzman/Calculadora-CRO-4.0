"""
Motor frecuentista basado en t-test de Welch (con Session ID).
Alternativa determinista al Bootstrap: mismo input siempre da el mismo resultado.
Usa el t-test de Welch (dos muestras independientes, varianzas no iguales),
válido tanto para datos binarios 0/1 como para métricas continuas por sesión.
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


class AnalisisTTest:
    """
    T-test de Welch para dos muestras independientes (con Session ID).
    H0: μ_B = μ_A  |  H1: μ_B ≠ μ_A / μ_B > μ_A / μ_B < μ_A
    """

    def __init__(self):
        self.resultados: Dict[str, Any] = {}
        self.col_a: str = "A"
        self.col_b: str = "B"

    def analizar(self, values_a: np.ndarray, values_b: np.ndarray,
                 col_a: str = "A", col_b: str = "B") -> None:
        self.col_a = col_a
        self.col_b = col_b

        n_a = len(values_a)
        n_b = len(values_b)
        mean_a = float(np.mean(values_a))
        mean_b = float(np.mean(values_b))
        conv_a = float(np.sum(values_a))
        conv_b = float(np.sum(values_b))
        diff = mean_b - mean_a

        # T-test de Welch (two-sided)
        t_stat, p_two  = stats.ttest_ind(values_b, values_a, equal_var=False, alternative="two-sided")
        _, p_right = stats.ttest_ind(values_b, values_a, equal_var=False, alternative="greater")
        _, p_left  = stats.ttest_ind(values_b, values_a, equal_var=False, alternative="less")
        t_stat = float(t_stat)

        # Error estándar de la diferencia (Welch)
        se_a = np.std(values_a, ddof=1) / np.sqrt(n_a) if n_a > 1 else 0.0
        se_b = np.std(values_b, ddof=1) / np.sqrt(n_b) if n_b > 1 else 0.0
        se_diff = float(np.sqrt(se_a**2 + se_b**2))

        se_control = float(np.sqrt(mean_a * (1 - mean_a) / n_a)) if n_a else 0.0
        se_variante = float(np.sqrt(mean_b * (1 - mean_b) / n_b)) if n_b else 0.0
        se_diferencia = float(np.sqrt(se_control**2 + se_variante**2))
        z_score = float(diff / se_diferencia) if se_diferencia > 0 else 0.0

        # Grados de libertad de Welch-Satterthwaite
        if se_a > 0 and se_b > 0:
            df_w = (se_a**2 + se_b**2)**2 / (se_a**4 / (n_a - 1) + se_b**4 / (n_b - 1))
        else:
            df_w = n_a + n_b - 2

        t_crit_two = float(stats.t.ppf(0.975, df_w))
        t_crit_one = float(stats.t.ppf(0.95,  df_w))

        ci_diff_low  = diff - t_crit_two * se_diff
        ci_diff_high = diff + t_crit_two * se_diff
        ci_right_bound = diff - t_crit_one * se_diff
        ci_left_bound  = diff + t_crit_one * se_diff

        if mean_a != 0:
            uplift_pct            = diff / mean_a * 100
            ci_uplift_center_low  = ci_diff_low   / mean_a * 100
            ci_uplift_center_high = ci_diff_high  / mean_a * 100
            ci_right_95_left      = ci_right_bound / mean_a * 100
            ci_left_95_right      = ci_left_bound  / mean_a * 100
        else:
            uplift_pct = ci_uplift_center_low = ci_uplift_center_high = 0.0
            ci_right_95_left = ci_left_95_right = 0.0

        self.resultados = {
            "n_a":    n_a,
            "n_b":    n_b,
            "conv_a": conv_a,
            "conv_b": conv_b,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "diferencia":    float(diff),
            "uplift_pct":    float(uplift_pct),
            "t_stat":        t_stat,
            "z_score":       z_score,
            "se_control":    se_control,
            "se_variante":   se_variante,
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
        print("  ANÁLISIS CON SESSION ID (T-TEST WELCH)  ".center(50))
        print("=" * 50)
        print(f"{self.col_a} (A): {r['n_a']} filas | {r['conv_a']:.0f} convs | Media: {r['mean_a']:.4f}")
        print(f"{self.col_b} (B): {r['n_b']} filas | {r['conv_b']:.0f} convs | Media: {r['mean_b']:.4f}")
        print("-" * 50)
        print(f"ESTADÍSTICO T (Welch):  {r['t_stat']:.4f}")
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

        figs = []

        # --- Figura 1: distribución de valores por grupo ---
        fig1, ax = plt.subplots(figsize=(10, 5))
        ax.set_title("Distribución de medias por variante (Session ID)")
        ax.set_xlabel("Media de la métrica")
        ax.set_ylabel("Frecuencia")
        ax.legend([self.col_a, self.col_b])
        if pdf:
            pdf.savefig(fig1)
        figs.append(fig1)

        # --- Figura 2: IC de la diferencia ---
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        diff = r["diferencia"]
        ci_low  = r["ci_diff_low"]
        ci_high = r["ci_diff_high"]
        ax2.errorbar([0], [diff * 100],
                     yerr=[[(diff - ci_low) * 100], [(ci_high - diff) * 100]],
                     fmt="o", color="#6366f1", capsize=12, capthick=2, markersize=10)
        ax2.axhline(0, color="red", linestyle="--", label="Sin diferencia (H₀)")
        ax2.set_xticks([])
        ax2.set_ylabel("Diferencia B − A (%)")
        sig_label = "✓ Significativo" if r["p_value_two"] < 0.05 else "✗ No significativo"
        ax2.set_title(
            f"IC 95% diferencia  |  t = {r['t_stat']:.3f}  |  p = {r['p_value_two']:.4f}  |  {sig_label}"
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

    r = resultados
    sig = "sí" if r["p_value_two"] < 0.05 else "no"
    prompt = f"""
Eres un Director de CRO. Analiza estos resultados de un test A/B (t-test de Welch, con Session ID).
IMPORTANTE: No uses la palabra "probabilidad", usa siempre "NIVEL DE SIGNIFICANCIA".

TEST A/B (con Session ID):
Control (A): {r['n_a']} sesiones | Media: {r['mean_a']:.4f}
Variante (B): {r['n_b']} sesiones | Media: {r['mean_b']:.4f}
Uplift relativo: {r['uplift_pct']:.2f}%
Estadístico T (Welch): {r['t_stat']:.4f}
P-value (dos colas): {r['p_value_two']:.4f}
¿Resultado significativo (p < 0.05)? {sig}
IC 95% uplift centrado: [{r['ci_relativo_centrado'][0]:.2f}%, {r['ci_relativo_centrado'][1]:.2f}%]

Proporciona:
1. CONCLUSIÓN EJECUTIVA (2-3 líneas)
2. INTERPRETACIÓN DEL RESULTADO
3. ACCIÓN RECOMENDADA
"""
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
    generate_pdf   = bool(config.get("generate_pdf", False))
    include_ai     = bool(config.get("include_ai", False))
    openai_api_key = config.get("openai_api_key", "")

    cols = list(df.columns[:2])
    if len(cols) < 2:
        raise ValueError("El CSV debe tener al menos dos columnas (A y B).")

    col_a, col_b = cols[0], cols[1]
    values_a = df[col_a].dropna().values.astype(float)
    values_b = df[col_b].dropna().values.astype(float)

    analisis = AnalisisTTest()
    analisis.analizar(values_a, values_b, col_a=col_a, col_b=col_b)
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

    # El campo t_stat sirve como z_stat en el frontend (mismo nombre en la UI)
    summary = pd.DataFrame([{
        "grupo_A_col":           col_a,
        "grupo_B_col":           col_b,
        "n_A":                   r["n_a"],
        "n_B":                   r["n_b"],
        "conv_A":                r["conv_a"],
        "conv_B":                r["conv_b"],
        "media_A":               r["mean_a"],
        "media_B":               r["mean_b"],
        "uplift_%":              r["uplift_pct"],
        "z_stat":                r["t_stat"],   # alias para UI unificada
        "z_score":               r["z_score"],
        "se_control":            r["se_control"],
        "se_variante":           r["se_variante"],
        "se_diferencia":         r["se_diferencia"],
        "p_value_two":           r["p_value_two"],
        "p_value_right":         r["p_value_right"],
        "p_value_left":          r["p_value_left"],
        "ci_diff_low":           r["ci_diff_low"],
        "ci_diff_high":          r["ci_diff_high"],
        "ci_uplift_center_low":  r["ci_relativo_centrado"][0],
        "ci_uplift_center_high": r["ci_relativo_centrado"][1],
        "ci_right_95_left":      r["ci_relativo_derecha_izq"],
        "ci_left_95_right":      r["ci_relativo_izquierda_der"],
    }])

    return {
        "summary":    summary,
        "figures":    figures,
        "pdf_bytes":  pdf_bytes,
        "log_text":   log_text,
        "comparisons": None,
    }
