from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


CONTROL_GROUP = "A"
VARIANT_GROUPS = ("B", "C", "D", "E")
ALLOWED_GROUPS = (CONTROL_GROUP, *VARIANT_GROUPS)

STATUS_WINNER = "Ganadora"
STATUS_BEST_CANDIDATE = "Mejor candidata"
STATUS_NOT_CONCLUSIVE = "Sin ganador concluyente"

_AGGREGATE_COLUMN = re.compile(r"^(Visitas|Conversiones) ([A-Z])$")
_SESSION_COLUMN = re.compile(r"^Conversiones ([A-Z])$")


@dataclass(frozen=True)
class ExperimentGroups:
    control: str
    variants: tuple[str, ...]
    value_columns: Mapping[str, str]
    visit_columns: Optional[Mapping[str, str]] = None

    @property
    def groups(self) -> tuple[str, ...]:
        return (self.control, *self.variants)


def _ordered_groups(groups: Iterable[str]) -> List[str]:
    detected = set(groups)
    unsupported = sorted(detected.difference(ALLOWED_GROUPS))
    if unsupported:
        raise ValueError(
            "Solo se admiten el control A y las variantes B, C, D y E. "
            f"Grupos no admitidos: {', '.join(unsupported)}."
        )

    if CONTROL_GROUP not in detected:
        raise ValueError("Falta el grupo control A.")

    variants = [group for group in VARIANT_GROUPS if group in detected]
    if not variants:
        raise ValueError("Debe existir al menos una variante entre B, C, D y E.")

    return [CONTROL_GROUP, *variants]


def detect_aggregate_groups(columns: Iterable[Any]) -> ExperimentGroups:
    visits: Dict[str, str] = {}
    conversions: Dict[str, str] = {}
    detected_groups = set()

    for raw_column in columns:
        column = str(raw_column).strip()
        match = _AGGREGATE_COLUMN.fullmatch(column)
        if not match:
            continue

        metric, group = match.groups()
        detected_groups.add(group)
        target = visits if metric == "Visitas" else conversions
        target[group] = column

    groups = _ordered_groups(detected_groups)
    incomplete = [
        group
        for group in groups
        if group not in visits or group not in conversions
    ]
    if incomplete:
        missing = []
        for group in incomplete:
            if group not in visits:
                missing.append(f"Visitas {group}")
            if group not in conversions:
                missing.append(f"Conversiones {group}")
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(missing)}.")

    return ExperimentGroups(
        control=CONTROL_GROUP,
        variants=tuple(groups[1:]),
        value_columns={group: conversions[group] for group in groups},
        visit_columns={group: visits[group] for group in groups},
    )


def detect_session_groups(columns: Iterable[Any]) -> ExperimentGroups:
    canonical: Dict[str, str] = {}
    legacy: Dict[str, str] = {}

    for raw_column in columns:
        column = str(raw_column).strip()
        match = _SESSION_COLUMN.fullmatch(column)
        if match:
            canonical[match.group(1)] = column
        elif len(column) == 1 and column.isalpha() and column.isupper():
            legacy[column] = column

    if canonical and legacy:
        raise ValueError(
            "No deben mezclarse columnas Session ID canónicas "
            "('Conversiones X') con columnas heredadas ('A', 'B', etc.)."
        )

    value_columns = canonical if canonical else legacy
    groups = _ordered_groups(value_columns)

    return ExperimentGroups(
        control=CONTROL_GROUP,
        variants=tuple(groups[1:]),
        value_columns={group: value_columns[group] for group in groups},
    )


def make_comparison_record(
    *,
    variant: str,
    control_value: float,
    variant_value: float,
    uplift_pct: Optional[float],
    difference: float,
    evidence_name: str,
    evidence_value: float,
    interval_name: str,
    interval: Sequence[Optional[float]],
    favorable: bool,
    significant: bool,
    metrics: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if variant not in VARIANT_GROUPS:
        raise ValueError("La comparación debe usar una variante entre B, C, D y E.")
    if len(interval) != 2:
        raise ValueError("El intervalo debe contener exactamente dos límites.")

    record: Dict[str, Any] = {
        "control": CONTROL_GROUP,
        "variant": variant,
        "control_value": _scalar(control_value),
        "variant_value": _scalar(variant_value),
        "uplift_pct": _optional_scalar(uplift_pct),
        "difference": _scalar(difference),
        "evidence": {
            "name": str(evidence_name),
            "value": _scalar(evidence_value),
        },
        "interval": {
            "name": str(interval_name),
            "low": _optional_scalar(interval[0]),
            "high": _optional_scalar(interval[1]),
        },
        "favorable": bool(favorable),
        "significant": bool(significant),
        "comparison_status": (
            STATUS_WINNER if favorable and significant else STATUS_NOT_CONCLUSIVE
        ),
        "selection_label": None,
        "is_best": False,
        "metrics": _lightweight_mapping(metrics or {}),
    }
    return record


def mark_best_comparison(
    comparisons: Sequence[Mapping[str, Any]],
    variant: Optional[str],
    *,
    winner: bool,
) -> List[Dict[str, Any]]:
    if variant is not None and variant not in VARIANT_GROUPS:
        raise ValueError("La mejor comparación debe corresponder a B, C, D o E.")

    found = variant is None
    normalized: List[Dict[str, Any]] = []
    for comparison in comparisons:
        record = _lightweight_mapping(comparison)
        is_best = variant is not None and record.get("variant") == variant
        if is_best:
            found = True
        record["is_best"] = is_best
        record["selection_label"] = None
        if is_best:
            if winner and record.get("comparison_status") != STATUS_WINNER:
                raise ValueError(
                    "Una comparación solo puede seleccionarse como Ganadora si "
                    "su estado individual es concluyente."
                )
            record["selection_label"] = (
                STATUS_WINNER if winner else STATUS_BEST_CANDIDATE
            )
        normalized.append(record)

    if not found:
        raise ValueError(f"No existe una comparación A vs {variant}.")

    return normalized


def _optional_scalar(value: Optional[Any]) -> Optional[Any]:
    return None if value is None else _scalar(value)


def _scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, Real):
        return value.item() if hasattr(value, "item") else value
    if hasattr(value, "item") and not hasattr(value, "__len__"):
        return value.item()
    raise TypeError(f"Se esperaba una métrica escalar, no {type(value).__name__}.")


def _lightweight_mapping(values: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(key): _lightweight_value(value) for key, value in values.items()}


def _lightweight_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Real):
        return value.item() if hasattr(value, "item") else value
    if isinstance(value, Mapping):
        return _lightweight_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_lightweight_value(item) for item in value]
    if hasattr(value, "item") and not hasattr(value, "__len__"):
        return value.item()
    raise TypeError(
        "comparisons solo admite escalares, intervalos y estructuras ligeras; "
        f"se recibió {type(value).__name__}."
    )
