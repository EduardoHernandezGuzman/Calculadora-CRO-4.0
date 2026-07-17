from __future__ import annotations

import math
import re
from typing import Any, Mapping, Optional

import pandas as pd
from scipy.stats import chisquare

from backend.core.experiment_groups import (
    detect_aggregate_groups,
    detect_session_groups,
)


DEFAULT_ALPHA = 0.01
_VISIT_COLUMN = re.compile(r"^Visitas [A-Z]$")
_SESSION_VALUE_COLUMN = re.compile(r"^Conversiones [A-Z]$")
_LEGACY_SESSION_COLUMN = re.compile(r"^[A-Z]$")


def calculate_srm(
    df: pd.DataFrame,
    *,
    session_id: bool,
    expected_ratios: Optional[Mapping[str, float]] = None,
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, Any]:
    """Run one global SRM check over A and every detected variant."""
    if not 0 < alpha < 1:
        raise ValueError("SRM alpha debe ser mayor que 0 y menor que 1.")

    columns = [str(column).strip() for column in df.columns]
    has_visit_columns = any(_VISIT_COLUMN.fullmatch(column) for column in columns)
    has_session_columns = any(
        _SESSION_VALUE_COLUMN.fullmatch(column)
        or _LEGACY_SESSION_COLUMN.fullmatch(column)
        for column in columns
    )

    if session_id and has_visit_columns:
        raise ValueError(
            "La configuración indica Session ID, pero el CSV usa columnas "
            "agregadas 'Visitas X'."
        )
    if not session_id and not has_visit_columns and has_session_columns:
        raise ValueError(
            "La configuración indica datos sin Session ID, pero el CSV usa "
            "un formato de muestras por sesión."
        )

    if session_id:
        layout = detect_session_groups(columns)
        sample_counts = {
            group: int(df[layout.value_columns[group]].notna().sum())
            for group in layout.groups
        }
    else:
        layout = detect_aggregate_groups(columns)
        sample_counts = {
            group: int(df[layout.visit_columns[group]].sum())
            for group in layout.groups
        }

    groups = list(layout.groups)
    if len(groups) < 2:
        raise ValueError("SRM requiere al menos dos grupos.")

    total_sample = int(sum(sample_counts.values()))
    if total_sample == 0:
        raise ValueError("SRM no puede calcularse porque el tamaño muestral total es 0.")

    ratios = _normalize_expected_ratios(groups, expected_ratios)
    expected_counts = {
        group: float(total_sample * ratios[group]) for group in groups
    }
    if any(value <= 0 for value in expected_counts.values()):
        raise ValueError("Ninguna muestra esperada de SRM puede ser 0.")

    result = chisquare(
        f_obs=[sample_counts[group] for group in groups],
        f_exp=[expected_counts[group] for group in groups],
    )
    chi2 = float(result.statistic)
    p_value = float(result.pvalue)
    observed_ratios = {
        group: float(sample_counts[group] / total_sample) for group in groups
    }

    output = {
        "has_srm": bool(p_value < alpha),
        "alpha": float(alpha),
        "chi2": chi2,
        "p_value": p_value,
        "degrees_of_freedom": len(groups) - 1,
        "total_sample": total_sample,
        "groups": groups,
        "sample_counts": sample_counts,
        "expected_counts": expected_counts,
        "expected_ratios": ratios,
        "observed_ratios": observed_ratios,
    }
    return output


def _normalize_expected_ratios(
    groups: list[str], expected_ratios: Optional[Mapping[str, float]]
) -> dict[str, float]:
    if expected_ratios is None:
        uniform_ratio = 1.0 / len(groups)
        return {group: uniform_ratio for group in groups}

    if set(expected_ratios) != set(groups):
        raise ValueError(
            "Las claves de expected_ratios deben coincidir exactamente con "
            "los grupos detectados."
        )

    ratios = {group: float(expected_ratios[group]) for group in groups}
    if any(not math.isfinite(value) or value <= 0 for value in ratios.values()):
        raise ValueError("Todas las ratios esperadas deben ser finitas y mayores que 0.")
    if not math.isclose(sum(ratios.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Las ratios esperadas de SRM deben sumar 1.")
    return ratios
