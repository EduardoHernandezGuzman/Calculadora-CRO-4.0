from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EngineInfo(BaseModel):
    key: str
    label: str
    enfoque: str
    tipo: str


class AnalyzeResponse(BaseModel):
    summary: Optional[List[Dict[str, Any]]] = None
    figures: Optional[List[str]] = None
    pdf_bytes: Optional[str] = None
    log_text: Optional[str] = None
    comparisons: Optional[List[Dict[str, Any]]] = None
