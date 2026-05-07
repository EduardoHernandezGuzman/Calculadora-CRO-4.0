const ENGINES_MAP = {
  bayes_0_1_no_sid: 'Bayesiana [0,1] sin Session ID',
  bayes_0_1_sid: 'Bayesiana [0,1] con Session ID',
  bayes_0_inf_no_sid: 'Bayesiana [0,∞] sin Session ID',
  bayes_0_inf_sid: 'Bayesiana [0,∞] con Session ID',
  freq_no_sid: 'Frecuentista (Bootstrap) sin Session ID',
  freq_sid: 'Frecuentista (Bootstrap) con Session ID',
};

function getEngineKey() {
  const enfoque = window.State.enfoque;
  const sid = window.State.session_id;
  const tipo = window.State.tipo_valores;

  if (enfoque === 'bayesiano') {
    if (tipo === '0_1' && sid === false) return 'bayes_0_1_no_sid';
    if (tipo === '0_1' && sid === true) return 'bayes_0_1_sid';
    if (tipo === '0_inf' && sid === false) return 'bayes_0_inf_no_sid';
    if (tipo === '0_inf' && sid === true) return 'bayes_0_inf_sid';
  }
  if (enfoque === 'frecuentista') {
    return sid ? 'freq_sid' : 'freq_no_sid';
  }
  return null;
}

function isRouteReady() {
  const s = window.State;
  if (!s.enfoque || s.session_id === null || s.session_id === undefined) return false;
  if (s.enfoque === 'bayesiano' && !s.tipo_valores) return false;
  if (s.enfoque === 'frecuentista' && !s.freq_interval_type) return false;
  return true;
}

function selectModel(value) {
  window.State.enfoque = value;
  goToStep(2);
}

function selectSessionId(value) {
  window.State.session_id = value;
  if (window.State.enfoque === 'bayesiano') {
    goToStep(3);
    showWizardStep3Bayes();
  } else {
    goToStep(3);
    showWizardStep3Freq();
  }
}

function selectBayesType(value) {
  window.State.tipo_valores = value;
  goToStep(4);
  renderStep4Summary();
}

function selectFreqInterval(value) {
  window.State.freq_interval_type = value;
  window.State.tipo_valores = value;
  goToStep(4);
  renderStep4Summary();
}

function goToStep(step) {
  window.State.wizard_step = step;
  showStep(step);

  if (step === 2) {
    const enfoqueLabel = window.State.enfoque === 'bayesiano' ? 'Bayesiano' : 'Frecuentista';
    document.getElementById('step2-enfoque').textContent = enfoqueLabel;
  }
}

function showWizardStep3Bayes() {
  const sidTxt = window.State.session_id ? 'con Session ID' : 'sin Session ID';
  document.getElementById('step3-subtitle').innerHTML =
    `Analizar&aacute;s tu test A/B ${sidTxt}...`;
}

function showWizardStep3Freq() {
  const sidTxt = window.State.session_id ? 'con Session ID' : 'sin Session ID';
  document.getElementById('step3-subtitle').innerHTML =
    `Analizar&aacute;s tu test A/B ${sidTxt}...`;
}

function renderStep4Summary() {
  const engineKey = getEngineKey();
  const label = ENGINES_MAP[engineKey] || engineKey;

  const s = window.State;
  let extra = '';

  if (s.enfoque === 'bayesiano') {
    const tv = s.tipo_valores === '0_1' ? 'Conversiones únicas (Beta-Binomial)' : 'Conversiones múltiples (Gamma-Poisson)';
    const sid = s.session_id ? 'Con Session ID' : 'Sin Session ID';
    extra = `Tipo de conversiones: <b>${tv}</b><br>Unidad de análisis: <b>${sid}</b>`;
  } else {
    const intervalMap = { centrado: 'IC Centrado', derecha: 'Cola derecha', izquierda: 'Cola izquierda' };
    const sid = s.session_id ? 'Con Session ID' : 'Sin Session ID';
    extra = `Intervalo: <b>${intervalMap[s.freq_interval_type]}</b><br>Unidad de análisis: <b>${sid}</b>`;
  }

  document.getElementById('step4-summary').innerHTML = `
    <div class="result-card">
      <div class="choice-title">¡Listo!</div>
      <div class="choice-text">
        Ruta disponible ✅<br>
        Motor seleccionado: <b>${label}</b><br><br>
        ${extra}
      </div>
    </div>
    <div class="btn-row" style="justify-content:center;">
      <button class="btn btn-primary" onclick="startAnalysis()">Analizar test A/B</button>
    </div>
  `;

  document.getElementById('step4-not-ready').style.display = 'none';
  document.getElementById('step4-back-row').style.display = '';
}

function startAnalysis() {
  window.State.selected_engine_key = getEngineKey();
  window.State.show_app = true;
  document.getElementById('wizard-section').style.display = 'none';
  document.getElementById('calculator-section').style.display = '';
  renderCalculator();
}
