from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from backend.core.engine_router import EngineOutput
from backend.main import app


class InputValidationApiTests(unittest.TestCase):
    client = TestClient(app)

    def post(self, content: bytes | str, engine: str, config=None):
        if isinstance(content, str):
            content = content.encode("utf-8")
        config_value = json.dumps(config or {}) if not isinstance(config, str) else config
        with patch("backend.api.routes.run_engine", return_value=EngineOutput()) as mocked:
            response = self.client.post(
                "/api/analyze",
                files={"file": ("input.csv", content, "text/csv")},
                data={"engine_key": engine, "config": config_value},
            )
        return response, mocked

    def assert_bad_request(self, content, *, engine="bayes_0_1_no_sid", text=None, config=None):
        response, mocked = self.post(content, engine, config)
        self.assertEqual(response.status_code, 400, response.text)
        if text:
            self.assertIn(text, response.json()["detail"])
        mocked.assert_not_called()

    def test_rejects_empty_invalid_encoding_parser_and_config(self):
        self.assert_bad_request(b"", text="está vacío")
        self.assert_bad_request(
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n"
            "mañana,10,1,10,1\n".encode("windows-1252"),
            text="CSV UTF-8",
        )
        self.assert_bad_request(
            "Día,Visitas A\n1,10,extra\n",
            text="mismo número de columnas",
        )
        self.assert_bad_request(
            "Día;Visitas A;Conversiones A;Visitas B;Conversiones B\n1;10;1;10;1\n",
            text="comas como separador",
        )
        self.assert_bad_request(
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n1,10,1,10,1\n",
            config="{invalid",
            text="JSON válido",
        )

    def test_rejects_unknown_engine(self):
        self.assert_bad_request(
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n1,10,1,10,1\n",
            engine="unknown",
            text="no existe",
        )

    def test_rejects_invalid_aggregate_values(self):
        header = "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n"
        cases = (
            ("1,10,,10,1\n", "celdas vacías"),
            ("1,texto,1,10,1\n", "valores numéricos"),
            ("1,10.5,1,10,1\n", "valores enteros"),
            ("1,10,1.5,10,1\n", "valores enteros"),
            ("1,-10,1,10,1\n", "valores negativos"),
            ("1,10,-1,10,1\n", "valores negativos"),
            ("1,10,11,10,1\n", "no puede superar"),
        )
        for row, message in cases:
            with self.subTest(row=row):
                self.assert_bad_request(header + row, text=message)

    def test_gamma_poisson_allows_conversions_above_visits(self):
        csv = (
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n"
            "1,10,15,10,20\n"
        )
        response, mocked = self.post(csv, "bayes_0_inf_no_sid")
        self.assertEqual(response.status_code, 200, response.text)
        mocked.assert_called_once()

        session = (
            "Día,SessionID,Conversiones A,Conversiones B\n"
            "1,A-1,2,\n1,B-1,,3\n"
        )
        response, mocked = self.post(session, "bayes_0_inf_sid")
        self.assertEqual(response.status_code, 200, response.text)
        mocked.assert_called_once()

    def test_frequentist_rejects_conversions_above_visits(self):
        csv = (
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n"
            "1,10,11,10,1\n"
        )
        self.assert_bad_request(csv, engine="freq_pvalue_no_sid", text="no puede superar")

    def test_rejects_invalid_session_data(self):
        self.assert_bad_request(
            "Día,Conversiones A,Conversiones B\n1,0,\n1,,1\n",
            engine="bayes_0_1_sid",
            text="SessionID",
        )
        self.assert_bad_request(
            "Día,SessionID,Conversiones A,Conversiones B\n1,A-1,0,\n1,, ,1\n",
            engine="bayes_0_1_sid",
            text="SessionID",
        )
        self.assert_bad_request(
            "Día,SessionID,Conversiones A,Conversiones B\n1,A-1,2,\n1,B-1,,1\n",
            engine="bayes_0_1_sid",
            text="solo puede contener 0 o 1",
        )
        self.assert_bad_request(
            "Día,SessionID,Conversiones A,Conversiones B\n1,A-1,0.5,\n1,B-1,,1\n",
            engine="bayes_0_inf_sid",
            text="valores enteros",
        )

    def test_drops_a_completely_empty_optional_variant(self):
        csv = (
            "Día,SessionID,Conversiones A,Conversiones B,Conversiones C\n"
            "1,A-1,0,,\n"
            "1,C-1,,,1\n"
        )
        response, mocked = self.post(csv, "bayes_0_1_sid")
        self.assertEqual(response.status_code, 200, response.text)
        validated = mocked.call_args.args[1]
        self.assertNotIn("Conversiones B", validated.columns)
        self.assertIn("Conversiones C", validated.columns)

    def test_preserves_incomplete_and_unknown_group_errors(self):
        self.assert_bad_request(
            "Día,Visitas A,Conversiones A,Visitas B\n1,10,1,10\n",
            text="Conversiones B",
        )
        self.assert_bad_request(
            "Día,Visitas A,Conversiones A,Visitas F,Conversiones F\n1,10,1,10,1\n",
            text="no admitidos",
        )

    def test_accepts_utf8_bom_crlf_and_valid_families(self):
        aggregate = (
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\r\n"
            "1,10,1,10,2\r\n"
        )
        response, mocked = self.post(b"\xef\xbb\xbf" + aggregate.encode(), "bayes_0_1_no_sid")
        self.assertEqual(response.status_code, 200, response.text)
        mocked.assert_called_once()

        session = (
            "Día,SessionID,Conversiones A,Conversiones B\n"
            "1,A-1,0,\n1,B-1,,1\n"
        )
        for engine in ("bayes_0_1_sid", "freq_pvalue_sid"):
            with self.subTest(engine=engine):
                response, mocked = self.post(session, engine)
                self.assertEqual(response.status_code, 200, response.text)
                mocked.assert_called_once()

    def test_accepts_legacy_session_format_with_required_identifiers(self):
        csv = "Día,SessionID,A,B\n1,A-1,0,\n1,B-1,,1\n"
        response, mocked = self.post(csv, "freq_pvalue_sid")
        self.assertEqual(response.status_code, 200, response.text)
        mocked.assert_called_once()

    def test_expected_engine_errors_are_400_and_unexpected_errors_remain_500(self):
        csv = (
            "Día,Visitas A,Conversiones A,Visitas B,Conversiones B\n"
            "1,10,1,10,2\n"
        )
        with patch("backend.api.routes.run_engine", side_effect=ValueError("Dato no válido.")):
            response = self.client.post(
                "/api/analyze",
                files={"file": ("input.csv", csv, "text/csv")},
                data={"engine_key": "bayes_0_1_no_sid", "config": "{}"},
            )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"], "Dato no válido.")

        client = TestClient(app, raise_server_exceptions=False)
        with patch("backend.api.routes.run_engine", side_effect=RuntimeError("internal")):
            response = client.post(
                "/api/analyze",
                files={"file": ("input.csv", csv, "text/csv")},
                data={"engine_key": "bayes_0_1_no_sid", "config": "{}"},
            )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("internal", response.text)


if __name__ == "__main__":
    unittest.main()
