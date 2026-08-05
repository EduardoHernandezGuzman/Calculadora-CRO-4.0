from __future__ import annotations

import math
import re
from typing import Iterable

import pandas as pd

from backend.core.engine_router import (
    ENGINE_0_1_NO_SID,
    ENGINE_0_1_SID,
    ENGINE_0_INF_NO_SID,
    ENGINE_0_INF_SID,
    ENGINE_FREQ_NO_SID,
    ENGINE_FREQ_PVALUE_NO_SID,
    ENGINE_FREQ_PVALUE_SID,
    ENGINE_FREQ_SID,
)
from backend.core.experiment_groups import (
    CONTROL_GROUP,
    detect_aggregate_groups,
    detect_session_groups,
)


_SESSION_ENGINES = {
    ENGINE_0_1_SID,
    ENGINE_0_INF_SID,
    ENGINE_FREQ_SID,
    ENGINE_FREQ_PVALUE_SID,
}
_NO_SESSION_ENGINES = {
    ENGINE_0_1_NO_SID,
    ENGINE_0_INF_NO_SID,
    ENGINE_FREQ_NO_SID,
    ENGINE_FREQ_PVALUE_NO_SID,
}
_GAMMA_ENGINES = {ENGINE_0_INF_NO_SID, ENGINE_0_INF_SID}
_VISIT_COLUMN = re.compile(r"^Visitas [A-Z]$")
_SESSION_VALUE_COLUMN = re.compile(r"^Conversiones [A-Z]$")
_LEGACY_SESSION_COLUMN = re.compile(r"^[A-Z]$")


def validate_analysis_input(
    df: pd.DataFrame,
    *,
    engine_key: str,
    session_id: bool,
) -> pd.DataFrame:
    """Validate user data before SRM and engine-specific casts."""
    if engine_key not in _SESSION_ENGINES | _NO_SESSION_ENGINES:
        raise ValueError("El motor estadístico seleccionado no existe.")

    cleaned = df.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    _validate_format_matches(cleaned.columns, session_id=session_id)

    if session_id:
        return _validate_session_data(cleaned, binary=engine_key not in _GAMMA_ENGINES)
    return _validate_aggregate_data(cleaned, binary=engine_key not in _GAMMA_ENGINES)


def _validate_format_matches(columns: Iterable[str], *, session_id: bool) -> None:
    columns = list(columns)
    has_visits = any(_VISIT_COLUMN.fullmatch(column) for column in columns)
    has_session_values = any(
        _SESSION_VALUE_COLUMN.fullmatch(column)
        or _LEGACY_SESSION_COLUMN.fullmatch(column)
        for column in columns
    )
    if session_id and has_visits:
        raise ValueError(
            "La configuración indica Session ID, pero el CSV usa columnas "
            "agregadas 'Visitas X'."
        )
    if not session_id and not has_visits and has_session_values:
        raise ValueError(
            "La configuración indica datos sin Session ID, pero el CSV usa "
            "un formato de muestras por sesión."
        )


def _validate_aggregate_data(df: pd.DataFrame, *, binary: bool) -> pd.DataFrame:
    _validate_day(df)
    layout = detect_aggregate_groups(df.columns)

    for group in layout.groups:
        visits_column = layout.visit_columns[group]
        conversions_column = layout.value_columns[group]
        visits = _numeric_integer_series(df[visits_column], visits_column, allow_null=False)
        conversions = _numeric_integer_series(
            df[conversions_column], conversions_column, allow_null=False
        )
        if (visits < 0).any():
            raise ValueError(f"'{visits_column}' no puede contener valores negativos.")
        if (conversions < 0).any():
            raise ValueError(f"'{conversions_column}' no puede contener valores negativos.")
        if int(visits.sum()) <= 0:
            raise ValueError(f"El grupo {group} debe tener al menos una visita.")
        if binary and (conversions > visits).any():
            raise ValueError(
                f"'{conversions_column}' no puede superar a '{visits_column}' "
                "para el motor seleccionado."
            )
        df[visits_column] = visits.astype("int64")
        df[conversions_column] = conversions.astype("int64")
    return df


def _validate_session_data(df: pd.DataFrame, *, binary: bool) -> pd.DataFrame:
    _validate_day(df)
    if "SessionID" not in df.columns:
        raise ValueError("Falta la columna obligatoria 'SessionID'.")
    session_ids = df["SessionID"]
    if session_ids.isna().any() or session_ids.astype(str).str.strip().eq("").any():
        raise ValueError("La columna 'SessionID' no puede contener valores vacíos.")

    initial_layout = detect_session_groups(df.columns)
    empty_variants = [
        group
        for group in initial_layout.variants
        if df[initial_layout.value_columns[group]].isna().all()
    ]
    if empty_variants:
        df = df.drop(columns=[initial_layout.value_columns[group] for group in empty_variants])

    layout = detect_session_groups(df.columns)
    for group in layout.groups:
        column = layout.value_columns[group]
        values = _numeric_integer_series(df[column], column, allow_null=True)
        valid_values = values.dropna()
        if valid_values.empty:
            label = "control A" if group == CONTROL_GROUP else f"grupo {group}"
            raise ValueError(f"El {label} debe tener al menos una observación válida.")
        if (valid_values < 0).any():
            raise ValueError(f"'{column}' no puede contener valores negativos.")
        if binary and not valid_values.isin((0, 1)).all():
            raise ValueError(
                f"'{column}' solo puede contener 0 o 1 para el motor seleccionado."
            )
        df[column] = values
    return df


def _validate_day(df: pd.DataFrame) -> None:
    if "Día" not in df.columns:
        raise ValueError("Falta la columna obligatoria 'Día'.")
    if df["Día"].isna().any() or df["Día"].astype(str).str.strip().eq("").any():
        raise ValueError("La columna 'Día' no puede contener valores vacíos.")


def _numeric_integer_series(
    series: pd.Series,
    column: str,
    *,
    allow_null: bool,
) -> pd.Series:
    if not allow_null and series.isna().any():
        raise ValueError(f"La columna '{column}' no puede contener celdas vacías.")
    try:
        numeric = pd.to_numeric(series, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"La columna '{column}' debe contener valores numéricos.") from exc

    finite_values = numeric.dropna()
    if not finite_values.map(lambda value: math.isfinite(float(value))).all():
        raise ValueError(f"La columna '{column}' debe contener valores finitos.")
    if not finite_values.map(lambda value: float(value).is_integer()).all():
        raise ValueError(f"La columna '{column}' debe contener valores enteros.")
    return numeric
