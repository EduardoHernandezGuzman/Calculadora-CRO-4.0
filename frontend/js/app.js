function createInitialState() {
  return {
    wizard_step: 1,
    enfoque: null,
    session_id: null,
    tipo_valores: null,
    freq_interval_type: null,
    selected_engine_key: null,
    show_app: false,
    outputs: null,
    datos_procesados: false,
  };
}

window.State = createInitialState();

document.addEventListener('DOMContentLoaded', function() {
  showStep(1);

  document.getElementById('step-1').addEventListener('click', function(e) {
    const card = e.target.closest('.choice-card');
    if (card) {
      selectCard(card);
    }
  });

  document.getElementById('step-2').addEventListener('click', function(e) {
    const card = e.target.closest('.choice-card');
    if (card) {
      selectCard(card);
    }
  });

  document.getElementById('step-3-bayes').addEventListener('click', function(e) {
    const card = e.target.closest('.choice-card');
    if (card) {
      selectCard(card);
    }
  });

  document.getElementById('step-3-freq').addEventListener('click', function(e) {
    const card = e.target.closest('.choice-card');
    if (card) {
      selectCard(card);
    }
  });
});
