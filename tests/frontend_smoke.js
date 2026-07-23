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
  toggleSpinner: () => {},
  analyzeCsv: async () => {},
  File: class {},
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('frontend/js/calculator.js', 'utf8'), context);
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
    addEventListener() {},
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

for (const group of ['c', 'd', 'e']) element(`manual-group-${group}`);
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
if (evaluate('visibleManualVariantCount') !== 3) throw new Error('Se añaden variantes duplicadas.');

context.window.State.session_id = true;
evaluate('renderCalculatorMain()');
const bayesSidHtml = elements['calculator-main'].innerHTML;
if (!bayesSidHtml.includes('Cargar CSV') || !bayesSidHtml.includes('Introducir datos manualmente')) {
  throw new Error('CSV y entrada manual no aparecen en Bayesiano con Session ID.');
}
if (evaluate('visibleManualVariantCount') !== 0) throw new Error('Cambiar Session ID no reinicia las variantes manuales.');

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
if ((cards.match(/data-is-best="true"/g) || []).length !== 1) throw new Error('Destacado principal inválido.');
if (!cards.includes('A vs B') || !cards.includes('A vs E')) throw new Error('Faltan tarjetas multivariantes.');
if (!cards.includes('> 1.20%') || !cards.includes('< -1.40%')) throw new Error('Intervalos null incorrectos.');
if (/\b(null|NaN|undefined)\b/.test(cards)) throw new Error('Se muestran valores técnicos vacíos.');
if (!cards.includes('Resultado concluyente')) throw new Error('Falta el estado concluyente no seleccionado.');
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

element('results-container');
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
element('chk-ai').checked = false;
element('input-ai-key').value = '';
context.window.State.enfoque = 'frecuentista';
context.window.State.freq_interval_type = 'izquierda';
const config = evaluate('buildAnalysisConfig()');
if (config.freq_interval_type !== 'izquierda') throw new Error('freq_interval_type no se transporta.');
if (config.session_id !== true) throw new Error('session_id no se transporta.');

const css = fs.readFileSync('frontend/css/styles.css', 'utf8');
if (!css.includes('@media (max-width: 700px)') || !css.includes('.comparisons-grid')) {
  throw new Error('Falta soporte responsive básico.');
}
if (!css.includes('.evidence-tooltip-popover.visible') || !css.includes('position: fixed') || !css.includes('calc(100vw - 3rem)')) {
  throw new Error('El tooltip no cubre ratón, teclado y ancho móvil.');
}

console.log('Frontend multivariante: smoke tests correctos.');
