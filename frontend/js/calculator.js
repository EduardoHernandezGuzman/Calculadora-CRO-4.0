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
      <div class="expander-header">Modelo Estad&iacute;stico <span class="arrow">&#9660;</span></div>
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
  const freq = isFreqEngine();

  const csvPanel = `
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
  `;

  main.innerHTML = `
    <h2 class="main-header">Calculadora para Tests A/B</h2>
    <div class="info-box">
      Esta herramienta te permite analizar los resultados de tus tests A/B usando modelos estad&iacute;sticos bayesianos o frecuentistas. Adem&aacute;s, te ayudaremos a la interpretaci&oacute;n de los resultados mediante Inteligencia Artificial. Sube un archivo CSV con el formato indicado y analiza tu test A/B.
    </div>
    <div class="section-spacer"></div>
    ${freq ? renderInputMethodTabs() : ''}
    ${csvPanel}
    ${freq ? renderManualEntryPanel() : ''}
    <div id="results-container"></div>
  `;

  setupFileUpload();
}

function renderInputMethodTabs() {
  return `
    <div class="tabs" id="input-method-tabs">
      <button class="tab active" id="tab-method-csv" onclick="selectInputMethod('csv')">Cargar CSV</button>
      <button class="tab" id="tab-method-manual" onclick="selectInputMethod('manual')">Introducir datos manualmente</button>
    </div>
  `;
}

function renderManualEntryPanel() {
  return `
    <div id="method-manual" style="display:none;">
      <p class="sub-header">Introducir datos manualmente</p>
      <div class="hint-row">
        <span style="font-size:18px;">✍️</span>
        <span>Introduce los totales agregados de tu test A/B (usuarios o sesiones y conversiones de cada variante).</span>
      </div>
      <div class="subsection-spacer"></div>
      <div class="manual-entry-grid">
        <div class="manual-entry-group">
          <div class="manual-entry-title">Variante A (Control)</div>
          <label class="input-label" for="manual-a-visitas">Usuarios / sesiones</label>
          <input type="number" min="0" step="1" id="manual-a-visitas" class="form-input" placeholder="Ej. 2823">
          <label class="input-label" for="manual-a-conv">Conversiones</label>
          <input type="number" min="0" step="1" id="manual-a-conv" class="form-input" placeholder="Ej. 589">
        </div>
        <div class="manual-entry-group">
          <div class="manual-entry-title">Variante B</div>
          <label class="input-label" for="manual-b-visitas">Usuarios / sesiones</label>
          <input type="number" min="0" step="1" id="manual-b-visitas" class="form-input" placeholder="Ej. 2694">
          <label class="input-label" for="manual-b-conv">Conversiones</label>
          <input type="number" min="0" step="1" id="manual-b-conv" class="form-input" placeholder="Ej. 541">
        </div>
      </div>
      <div class="btn-row" style="justify-content:center;">
        <button class="btn btn-primary" onclick="runManualAnalysis()">Analizar experimento</button>
      </div>
    </div>
  `;
}

function selectInputMethod(method) {
  const csv = document.getElementById('method-csv');
  const manual = document.getElementById('method-manual');
  const tabCsv = document.getElementById('tab-method-csv');
  const tabManual = document.getElementById('tab-method-manual');
  const isManual = method === 'manual';

  csv.style.display = isManual ? 'none' : '';
  manual.style.display = isManual ? '' : 'none';
  tabCsv.classList.toggle('active', !isManual);
  tabManual.classList.toggle('active', isManual);

  document.getElementById('results-container').innerHTML = '';
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
    const headers = lines[0].split(',').map(h => h.trim());

    let tableHtml = '<div class="section-spacer"></div><div class="success-box">✅ \u00a1Archivo cargado correctamente!</div>';
    tableHtml += '<p style="font-weight:600;margin-bottom:0.5rem;">Vista previa de tus datos:</p>';
    tableHtml += '<table class="data-table"><thead><tr>';
    headers.forEach(h => { tableHtml += `<th>${h}</th>`; });
    tableHtml += '</tr></thead><tbody>';

    const maxRows = Math.min(lines.length - 1, 10);
    for (let i = 1; i <= maxRows; i++) {
      const cols = lines[i].split(',').map(c => c.trim());
      tableHtml += '<tr>';
      cols.forEach(c => { tableHtml += `<td>${c}</td>`; });
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
  };

  if (window.State.enfoque === 'bayesiano') {
    config.num_samples = 20000;
  } else {
    config.n_iteraciones = 10000;
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

// Construye un CSV a partir de los totales agregados introducidos manualmente,
// en el formato que espera el motor frecuentista seleccionado.
function buildManualCsv(engineKey, va, ca, vb, cb) {
  if (engineKey === 'freq_sid') {
    // El motor con Session ID espera valores por sesión en dos columnas (A, B).
    // Representamos los datos binomiales como vectores 0/1 (convierte / no convierte),
    // estadísticamente equivalentes a los totales agregados.
    const n = Math.max(va, vb);
    const lines = ['A,B'];
    for (let i = 0; i < n; i++) {
      const a = i < va ? (i < ca ? 1 : 0) : '';
      const b = i < vb ? (i < cb ? 1 : 0) : '';
      lines.push(`${a},${b}`);
    }
    return lines.join('\n') + '\n';
  }
  // freq_no_sid: totales agregados en una sola fila.
  return `Visitas A,Visitas B,Conversiones A,Conversiones B\n${va},${vb},${ca},${cb}\n`;
}

async function runManualAnalysis() {
  const engineKey = window.State.selected_engine_key;
  if (!engineKey) {
    showError('No hay motor seleccionado. Vuelve al wizard.');
    return;
  }

  const va = parseInt(document.getElementById('manual-a-visitas').value, 10);
  const ca = parseInt(document.getElementById('manual-a-conv').value, 10);
  const vb = parseInt(document.getElementById('manual-b-visitas').value, 10);
  const cb = parseInt(document.getElementById('manual-b-conv').value, 10);

  const campos = [
    ['Usuarios / sesiones (A)', va],
    ['Conversiones (A)', ca],
    ['Usuarios / sesiones (B)', vb],
    ['Conversiones (B)', cb],
  ];
  for (const [label, v] of campos) {
    if (isNaN(v) || v < 0) {
      showError(`Introduce un valor válido (entero ≥ 0) en "${label}".`);
      return;
    }
  }
  if (va === 0 || vb === 0) {
    showError('Los usuarios / sesiones de A y B deben ser mayores que 0.');
    return;
  }
  if (ca > va) {
    showError('Las conversiones de A no pueden superar sus usuarios / sesiones.');
    return;
  }
  if (cb > vb) {
    showError('Las conversiones de B no pueden superar sus usuarios / sesiones.');
    return;
  }

  const csv = buildManualCsv(engineKey, va, ca, vb, cb);
  const file = new File([csv], 'datos_manuales.csv', { type: 'text/csv' });

  await analyzeFile(file, engineKey);
}

function isBayesEngine() {
  const k = window.State.selected_engine_key;
  return k && (k.startsWith('bayes_'));
}

function isFreqEngine() {
  const k = window.State.selected_engine_key;
  return k && (k.startsWith('freq_'));
}

function displayResults(out) {
  const container = document.getElementById('results-container');
  let html = '<div class="section-spacer"></div><hr><div class="section-spacer"></div>';
  html += '<h2 class="main-header">Resultados</h2>';

  const hasSummary = out.summary && out.summary.length > 0;
  const hasConsole = hasSummary;
  const hasLog = out.log_text;
  const hasFigs = out.figures && out.figures.length > 0;
  const hasPdf = out.pdf_bytes;

  const tabs = [];
  if (hasSummary) tabs.push('resumen');
  if (hasConsole) tabs.push('consola');
  if (hasLog) tabs.push('log');
  if (hasFigs) tabs.push('graficos');
  if (hasPdf) tabs.push('pdf');

  if (tabs.length > 0) {
    html += '<div class="tabs" id="result-tabs">';
    const tabLabels = {
      resumen: 'Resumen',
      consola: 'Salida tipo consola',
      log: out.log_text && (out.log_text.includes('IA') || out.log_text.includes('GPT') || out.log_text.includes('OpenAI'))
        ? 'Interpretaci\u00f3n IA'
        : 'Interpretaci\u00f3n / Log',
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
    else if (t === 'log') html += renderLogTab(out);
    else if (t === 'graficos') html += renderFiguresTab(out);
    else if (t === 'pdf') html += renderPdfTab(out);
    html += '</div>';
  });

  container.innerHTML = html;
}

function _pct(v) {
  if (v === null || v === undefined) return '';
  const n = typeof v === 'number' ? v : parseFloat(v);
  if (isNaN(n)) return v;
  return (n * 100).toFixed(2) + '%';
}

function _findComparison(comparisons, dia) {
  if (!comparisons) return null;
  const target = String(dia);
  for (const c of comparisons) {
    if (String(c.dia) === target || String(c.dia) === 'D\u00eda ' + target) {
      return c;
    }
  }
  return null;
}

function renderSummaryTab(out) {
  let html = '<h3>Resumen</h3>';

  const excludeCols = ['ci_low', 'ci_high', 'ci_uplift_center_low', 'ci_uplift_center_high'];
  const keys = Object.keys(out.summary[0]).filter(k => !excludeCols.includes(k));

  html += '<table class="data-table"><thead><tr>';
  keys.forEach(k => { html += `<th>${k}</th>`; });
  html += '</tr></thead><tbody>';

  out.summary.forEach(row => {
    html += '<tr>';
    keys.forEach(k => {
      let val = row[k];
      if (val === null || val === undefined) val = '';
      else if (typeof val === 'number') val = val.toFixed(4);
      html += `<td>${val}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';

  return html;
}

function renderConsoleTab(out) {
  let html = '<h3>Salida tipo consola</h3>';

  const hasDia = out.summary.some(r => r.dia !== undefined && r.dia !== null);
  const hasGrupo = out.summary.some(r => r.grupo !== undefined && r.grupo !== null);

  if (hasDia && hasGrupo) {
    html += renderBayesConsoleBlocks(out);
  } else {
    html += renderFreqConsoleBlocks(out);
  }

  return html;
}

function renderBayesConsoleBlocks(out) {
  const summaries = out.summary;
  const comparisons = out.comparisons || [];

  const dias = [...new Set(summaries.map(r => r.dia))];

  let blocks = [];

  dias.forEach(dia => {
    const rows = summaries.filter(r => String(r.dia) === String(dia));
    rows.sort((a, b) => String(a.grupo).localeCompare(String(b.grupo)));

    let lines = [];
    lines.push('\uD83D\uDDD3\ufe0f  ' + dia);

    const grupos = [];
    rows.forEach(r => {
      const g = String(r.grupo || '');
      grupos.push(g);
      const visitas = r.visitas ?? '';
      const conv = r.conversiones ?? '';
      const acumV = r.acum_visitas ?? '';
      const acumC = r.acum_conversiones ?? '';
      const media = r.media ?? '';
      const ciLow = r.ci_low ?? '';
      const ciHigh = r.ci_high ?? '';

      lines.push('Grupo ' + g + ':');
      lines.push('  \uD83D\uDCCA Acumulado: ' + acumV + ' visitas | ' + acumC + ' conversiones');
      lines.push('  Visitas d\u00eda: ' + visitas + ' | Conversiones d\u00eda: ' + conv);
      lines.push('  Media: ' + _pct(media));
      lines.push('  IC 95%: [' + _pct(ciLow) + ', ' + _pct(ciHigh) + ']');
    });

    if (grupos.length >= 2) {
      lines.push('');
      const g1 = grupos[0];
      const g2 = grupos[1];
      const comp = _findComparison(comparisons, dia);
      if (comp) {
        [g1 + '_vs_' + g2, g2 + '_vs_' + g1].forEach(key => {
          const stats = comp[key];
          if (stats && typeof stats === 'object') {
            const upliftMedia = parseFloat(stats.uplift_media || 0) * 100;
            const probMejor = parseFloat(stats.prob_mejor || 0) * 100;
            const ciCentered = stats.ci_centered;
            const ciRight = stats.ci_right;
            const ciLeft = stats.ci_left;

            const fmtCent = ciCentered && ciCentered.length >= 2
              ? '[' + (ciCentered[0] * 100).toFixed(2) + '%, ' + (ciCentered[1] * 100).toFixed(2) + '%]'
              : '—';
            const fmtRight = ciRight && ciRight.length >= 1
              ? '> ' + (ciRight[0] * 100).toFixed(2) + '%'
              : '—';
            const fmtLeft = ciLeft && ciLeft.length >= 1
              ? '< ' + (ciLeft[0] * 100).toFixed(2) + '%'
              : '—';

            lines.push('\uD83D\uDCC8 Uplift (relativo ' + key + '):');
            lines.push('  Media estimada: ' + upliftMedia.toFixed(2) + '%');
            lines.push('  ---------------------------------------------');
            lines.push('  1. IC Centrado:   ' + fmtCent + ' (Est\u00e1ndar)');
            lines.push('  2. IC Suelo:      ' + fmtRight + ' (M\u00ednimo asegurado 95%)');
            lines.push('  3. IC Techo:      ' + fmtLeft + ' (M\u00e1ximo riesgo 95%)');
            lines.push('  ---------------------------------------------');
            lines.push('  Probabilidad de que ' + g1 + ' > ' + g2 + ': ' + probMejor.toFixed(2) + '%');
          }
        });
      }
    }

    blocks.push(lines.join('\n'));
  });

  if (blocks.length === 0) {
    return '<div class="code-block">No hay datos de consola disponibles.</div>';
  }

  return blocks.map(b => '<div class="code-block">' + b + '</div>').join('');
}

function renderFreqConsoleBlocks(out) {
  const r = out.summary[0] || {};
  const comparisons = out.comparisons || [];

  const intervalType = window.State.freq_interval_type || 'centrado';

  let lines = [];
  lines.push('==================================================');
  lines.push('           AN\u00c1LISIS DE PRECISI\u00d3N B vs A');
  lines.push('==================================================');

  const hasAggregated = r.n_visitas_A !== undefined;

  if (hasAggregated) {
    lines.push(
      'Dise\u00f1o A             | Visitas: ' + String(parseInt(r.n_visitas_A) || 0).padStart(8) + ' | Convs: ' + String(parseInt(r.conv_A) || 0).padStart(6)
    );
    lines.push(
      'Dise\u00f1o B             | Visitas: ' + String(parseInt(r.n_visitas_B) || 0).padStart(8) + ' | Convs: ' + String(parseInt(r.conv_B) || 0).padStart(6)
    );
  } else {
    const ga = r.grupo_A_col || 'A';
    const gb = r.grupo_B_col || 'B';
    lines.push(
      ga + ' (A): ' + String(parseInt(r.n_A) || 0) + ' filas | ' + String(parseFloat(r.conv_A) || 0) + ' convs | Media: ' + (parseFloat(r.media_A) || 0).toFixed(4)
    );
    lines.push(
      gb + ' (B): ' + String(parseInt(r.n_B) || 0) + ' filas | ' + String(parseFloat(r.conv_B) || 0) + ' convs | Media: ' + (parseFloat(r.media_B) || 0).toFixed(4)
    );
  }

  lines.push('--------------------------------------------------');

  const significancia = parseFloat(r.precision_B_mejor || 0) * 100;
  lines.push('NIVEL DE SIGNIFICANCIA DE QUE B > A: ' + significancia.toFixed(2) + '%');

  if (intervalType === 'centrado') {
    const low = r.ci_uplift_center_low;
    const high = r.ci_uplift_center_high;
    if (low !== undefined && high !== undefined) {
      lines.push('IC CENTRADO (UPLIFT): [' + parseFloat(low).toFixed(2) + '%, ' + parseFloat(high).toFixed(2) + '%]');
    } else {
      lines.push('IC CENTRADO (UPLIFT): [—]');
    }
  } else if (intervalType === 'derecha') {
    const val = r.ci_right_95_left;
    if (val !== undefined) {
      lines.push('COLA DERECHA (IC 95% IZQUIERDA): > ' + parseFloat(val).toFixed(2) + '%');
    } else {
      lines.push('COLA DERECHA (IC 95% IZQUIERDA): —');
    }
  } else if (intervalType === 'izquierda') {
    const val = r.ci_left_95_right;
    if (val !== undefined) {
      lines.push('COLA IZQUIERDA (IC 95% DERECHA): < ' + parseFloat(val).toFixed(2) + '%');
    } else {
      lines.push('COLA IZQUIERDA (IC 95% DERECHA): —');
    }
  }

  if (comparisons && comparisons.length > 0) {
    comparisons.forEach(comp => {
      lines.push('--------------------------------------------------');
      Object.keys(comp).forEach(k => {
        if (k === 'dia') return;
        const v = comp[k];
        if (typeof v === 'object' && v !== null) {
          lines.push(k + ':');
          Object.entries(v).forEach(([kk, vv]) => {
            if (typeof vv === 'number') vv = (vv * 100).toFixed(2) + '%';
            lines.push('  ' + kk + ': ' + vv);
          });
        }
      });
    });
  }

  lines.push('==================================================');

  return '<div class="code-block">' + lines.join('\n') + '</div>';
}

function renderLogTab(out) {
  if (out.log_text) {
    const isAi = out.log_text.includes('IA') || out.log_text.includes('GPT') || out.log_text.includes('OpenAI');
    return `<h3>${isAi ? 'Interpretaci\u00f3n IA' : 'Interpretaci\u00f3n / Log'}</h3>
      <div class="code-block">${out.log_text}</div>`;
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
    <button class="btn-download" onclick="downloadPdf('${out.pdf_bytes}', 'reporte.pdf')">
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
  document.getElementById('csv-preview').innerHTML = '';
  document.getElementById('results-container').innerHTML = '';
  showSuccess('Reiniciado correctamente');
}
