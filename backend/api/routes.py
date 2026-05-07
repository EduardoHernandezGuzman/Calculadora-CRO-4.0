from __future__ import annotations

import base64
import io
import json
import os
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, UploadFile

from backend.api.schemas import AnalyzeResponse, EngineInfo
from backend.core.engine_router import (
    ENGINE_0_1_NO_SID,
    ENGINE_0_1_SID,
    ENGINE_0_INF_NO_SID,
    ENGINE_0_INF_SID,
    ENGINE_FREQ_NO_SID,
    ENGINE_FREQ_SID,
    ENGINE_LABELS,
    get_engine_label,
    run_engine,
)

router = APIRouter()


def _convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: _convert_numpy(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_numpy(v) for v in obj]
    if hasattr(obj, "dtype"):
        if obj.ndim == 0:
            return obj.item()
        return [_convert_numpy(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj or obj == float("inf") or obj == float("-inf"):
            return None
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


@router.get("/health")
async def health():
    return {"status": "ok"}


ENGINES_META = {
    ENGINE_0_1_NO_SID: EngineInfo(
        key=ENGINE_0_1_NO_SID, label=ENGINE_LABELS[ENGINE_0_1_NO_SID],
        enfoque="bayesiano", tipo="0_1",
    ),
    ENGINE_0_1_SID: EngineInfo(
        key=ENGINE_0_1_SID, label=ENGINE_LABELS[ENGINE_0_1_SID],
        enfoque="bayesiano", tipo="0_1",
    ),
    ENGINE_0_INF_NO_SID: EngineInfo(
        key=ENGINE_0_INF_NO_SID, label=ENGINE_LABELS[ENGINE_0_INF_NO_SID],
        enfoque="bayesiano", tipo="0_inf",
    ),
    ENGINE_0_INF_SID: EngineInfo(
        key=ENGINE_0_INF_SID, label=ENGINE_LABELS[ENGINE_0_INF_SID],
        enfoque="bayesiano", tipo="0_inf",
    ),
    ENGINE_FREQ_NO_SID: EngineInfo(
        key=ENGINE_FREQ_NO_SID, label=ENGINE_LABELS[ENGINE_FREQ_NO_SID],
        enfoque="frecuentista", tipo="freq",
    ),
    ENGINE_FREQ_SID: EngineInfo(
        key=ENGINE_FREQ_SID, label=ENGINE_LABELS[ENGINE_FREQ_SID],
        enfoque="frecuentista", tipo="freq",
    ),
}


@router.get("/engines", response_model=list[EngineInfo])
async def list_engines():
    return list(ENGINES_META.values())


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    engine_key: str = Form(...),
    config: str = Form("{}"),
):
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))

    config_dict = json.loads(config) if isinstance(config, str) else config

    if "include_ai" in config_dict:
        config_dict["include_ai"] = str(config_dict.get("include_ai", "false")).lower() in ("true", "1", "yes")
    if "generate_pdf" in config_dict:
        config_dict["generate_pdf"] = str(config_dict.get("generate_pdf", "false")).lower() in ("true", "1", "yes")

    out = run_engine(engine_key, df, config_dict)

    summary_list = None
    if out.summary is not None:
        summary_list = out.summary.replace(
            {float("nan"): None, float("inf"): None, float("-inf"): None}
        ).to_dict(orient="records")
        summary_list = _convert_numpy(summary_list)

    figures_b64 = None
    if out.figures:
        figures_b64 = []
        for fig in out.figures:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            buf.seek(0)
            figures_b64.append(base64.b64encode(buf.read()).decode("utf-8"))

    pdf_b64 = None
    if out.pdf_bytes:
        pdf_b64 = base64.b64encode(out.pdf_bytes).decode("utf-8")

    comparisons_clean = _convert_numpy(out.comparisons) if out.comparisons else None

    return AnalyzeResponse(
        summary=summary_list,
        figures=figures_b64,
        pdf_bytes=pdf_b64,
        log_text=out.log_text,
        comparisons=comparisons_clean,
    )
