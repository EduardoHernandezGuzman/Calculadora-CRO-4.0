const API_BASE = '/api';

async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Error ${res.status}: ${text}`);
  }
  return res.json();
}

async function fetchEngines() {
  return apiRequest('/engines');
}

async function analyzeCsv(file, engineKey, config) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('engine_key', engineKey);
  formData.append('config', JSON.stringify(config));
  return apiRequest('/analyze', { method: 'POST', body: formData });
}

function downloadPdf(pdfBase64, filename = 'reporte.pdf') {
  const byteChars = atob(pdfBase64);
  const byteNums = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) {
    byteNums[i] = byteChars.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNums);
  const blob = new Blob([byteArray], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
