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
        <input type="checkbox" id="chk-ai" checked> Interpretaci&oacute;n IA (OpenAI)
      </label>
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
      ? 'Se eval&uacute;a si el valor de la m&eacute;trica en la variante es mayor que en el control.'
      : 'Se eval&uacute;a si el valor de la m&eacute;trica en la variante es menor que en el control.';
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
          ? 'Se analiza cualquier diferencia, tanto mejora como empeoramiento.'
          : 'Se analiza &uacute;nicamente una diferencia en una direcci&oacute;n espec&iacute;fica.'}
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
  main.innerHTML = `
    <h2 class="main-header">Calculadora para Tests A/B</h2>
    <div class="info-box">
      Esta herramienta te permite analizar los resultados de tus tests A/B usando modelos estad&iacute;sticos bayesianos o frecuentistas. Adem&aacute;s, te ayudaremos a la interpretaci&oacute;n de los resultados mediante Inteligencia Artificial. Sube un archivo CSV con el formato indicado y analiza tu test A/B.
    </div>
    <div class="section-spacer"></div>
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
    <div id="results-container"></div>
  `;

  setupFileUpload();
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

    let tableHtml = '<div class="section-spacer"></div><div class="success-box">✅ Archivo cargado correctamente!</div>';
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

  const generatePdf = document.getElementById('chk-pdf') ? document.getElementById('chk-pdf').checked : false;
  const includeAi = document.getElementById('chk-ai') ? document.getElementById('chk-ai').checked : false;

  const config = {
    generate_pdf: generatePdf,
    include_ai: includeAi,
  };

  if (window.State.enfoque === 'bayesiano') {
    config.num_samples = 20000;
  } else {
    config.n_iteraciones = 10000;
  }

  toggleSpinner(true);

  try {
    const result = await analyzeCsv(uploadedCsvFile, engineKey, config);
    window.State.outputs = result;
    window.State.datos_procesados = true;
    toggleSpinner(false);
    displayResults(result);
  } catch (err) {
    toggleSpinner(false);
    showError(`Error ejecutando el motor: ${err.message}`);
  }
}

function displayResults(out) {
  const container = document.getElementById('results-container');
  let html = '<div class="section-spacer"></div><hr><div class="section-spacer"></div>';
  html += '<h2 class="main-header">Resultados</h2>';

  const hasSummary = out.summary && out.summary.length > 0;
  const hasLog = out.log_text;
  const hasFigs = out.figures && out.figures.length > 0;
  const hasPdf = out.pdf_bytes;

  const tabs = [];
  if (hasSummary) tabs.push('resumen');
  if (hasLog) tabs.push('log');
  if (hasFigs) tabs.push('graficos');
  if (hasPdf) tabs.push('pdf');

  if (tabs.length > 0) {
    html += '<div class="tabs" id="result-tabs">';
    const tabLabels = { resumen: 'Resumen', log: 'Interpretaci\u00f3n' + (window.State.outputs?.log_text?.includes('IA') ? ' IA' : ''), graficos: 'Gr\u00e1ficos', pdf: 'Reporte' };
    tabs.forEach((t, i) => {
      html += `<button class="tab ${i === 0 ? 'active' : ''}" onclick="switchTab('${t}', this)">${tabLabels[t] || t}</button>`;
    });
    html += '</div>';
  }

  tabs.forEach((t, i) => {
    html += `<div class="tab-content ${i === 0 ? 'active' : ''}" id="tab-${t}">`;
    if (t === 'resumen') html += renderSummaryTab(out);
    else if (t === 'log') html += renderLogTab(out);
    else if (t === 'graficos') html += renderFiguresTab(out);
    else if (t === 'pdf') html += renderPdfTab(out);
    html += '</div>';
  });

  container.innerHTML = html;
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

  if (out.comparisons && out.comparisons.length > 0) {
    html += '<h3 style="margin-top:1.5rem;">Comparaciones</h3>';
    out.comparisons.forEach(comp => {
      html += '<div class="code-block">';
      html += `<b>D&iacute;a ${comp.dia}:</b>\n`;
      Object.keys(comp).forEach(k => {
        if (k === 'dia') return;
        const v = comp[k];
        if (typeof v === 'object' && v !== null) {
          html += `${k}:\n`;
          Object.entries(v).forEach(([kk, vv]) => {
            if (typeof vv === 'number') vv = (vv * 100).toFixed(2) + '%';
            html += `  ${kk}: ${vv}\n`;
          });
        }
      });
      html += '</div>';
    });
  }

  return html;
}

function renderLogTab(out) {
  if (out.log_text) {
    return `<h3>${window.State.outputs?.log_text?.includes('IA') ? 'Interpretaci\u00f3n IA' : 'Interpretaci\u00f3n / Log'}</h3>
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
