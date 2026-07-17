from __future__ import annotations

import contextlib
import io
import json
import types
import unittest
from unittest.mock import patch

import matplotlib.pyplot as plt
import numpy as np
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
    run_engine,
)
from backend.core.experiment_groups import (
    detect_aggregate_groups,
    detect_session_groups,
)


GROUP_RATES = {"A": 0.30, "B": 0.45, "C": 0.10, "D": 0.50, "E": 0.25}
ALL_ENGINES = (
    ENGINE_0_1_NO_SID,
    ENGINE_0_INF_NO_SID,
    ENGINE_FREQ_NO_SID,
    ENGINE_FREQ_PVALUE_NO_SID,
    ENGINE_0_1_SID,
    ENGINE_0_INF_SID,
    ENGINE_FREQ_SID,
    ENGINE_FREQ_PVALUE_SID,
)
SESSION_ENGINES = {
    ENGINE_0_1_SID,
    ENGINE_0_INF_SID,
    ENGINE_FREQ_SID,
    ENGINE_FREQ_PVALUE_SID,
}
BOOTSTRAP_ENGINES = {ENGINE_FREQ_NO_SID, ENGINE_FREQ_SID}
PVALUE_ENGINES = {ENGINE_FREQ_PVALUE_NO_SID, ENGINE_FREQ_PVALUE_SID}
BAYES_ENGINES = {
    ENGINE_0_1_NO_SID,
    ENGINE_0_INF_NO_SID,
    ENGINE_0_1_SID,
    ENGINE_0_INF_SID,
}


def aggregate_frame(groups: tuple[str, ...], visits: int = 500) -> pd.DataFrame:
    data = {"Día": [1]}
    for group in groups:
        data[f"Visitas {group}"] = [visits]
        data[f"Conversiones {group}"] = [int(visits * GROUP_RATES[group])]
    return pd.DataFrame(data)


def session_frame(groups: tuple[str, ...], visits: int = 80) -> pd.DataFrame:
    rows = []
    for group in groups:
        conversions = int(visits * GROUP_RATES[group])
        for index in range(visits):
            row = {"Día": 1, "SessionID": f"{group}-{index}"}
            for candidate in groups:
                row[f"Conversiones {candidate}"] = (
                    float(index < conversions) if candidate == group else np.nan
                )
            rows.append(row)
    return pd.DataFrame(rows)


def engine_frame(engine: str, groups: tuple[str, ...]) -> pd.DataFrame:
    return session_frame(groups) if engine in SESSION_ENGINES else aggregate_frame(groups)


def engine_config(engine: str, **extra) -> dict:
    config = {"include_ai": False, "generate_pdf": False}
    if engine in BAYES_ENGINES:
        config["num_samples"] = 500
    if engine in BOOTSTRAP_ENGINES:
        config["n_iteraciones"] = 80
    config.update(extra)
    return config


def run_silently(engine: str, frame: pd.DataFrame, **config):
    np.random.seed(20260717)
    with contextlib.redirect_stdout(io.StringIO()):
        return run_engine(engine, frame, engine_config(engine, **config))


def assert_lightweight(test: unittest.TestCase, value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            test.assertIsInstance(key, str)
            assert_lightweight(test, item)
        return
    if isinstance(value, list):
        for item in value:
            assert_lightweight(test, item)
        return
    test.assertTrue(value is None or isinstance(value, (str, int, float, bool)))


class FakeCompletions:
    prompts: list[str] = []

    def create(self, **kwargs):
        self.prompts.append(kwargs["messages"][-1]["content"])
        message = types.SimpleNamespace(content="interpretación falsa")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


class FakeOpenAI:
    def __init__(self, **_kwargs):
        self.chat = types.SimpleNamespace(completions=FakeCompletions())


class ExperimentGroupTests(unittest.TestCase):
    def test_detects_aggregate_and_session_groups(self):
        aggregate = detect_aggregate_groups(aggregate_frame(tuple("ABCDE")).columns)
        session = detect_session_groups(session_frame(tuple("ABC")).columns)
        self.assertEqual(aggregate.control, "A")
        self.assertEqual(aggregate.variants, tuple("BCDE"))
        self.assertEqual(session.variants, tuple("BC"))

    def test_rejects_missing_control_and_missing_variants(self):
        with self.assertRaisesRegex(ValueError, "control A"):
            detect_aggregate_groups(["Visitas B", "Conversiones B"])
        with self.assertRaisesRegex(ValueError, "al menos una variante"):
            detect_aggregate_groups(["Visitas A", "Conversiones A"])

    def test_rejects_incomplete_aggregate_variant(self):
        with self.assertRaisesRegex(ValueError, "Conversiones B"):
            detect_aggregate_groups(["Visitas A", "Conversiones A", "Visitas B"])
        with self.assertRaisesRegex(ValueError, "Visitas B"):
            detect_aggregate_groups(["Visitas A", "Conversiones A", "Conversiones B"])

    def test_rejects_mixed_session_formats_and_unknown_groups(self):
        with self.assertRaisesRegex(ValueError, "mezclarse"):
            detect_session_groups(["Conversiones A", "Conversiones B", "A", "B"])
        with self.assertRaisesRegex(ValueError, "no admitidos"):
            detect_aggregate_groups(
                ["Visitas A", "Conversiones A", "Visitas F", "Conversiones F"]
            )
        with self.assertRaisesRegex(ValueError, "no admitidos"):
            detect_session_groups(["Conversiones A", "Conversiones F"])


class EngineContractTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def assert_contract(self, engine: str, groups: tuple[str, ...], output) -> None:
        comparisons = output.comparisons or []
        variants = list(groups[1:])
        self.assertEqual([item["variant"] for item in comparisons], variants)
        self.assertEqual(
            [(item["control"], item["variant"]) for item in comparisons],
            [("A", variant) for variant in variants],
        )
        self.assertLessEqual(sum(bool(item["is_best"]) for item in comparisons), 1)
        json.dumps(comparisons, allow_nan=False)
        assert_lightweight(self, comparisons)
        forbidden = {("B", "C"), ("C", "D"), ("B", "A")}
        self.assertFalse(forbidden.intersection(
            (item["control"], item["variant"]) for item in comparisons
        ))
        if engine in BOOTSTRAP_ENGINES:
            self.assertTrue(all("p_value" not in json.dumps(item) for item in comparisons))
        if engine in PVALUE_ENGINES or engine in BOOTSTRAP_ENGINES:
            self.assertEqual(len(output.summary), len(variants))
            self.assertEqual(list(output.summary["variant"]), variants)
        else:
            self.assertGreaterEqual(len(output.summary), len(groups))

    def test_all_engines_support_ab_abc_and_abcde(self):
        for engine in ALL_ENGINES:
            for groups in (tuple("AB"), tuple("ABC"), tuple("ABCDE")):
                with self.subTest(engine=engine, groups=groups):
                    output = run_silently(engine, engine_frame(engine, groups))
                    self.assert_contract(engine, groups, output)

    def test_selection_uses_each_engine_evidence(self):
        for engine in ALL_ENGINES:
            with self.subTest(engine=engine):
                output = run_silently(engine, engine_frame(engine, tuple("ABCDE")))
                comparisons = output.comparisons or []
                selected = [item for item in comparisons if item["is_best"]]
                self.assertEqual(len(selected), 1)
                winners = [item for item in comparisons if item["favorable"] and item["significant"]]
                pool = winners or [item for item in comparisons if item["favorable"]]
                values = [item["evidence"]["value"] for item in pool]
                expected = min(values) if engine in PVALUE_ENGINES else max(values)
                self.assertEqual(selected[0]["evidence"]["value"], expected)

    def test_ab_metrics_are_unchanged_when_c_is_added(self):
        for engine in ALL_ENGINES:
            with self.subTest(engine=engine):
                ab = run_silently(engine, engine_frame(engine, tuple("AB")))
                abc = run_silently(engine, engine_frame(engine, tuple("ABC")))
                ab_record = (ab.comparisons or [])[0]
                abc_record = (abc.comparisons or [])[0]
                for key in (
                    "control",
                    "variant",
                    "control_value",
                    "variant_value",
                    "uplift_pct",
                    "difference",
                    "evidence",
                    "interval",
                    "favorable",
                    "significant",
                    "metrics",
                ):
                    self.assertEqual(ab_record[key], abc_record[key], msg=f"{engine}: {key}")

    def test_frequentist_interval_directions(self):
        expected_names = {
            "centrado": "centered_95",
            "derecha": "right_95",
            "izquierda": "left_95",
        }
        engines = (*BOOTSTRAP_ENGINES, *PVALUE_ENGINES)
        for engine in engines:
            for interval_type, interval_name in expected_names.items():
                with self.subTest(engine=engine, interval=interval_type):
                    output = run_silently(
                        engine,
                        engine_frame(engine, tuple("ABCDE")),
                        freq_interval_type=interval_type,
                    )
                    self.assertTrue(all(
                        item["interval"]["name"] == interval_name
                        for item in output.comparisons or []
                    ))
                    if interval_type == "derecha":
                        self.assertTrue(all(item["interval"]["high"] is None for item in output.comparisons or []))
                    if interval_type == "izquierda":
                        self.assertTrue(all(item["interval"]["low"] is None for item in output.comparisons or []))

    def test_pdf_generation_with_five_groups(self):
        for engine in ALL_ENGINES:
            with self.subTest(engine=engine):
                output = run_silently(
                    engine,
                    engine_frame(engine, tuple("ABCDE")),
                    generate_pdf=True,
                )
                self.assertIsInstance(output.pdf_bytes, bytes)
                self.assertGreater(len(output.pdf_bytes or b""), 1000)
                self.assertGreaterEqual(len(output.figures or []), 1)

    def test_ai_prompt_contains_every_control_comparison(self):
        import backend.engines.varios_diseno_frecuentista as bootstrap
        import backend.engines.varios_diseno_frecuentista_pvalue as pvalue
        import backend.engines.varios_disenos_frecuentista_pvalue_sessionid as pvalue_sid
        import backend.engines.varios_disenos_frecuentista_sessionid as bootstrap_sid

        FakeCompletions.prompts.clear()
        fake_module = types.SimpleNamespace(OpenAI=FakeOpenAI)
        freq_modules = (bootstrap, bootstrap_sid, pvalue, pvalue_sid)
        with patch.dict("sys.modules", {"openai": fake_module}):
            with patch.multiple(bootstrap, OpenAI=FakeOpenAI), patch.multiple(
                bootstrap_sid, OpenAI=FakeOpenAI
            ), patch.multiple(pvalue, OpenAI=FakeOpenAI), patch.multiple(
                pvalue_sid, OpenAI=FakeOpenAI
            ):
                for engine in ALL_ENGINES:
                    run_silently(
                        engine,
                        engine_frame(engine, tuple("ABCDE")),
                        include_ai=True,
                        openai_api_key="fake",
                    )

        self.assertEqual(len(FakeCompletions.prompts), len(ALL_ENGINES))
        for prompt in FakeCompletions.prompts:
            for variant in "BCDE":
                self.assertTrue(
                    f"A_vs_{variant}" in prompt
                    or f"A vs {variant}" in prompt
                    or f"A/{variant}" in prompt
                    or f"Variante ({variant})" in prompt,
                    msg=f"Falta A vs {variant} en el prompt",
                )


if __name__ == "__main__":
    unittest.main()
