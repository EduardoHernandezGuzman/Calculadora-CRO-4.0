function $(sel, ctx) {
  return (ctx || document).querySelector(sel);
}

function $$(sel, ctx) {
  return Array.from((ctx || document).querySelectorAll(sel));
}

function show(id) {
  const el = typeof id === 'string' ? document.getElementById(id) : id;
  if (el) el.style.display = '';
}

function hide(id) {
  const el = typeof id === 'string' ? document.getElementById(id) : id;
  if (el) el.style.display = 'none';
}

function html(id, content) {
  const el = typeof id === 'string' ? document.getElementById(id) : id;
  if (el) el.innerHTML = content;
}

function toggleSpinner(showSpinner) {
  const spinner = document.getElementById('spinner');
  if (showSpinner) {
    spinner.classList.add('show');
  } else {
    spinner.classList.remove('show');
  }
}

function showError(msg) {
  const main = document.getElementById('calculator-main');
  main.insertAdjacentHTML('afterbegin',
    `<div class="error-box">${msg}</div>`
  );
  window.scrollTo({ top: main.offsetTop, behavior: 'smooth' });
}

function showSuccess(msg) {
  const main = document.getElementById('calculator-main');
  main.insertAdjacentHTML('afterbegin',
    `<div class="success-box">${msg}</div>`
  );
}

function updateStepsIndicator(step) {
  $$('.step-dot').forEach(dot => {
    const s = parseInt(dot.dataset.step);
    dot.className = 'step-dot';
    if (s === step) dot.classList.add('active');
    else if (s < step) dot.classList.add('done');
  });
}

function showStep(step) {
  $$('.step-block').forEach(el => el.classList.remove('step-active'));
  let target;
  if (step === 3) {
    const suffix = (window.State.enfoque === 'bayesiano') ? 'bayes' : 'freq';
    target = document.getElementById(`step-3-${suffix}`);
  } else {
    target = document.getElementById(`step-${step}`);
  }
  if (target) target.classList.add('step-active');
  const backRow = document.getElementById('step4-back-row');
  if (backRow) backRow.style.display = step === 4 ? '' : 'none';
  updateStepsIndicator(step);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function clearSelection() {
  $$('.choice-card').forEach(c => c.classList.remove('selected'));
}

function selectCard(el) {
  clearSelection();
  el.classList.add('selected');
}

function openCsvModal() {
  document.getElementById('csv-modal').classList.add('show');
}

function closeCsvModal() {
  document.getElementById('csv-modal').classList.remove('show');
}

document.getElementById('csv-modal').addEventListener('click', function(e) {
  if (e.target === this) closeCsvModal();
});
