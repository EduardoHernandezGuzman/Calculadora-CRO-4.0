from __future__ import annotations

from typing import Any, Dict, List


def build_frequentist_ai_prompt(
    resultados: Any,
    *,
    n_control_key: str,
    n_variante_key: str,
    conv_control_key: str,
    conv_variante_key: str,
    tasa_control_key: str,
    tasa_variante_key: str,
    variant_key: str,
) -> str:
    comparison_results: List[Dict[str, Any]] = (
        resultados if isinstance(resultados, list) else [resultados]
    )
    data_blocks = []
    for comparison in comparison_results:
        variant = comparison.get(variant_key, "B")
        nivel_significancia = (1 - comparison["p_value_two"]) * 100
        data_blocks.append(
            f"""DATOS DEL TEST

Grupo Control (A)

Visitas acumuladas: {comparison[n_control_key]}
Conversiones acumuladas: {comparison[conv_control_key]}
Tasa de conversión: {comparison[tasa_control_key]:.4f}

Grupo Variante ({variant})

Visitas acumuladas: {comparison[n_variante_key]}
Conversiones acumuladas: {comparison[conv_variante_key]}
Tasa de conversión: {comparison[tasa_variante_key]:.4f}

RESULTADOS PRINCIPALES

Control (A)

Tasa de conversión: {comparison[tasa_control_key]:.4f}

Variante ({variant})

Tasa de conversión: {comparison[tasa_variante_key]:.4f}

Uplift estimado:

{comparison['uplift_pct']:.2f}%

Nivel de significancia:

{nivel_significancia:.2f}%

Z-Score:

{comparison['z_score']:.3f}

Error estándar del control:

{comparison['se_control']:.6f}

Error estándar de la variante:

{comparison['se_variante']:.6f}

Error estándar de la diferencia:

{comparison['se_diferencia']:.6f}

INTERVALO DE CONFIANZA DEL UPLIFT RELATIVO (95%)

Intervalo principal: [{comparison['ci_relativo_centrado'][0]:.2f}%, {comparison['ci_relativo_centrado'][1]:.2f}%]

Escenario conservador: > {comparison['ci_relativo_derecha_izq']:.2f}%

Escenario optimista: < {comparison['ci_relativo_izquierda_der']:.2f}%"""
        )
    comparison_data = "\n\n".join(data_blocks)

    return f"""
Eres Director de CRO (Conversion Rate Optimization) especializado en experimentación y toma de decisiones basada en datos.

Tu objetivo es analizar los resultados de un test A/B utilizando inferencia frecuentista y proporcionar una recomendación de negocio clara, accionable y comprensible para perfiles no estadísticos.

INSTRUCCIONES IMPORTANTES

Utiliza lenguaje ejecutivo, claro y orientado a negocio.
No muestres fórmulas matemáticas.
No expliques cálculos internos.
No uses la palabra "probabilidad".
Usa siempre la expresión "NIVEL DE SIGNIFICANCIA".
Explica brevemente el significado práctico de las métricas estadísticas cuando aporten contexto para la decisión.
Prioriza la toma de decisiones y la gestión del riesgo frente al detalle técnico.

{comparison_data}

GUÍA DE INTERPRETACIÓN

Ten en cuenta los siguientes criterios:

Evidencia estadística

Si el intervalo de confianza incluye el 0%, el resultado no es concluyente.
Si el intervalo de confianza está completamente por encima de 0%, existe evidencia de mejora.
Si el intervalo de confianza está completamente por debajo de 0%, existe evidencia de empeoramiento.

Nivel de significancia

Superior al 95%: evidencia fuerte para tomar una decisión.
Entre 90% y 95%: evidencia moderada; valorar riesgo y contexto de negocio.
Inferior al 90%: evidencia insuficiente para declarar un ganador.

Interpretación del Z-Score

Explica brevemente si el Z-Score refleja una diferencia claramente detectable o una diferencia todavía débil respecto al ruido estadístico.

Interpretación de los errores estándar

Explica qué indican los errores estándar del control y la variante sobre la estabilidad de las tasas de conversión observadas.
Explica qué implica el error estándar de la diferencia respecto a la precisión de la comparación entre ambas versiones.
Si los errores estándar son elevados, menciona que todavía existe incertidumbre relevante en la estimación.
Si son reducidos, menciona que las estimaciones son más estables y fiables.

Gestión del riesgo

Traduce el intervalo de uplift a impacto de negocio:

Explica qué significaría el escenario conservador.
Explica qué significaría el escenario optimista.
Destaca el riesgo de implementar o no implementar la variante.

ESTRUCTURA DE RESPUESTA

DICTAMEN

Indica de forma directa una de estas conclusiones:

La variante B es la ganadora.
El control A sigue siendo la mejor opción.
No existe evidencia suficiente para declarar un ganador.

INTERPRETACIÓN DE RESULTADOS

Explica brevemente:

Diferencia observada entre variantes.
Qué aporta el nivel de significancia.
Qué indica el Z-Score.
Qué indican los errores estándar sobre la fiabilidad de los resultados.

ANÁLISIS DE RIESGO

Describe:

Escenario conservador.
Escenario optimista.
Riesgo de tomar una decisión prematura.

ACCIÓN RECOMENDADA

Selecciona una única recomendación:

Implementar la variante.
Mantener el control.
Continuar recopilando datos.

Justifica la decisión en 2-4 frases, priorizando impacto de negocio y nivel de confianza en la evidencia.
""".strip()
