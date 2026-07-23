function renderCalculator() {
  renderSidebar();
  renderCalculatorMain();
}

function renderSidebar() {
  const s = window.State;
  const engineKey = s.selected_engine_key;
  const enfoque = s.enfoque;
  const sidebar = document.getElementById('calculator-sidebar');

  const title = enfoque === 'bayesiano' ? 'Calculadora Bayesiana'
    : enfoque === 'frecuentista' ? 'Calculadora Frecuentista'
    : 'Calculadora';

  let body = `
    <div class="sidebar-title">${title}</div>
    <div class="sidebar-section-title">Configuraci&oacute;n del test</div>
  `;

  body += renderModelExpander(enfoque);
  body += `<div class="sidebar-section-title">Opciones de ejecuci&oacute;n</div>`;
  body += renderExecutionOptions(enfoque);

  if (enfoque === 'bayesiano') {
    body += renderBayesConfig();
  } else if (enfoque === 'frecuentista') {
    body += renderFreqConfig();
  }

  body += `<div class="sidebar-divider"></div>`;
  body += `
    <div class="sidebar-actions">
      <button class="btn btn-secondary" onclick="resetWizard()">Empezar nuevo an&aacute;lisis</button>
      <button class="btn btn-secondary" onclick="resetData()">Cargar nuevos datos</button>
    </div>
  `;

  sidebar.innerHTML = body;

  $$('.expander').forEach(el => {
    const header = el.querySelector('.expander-header');
    header.addEventListener('click', () => {
      el.classList.toggle('open');
    });
  });

  toggleAiKeyInput();
}

function renderModelExpander(enfoque) {
  const modelTxt = enfoque === 'bayesiano' ? 'Bayesiano' : 'Frecuentista';
  const desc = enfoque === 'bayesiano'
    ? 'El enfoque bayesiano interpreta los resultados en t&eacute;rminos de probabilidad directa. En lugar de preguntarse si el resultado es estad&iacute;sticamente significativo, responde: &iquest;cu&aacute;l es la probabilidad de que la variante B sea mejor que la A?<br><br>- No necesitas un tama&ntilde;o de muestra fijo.<br>- An&aacute;lisis de resultados basado en probabilidad.<br>- Decisi&oacute;n m&aacute;s r&aacute;pida: puedes parar el test cuando desees.'
    : 'El enfoque frecuentista comprueba si la diferencia observada podr&iacute;a deberse al azar, respondiendo: &iquest;la diferencia entre A y B es estad&iacute;sticamente significativa? &iquest;podemos rechazar la hip&oacute;tesis nula?<br><br>- Debes calcular previamente la muestra y esperar hasta alcanzarla.<br>- An&aacute;lisis de resultados basado en p-value.';

  return `
    <div class="expander">
      <div class="expander-header">Enfoque Estad&iacute;stico <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">${modelTxt}</div>
        ${desc}
      </div>
    </div>
  `;
}

function renderExecutionOptions(enfoque) {
  return `
    <div class="checkbox-group">
      <label class="checkbox-item">
        <input type="checkbox" id="chk-pdf"> Generar PDF
      </label>
      <label class="checkbox-item">
        <input type="checkbox" id="chk-ai" checked onchange="toggleAiKeyInput()"> Interpretaci&oacute;n IA (OpenAI)
      </label>
    </div>
    <div id="ai-key-row" class="ai-key-row">
      <label class="input-label">OpenAI API Key</label>
      <input type="password" id="input-ai-key" class="form-input" placeholder="sk-..." autocomplete="off">
    </div>
  `;
}

function renderBayesConfig() {
  const s = window.State;
  const tv = s.tipo_valores === '0_1'
    ? { label: 'Conversi&oacute;n &uacute;nica (Beta-Binomial)', desc: 'Los usuarios pueden convertir s&oacute;lo una vez. Se analizar&aacute; mediante la distribuci&oacute;n previa <b>Beta</b>, ideal para conversiones donde <b>0</b> = no convierte y <b>1</b> = convierte en la sesi&oacute;n.' }
    : { label: 'Conversiones m&uacute;ltiples (Gamma-Poisson)', desc: 'Se analizar&aacute; mediante la distribuci&oacute;n previa <b>Gamma-Poisson</b>, adecuada para conteos de m&eacute;tricas donde un usuario puede convertir m&aacute;s de una vez.' };

  const sidTxt = s.session_id ? 'Con Session ID' : 'Sin Session ID';
  const sidDesc = s.session_id
    ? 'Analizar&aacute;s tu test A/B <b>con Session ID</b>. El CSV de tu test A/B deber&aacute; contener una columna con los Session ID de cada sesi&oacute;n.'
    : 'Analizar&aacute;s tu test A/B <b>sin Session ID</b>. El an&aacute;lisis se realizar&aacute; utilizando eventos y sesiones agregados.';

  return `
    <div class="expander">
      <div class="expander-header">Tipo de conversiones <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">${tv.label}</div>
        ${tv.desc}
      </div>
    </div>
    <div class="expander">
      <div class="expander-header">Nivel de confianza <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">95% (Default)</div>
        Es el umbral de probabilidad de que la variante sea mejor que el control. Un intervalo de credibilidad del <b>95%</b> es el m&aacute;s com&uacute;n y significa que, dados los datos y el modelo, existe un 95% de probabilidad de que el verdadero par&aacute;metro est&eacute; dentro de ese rango.
      </div>
    </div>
    <div class="expander">
      <div class="expander-header">Unidad de an&aacute;lisis <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">${sidTxt}</div>
        ${sidDesc}
      </div>
    </div>
  `;
}

function renderFreqConfig() {
  const s = window.State;
  const intervalMap = { centrado: 'Two-Tailed', derecha: 'One-Tailed', izquierda: 'One-Tailed' };
  const intervalTxt = { centrado: 'IC Centrado', derecha: 'Cola derecha', izquierda: 'Cola izquierda' };
  const tipo = intervalMap[s.freq_interval_type];
  const dirTxt = s.freq_interval_type === 'derecha' ? 'Mejora (cola derecha)' : s.freq_interval_type === 'izquierda' ? 'Empeora (cola izquierda)' : '';

  const sidTxt = s.session_id ? 'Con Session ID' : 'Sin Session ID';
  const sidDesc = s.session_id
    ? 'Analizar&aacute;s tu test A/B <b>con Session ID</b>.'
    : 'Analizar&aacute;s tu test A/B <b>sin Session ID</b>.';

  let dirHtml = '';
  if (dirTxt) {
    const dirDesc = s.freq_interval_type === 'derecha'
      ? 'Se eval\u00faa si el valor de la m\u00e9trica en la variante es mayor que en el control, seg\u00fan el criterio definido para el experimento.'
      : 'Se eval\u00faa si el valor de la m\u00e9trica en la variante es menor que en el control, seg\u00fan el criterio definido para el experimento.';
    dirHtml = `
      <div class="expander">
        <div class="expander-header">Direcci&oacute;n de hip&oacute;tesis <span class="arrow">&#9660;</span></div>
        <div class="expander-body">
          <div class="dd-value">${dirTxt}</div>
          ${dirDesc}
        </div>
      </div>
    `;
  }

  return `
    <div class="expander">
      <div class="expander-header">Tipo de hip&oacute;tesis <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">${tipo}</div>
        ${tipo === 'Two-Tailed'
          ? 'Se analiza cualquier diferencia, tanto mejora como empeoramiento. Este enfoque eval\u00faa si existe un efecto estad\u00edsticamente significativo sin asumir de antemano el sentido del cambio.'
          : 'Se analiza \u00fanicamente una diferencia en una direcci\u00f3n espec\u00edfica, ya sea mejorar o empeorar la m\u00e9trica objetivo. En caso de seleccionar One-Tailed, en el siguiente paso se indicar\u00e1 si el an\u00e1lisis debe detectar una mejora o un empeoramiento de la m\u00e9trica.'}
      </div>
    </div>
    ${dirHtml}
    <div class="expander">
      <div class="expander-header">Nivel de confianza <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">95% (Default)</div>
        Es el umbral que determina si el resultado es estad&iacute;sticamente significativo. Con un nivel de confianza del <b>95%</b> (&alpha; = 0.05), rechazamos la hip&oacute;tesis nula cuando el p-value es inferior a 0.05.
      </div>
    </div>
    <div class="expander">
      <div class="expander-header">Unidad de an&aacute;lisis <span class="arrow">&#9660;</span></div>
      <div class="expander-body">
        <div class="dd-value">${sidTxt}</div>
        ${sidDesc}
      </div>
    </div>
  `;
}

function renderCalculatorMain() {
  const main = document.getElementById('calculator-main');
  const allowsCsv = window.State.enfoque === 'bayesiano';
  visibleManualVariantCount = 0;

  const csvPanel = allowsCsv ? `
    <div id="method-csv">
      <p class="sub-header">Cargar datos desde CSV</p>
      <div class="hint-row">
        <span style="font-size:18px;">💡</span>
        <span>Sube un CSV con el formato requerido.</span>
        <button class="btn-link" onclick="openCsvModal()">Ver ejemplo de formato</button>
      </div>
      <div class="subsection-spacer"></div>
      <div class="file-upload-zone" id="upload-zone">
        <div class="upload-icon">📂</div>
        <div class="upload-text">Arrastra y suelta tu archivo aqu&iacute;</div>
        <div class="upload-hint">L&iacute;mite 200 MB por archivo &bull; CSV</div>
        <button class="upload-btn" onclick="document.getElementById('csv-file-input').click()">Adjuntar</button>
        <input type="file" id="csv-file-input" accept=".csv">
      </div>
      <div id="csv-preview"></div>
    </div>
  ` : '';

  const introText = allowsCsv
    ? 'Sube un archivo CSV con el formato indicado o introduce los datos manualmente para analizar tu test A/B.'
    : 'Introduce los datos manualmente para analizar tu test A/B.';

  main.innerHTML = `
    <h2 class="main-header">Calculadora para Tests A/B</h2>
    <div class="info-box">
      Esta herramienta te permite analizar los resultados de tus tests A/B usando modelos estad&iacute;sticos bayesianos o frecuentistas. Adem&aacute;s, te ayudaremos a la interpretaci&oacute;n de los resultados mediante Inteligencia Artificial. ${introText}
    </div>
    <div class="section-spacer"></div>
    ${allowsCsv ? renderInputMethodTabs() : ''}
    ${csvPanel}
    ${renderManualEntryPanel(!allowsCsv)}
    <div id="results-container"></div>
  `;

  if (allowsCsv) setupFileUpload();
}

function renderInputMethodTabs() {
  return `
    <div class="tabs" id="input-method-tabs">
      <button class="tab active" id="tab-method-csv" onclick="selectInputMethod('csv')">Cargar CSV</button>
      <button class="tab" id="tab-method-manual" onclick="selectInputMethod('manual')">Introducir datos manualmente</button>
    </div>
  `;
}

function renderManualEntryPanel(isVisible = false) {
  const groups = ['A', 'B', 'C', 'D', 'E'];
  const cards = groups.map(group => {
    const isInitiallyHidden = MANUAL_OPTIONAL_VARIANTS.includes(group);
    return `
    <div id="manual-group-${group.toLowerCase()}" class="manual-entry-group ${group === 'A' ? 'manual-control' : ''}"${isInitiallyHidden ? ' style="display:none;"' : ''}>
      <div class="manual-entry-title">${group === 'A' ? 'Grupo A (Control)' : `Variante ${group}`}</div>
      <label class="input-label" for="manual-${group.toLowerCase()}-visitas">Usuarios / sesiones</label>
      <input type="number" min="0" step="1" id="manual-${group.toLowerCase()}-visitas" class="form-input" placeholder="${group === 'A' || group === 'B' ? 'Ej. 2800' : 'Dejar vacío si no se usa'}">
      <label class="input-label" for="manual-${group.toLowerCase()}-conv">Conversiones</label>
      <input type="number" min="0" step="1" id="manual-${group.toLowerCase()}-conv" class="form-input" placeholder="${group === 'A' || group === 'B' ? 'Ej. 580' : 'Dejar vacío si no se usa'}">
    </div>
  `;
  }).join('');
  return `
    <div id="method-manual"${isVisible ? '' : ' style="display:none;"'}>
      <p class="sub-header">Introducir datos manualmente</p>
      <div class="hint-row">
        <span style="font-size:18px;">✍️</span>
        <span>Introduce el control A y entre una y cuatro variantes. Las variantes vacías no se enviarán.</span>
      </div>
      <div class="subsection-spacer"></div>
      <div class="manual-entry-grid">
        ${cards}
      </div>
      <div class="btn-row" id="add-manual-variant-row" style="justify-content:center;">
        <button class="btn btn-secondary" onclick="addManualVariant()">A&ntilde;adir variante</button>
      </div>
      <div class="btn-row" style="justify-content:center;">
        <button class="btn btn-primary" onclick="runManualAnalysis()">Analizar experimento</button>
      </div>
    </div>
  `;
}

const MANUAL_OPTIONAL_VARIANTS = ['C', 'D', 'E'];
let visibleManualVariantCount = 0;

function addManualVariant() {
  if (visibleManualVariantCount >= MANUAL_OPTIONAL_VARIANTS.length) return;

  const group = MANUAL_OPTIONAL_VARIANTS[visibleManualVariantCount];
  const card = document.getElementById(`manual-group-${group.toLowerCase()}`);
  if (card) card.style.display = '';
  visibleManualVariantCount += 1;

  if (visibleManualVariantCount === MANUAL_OPTIONAL_VARIANTS.length) {
    const addRow = document.getElementById('add-manual-variant-row');
    if (addRow) addRow.style.display = 'none';
  }
}

function selectInputMethod(method) {
  if (window.State.enfoque !== 'bayesiano') method = 'manual';
  const csv = document.getElementById('method-csv');
  const manual = document.getElementById('method-manual');
  const tabCsv = document.getElementById('tab-method-csv');
  const tabManual = document.getElementById('tab-method-manual');
  const isManual = method === 'manual';

  if (csv) csv.style.display = isManual ? 'none' : '';
  if (manual) manual.style.display = isManual ? '' : 'none';
  if (tabCsv) tabCsv.classList.toggle('active', !isManual);
  if (tabManual) tabManual.classList.toggle('active', isManual);

  const results = document.getElementById('results-container');
  if (results) results.innerHTML = '';
}

let uploadedCsvFile = null;
let uploadedCsvData = null;

function setupFileUpload() {
  const input = document.getElementById('csv-file-input');
  const zone = document.getElementById('upload-zone');

  input.addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  zone.addEventListener('dragover', function(e) {
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', function() {
    zone.classList.remove('dragover');
  });

  zone.addEventListener('drop', function(e) {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  });
}

function handleFile(file) {
  if (!file.name.endsWith('.csv')) {
    showError('Solo se permiten archivos CSV.');
    return;
  }

  uploadedCsvFile = file;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    const lines = text.split('\n').filter(l => l.trim());
    if (lines.length === 0) {
      showError('El CSV está vacío.');
      return;
    }
    const headers = lines[0].split(',').map(h => h.trim());
    const validationError = validateCsvHeaders(headers);
    if (validationError) {
      uploadedCsvFile = null;
      document.getElementById('csv-preview').innerHTML = '';
      showError(validationError);
      return;
    }

    let tableHtml = '<div class="section-spacer"></div><div class="success-box">✅ \u00a1Archivo cargado correctamente!</div>';
    tableHtml += '<p style="font-weight:600;margin-bottom:0.5rem;">Vista previa de tus datos:</p>';
    tableHtml += '<table class="data-table"><thead><tr>';
    headers.forEach(h => { tableHtml += `<th>${escapeHtml(h)}</th>`; });
    tableHtml += '</tr></thead><tbody>';

    const maxRows = Math.min(lines.length - 1, 10);
    for (let i = 1; i <= maxRows; i++) {
      const cols = lines[i].split(',').map(c => c.trim());
      tableHtml += '<tr>';
      cols.forEach(c => { tableHtml += `<td>${escapeHtml(c)}</td>`; });
      tableHtml += '</tr>';
    }
    tableHtml += '</tbody></table>';
    tableHtml += `<div class="btn-row" style="justify-content:center;">
      <button class="btn btn-primary" onclick="runAnalysis()">Analizar experimento</button>
    </div>`;

    document.getElementById('csv-preview').innerHTML = tableHtml;
    document.getElementById('results-container').innerHTML = '';
  };
  reader.readAsText(file);
}

function toggleAiKeyInput() {
  const chkAi = document.getElementById('chk-ai');
  const row = document.getElementById('ai-key-row');
  if (row) {
    row.style.display = chkAi && chkAi.checked ? 'flex' : 'none';
  }
}

function buildAnalysisConfig() {
  const generatePdf = document.getElementById('chk-pdf') ? document.getElementById('chk-pdf').checked : false;
  const includeAi = document.getElementById('chk-ai') ? document.getElementById('chk-ai').checked : false;
  const openaiApiKey = document.getElementById('input-ai-key') ? document.getElementById('input-ai-key').value.trim() : '';

  const config = {
    generate_pdf: generatePdf,
    include_ai: includeAi,
    openai_api_key: openaiApiKey,
    session_id: Boolean(window.State.session_id),
  };

  if (window.State.enfoque === 'bayesiano') {
    config.num_samples = 20000;
  } else {
    config.n_iteraciones = 10000;
    config.freq_interval_type = window.State.freq_interval_type || 'centrado';
  }

  return config;
}

async function analyzeFile(file, engineKey) {
  toggleSpinner(true);
  try {
    const result = await analyzeCsv(file, engineKey, buildAnalysisConfig());
    window.State.outputs = result;
    window.State.datos_procesados = true;
    toggleSpinner(false);
    displayResults(result);
  } catch (err) {
    toggleSpinner(false);
    showError(`Error ejecutando el motor: ${err.message}`);
  }
}

async function runAnalysis() {
  if (!uploadedCsvFile) {
    showError('No hay archivo CSV cargado.');
    return;
  }

  const engineKey = window.State.selected_engine_key;
  if (!engineKey) {
    showError('No hay motor seleccionado. Vuelve al wizard.');
    return;
  }

  await analyzeFile(uploadedCsvFile, engineKey);
}

function validateCsvHeaders(headers) {
  const headerSet = new Set(headers);
  const canonical = ['A', 'B', 'C', 'D', 'E'].filter(group => headerSet.has(`Conversiones ${group}`));
  const legacy = ['A', 'B', 'C', 'D', 'E'].filter(group => headerSet.has(group));
  const sessionMode = Boolean(window.State.session_id);

  if (sessionMode && canonical.length && legacy.length) {
    return 'No mezcles columnas canónicas “Conversiones X” con columnas heredadas “A”, “B”, etc.';
  }
  const invalidVariants = headers.filter(header => {
    const match = header.match(/^(?:Visitas|Conversiones)\s+(.+)$/i);
    return match && !['A', 'B', 'C', 'D', 'E'].includes(match[1].toUpperCase());
  });
  if (invalidVariants.length) return 'Solo se admiten variantes entre B y E.';

  if (sessionMode) {
    const groups = canonical.length ? canonical : legacy;
    if (!groups.includes('A')) return 'Falta el grupo control A en el CSV.';
    if (!groups.some(group => group !== 'A')) return 'Debe existir al menos una variante entre B y E.';
    if (canonical.length && !headerSet.has('Día')) return 'El formato recomendado con Session ID debe incluir la columna Día.';
    if (canonical.length && !headerSet.has('SessionID')) return 'El formato con Session ID debe incluir la columna SessionID.';
    return '';
  }

  if (!headerSet.has('Visitas A') || !headerSet.has('Conversiones A')) {
    return 'Faltan “Visitas A” o “Conversiones A” para el grupo control.';
  }
  const variants = ['B', 'C', 'D', 'E'].filter(group => headerSet.has(`Visitas ${group}`) || headerSet.has(`Conversiones ${group}`));
  if (!variants.length) return 'Debe existir al menos una variante entre B y E.';
  for (const group of variants) {
    if (!headerSet.has(`Visitas ${group}`) || !headerSet.has(`Conversiones ${group}`)) {
      return `La variante ${group} necesita las columnas “Visitas ${group}” y “Conversiones ${group}”.`;
    }
  }
  return '';
}

// Construye únicamente las columnas de los grupos utilizados.
function buildManualCsv(engineKey, groups) {
  if (window.State.session_id) {
    const headers = ['Día', 'SessionID', ...groups.map(item => `Conversiones ${item.group}`)];
    const lines = [headers.join(',')];
    groups.forEach(item => {
      const baseConversions = Math.floor(item.conversions / item.visits);
      const remainder = item.conversions % item.visits;
      for (let i = 0; i < item.visits; i++) {
        const sessionConversions = baseConversions + (i < remainder ? 1 : 0);
        const values = groups.map(candidate => candidate.group === item.group ? sessionConversions : '');
        lines.push(['1', `${item.group}-${i + 1}`, ...values].join(','));
      }
    });
    return lines.join('\n') + '\n';
  }
  const headers = ['Día'];
  const values = ['1'];
  groups.forEach(item => {
    headers.push(`Visitas ${item.group}`, `Conversiones ${item.group}`);
    values.push(item.visits, item.conversions);
  });
  return `${headers.join(',')}\n${values.join(',')}\n`;
}

function readManualGroups() {
  const groups = [];
  const allowsMultipleConversions = window.State.enfoque === 'bayesiano' && window.State.tipo_valores === '0_inf';
  const visibleGroups = ['A', 'B', ...MANUAL_OPTIONAL_VARIANTS.slice(0, visibleManualVariantCount)];
  for (const group of visibleGroups) {
    const visitsRaw = document.getElementById(`manual-${group.toLowerCase()}-visitas`).value.trim();
    const conversionsRaw = document.getElementById(`manual-${group.toLowerCase()}-conv`).value.trim();
    if (!visitsRaw && !conversionsRaw && group !== 'A') continue;
    if (!visitsRaw || !conversionsRaw) throw new Error(`Completa usuarios y conversiones del grupo ${group}, o deja ambos campos vacíos.`);
    const visits = Number(visitsRaw);
    const conversions = Number(conversionsRaw);
    if (!Number.isInteger(visits) || visits <= 0) throw new Error(`Los usuarios / sesiones de ${group} deben ser un entero mayor que 0.`);
    if (!Number.isInteger(conversions) || conversions < 0) throw new Error(`Las conversiones de ${group} deben ser un entero igual o mayor que 0.`);
    if (!allowsMultipleConversions && conversions > visits) {
      throw new Error(`Las conversiones de ${group} no pueden superar sus usuarios / sesiones.`);
    }
    groups.push({ group, visits, conversions });
  }
  if (!groups.some(item => item.group === 'A')) throw new Error('El grupo control A es obligatorio.');
  if (!groups.some(item => item.group !== 'A')) throw new Error('Introduce al menos una variante entre B y E.');
  return groups;
}
async function runManualAnalysis() {
  const engineKey = window.State.selected_engine_key;
  if (!engineKey) {
    showError('No hay motor seleccionado. Vuelve al wizard.');
    return;
  }

  let groups;
  try {
    groups = readManualGroups();
  } catch (error) {
    showError(error.message);
    return;
  }
  const csv = buildManualCsv(engineKey, groups);
  const file = new File([csv], 'datos_manuales.csv', { type: 'text/csv' });

  await analyzeFile(file, engineKey);
}

function isBayesEngine() {
  const k = window.State.selected_engine_key;
  return k && k.startsWith('bayes_');
}

function isFreqEngine() {
  const k = window.State.selected_engine_key;
  return k && k.startsWith('freq_');
}

function isPvalueEngine() {
  const k = window.State.selected_engine_key;
  return k && k.startsWith('freq_pvalue');
}

function displayResults(out) {
  const container = document.getElementById('results-container');
  let html = '<div class="section-spacer"></div><hr><div class="section-spacer"></div>';
  html += '<h2 class="main-header">Resultados</h2>';
  html += renderSrmBanner(out.srm);

  const comparisons = Array.isArray(out.comparisons) ? out.comparisons : [];
  const best = comparisons.filter(item => item && item.is_best === true);
  if (!comparisons.length) {
    container.innerHTML = html + '<div class="error-box"><b>No se recibieron comparativas.</b><br>El backend debe devolver al menos una comparación de una variante contra A.</div>';
    return;
  }
  if (best.length > 1) {
    container.innerHTML = html + '<div class="error-box"><b>Respuesta inconsistente.</b><br>El backend ha marcado más de una variante como mejor resultado.</div>';
    return;
  }

  html += renderSelectionOverview(comparisons);
  html += renderComparisonCards(comparisons, out.summary || []);

  const hasSummary = Array.isArray(out.summary) && out.summary.length > 0;
  const hasConsole = hasSummary;
  const hasLog = typeof out.log_text === 'string' && out.log_text.trim() !== '';
  const hasFigs = out.figures && out.figures.length > 0;
  const hasPdf = out.pdf_bytes;

  if (hasLog) html += renderLogTab(out);

  const tabs = [];
  if (hasSummary) tabs.push('resumen');
  if (hasConsole) tabs.push('consola');
  if (hasFigs) tabs.push('graficos');
  if (hasPdf) tabs.push('pdf');

  if (tabs.length > 0) {
    html += '<div class="tabs" id="result-tabs">';
    const tabLabels = {
      resumen: 'Resumen',
      consola: 'Salida tipo consola',
      graficos: 'Gr\u00e1ficos',
      pdf: 'Reporte'
    };
    tabs.forEach((t, i) => {
      html += `<button class="tab ${i === 0 ? 'active' : ''}" onclick="switchTab('${t}', this)">${tabLabels[t] || t}</button>`;
    });
    html += '</div>';
  }

  tabs.forEach((t, i) => {
    html += `<div class="tab-content ${i === 0 ? 'active' : ''}" id="tab-${t}">`;
    if (t === 'resumen') html += renderSummaryTab(out);
    else if (t === 'consola') html += renderConsoleTab(out);
    else if (t === 'graficos') html += renderFiguresTab(out);
    else if (t === 'pdf') html += renderPdfTab(out);
    html += '</div>';
  });

  container.innerHTML = html;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function formatSrmPValue(value) {
  const number = finiteNumber(value);
  if (number === null) return '—';
  if (number > 0 && number < 0.000001) return number.toExponential(2);
  return number.toFixed(6);
}

function renderSrmBanner(srm) {
  if (!srm || typeof srm !== 'object') {
    return `
      <section class="srm-banner srm-unavailable" role="status" aria-label="Chequeo SRM no disponible">
        <div><h3>Chequeo SRM no disponible</h3><p>Esta respuesta no incluye información sobre el reparto de la muestra.</p></div>
      </section>`;
  }

  const hasSrm = srm.has_srm === true;
  const title = hasSrm ? 'Se detectó SRM' : 'No se detectó SRM';
  const description = hasSrm
    ? 'Se ha detectado Sample Ratio Mismatch (SRM) en el experimento. El número de usuarios asignados a cada variante es significativamente diferente del esperado. Un SRM suele indicar errores en la asignación de tráfico, el tracking o un fallo en tu herramienta de testing, y puede invalidar las conclusiones del test.'
    : 'La asignación de usuarios entre variantes coincide con la proporción esperada. No hay evidencias de problemas en el reparto de la muestra.';
  return `
    <section class="srm-banner ${hasSrm ? 'srm-detected' : 'srm-clear'}" role="status" aria-label="${title}">
      <div>
        <h3>${title}</h3>
        <p>${description}</p>
        <div class="srm-metrics"><span>p-value SRM: <b>${formatSrmPValue(srm.p_value)}</b></span><span>alpha: <b>${formatNumber(srm.alpha, 4)}</b></span></div>
      </div>
    </section>`;
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function formatNumber(value, decimals = 4) {
  const number = finiteNumber(value);
  return number === null ? '—' : number.toFixed(decimals);
}

function formatPercentValue(value, decimals = 2) {
  const number = finiteNumber(value);
  return number === null ? '—' : `${number.toFixed(decimals)}%`;
}

function formatRateOrMean(value) {
  return formatNumber(value, 4);
}

function formatInterval(interval) {
  if (!interval || typeof interval !== 'object') return '—';
  const low = finiteNumber(interval.low);
  const high = finiteNumber(interval.high);
  if (low !== null && high === null) return `> ${low.toFixed(2)}%`;
  if (low === null && high !== null) return `< ${high.toFixed(2)}%`;
  if (low !== null && high !== null) return `[${low.toFixed(2)}%, ${high.toFixed(2)}%]`;
  return '—';
}

function evidenceLabel(comparison) {
  const variant = escapeHtml(comparison.variant || '—');
  const name = comparison.evidence && comparison.evidence.name;
  if (name === 'probability_superiority') return `Probabilidad de que ${variant} supere al control`;
  if (name === 'level_of_significance') return `Nivel de significancia de que ${variant} supere al control`;
  return 'p-value';
}

const P_VALUE_TOOLTIP_TEXT = 'Indica la probabilidad de que la diferencia observada entre las variantes no se debe al azar. Un p-value inferior al nivel de significancia (0,05 en este caso) sugiere que la diferencia observada es estadísticamente significativa.';

function renderEvidenceLabel(comparison, index) {
  const label = evidenceLabel(comparison);
  if (!comparison.evidence || comparison.evidence.name !== 'p_value') return label;

  return `<span class="evidence-label">${label}<span class="evidence-tooltip">
    <button type="button" class="evidence-tooltip-trigger" aria-label="Información sobre p-value: ${P_VALUE_TOOLTIP_TEXT}" aria-describedby="evidence-tooltip-popover" aria-expanded="false" data-tooltip="${P_VALUE_TOOLTIP_TEXT}" onmouseenter="showEvidenceTooltip(event)" onmouseleave="hideEvidenceTooltip(event)" onfocus="showEvidenceTooltip(event)" onblur="hideEvidenceTooltip(event)" onclick="toggleEvidenceTooltip(event)">i</button>
  </span></span>`;
}

function getEvidenceTooltipPopover() {
  let tooltip = document.getElementById('evidence-tooltip-popover');
  if (tooltip) return tooltip;

  tooltip = document.createElement('div');
  tooltip.id = 'evidence-tooltip-popover';
  tooltip.className = 'evidence-tooltip-popover';
  tooltip.setAttribute('role', 'tooltip');
  document.body.appendChild(tooltip);
  return tooltip;
}

function positionEvidenceTooltip(trigger, tooltip) {
  const triggerRect = trigger.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  const viewportWidth = document.documentElement.clientWidth;
  let left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;
  left = Math.max(8, Math.min(left, viewportWidth - tooltipRect.width - 8));
  let top = triggerRect.top - tooltipRect.height - 10;
  if (top < 8) top = triggerRect.bottom + 10;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function showEvidenceTooltip(event) {
  const trigger = event.currentTarget;
  const tooltip = getEvidenceTooltipPopover();
  tooltip.textContent = trigger.dataset.tooltip;
  tooltip.classList.add('visible');
  trigger.setAttribute('aria-expanded', 'true');
  positionEvidenceTooltip(trigger, tooltip);
}

function hideEvidenceTooltip(event) {
  const tooltip = document.getElementById('evidence-tooltip-popover');
  if (tooltip) tooltip.classList.remove('visible');
  if (event && event.currentTarget) event.currentTarget.setAttribute('aria-expanded', 'false');
}

function toggleEvidenceTooltip(event) {
  event.preventDefault();
  const tooltip = document.getElementById('evidence-tooltip-popover');
  if (tooltip && tooltip.classList.contains('visible')) {
    hideEvidenceTooltip(event);
  } else {
    showEvidenceTooltip(event);
  }
}

function evidenceValue(comparison) {
  const name = comparison.evidence && comparison.evidence.name;
  const value = comparison.evidence && comparison.evidence.value;
  return name === 'p_value' ? formatNumber(value, 4) : formatPercentValue(finiteNumber(value) === null ? null : Number(value) * 100, 2);
}

function renderSelectionOverview(comparisons) {
  const selected = comparisons.find(item => item.is_best === true);
  if (!selected) {
    return '<div class="selection-overview selection-none"><span class="selection-icon" aria-hidden="true">○</span><div><b>No hay una variante ganadora concluyente</b><span>Ninguna comparación favorable ha sido seleccionada.</span></div></div>';
  }
  const variant = escapeHtml(selected.variant);
  if (selected.selection_label === 'Ganadora') {
    return `<div class="selection-overview selection-winner"><span class="selection-icon" aria-hidden="true">★</span><div><b>Variante ganadora: ${variant}</b><span>Cumple los criterios estadísticos del modelo.</span></div></div>`;
  }
  return `<div class="selection-overview selection-candidate"><span class="selection-icon" aria-hidden="true">◇</span><div><b>Mejor candidata: ${variant}, resultado todavía no concluyente</b><span>Es la mejor comparación favorable, pero no alcanza todos los criterios de ganadora.</span></div></div>`;
}

function summaryForVariant(summary, variant) {
  return summary.find(row => String(row.variant || row.grupo_B_col || '') === String(variant)) || {};
}

function renderComparisonCards(comparisons, summary) {
  const cards = comparisons.map((comparison, index) => {
    const row = summaryForVariant(summary, comparison.variant);
    const metrics = comparison.metrics || {};
    const classes = comparison.is_best
      ? comparison.selection_label === 'Ganadora' ? 'comparison-winner' : 'comparison-candidate'
      : comparison.comparison_status === 'Ganadora' ? 'comparison-conclusive' : 'comparison-neutral';
    const badge = comparison.is_best
      ? comparison.selection_label
      : comparison.comparison_status === 'Ganadora' ? 'Resultado concluyente' : 'Sin ganador concluyente';
    const visitsA = row.n_visitas_A ?? row.n_A;
    const visitsVariant = row.n_visitas_B ?? row.n_B;
    const conversionsA = row.conv_A;
    const conversionsVariant = row.conv_B;
    const detailItems = [];
    if (finiteNumber(visitsA) !== null) detailItems.push(`<span><b>Observaciones A</b>${formatNumber(visitsA, 0)}</span>`);
    if (finiteNumber(visitsVariant) !== null) detailItems.push(`<span><b>Observaciones ${escapeHtml(comparison.variant)}</b>${formatNumber(visitsVariant, 0)}</span>`);
    if (finiteNumber(conversionsA) !== null) detailItems.push(`<span><b>Conversiones A</b>${formatNumber(conversionsA, 0)}</span>`);
    if (finiteNumber(conversionsVariant) !== null) detailItems.push(`<span><b>Conversiones ${escapeHtml(comparison.variant)}</b>${formatNumber(conversionsVariant, 0)}</span>`);
    if (finiteNumber(metrics.z_score) !== null) detailItems.push(`<span><b>Z-score</b>${formatNumber(metrics.z_score, 4)}</span>`);
    if (finiteNumber(metrics.se_control) !== null) detailItems.push(`<span><b>EE control</b>${formatNumber(metrics.se_control, 4)}</span>`);
    if (finiteNumber(metrics.se_variante) !== null) detailItems.push(`<span><b>EE variante</b>${formatNumber(metrics.se_variante, 4)}</span>`);
    if (finiteNumber(metrics.se_diferencia) !== null) detailItems.push(`<span><b>EE diferencia</b>${formatNumber(metrics.se_diferencia, 4)}</span>`);
    return `
      <article class="comparison-card ${classes}" data-variant="${escapeHtml(comparison.variant)}" data-is-best="${comparison.is_best === true}">
        <div class="comparison-card-header">
          <div><span class="comparison-kicker">Comparación</span><h3>A vs ${escapeHtml(comparison.variant)}</h3></div>
          <span class="comparison-badge">${escapeHtml(badge || 'Sin ganador concluyente')}</span>
        </div>
        <div class="comparison-core">
          <div><span>Control A · tasa/media</span><strong>${formatRateOrMean(comparison.control_value)}</strong></div>
          <div><span>Variante ${escapeHtml(comparison.variant)} · tasa/media</span><strong>${formatRateOrMean(comparison.variant_value)}</strong></div>
          <div><span>Uplift</span><strong>${formatPercentValue(comparison.uplift_pct)}</strong></div>
          <div><span>${renderEvidenceLabel(comparison, index)}</span><strong>${evidenceValue(comparison)}</strong></div>
        </div>
        <div class="comparison-interval"><span>Intervalo ${escapeHtml((comparison.interval && comparison.interval.name) || '')}</span><strong>${formatInterval(comparison.interval)}</strong></div>
        ${detailItems.length ? `<div class="comparison-details">${detailItems.join('')}</div>` : ''}
      </article>`;
  }).join('');
  return `<section class="comparisons-section" aria-label="Comparaciones contra el control"><div class="comparisons-grid">${cards}</div></section>`;
}

function renderSummaryTab(out) {
  let html = '<h3>Resumen</h3>';

  const keys = [...new Set(out.summary.flatMap(row => Object.keys(row)))];

  html += '<div class="table-scroll"><table class="data-table"><thead><tr>';
  keys.forEach(k => { html += `<th>${escapeHtml(k)}</th>`; });
  html += '</tr></thead><tbody>';

  out.summary.forEach(row => {
    html += '<tr>';
    keys.forEach(k => {
      let val = row[k];
      if (val === null || val === undefined || (typeof val === 'number' && !Number.isFinite(val))) val = '—';
      else if (typeof val === 'number') val = val.toFixed(4);
      html += `<td>${escapeHtml(val)}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';

  return html;
}

function renderConsoleTab(out) {
  let html = '<h3>Salida tipo consola</h3>';
  const blocks = out.comparisons.map(comparison => {
    const row = summaryForVariant(out.summary, comparison.variant);
    const metrics = comparison.metrics || {};
    const lines = [
      '==================================================',
      `                 ANÁLISIS ${comparison.variant} vs A`,
      '==================================================',
      `Control A · tasa/media: ${formatRateOrMean(comparison.control_value)}`,
      `Variante ${comparison.variant} · tasa/media: ${formatRateOrMean(comparison.variant_value)}`,
    ];
    const nA = row.n_visitas_A ?? row.n_A;
    const nVariant = row.n_visitas_B ?? row.n_B;
    if (finiteNumber(nA) !== null) lines.push(`Observaciones A: ${formatNumber(nA, 0)} | Observaciones ${comparison.variant}: ${formatNumber(nVariant, 0)}`);
    if (finiteNumber(row.conv_A) !== null) lines.push(`Conversiones A: ${formatNumber(row.conv_A, 0)} | Conversiones ${comparison.variant}: ${formatNumber(row.conv_B, 0)}`);
    lines.push('--------------------------------------------------');
    lines.push(`UPLIFT: ${formatPercentValue(comparison.uplift_pct)}`);
    lines.push(`${evidenceLabel(comparison).toUpperCase()}: ${evidenceValue(comparison)}`);
    lines.push(`INTERVALO: ${formatInterval(comparison.interval)}`);
    if (finiteNumber(metrics.z_score) !== null) lines.push(`Z-SCORE: ${formatNumber(metrics.z_score, 4)}`);
    if (finiteNumber(metrics.se_control) !== null) lines.push(`ERROR ESTÁNDAR CONTROL: ${formatNumber(metrics.se_control, 4)}`);
    if (finiteNumber(metrics.se_variante) !== null) lines.push(`ERROR ESTÁNDAR VARIANTE: ${formatNumber(metrics.se_variante, 4)}`);
    if (finiteNumber(metrics.se_diferencia) !== null) lines.push(`ERROR ESTÁNDAR DIFERENCIA: ${formatNumber(metrics.se_diferencia, 4)}`);
    lines.push(`ESTADO INDIVIDUAL: ${comparison.comparison_status || 'Sin ganador concluyente'}`);
    if (comparison.is_best) lines.push(`DESTACADO PRINCIPAL: ${comparison.selection_label}`);
    lines.push('==================================================');
    return `<div class="code-block">${escapeHtml(lines.join('\n'))}</div>`;
  });
  return html + blocks.join('');
}

function renderLogTab(out) {
  if (out.log_text) {
    return `<section class="ai-interpretation"><div class="ai-heading"><span aria-hidden="true">IA</span><h3>Interpretación IA</h3></div>
      <div class="code-block">${escapeHtml(out.log_text)}</div></section>`;
  }
  return '';
}

function renderFiguresTab(out) {
  if (!out.figures || out.figures.length === 0) return '';
  let html = '<h3>Gr\u00e1ficos</h3>';
  out.figures.forEach((fig, i) => {
    html += `<div class="figure-container">
      <img src="data:image/png;base64,${fig}" alt="Gr\u00e1fico ${i+1}">
    </div>`;
  });
  return html;
}

function renderPdfTab(out) {
  if (!out.pdf_bytes) return '';
  return `<h3>Reporte</h3>
    <button class="btn-download" onclick="downloadPdf('${out.pdf_bytes}', 'reporte-multivariante.pdf')">
      📄 Descargar PDF
    </button>`;
}

function switchTab(tabId, btn) {
  $$('.tab').forEach(t => t.classList.remove('active'));
  $$('.tab-content').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.add('active');
}

function resetWizard() {
  window.State = createInitialState();
  document.getElementById('calculator-section').style.display = 'none';
  document.getElementById('wizard-section').style.display = '';
  showStep(1);
}

function resetData() {
  window.State.outputs = null;
  window.State.datos_procesados = false;
  uploadedCsvFile = null;
  uploadedCsvData = null;
  const csvPreview = document.getElementById('csv-preview');
  const results = document.getElementById('results-container');
  if (csvPreview) csvPreview.innerHTML = '';
  if (results) results.innerHTML = '';
  showSuccess('Reiniciado correctamente');
}
