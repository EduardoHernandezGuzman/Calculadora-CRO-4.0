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


def aggregate_ab(
    conversions_a: int, conversions_b: int, visits: int = 1000
) -> pd.DataFrame:
    return pd.DataFrame({
        "Día": [1],
        "Visitas A": [visits],
        "Conversiones A": [conversions_a],
        "Visitas B": [visits],
        "Conversiones B": [conversions_b],
    })


def session_ab(
    conversions_a: int, conversions_b: int, visits: int = 1000
) -> pd.DataFrame:
    rows = []
    for group, conversions in (("A", conversions_a), ("B", conversions_b)):
        for index in range(visits):
            rows.append({
                "Día": 1,
                "SessionID": f"{group}-{index}",
                "Conversiones A": float(index < conversions) if group == "A" else np.nan,
                "Conversiones B": float(index < conversions) if group == "B" else np.nan,
            })
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
        if engine in BAYES_ENGINES:
            self.assertTrue(all(
                item["reverse_comparison"]["reference"] == item["variant"]
                and item["reverse_comparison"]["compared"] == "A"
                and item["reverse_comparison"]["is_best"] is False
                for item in comparisons
            ))

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
                variant_winners = [
                    item for item in comparisons
                    if item.get("comparison_winner") == item["variant"]
                ]
                if not selected and engine in (ENGINE_0_1_SID, ENGINE_0_INF_SID):
                    self.assertFalse(variant_winners)
                    self.assertTrue(any(
                        item.get("comparison_winner") == "A" for item in comparisons
                    ))
                    continue
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

    def test_pvalue_bilateral_recognizes_variant_control_and_no_winner(self):
        cases = ((500, 560, "B"), (560, 500, "A"), (500, 510, None))
        for conversions_a, conversions_b, expected_winner in cases:
            with self.subTest(expected_winner=expected_winner):
                output = run_silently(
                    ENGINE_FREQ_PVALUE_NO_SID,
                    aggregate_ab(conversions_a, conversions_b),
                    freq_interval_type="centrado",
                )
                comparison = output.comparisons[0]
                self.assertEqual(comparison["comparison_winner"], expected_winner)
                self.assertEqual(
                    comparison["comparison_status"],
                    "Resultado concluyente" if expected_winner else "Sin ganador concluyente",
                )
                self.assertLessEqual(sum(item["is_best"] for item in output.comparisons), 1)
                json.dumps(output.comparisons, allow_nan=False)

    def test_pvalue_one_tailed_interpretation_is_unchanged(self):
        frame = aggregate_ab(560, 500)
        right = run_silently(
            ENGINE_FREQ_PVALUE_NO_SID, frame, freq_interval_type="derecha"
        ).comparisons[0]
        left = run_silently(
            ENGINE_FREQ_PVALUE_NO_SID, frame, freq_interval_type="izquierda"
        ).comparisons[0]
        self.assertEqual(right["interval"]["name"], "right_95")
        self.assertEqual(right["comparison_status"], "Sin ganador concluyente")
        self.assertEqual(left["interval"]["name"], "left_95")
        self.assertEqual(left["comparison_status"], "Ganadora")

    def test_all_bayesian_engines_use_the_same_probability_thresholds(self):
        for engine in BAYES_ENGINES:
            cases = ((500, 560, "B"), (560, 500, "A"), (500, 510, None))
            for conversions_a, conversions_b, expected_winner in cases:
                with self.subTest(engine=engine, expected_winner=expected_winner):
                    frame = (
                        session_ab(conversions_a, conversions_b, visits=10000)
                        if engine in SESSION_ENGINES
                        else aggregate_ab(conversions_a, conversions_b, visits=10000)
                    )
                    output = run_silently(
                        engine,
                        frame,
                        num_samples=10000,
                    )
                    comparison = output.comparisons[0]
                    self.assertEqual(comparison["comparison_winner"], expected_winner)
                    self.assertEqual(
                        comparison["comparison_status"],
                        "Resultado concluyente" if expected_winner else "Sin ganador concluyente",
                    )
                    probability = comparison["evidence"]["value"]
                    reverse = comparison["reverse_comparison"]
                    self.assertAlmostEqual(
                        probability + reverse["evidence"]["value"], 1.0, places=12
                    )
                    self.assertAlmostEqual(
                        comparison["difference"], -reverse["difference"], places=12
                    )
                    self.assertEqual(
                        comparison["comparison_winner"], reverse["comparison_winner"]
                    )
                    self.assertFalse(reverse["is_best"])
                    if expected_winner == "B":
                        self.assertGreaterEqual(probability, 0.95)
                    elif expected_winner == "A":
                        self.assertLessEqual(probability, 0.05)
                    else:
                        self.assertGreater(probability, 0.05)
                        self.assertLess(probability, 0.95)
                    self.assertEqual(comparison["interval"]["name"], "centered_95")
                    self.assertIsNotNone(comparison["interval"]["low"])
                    self.assertIsNotNone(comparison["interval"]["high"])
                    self.assertLess(comparison["interval"]["low"], 0)
                    self.assertGreater(comparison["interval"]["high"], 0)
                    self.assertLessEqual(sum(item["is_best"] for item in output.comparisons), 1)
                    json.dumps(output.comparisons, allow_nan=False)

    def test_bayesian_reverse_metrics_use_the_existing_samples(self):
        import backend.engines.varios_disenos_0_1 as beta_no_sid
        import backend.engines.varios_disenos_0_inf as gamma_no_sid
        import backend.engines.varios_disenos_sessionid_0_1 as beta
        import backend.engines.varios_disenos_sessionid_0_inf as gamma

        control_samples = np.array([1.0, 2.0, 3.0, 4.0])
        variant_samples = np.array([2.1, 2.1, 2.1, 2.1])
        forward_difference = variant_samples - control_samples
        forward_uplift = forward_difference / control_samples
        paso = {
            "A": {"media": float(np.mean(control_samples)), "muestras": control_samples},
            "B": {"media": float(np.mean(variant_samples)), "muestras": variant_samples},
            "A_vs_B": {
                "prob_mejor": float(np.mean(forward_difference > 0)),
                "uplift_media": float(np.mean(forward_uplift)),
                "uplift_std": float(np.std(forward_uplift)),
                "ci_centered": np.percentile(forward_uplift, [2.5, 97.5]),
                "ci_right": np.percentile(forward_uplift, [5.0, 100.0]),
                "ci_left": np.percentile(forward_uplift, [0.0, 95.0]),
                "diff": forward_difference,
                "tipo_ic": "centrado",
            },
        }
        expected_difference = control_samples - variant_samples
        expected_uplift = expected_difference / variant_samples
        expected_interval = np.percentile(expected_uplift, [2.5, 97.5]) * 100

        for module in (beta_no_sid, gamma_no_sid, beta, gamma):
            with self.subTest(module=module.__name__):
                comparison = module._build_lightweight_comparisons(paso, ("B",))[0]
                reverse = comparison["reverse_comparison"]
                self.assertAlmostEqual(
                    reverse["uplift_pct"], float(np.mean(expected_uplift) * 100)
                )
                self.assertAlmostEqual(
                    reverse["difference"], float(np.mean(expected_difference))
                )
                self.assertAlmostEqual(
                    reverse["evidence"]["value"],
                    float(np.mean(control_samples > variant_samples)),
                )
                np.testing.assert_allclose(
                    [reverse["interval"]["low"], reverse["interval"]["high"]],
                    expected_interval,
                )
                self.assertEqual(
                    reverse["comparison_winner"], comparison["comparison_winner"]
                )
                self.assertFalse(reverse["is_best"])
                json.dumps(comparison, allow_nan=False)

    def test_control_is_global_winner_only_when_it_beats_every_variant(self):
        output = run_silently(
            ENGINE_FREQ_PVALUE_NO_SID,
            pd.DataFrame({
                "Día": [1],
                "Visitas A": [1000], "Conversiones A": [560],
                "Visitas B": [1000], "Conversiones B": [500],
                "Visitas C": [1000], "Conversiones C": [510],
            }),
            freq_interval_type="centrado",
        )
        self.assertTrue(all(item["comparison_winner"] == "A" for item in output.comparisons))
        self.assertFalse(any(item["is_best"] for item in output.comparisons))

        mixed = run_silently(
            ENGINE_FREQ_PVALUE_NO_SID,
            pd.DataFrame({
                "Día": [1],
                "Visitas A": [1000], "Conversiones A": [560],
                "Visitas B": [1000], "Conversiones B": [500],
                "Visitas C": [1000], "Conversiones C": [555],
            }),
            freq_interval_type="centrado",
        )
        self.assertEqual([item["comparison_winner"] for item in mixed.comparisons], ["A", None])
        self.assertFalse(any(item["is_best"] for item in mixed.comparisons))

        opposite_winners = run_silently(
            ENGINE_FREQ_PVALUE_NO_SID,
            pd.DataFrame({
                "Día": [1],
                "Visitas A": [1000], "Conversiones A": [560],
                "Visitas B": [1000], "Conversiones B": [500],
                "Visitas C": [1000], "Conversiones C": [620],
            }),
            freq_interval_type="centrado",
        )
        self.assertEqual(
            [item["comparison_winner"] for item in opposite_winners.comparisons],
            ["A", "C"],
        )
        selected = [item for item in opposite_winners.comparisons if item["is_best"]]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["variant"], "C")

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
