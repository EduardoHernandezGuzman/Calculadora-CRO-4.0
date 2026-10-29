import copy
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from test_multivariate_engines import (
    ALL_ENGINES, FakeCompletions, FakeOpenAI, multi_day_engine_frame,
    run_silently,
)
from backend.engines import varios_disenos_sessionid_0_1 as beta
from backend.engines import varios_disenos_sessionid_0_inf as gamma


class BayesianTemporalAITests(unittest.TestCase):
    def setUp(self):
        FakeCompletions.prompts.clear()
        self.mock_openai = patch.dict('sys.modules', {'openai': types.SimpleNamespace(OpenAI=FakeOpenAI)})
        self.mock_openai.start()
        self.addCleanup(self.mock_openai.stop)

    def test_prompts_receive_existing_history_in_order_without_mutation(self):
        for module, function in ((beta, beta._interpretar_con_ia), (gamma, gamma.interpretar_con_ia)):
            with self.subTest(module=module.__name__):
                history = [
                    {'dia': f'Día {day}', **{
                        f'A_vs_{v}': {'prob_mejor': p}
                        for v in 'BCDE'
                    }} for day, p in ((1, .65), (2, .72), (10, .96))
                ]
                final = copy.deepcopy(history[-1])
                for value in final.values():
                    if isinstance(value, dict):
                        value.update(uplift_media=.1, ci_centered=[-.01, .2],
                                     ci_right=[-.02, .3], ci_left=[-.1, .25])
                original = copy.deepcopy(history)
                original_final = copy.deepcopy(final)
                function(final, api_key='fake', historial=history)
                prompt = FakeCompletions.prompts[-1]
                self.assertEqual(history, original)
                self.assertEqual(final, original_final)
                self.assertNotIn('el primero sea mejor', prompt)
                for v in 'BCDE':
                    self.assertIn(f'Comparativa A vs {v} · P({v} > A):', prompt)
                    probability = original_final[f'A_vs_{v}']['prob_mejor']
                    self.assertIn(f'Probabilidad de que {v} supere a A: {probability * 100:.2f}%', prompt)
                self.assertLess(prompt.index('Día 1: 65%'), prompt.index('Día 2: 72%'))
                self.assertLess(prompt.index('Día 2: 72%'), prompt.index('Día 10: 96%'))
                self.assertIn('evidencia acumulada', prompt)
                self.assertIn('No consideres una tendencia positiva únicamente', prompt)
                self.assertIn('DETENER EL TEST / CONTINUAR EL TEST', prompt)
                self.assertIn('Muy volátil/inconclusa', prompt)
                if module is gamma:
                    self.assertIn('modelo Gamma-Poisson', prompt)
                    self.assertIn('Regla específica para probabilidades >95%', prompt)
                else:
                    self.assertIn('¿La evidencia está consolidándose o es inestable?', prompt)

    def test_single_period_and_missing_values_are_not_invented(self):
        for function in (beta._interpretar_con_ia, gamma.interpretar_con_ia):
            function({}, api_key='fake', historial=[{
                'dia': 'Día 7', 'A_vs_B': {'prob_mejor': .8},
                'A_vs_C': {'prob_mejor': None}, 'A_vs_D': {'prob_mejor': np.nan},
            }])
            prompt = FakeCompletions.prompts[-1]
            self.assertIn('Día 7: 80%', prompt)
            self.assertIn('No existe información temporal suficiente para analizar una tendencia.', prompt)
            self.assertNotIn('Día 1:', prompt)
            self.assertNotIn('nan%', prompt)
            self.assertNotIn('None%', prompt)

    def test_ai_does_not_change_statistics_for_all_eight_engines(self):
        for engine in ALL_ENGINES:
            for days in (1, 3):
                with self.subTest(engine=engine, days=days):
                    frame = multi_day_engine_frame(engine, tuple('ABCDE'), days)
                    original = frame.copy(deep=True)
                    calls_before = len(FakeCompletions.prompts)
                    before = run_silently(engine, frame, generate_figures=False)
                    self.assertEqual(len(FakeCompletions.prompts), calls_before)
                    count = len(FakeCompletions.prompts)
                    after = run_silently(engine, frame, generate_figures=False,
                                         include_ai=True, openai_api_key='fake')
                    pd.testing.assert_frame_equal(before.summary, after.summary)
                    pd.testing.assert_frame_equal(frame, original)
                    self.assertEqual(before.comparisons, after.comparisons)
                    self.assertEqual(before.figures, after.figures)
                    self.assertEqual(before.pdf_bytes, after.pdf_bytes)
                    self.assertIn('interpretación falsa', after.log_text)
                    self.assertEqual(len(FakeCompletions.prompts), count + 1)
                    prompt = FakeCompletions.prompts[-1]
                    if engine in ('bayes_0_1_sid', 'bayes_0_inf_sid'):
                        self.assertIn('RESULTADO ESTADÍSTICO CALCULADO POR EL MOTOR', prompt)
                        self.assertIn('Día 1:', prompt)
                        if days == 3:
                            self.assertIn('Día 3:', prompt)
                    else:
                        self.assertNotIn('EVOLUCIÓN TEMPORAL DE LA PROBABILIDAD:', prompt)


if __name__ == '__main__':
    unittest.main()
