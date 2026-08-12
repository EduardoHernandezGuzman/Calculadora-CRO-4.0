const fs = require('fs');
const vm = require('vm');

const elements = {};
const context = {
  console,
  window: {
    State: {
      enfoque: 'bayesiano',
      tipo_valores: '0_1',
      session_id: false,
      freq_interval_type: 'derecha',
      selected_engine_key: 'bayes_0_1_no_sid',
    },
  },
  document: {
    getElementById: id => elements[id] || null,
    createElement: () => element(''),
    documentElement: { clientWidth: 1200 },
    body: { appendChild: child => { elements[child.id] = child; } },
  },
  $$: () => [],
  showError: () => {},
  showSuccess: () => {},
  showStep: step => { context.shownStep = step; },
  clearSelection: () => {},
  toggleSpinner: () => {},
  analyzeCsv: async () => {},
  File: class {},
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/js/calculator.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('frontend/js/wizard.js', 'utf8'), context);
const evaluate = expression => vm.runInContext(expression, context);

function element(id, value = '') {
  const classes = new Set();
  elements[id] = {
    value,
    checked: false,
    innerHTML: '',
    textContent: '',
    dataset: {},
    attributes: {},
    style: {},
    scrollOptions: null,
    addEventListener() {},
    scrollIntoView(options) { this.scrollOptions = options; },
    setAttribute(name, attributeValue) { this.attributes[name] = attributeValue; },
    getBoundingClientRect() { return { left: 100, top: 100, right: 120, bottom: 120, width: 20, height: 20 }; },
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      toggle(name) { classes.has(name) ? classes.delete(name) : classes.add(name); },
      contains(name) { return classes.has(name); },
    },
  };
  return elements[id];
}

function comparison(variant, options = {}) {
  return {
    control: 'A',
    variant,
    control_value: 0.20,
    variant_value: options.variantValue ?? 0.23,
    uplift_pct: options.uplift ?? 15,
    difference: options.difference ?? 0.03,
    evidence: {
      name: options.evidenceName || 'p_value',
      value: options.evidence ?? 0.03,
    },
    interval: options.interval || { name: 'centered_95', low: -2, high: 32 },
    favorable: options.favorable ?? true,
    significant: options.significant ?? false,
    comparison_status: options.significant ? 'Ganadora' : 'Sin ganador concluyente',
    comparison_winner: options.comparisonWinner ?? (options.significant ? variant : null),
    selection_label: options.selectionLabel ?? null,
    is_best: options.isBest ?? false,
    metrics: {
      z_score: 1.63,
      se_control: 0.0126,
      se_variante: 0.0133,
      se_diferencia: 0.0184,
    },
  };
}

function bayesianComparison(variant, options = {}) {
  const direct = comparison(variant, {
    ...options,
    evidenceName: 'probability_superiority',
  });
  direct.reverse_comparison = {
    reference: variant,
    compared: 'A',
    reference_value: direct.variant_value,
    compared_value: direct.control_value,
    uplift_pct: -10.71,
    difference: -direct.difference,
    evidence: {
      name: 'probability_superiority',
      value: 1 - direct.evidence.value,
    },
    interval: { name: 'centered_95', low: -22, high: 1.5 },
    comparison_winner: direct.comparison_winner,
    comparison_status: direct.comparison_status,
    is_best: false,
  };
  return direct;
}

element('step3-subtitle');
element('step3-subtitle-extra');
element('step2-enfoque');
context.window.State.session_id = null;
context.window.State.tipo_valores = null;
evaluate("selectModel('bayesiano')");
if (context.shownStep !== 2 || context.window.State.wizard_step !== 2) {
  throw new Error('El flujo bayesiano no muestra la pantalla de Session ID.');
}
if (context.window.State.session_id !== null) throw new Error('El flujo bayesiano fija Session ID antes de que el usuario elija.');
evaluate('selectSessionId(true)');
if (context.shownStep !== 3 || context.window.State.wizard_step !== 3 || context.window.State.session_id !== true) {
  throw new Error('Tengo Session ID no abre las conversiones bayesianas con session_id=true.');
}
context.window.State.tipo_valores = '0_1';
if (evaluate('getEngineKey()') !== 'bayes_0_1_sid') throw new Error('Conversiones únicas con Session ID resuelven un motor incorrecto.');
context.window.State.tipo_valores = '0_inf';
if (evaluate('getEngineKey()') !== 'bayes_0_inf_sid') throw new Error('Conversiones múltiples con Session ID resuelven un motor incorrecto.');
evaluate("selectModel('bayesiano')");
if (context.window.State.session_id !== null || context.shownStep !== 2) {
  throw new Error('Volver a seleccionar Bayesiano no reinicia la elección de Session ID.');
}
evaluate('selectSessionId(false)');
if (context.shownStep !== 3 || context.window.State.wizard_step !== 3 || context.window.State.session_id !== false) {
  throw new Error('No tengo Session ID no abre las conversiones bayesianas con session_id=false.');
}
context.window.State.tipo_valores = '0_1';
if (evaluate('getEngineKey()') !== 'bayes_0_1_no_sid') throw new Error('Conversiones únicas sin Session ID resuelven un motor incorrecto.');
context.window.State.tipo_valores = '0_inf';
if (evaluate('getEngineKey()') !== 'bayes_0_inf_no_sid') throw new Error('Conversiones múltiples sin Session ID resuelven un motor incorrecto.');
element('freq-tail-choice');
element('freq-direction-choice');
context.window.State.session_id = true;
evaluate("selectModel('freq_pvalue')");
if (context.shownStep !== 3 || context.window.State.wizard_step !== 3) {
  throw new Error('El flujo frecuentista no salta directamente a la pantalla del tipo de hipótesis.');
}
if (context.window.State.session_id !== false) throw new Error('El flujo frecuentista no fija session_id=false.');
if (elements['freq-tail-choice'].style.display !== '' || elements['freq-direction-choice'].style.display !== 'none') {
  throw new Error('La pantalla inicial de hipótesis frecuentista no queda visible.');
}
context.window.State.freq_interval_type = 'derecha';
if (evaluate('getEngineKey()') !== 'freq_pvalue_no_sid') throw new Error('El flujo frecuentista no resuelve freq_pvalue_no_sid.');
const indexHtml = fs.readFileSync('frontend/index.html', 'utf8');
const modelSelectionStep = indexHtml.slice(indexHtml.indexOf('id="step-1"'), indexHtml.indexOf('id="step-2"'));
if (modelSelectionStep.includes("selectModel('frecuentista')") || modelSelectionStep.includes('Enfoque Frecuentista (Bootstrap)')) {
  throw new Error('Bootstrap sigue siendo seleccionable desde la interfaz.');
}
if ((modelSelectionStep.match(/onclick="selectModel\('/g) || []).length !== 2 || !modelSelectionStep.includes('choice-row-primary')) {
  throw new Error('El selector principal no contiene únicamente dos opciones centradas.');
}
const bayesStep = indexHtml.slice(indexHtml.indexOf('id="step-3-bayes"'), indexHtml.indexOf('id="step-3-freq"'));
if (!bayesStep.includes('onclick="goToStep(2)"') || bayesStep.includes('onclick="goToStep(1)"')) {
  throw new Error('Volver desde conversiones bayesianas no regresa a Session ID.');
}
const freqStep = indexHtml.slice(indexHtml.indexOf('id="step-3-freq"'), indexHtml.indexOf('id="step-4"'));
if (!freqStep.includes('onclick="goToStep(1)"') || freqStep.includes('onclick="goToStep(2)"')) {
  throw new Error('Volver desde la hipótesis frecuentista no regresa directamente al selector de enfoque.');
}
context.window.State.enfoque = 'bayesiano';
context.window.State.tipo_valores = '0_1';
context.window.State.session_id = false;

element('calculator-main');
element('csv-file-input');
element('upload-zone');
evaluate('renderCalculatorMain()');
const bayesNoSidHtml = elements['calculator-main'].innerHTML;
if (!bayesNoSidHtml.includes('Cargar CSV') || !bayesNoSidHtml.includes('Introducir datos manualmente')) {
  throw new Error('La entrada manual no aparece en Bayesiano.');
}
if (bayesNoSidHtml.includes('id="manual-group-a" style="display:none;"') || bayesNoSidHtml.includes('id="manual-group-b" style="display:none;"')) {
  throw new Error('A o B aparecen ocultos inicialmente.');
}
for (const group of ['c', 'd', 'e']) {
  if (!bayesNoSidHtml.includes(`id="manual-group-${group}" class="manual-entry-group " style="display:none;"`)) {
    throw new Error(`La variante ${group.toUpperCase()} aparece visible inicialmente.`);
  }
}
if (!bayesNoSidHtml.includes('A&ntilde;adir variante')) throw new Error('Falta el CTA para añadir variantes.');
if (bayesNoSidHtml.includes('Dejar vacío si no se usa') || (bayesNoSidHtml.match(/placeholder="Ej\. 2800"/g) || []).length !== 5 || (bayesNoSidHtml.match(/placeholder="Ej\. 580"/g) || []).length !== 5) {
  throw new Error('Los placeholders no son iguales para A-E.');
}
if (bayesNoSidHtml.includes('aria-label="Eliminar variante A"') || bayesNoSidHtml.includes('aria-label="Eliminar variante B"')) {
  throw new Error('A o B permiten eliminarse.');
}
for (const group of ['C', 'D', 'E']) {
  if (!bayesNoSidHtml.includes(`aria-label="Eliminar variante ${group}"`)) throw new Error(`Falta el botón para eliminar ${group}.`);
}

for (const group of ['c', 'd', 'e']) {
  element(`manual-group-${group}`);
  element(`manual-${group}-visitas`);
  element(`manual-${group}-conv`);
}
for (const group of ['a', 'b']) {
  element(`manual-${group}-visitas`);
  element(`manual-${group}-conv`);
}
element('add-manual-variant-row');
evaluate('addManualVariant()');
if (elements['manual-group-c'].style.display !== '' || elements['manual-group-d'].style.display === '') {
  throw new Error('El primer clic no muestra exclusivamente C.');
}
evaluate('addManualVariant()');
if (elements['manual-group-d'].style.display !== '' || elements['manual-group-e'].style.display === '') {
  throw new Error('El segundo clic no muestra exclusivamente D.');
}
evaluate('addManualVariant()');
if (elements['manual-group-e'].style.display !== '' || elements['add-manual-variant-row'].style.display !== 'none') {
  throw new Error('El tercer clic no muestra E y oculta el CTA.');
}
evaluate('addManualVariant()');
if (evaluate('visibleManualVariants.size') !== 3) throw new Error('Se añaden variantes duplicadas.');

elements['manual-d-visitas'].value = '100';
elements['manual-d-conv'].value = '20';
evaluate("removeManualVariant('D')");
if (elements['manual-group-d'].style.display !== 'none' || elements['manual-d-visitas'].value !== '' || elements['manual-d-conv'].value !== '') {
  throw new Error('Eliminar D no oculta la tarjeta y limpia sus valores.');
}
if (elements['manual-group-c'].style.display !== '' || elements['manual-group-e'].style.display !== '' || elements['add-manual-variant-row'].style.display !== '') {
  throw new Error('Eliminar D afecta a C/E o no recupera el CTA.');
}
for (const group of ['a', 'b', 'c', 'e']) {
  elements[`manual-${group}-visitas`].value = '100';
  elements[`manual-${group}-conv`].value = '20';
}
context.groupsAfterRemoval = evaluate('readManualGroups()');
if (context.groupsAfterRemoval.map(item => item.group).join('') !== 'ABCE') {
  throw new Error('La variante eliminada entra en readManualGroups().');
}
context.csvAfterRemoval = evaluate("buildManualCsv('bayes_0_1_no_sid', groupsAfterRemoval)");
if (context.csvAfterRemoval.includes('Visitas D') || context.csvAfterRemoval.includes('Conversiones D')) {
  throw new Error('La variante eliminada entra en el CSV manual.');
}
evaluate('addManualVariant()');
if (elements['manual-group-d'].style.display !== '' || evaluate('visibleManualVariants.size') !== 3) {
  throw new Error('D no puede volver a añadirse o se duplica.');
}
evaluate('addManualVariant()');
if (evaluate('visibleManualVariants.size') !== 3) throw new Error('Se crean duplicados tras volver a añadir D.');

context.window.State.session_id = true;
evaluate('renderCalculatorMain()');
const bayesSidHtml = elements['calculator-main'].innerHTML;
if (!bayesSidHtml.includes('Cargar CSV') || !bayesSidHtml.includes('Introducir datos manualmente')) {
  throw new Error('CSV y entrada manual no aparecen en Bayesiano con Session ID.');
}
if (evaluate('visibleManualVariants.size') !== 0) throw new Error('Cambiar Session ID no reinicia las variantes manuales.');

for (const enfoque of ['frecuentista', 'freq_pvalue']) {
  for (const sessionId of [false, true]) {
    context.window.State.enfoque = enfoque;
    context.window.State.session_id = sessionId;
    evaluate('renderCalculatorMain()');
    const frequentistHtml = elements['calculator-main'].innerHTML;
    if (frequentistHtml.includes('Cargar CSV') || frequentistHtml.includes('method-csv') || frequentistHtml.includes('upload-zone')) {
      throw new Error(`La carga CSV aparece en ${enfoque} con session_id=${sessionId}.`);
    }
    if (!frequentistHtml.includes('id="method-manual"') || frequentistHtml.includes('id="method-manual" style="display:none;"')) {
      throw new Error(`La entrada manual no aparece directamente en ${enfoque} con session_id=${sessionId}.`);
    }
  }
}

context.window.State.enfoque = 'frecuentista';
evaluate("selectInputMethod('csv')");
evaluate('resetData()');
context.window.State.enfoque = 'bayesiano';
context.window.State.session_id = false;

for (const group of 'ABCDE') {
  element(`manual-${group.toLowerCase()}-visitas`);
  element(`manual-${group.toLowerCase()}-conv`);
}
elements['manual-a-visitas'].value = '100';
elements['manual-a-conv'].value = '20';
elements['manual-b-visitas'].value = '100';
elements['manual-b-conv'].value = '25';
elements['manual-e-visitas'].value = '100';
elements['manual-e-conv'].value = '99';
context.manualGroups = evaluate('readManualGroups()');
if (context.manualGroups.length !== 2) throw new Error('Las variantes ocultas se incluyen en los datos manuales.');

elements['manual-a-conv'].value = '101';
let uniqueRejected = false;
try { evaluate('readManualGroups()'); } catch (_error) { uniqueRejected = true; }
if (!uniqueRejected) throw new Error('Bayesiano único permite conversiones superiores a visitas.');

context.window.State.tipo_valores = '0_inf';
context.manualGroups = evaluate('readManualGroups()');
if (context.manualGroups[0].conversions !== 101) throw new Error('Bayesiano múltiple rechaza conteos válidos.');

context.groups = [
  { group: 'A', visits: 2, conversions: 5 },
  { group: 'B', visits: 2, conversions: 7 },
  { group: 'E', visits: 1, conversions: 3 },
];
context.window.State.session_id = false;
let csv = evaluate("buildManualCsv('bayes_0_inf_no_sid', groups)");
if (!csv.startsWith('Día,Visitas A,Conversiones A,Visitas B,Conversiones B,Visitas E,Conversiones E')) {
  throw new Error('CSV agregado manual incorrecto.');
}
context.window.State.session_id = true;
csv = evaluate("buildManualCsv('bayes_0_inf_sid', groups)");
if (!csv.startsWith('Día,SessionID,Conversiones A,Conversiones B,Conversiones E')) {
  throw new Error('CSV Session ID manual incorrecto.');
}
if (csv.includes('Conversiones C') || csv.includes('Conversiones D')) {
  throw new Error('Se generan columnas para variantes vacías.');
}

if (evaluate("validateCsvHeaders(['Día','SessionID','Conversiones A','Conversiones B','Conversiones C'])") !== '') {
  throw new Error('CSV canónico multivariante rechazado.');
}
if (evaluate("validateCsvHeaders(['Día','SessionID','Conversiones A','Conversiones B','A','B'])") === '') {
  throw new Error('Se acepta un formato Session ID mezclado.');
}

context.comparisons = [
  comparison('B', { significant: true }),
  comparison('C', { isBest: true, selectionLabel: 'Ganadora', significant: true, evidence: 0.01 }),
  comparison('D', { interval: { name: 'right_95', low: 1.2, high: null } }),
  comparison('E', { favorable: false, uplift: -5, interval: { name: 'left_95', low: null, high: -1.4 } }),
];
context.summary = context.comparisons.map(item => ({ control: 'A', variant: item.variant }));
let cards = evaluate('renderComparisonCards(comparisons, summary)');
if ((cards.match(/<article class="comparison-card/g) || []).length !== 4 || cards.includes('data-mirror="true"')) {
  throw new Error('Frecuentista no mantiene una tarjeta por comparación.');
}
if ((cards.match(/data-is-best="true"/g) || []).length !== 1) throw new Error('Destacado principal inválido.');
if (!cards.includes('A vs B') || !cards.includes('A vs E')) throw new Error('Faltan tarjetas multivariantes.');
if (!cards.includes('> 1.20%') || !cards.includes('< -1.40%')) throw new Error('Intervalos null incorrectos.');
if (!cards.includes('Límite inferior (IC 95 %)') || !cards.includes('Límite superior (IC 95 %)')) {
  throw new Error('El intervalo frecuentista centrado no muestra sus límites por separado.');
}
if (cards.includes('[-2.00%, 32.00%]')) throw new Error('La tarjeta mantiene el formato conjunto del intervalo centrado.');
if (/\b(null|NaN|undefined)\b/.test(cards)) throw new Error('Se muestran valores técnicos vacíos.');
if (!cards.includes('Resultado concluyente')) throw new Error('Falta el estado concluyente no seleccionado.');
for (const [variants, expectedCards] of [[['B'], 2], [['B', 'C'], 4], [['B', 'C', 'D', 'E'], 8]]) {
  context.bayesianMirrorComparisons = variants.map((variant, index) => bayesianComparison(variant, {
    isBest: index === 0,
    selectionLabel: index === 0 ? 'Ganadora' : null,
    significant: index === 0,
    comparisonWinner: index === 0 ? variant : null,
  }));
  context.bayesianMirrorSummary = variants.map(variant => ({ control: 'A', variant }));
  const mirrorCards = evaluate('renderComparisonCards(bayesianMirrorComparisons, bayesianMirrorSummary)');
  if ((mirrorCards.match(/<article class="comparison-card/g) || []).length !== expectedCards) {
    throw new Error(`Bayesiano con ${variants.length} variantes no muestra ${expectedCards} tarjetas.`);
  }
  if ((mirrorCards.match(/data-mirror="true"/g) || []).length !== variants.length) {
    throw new Error('Falta alguna tarjeta espejo bayesiana.');
  }
  if ((mirrorCards.match(/data-is-best="true"/g) || []).length !== 1 ||
      (mirrorCards.match(/data-mirror="true"[^>]*data-is-best="true"/g) || []).length) {
    throw new Error('Una tarjeta espejo participa en la selección global.');
  }
  if (!mirrorCards.includes('B vs A') || mirrorCards.includes('B vs C')) {
    throw new Error('Las comparaciones espejo bayesianas son incorrectas.');
  }
  const renderedMirrors = mirrorCards.match(/<article class="comparison-card comparison-mirror[\s\S]*?<\/article>/g) || [];
  if (!renderedMirrors[0] || !renderedMirrors[0].includes('Probabilidad de que A supere a B')) {
    throw new Error('La tarjeta espejo no muestra la probabilidad inversa.');
  }
  if (renderedMirrors.some(card =>
    card.includes('Referencia ') ||
    card.includes('Grupo comparado ') ||
    card.includes('Uplift de ') ||
    card.includes('comparison-interval')
  )) {
    throw new Error('La tarjeta espejo muestra métricas adicionales.');
  }
}
context.bayesianComparisons = [comparison('B', { evidenceName: 'probability_superiority', interval: { name: 'credible_interval', low: 45.12, high: 97.97 } })];
context.bayesianCards = evaluate("renderComparisonCards(bayesianComparisons, [{ control: 'A', variant: 'B' }])");
if (!context.bayesianCards.includes('Límite inferior (IC 95 %)') || !context.bayesianCards.includes('45.12%') ||
    !context.bayesianCards.includes('Límite superior (IC 95 %)') || !context.bayesianCards.includes('97.97%')) {
  throw new Error('El intervalo bayesiano no muestra sus límites por separado.');
}
if (context.bayesianCards.includes('[45.12%, 97.97%]')) throw new Error('La tarjeta bayesiana mantiene el formato conjunto.');
const tooltipText = 'Indica la probabilidad de que la diferencia observada entre las variantes no se debe al azar. Un p-value inferior al nivel de significancia (0,05 en este caso) sugiere que la diferencia observada es estadísticamente significativa.';
if (!cards.includes(`data-tooltip="${tooltipText}"`) || !cards.includes('onmouseenter="showEvidenceTooltip(event)"') || !cards.includes('onfocus="showEvidenceTooltip(event)"')) {
  throw new Error('Tooltip de p-value incompleto o no accesible mediante teclado.');
}
context.tooltipTrigger = element('tooltip-trigger');
context.tooltipTrigger.dataset.tooltip = tooltipText;
evaluate('showEvidenceTooltip({ currentTarget: tooltipTrigger })');
const tooltipPopover = elements['evidence-tooltip-popover'];
if (!tooltipPopover || !tooltipPopover.classList.contains('visible') || tooltipPopover.textContent !== tooltipText) {
  throw new Error('El tooltip no se abre al pasar el ratón por el icono.');
}
evaluate('hideEvidenceTooltip({ currentTarget: tooltipTrigger })');
if (tooltipPopover.classList.contains('visible')) throw new Error('El tooltip no se cierra al retirar el ratón.');
context.nonPvalueComparisons = [
  comparison('B', { evidenceName: 'probability_superiority' }),
  comparison('C', { evidenceName: 'level_of_significance' }),
];
const nonPvalueCards = evaluate('renderComparisonCards(nonPvalueComparisons, [])');
if (nonPvalueCards.includes('evidence-tooltip-trigger') || nonPvalueCards.includes(tooltipText)) {
  throw new Error('El tooltip aparece en Bayesiano o Bootstrap.');
}

context.candidate = [comparison('B'), comparison('C', { isBest: true, selectionLabel: 'Mejor candidata' })];
if (!evaluate('renderSelectionOverview(candidate)').includes('Mejor candidata: C')) throw new Error('Mejor candidata incorrecta.');
context.noCandidate = [comparison('B', { favorable: false }), comparison('C', { favorable: false })];
if (!evaluate('renderSelectionOverview(noCandidate)').includes('No hay una variante ganadora concluyente')) {
  throw new Error('Estado sin ganador incorrecto.');
}
context.controlWinner = [comparison('B', {
  favorable: false,
  significant: true,
  comparisonWinner: 'A',
})];
context.controlWinner[0].comparison_status = 'Resultado concluyente';
context.controlWinner[0].is_best = false;
const controlOverview = evaluate('renderSelectionOverview(controlWinner)');
const controlCards = evaluate("renderComparisonCards(controlWinner, [{ control: 'A', variant: 'B' }])");
if (!controlOverview.includes('Ganador: Control A') ||
    !controlOverview.includes('El control supera de forma concluyente a la variante analizada.')) {
  throw new Error('El resumen no muestra al control A como ganador.');
}
if (!controlCards.includes('Ganador: Control A') ||
    !controlCards.includes('La variante B es significativamente peor que A.')) {
  throw new Error('La tarjeta no muestra correctamente la victoria del control A.');
}
context.variantWinner = [comparison('B', {
  favorable: true,
  significant: true,
  comparisonWinner: 'B',
  isBest: true,
  selectionLabel: 'Ganadora',
})];
if (!evaluate('renderSelectionOverview(variantWinner)').includes('Variante ganadora: B')) {
  throw new Error('La victoria concluyente de una variante ha cambiado.');
}
context.mixedControlResult = [context.controlWinner[0], comparison('C', { favorable: false })];
if (!evaluate('renderSelectionOverview(mixedControlResult)').includes('No hay una variante ganadora concluyente')) {
  throw new Error('Una victoria parcial de A se presenta incorrectamente como victoria global.');
}

element('results-container');
evaluate('scrollToResults()');
if (elements['results-container'].scrollOptions?.behavior !== 'smooth') {
  throw new Error('El scroll a resultados no utiliza comportamiento suave.');
}
const manualAnalysisSource = evaluate('runManualAnalysis.toString()');
if (!manualAnalysisSource.includes('if (analysisSucceeded) scrollToResults()')) {
  throw new Error('La entrada manual no limita el scroll a análisis completados correctamente.');
}
context.output = {
  comparisons: context.comparisons,
  summary: context.summary,
  log_text: 'Interpretación conjunta de IA',
  figures: ['figura-1', 'figura-2', 'figura-3', 'figura-4'],
  pdf_bytes: 'YWJj',
  srm: { has_srm: false, p_value: 0.42, alpha: 0.01 },
};
evaluate('displayResults(output)');
const rendered = elements['results-container'].innerHTML;
if (!rendered.includes('No se detectó SRM')) throw new Error('Falta el banner SRM verde.');
if ((rendered.match(/class="srm-banner/g) || []).length !== 1) throw new Error('El banner SRM aparece más de una vez.');
if (rendered.indexOf('No se detectó SRM') > rendered.indexOf('Variante ganadora')) throw new Error('Orden visual SRM incorrecto.');
if (rendered.indexOf('Interpretación IA') > rendered.indexOf('Resumen')) throw new Error('IA aparece demasiado tarde.');
if ((rendered.match(/data:image\/png;base64/g) || []).length !== 4) throw new Error('No se renderizan todas las figuras.');
if (!rendered.includes('reporte-multivariante.pdf')) throw new Error('PDF no descargable.');

context.redSrm = { has_srm: true, p_value: 0.0000000123, alpha: 0.01 };
const redBanner = evaluate('renderSrmBanner(redSrm)');
if (!redBanner.includes('Se detectó SRM') || !redBanner.includes('1.23e-8')) throw new Error('Banner SRM rojo o p-value científico incorrecto.');
if (!evaluate('renderSrmBanner(null)').includes('Chequeo SRM no disponible')) throw new Error('Una respuesta antigua sin SRM rompe el frontend.');

element('chk-pdf').checked = false;
element('chk-figures').checked = true;
element('chk-ai').checked = false;
element('input-ai-key').value = '';
context.window.State.enfoque = 'frecuentista';
context.window.State.freq_interval_type = 'izquierda';
const config = evaluate('buildAnalysisConfig()');
if (config.generate_figures !== true) throw new Error('La generación de gráficos no está activa por defecto.');
if (config.freq_interval_type !== 'izquierda') throw new Error('freq_interval_type no se transporta.');
if (config.session_id !== true) throw new Error('session_id no se transporta.');
if ('alpha' in config || 'significance_level' in config || 'statistical_power' in config || 'power' in config) {
  throw new Error('Los desplegables informativos alteran el payload estadístico.');
}

const significanceCopy = 'Umbral estad&iacute;stico utilizado para determinar si las diferencias observadas entre las variantes son suficientemente fiables como para no atribuirlas al azar. Representa la probabilidad m&aacute;xima aceptada de obtener un falso positivo.';
const powerCopy = 'Probabilidad de detectar una diferencia real entre las variantes cuando realmente existe. Un mayor poder reduce el riesgo de concluir err&oacute;neamente que no hay efecto (falso negativo).';
const bayesSidebarConfig = evaluate('renderBayesConfig()');
if (!bayesSidebarConfig.includes('Tipo de conversiones') || !bayesSidebarConfig.includes('Nivel de confianza') || !bayesSidebarConfig.includes('Unidad de an&aacute;lisis')) {
  throw new Error('Los desplegables bayesianos existentes han desaparecido.');
}
if (bayesSidebarConfig.includes('Nivel de significancia (95%)') || bayesSidebarConfig.includes('Poder estad&iacute;stico (80%)')) {
  throw new Error('Los desplegables frecuentistas aparecen en Bayesiano.');
}

for (const enfoque of ['frecuentista', 'freq_pvalue']) {
  context.window.State.enfoque = enfoque;
  context.window.State.session_id = false;
  element('calculator-sidebar');
  evaluate('renderSidebar()');
  const sidebarHtml = elements['calculator-sidebar'].innerHTML;
  if (!sidebarHtml.includes('Calculadora Frecuentista')) {
    throw new Error(`El enfoque ${enfoque} no se reconoce como familia frecuentista en el sidebar.`);
  }
  if (!sidebarHtml.includes('Nivel de significancia (95%)') || !sidebarHtml.includes(significanceCopy)) {
    throw new Error(`Falta el desplegable de significancia o su copy exacto en ${enfoque}.`);
  }
  if (!sidebarHtml.includes('Poder estad&iacute;stico (80%)') || !sidebarHtml.includes(powerCopy)) {
    throw new Error(`Falta el desplegable de poder o su copy exacto en ${enfoque}.`);
  }
  if (!sidebarHtml.includes('<div class="expander-header">Nivel de significancia (95%) <span class="arrow">&#9660;</span></div>') ||
      !sidebarHtml.includes('<div class="expander-header">Poder estad&iacute;stico (80%) <span class="arrow">&#9660;</span></div>')) {
    throw new Error('Significancia o poder no aparecen como acordeones independientes.');
  }
  for (const hiddenHeader of ['Tipo de hip&oacute;tesis', 'Direcci&oacute;n de hip&oacute;tesis', 'Nivel de confianza', 'Unidad de an&aacute;lisis']) {
    if (sidebarHtml.includes(`<div class="expander-header">${hiddenHeader}`)) {
      throw new Error(`${hiddenHeader} sigue visible en el sidebar frecuentista.`);
    }
  }
  if ((sidebarHtml.match(/class="expander"/g) || []).length !== 3) {
    throw new Error('El sidebar completo debe contener Enfoque y los dos expanders frecuentistas.');
  }
  if (sidebarHtml.indexOf('Nivel de significancia (95%)') > sidebarHtml.indexOf('Poder estad&iacute;stico (80%)')) {
    throw new Error('El orden de significancia y poder es incorrecto.');
  }
}

const frequentistConfig = evaluate('renderFreqConfig()');
const frequentistHeaders = [...frequentistConfig.matchAll(/class="expander-header">([^<]+)/g)].map(match => match[1].trim());
if (frequentistHeaders.join('|') !== 'Nivel de significancia (95%)|Poder estad&iacute;stico (80%)') {
  throw new Error(`La configuración frecuentista contiene headers inesperados: ${frequentistHeaders.join(', ')}`);
}

let expanderClick = null;
const interactiveExpander = {
  opened: false,
  querySelector(selector) {
    if (selector !== '.expander-header') return null;
    return { addEventListener(event, callback) { if (event === 'click') expanderClick = callback; } };
  },
  classList: { toggle(name) { if (name === 'open') interactiveExpander.opened = !interactiveExpander.opened; } },
};
context.$$ = selector => selector === '.expander' ? [interactiveExpander] : [];
context.window.State.enfoque = 'freq_pvalue';
evaluate('renderSidebar()');
if (typeof expanderClick !== 'function') throw new Error('El listener común no alcanza los nuevos expanders.');
expanderClick();
if (!interactiveExpander.opened) throw new Error('El desplegable frecuentista no se abre.');
expanderClick();
if (interactiveExpander.opened) throw new Error('El desplegable frecuentista no se cierra.');
context.$$ = () => [];

const executionOptions = evaluate("renderExecutionOptions('bayesiano')");
if (!executionOptions.includes('id="chk-figures" checked') || !executionOptions.includes('Generar gr&aacute;ficos')) {
  throw new Error('Falta el checkbox de gráficos activado por defecto.');
}
element('pdf-requires-figures');
elements['chk-pdf'].checked = true;
elements['chk-figures'].checked = false;
evaluate('toggleFigureOptions()');
if (elements['chk-pdf'].checked || !elements['chk-pdf'].disabled) {
  throw new Error('Desactivar gráficos no desactiva y desmarca el PDF.');
}
if (elements['pdf-requires-figures'].style.display !== 'block') {
  throw new Error('No se informa de que el PDF requiere gráficos.');
}
const noFiguresConfig = evaluate('buildAnalysisConfig()');
if (noFiguresConfig.generate_figures !== false || noFiguresConfig.generate_pdf !== false) {
  throw new Error('El frontend envía una configuración gráfica/PDF inconsistente.');
}
context.outputWithoutFigures = { ...context.output, figures: [], pdf_bytes: null };
evaluate('displayResults(outputWithoutFigures)');
const renderedWithoutFigures = elements['results-container'].innerHTML;
if (renderedWithoutFigures.includes('tab-graficos') || renderedWithoutFigures.includes("switchTab('graficos'")) {
  throw new Error('La pestaña Gráficos aparece sin figuras.');
}
if (!renderedWithoutFigures.includes('tab-resumen') || !renderedWithoutFigures.includes('tab-consola')) {
  throw new Error('Ocultar gráficos elimina Resumen o Salida tipo consola.');
}
if (!evaluate('runManualAnalysis.toString()').includes('analyzeFile') || !evaluate('analyzeFile.toString()').includes('buildAnalysisConfig')) {
  throw new Error('La entrada manual y CSV no comparten generate_figures.');
}

const css = fs.readFileSync('frontend/css/styles.css', 'utf8');
if (!css.includes('@media (max-width: 700px)') || !css.includes('.comparisons-grid')) {
  throw new Error('Falta soporte responsive básico.');
}
if (!css.includes('.evidence-tooltip-popover.visible') || !css.includes('position: fixed') || !css.includes('calc(100vw - 3rem)')) {
  throw new Error('El tooltip no cubre ratón, teclado y ancho móvil.');
}

console.log('Frontend multivariante: smoke tests correctos.');
