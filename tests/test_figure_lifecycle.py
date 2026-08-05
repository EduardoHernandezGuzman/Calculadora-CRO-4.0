from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd
from fastapi.testclient import TestClient

from backend.core.engine_router import EngineOutput
from backend.main import app


def aggregate_frame(groups: str) -> pd.DataFrame:
    data = {"Día": [1]}
    for index, group in enumerate(groups):
        data[f"Visitas {group}"] = [100]
        data[f"Conversiones {group}"] = [10 + index]
    return pd.DataFrame(data)


def session_frame(groups: str) -> pd.DataFrame:
    rows = []
    for group_index, group in enumerate(groups):
        for row_index in range(20):
            row = {"Día": 1, "SessionID": f"{group}-{row_index}"}
            for candidate in groups:
                row[f"Conversiones {candidate}"] = (
                    int(row_index < 2 + group_index) if candidate == group else None
                )
            rows.append(row)
    return pd.DataFrame(rows)


class FigureLifecycleTests(unittest.TestCase):
    client = TestClient(app)

    def post(self, engine: str, frame: pd.DataFrame, config: dict):
        return self.client.post(
            "/api/analyze",
            files={"file": ("figures.csv", frame.to_csv(index=False), "text/csv")},
            data={"engine_key": engine, "config": json.dumps(config)},
        )

    def test_repeated_analyses_do_not_accumulate_figures(self):
        baseline = set(plt.get_fignums())
        cases = (
            ("bayes_0_1_sid", True, {"num_samples": 200}),
            ("bayes_0_1_no_sid", False, {"num_samples": 200}),
            ("freq_pvalue_no_sid", False, {}),
            ("freq_no_sid", False, {"n_iteraciones": 40}),
        )

        for engine, uses_session, engine_config in cases:
            with self.subTest(engine=engine):
                ab_figure_count = None
                for run_number, groups in enumerate(("AB", "AB", "ABCDE")):
                    frame = session_frame(groups) if uses_session else aggregate_frame(groups)
                    config = {
                        "session_id": uses_session,
                        "include_ai": False,
                        "generate_pdf": run_number % 2 == 0,
                        **engine_config,
                    }
                    response = self.post(engine, frame, config)
                    self.assertEqual(response.status_code, 200, response.text)
                    figures = response.json()["figures"] or []
                    self.assertGreater(len(figures), 0)
                    if groups == "AB":
                        if ab_figure_count is None:
                            ab_figure_count = len(figures)
                        else:
                            self.assertEqual(len(figures), ab_figure_count)
                    for encoded in figures:
                        self.assertTrue(base64.b64decode(encoded).startswith(b"\x89PNG"))
                    if config["generate_pdf"]:
                        self.assertTrue(base64.b64decode(response.json()["pdf_bytes"]).startswith(b"%PDF"))
                    self.assertEqual(set(plt.get_fignums()), baseline)

    def test_all_figures_are_closed_when_serialization_fails(self):
        baseline = set(plt.get_fignums())
        first, _ = plt.subplots()
        second, _ = plt.subplots()
        output = EngineOutput(figures=[first, second])
        frame = aggregate_frame("AB")

        try:
            with (
                patch("backend.api.routes.run_engine", return_value=output),
                patch.object(first, "savefig", side_effect=RuntimeError("png failure")),
                self.assertRaisesRegex(RuntimeError, "png failure"),
            ):
                self.post(
                    "freq_pvalue_no_sid",
                    frame,
                    {"session_id": False, "include_ai": False},
                )
            self.assertEqual(set(plt.get_fignums()), baseline)
        finally:
            plt.close(first)
            plt.close(second)


if __name__ == "__main__":
    unittest.main()
