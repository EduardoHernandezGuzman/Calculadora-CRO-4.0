from __future__ import annotations

import json
import base64
import types
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from backend.core.engine_router import ENGINE_LABELS, EngineOutput
from backend.core.srm import calculate_srm
from backend.main import app


def aggregate_frame(counts: dict[str, int]) -> pd.DataFrame:
    data = {"Día": [1]}
    for group, count in counts.items():
        data[f"Visitas {group}"] = [count]
        data[f"Conversiones {group}"] = [0]
    return pd.DataFrame(data)


def session_frame(counts: dict[str, int]) -> pd.DataFrame:
    rows = []
    groups = list(counts)
    for group, count in counts.items():
        for index in range(count):
            row = {"Día": 1, "SessionID": f"{group}-{index}"}
            for candidate in groups:
                row[f"Conversiones {candidate}"] = 0 if candidate == group else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


class SrmTests(unittest.TestCase):
    def assert_json(self, result):
        json.dumps(result, allow_nan=False)

    def test_balanced_ab_has_no_srm(self):
        result = calculate_srm(aggregate_frame({"A": 1000, "B": 1000}), session_id=False)
        self.assertFalse(result["has_srm"])
        self.assertEqual(result["p_value"], 1.0)
        self.assertEqual(result["degrees_of_freedom"], 1)
        self.assert_json(result)

    def test_unbalanced_ab_has_srm(self):
        result = calculate_srm(aggregate_frame({"A": 1500, "B": 500}), session_id=False)
        self.assertTrue(result["has_srm"])

    def test_balanced_and_unbalanced_abc(self):
        balanced = calculate_srm(
            aggregate_frame({"A": 900, "B": 900, "C": 900}), session_id=False
        )
        unbalanced = calculate_srm(
            aggregate_frame({"A": 1800, "B": 450, "C": 450}), session_id=False
        )
        self.assertFalse(balanced["has_srm"])
        self.assertTrue(unbalanced["has_srm"])

    def test_abcde_uniform_contract(self):
        result = calculate_srm(
            aggregate_frame({group: 200 for group in "ABCDE"}), session_id=False
        )
        self.assertEqual(result["groups"], list("ABCDE"))
        self.assertEqual(result["total_sample"], 1000)
        self.assertTrue(all(value == 0.2 for value in result["expected_ratios"].values()))

    def test_session_counts_zero_and_ignores_nan(self):
        frame = pd.DataFrame({
            "Día": [1, 1, 1, 1],
            "SessionID": ["A-1", "A-2", "B-1", "B-2"],
            "Conversiones A": [0, 0, np.nan, np.nan],
            "Conversiones B": [np.nan, np.nan, 0, 0],
        })
        result = calculate_srm(frame, session_id=True)
        self.assertEqual(result["sample_counts"], {"A": 2, "B": 2})
        self.assertFalse(result["has_srm"])

    def test_session_abcde_balanced(self):
        result = calculate_srm(
            session_frame({group: 10 for group in "ABCDE"}), session_id=True
        )
        self.assertEqual(result["groups"], list("ABCDE"))
        self.assertEqual(result["sample_counts"], {group: 10 for group in "ABCDE"})
        self.assertFalse(result["has_srm"])

    def test_legacy_session_format(self):
        frame = pd.DataFrame({"A": [0, 1, np.nan], "B": [1, 0, 0]})
        result = calculate_srm(frame, session_id=True)
        self.assertEqual(result["sample_counts"], {"A": 2, "B": 3})

    def test_rejects_format_configuration_mismatch(self):
        with self.assertRaisesRegex(ValueError, "indica Session ID"):
            calculate_srm(aggregate_frame({"A": 10, "B": 10}), session_id=True)
        with self.assertRaisesRegex(ValueError, "sin Session ID"):
            calculate_srm(session_frame({"A": 10, "B": 10}), session_id=False)

    def test_custom_ratios_accept_different_key_order(self):
        result = calculate_srm(
            aggregate_frame({"A": 600, "B": 300, "C": 100}),
            session_id=False,
            expected_ratios={"C": 0.1, "A": 0.6, "B": 0.3},
        )
        self.assertEqual(list(result["expected_ratios"]), ["A", "B", "C"])
        self.assertFalse(result["has_srm"])

    def test_rejects_invalid_ratios_alpha_and_empty_sample(self):
        frame = aggregate_frame({"A": 10, "B": 10})
        with self.assertRaisesRegex(ValueError, "sumar 1"):
            calculate_srm(frame, session_id=False, expected_ratios={"A": 0.6, "B": 0.6})
        with self.assertRaisesRegex(ValueError, "claves"):
            calculate_srm(frame, session_id=False, expected_ratios={"A": 1.0})
        for alpha in (0, 1):
            with self.assertRaisesRegex(ValueError, "alpha"):
                calculate_srm(frame, session_id=False, alpha=alpha)
        with self.assertRaisesRegex(ValueError, "total es 0"):
            calculate_srm(aggregate_frame({"A": 0, "B": 0}), session_id=False)

    def test_p_value_equal_to_alpha_is_not_srm(self):
        fake_result = types.SimpleNamespace(statistic=5.0, pvalue=0.01)
        with patch("backend.core.srm.chisquare", return_value=fake_result):
            result = calculate_srm(
                aggregate_frame({"A": 12, "B": 8}), session_id=False, alpha=0.01
            )
        self.assertFalse(result["has_srm"])


class SrmApiTests(unittest.TestCase):
    client = TestClient(app)

    def request(self, engine: str, frame: pd.DataFrame, session_id: bool, **config):
        payload = {"session_id": session_id, "include_ai": False, **config}
        return self.client.post(
            "/api/analyze",
            files={"file": ("srm.csv", frame.to_csv(index=False), "text/csv")},
            data={"engine_key": engine, "config": json.dumps(payload)},
        )

    def test_srm_is_returned_by_all_eight_engines(self):
        session_engines = {
            "bayes_0_1_sid", "bayes_0_inf_sid", "freq_sid", "freq_pvalue_sid"
        }
        for engine in ENGINE_LABELS:
            with self.subTest(engine=engine):
                is_session = engine in session_engines
                frame = (
                    session_frame({"A": 20, "B": 20})
                    if is_session else aggregate_frame({"A": 100, "B": 100})
                )
                config = {"num_samples": 200} if engine.startswith("bayes_") else {}
                if engine in {"freq_no_sid", "freq_sid"}:
                    config["n_iteraciones"] = 40
                response = self.request(engine, frame, is_session, **config)
                self.assertEqual(response.status_code, 200, response.text)
                srm = response.json()["srm"]
                self.assertFalse(srm["has_srm"])
                json.dumps(srm, allow_nan=False)

    def test_api_rejects_config_and_format_mismatch(self):
        response = self.request(
            "freq_sid", aggregate_frame({"A": 10, "B": 10}), True,
            n_iteraciones=20,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("indica Session ID", response.text)

        response = self.request(
            "freq_no_sid", session_frame({"A": 10, "B": 10}), False,
            n_iteraciones=20,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("sin Session ID", response.text)

    def test_api_rejects_session_config_that_contradicts_engine(self):
        response = self.request(
            "freq_no_sid", aggregate_frame({"A": 10, "B": 10}), True,
            n_iteraciones=20,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("contradice", response.text)

    def test_api_uses_engine_key_as_session_fallback(self):
        response = self.client.post(
            "/api/analyze",
            files={
                "file": (
                    "fallback.csv",
                    aggregate_frame({"A": 20, "B": 20}).to_csv(index=False),
                    "text/csv",
                )
            },
            data={
                "engine_key": "freq_pvalue_no_sid",
                "config": json.dumps({"include_ai": False}),
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["srm"]["has_srm"])

    def test_api_supports_legacy_session_ab(self):
        legacy = pd.DataFrame({"A": [0, 1, 0, np.nan], "B": [1, 0, 0, 1]})
        response = self.request(
            "freq_pvalue_sid", legacy, True
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["srm"]["sample_counts"], {"A": 3, "B": 4})

    def test_only_srm_is_added_to_existing_envelope(self):
        figure, axis = plt.subplots()
        axis.plot([0, 1], [0, 1])
        previous = EngineOutput(
            summary=pd.DataFrame([{"control": "A", "variant": "B", "value": 1.0}]),
            figures=[figure],
            pdf_bytes=b"existing-pdf",
            log_text=None,
            comparisons=[{"control": "A", "variant": "B", "is_best": True}],
        )
        with patch("backend.api.routes.run_engine", return_value=previous):
            response = self.request(
                "freq_pvalue_no_sid",
                aggregate_frame({"A": 100, "B": 100}),
                False,
                generate_pdf=True,
            )
        plt.close(figure)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {"summary", "figures", "pdf_bytes", "log_text", "comparisons", "srm"},
        )
        self.assertEqual(payload["summary"], [{"control": "A", "variant": "B", "value": 1.0}])
        self.assertEqual(payload["comparisons"], previous.comparisons)
        self.assertEqual(base64.b64decode(payload["pdf_bytes"]), b"existing-pdf")
        self.assertIsNone(payload["log_text"])
        self.assertEqual(len(payload["figures"]), 1)
        self.assertTrue(base64.b64decode(payload["figures"][0]).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
