const state = { lang: 'en', data: null, selectedSector: 'F' };

const strings = {
  en: {
    navModel: 'Model', navTheory: 'Theory / Learn', navDashboard: 'Dashboard', navAuxiliary: 'Sources & limits',
    modelEyebrow: 'Macro-financial stock-flow system', modelHeading: 'Sector network and financial positions',
    positions: 'Positions', candidate: 'Candidate feedback',
    modelIntro: 'Select a sector to connect the diagram with its theory, evidence and current empirical status.',
    readOnlyTitle: 'Current capability:', readOnlyBody: 'structural and empirical inspection only. Interactive simulation is deliberately not enabled before Alpha 0.6.',
    theoryEyebrow: 'Contextual explanation', theoryHeading: 'Theory / Learn',
    dashboardEyebrow: 'Empirical status before engine metadata', dashboardHeading: 'Calibration & validation dashboard',
    auxiliaryEyebrow: 'Evidence, provenance and limitations', auxiliaryHeading: 'Auxiliary',
    footerText: 'InfoClar is the reference web interface. Native packaging remains deferred until the web product is mature near v1.',
    readOnlyMode: 'Read-only scientific interface',
    selected: 'Selected sector', empiricalStatus: 'Empirical status', evidence: 'Evidence status',
    sources: 'Sources', limitations: 'Limitations',
    months: 'months', validatedMechanisms: 'validated behavioural mechanisms', mechanismAudit: 'Alpha 0.4 mechanisms',
    calibration: 'Calibration', structuralSelection: 'Structural selection', holdout: 'Final holdout',
    noValidated: 'No validated behavioural mechanism',
    passThrough: 'Monetary pass-through', refinancing: 'Government refinancing'
  },
  ro: {
    navModel: 'Model', navTheory: 'Teorie / Învățare', navDashboard: 'Dashboard', navAuxiliary: 'Surse și limite',
    modelEyebrow: 'Sistem macro-financiar stock-flow', modelHeading: 'Rețea sectorială și poziții financiare',
    positions: 'Poziții', candidate: 'Feedback candidat',
    modelIntro: 'Selectează un sector pentru a conecta diagrama cu teoria, dovezile și starea empirică actuală.',
    readOnlyTitle: 'Capabilitate curentă:', readOnlyBody: 'doar inspecție structurală și empirică. Simularea interactivă nu este activată înainte de Alpha 0.6.',
    theoryEyebrow: 'Explicație contextuală', theoryHeading: 'Teorie / Învățare',
    dashboardEyebrow: 'Starea empirică înaintea metadatelor motorului', dashboardHeading: 'Dashboard calibrare și validare',
    auxiliaryEyebrow: 'Dovezi, proveniență și limitări', auxiliaryHeading: 'Auxiliar',
    footerText: 'InfoClar este interfața web de referință. Împachetarea nativă rămâne amânată până când produsul web se maturizează aproape de v1.',
    readOnlyMode: 'Interfață științifică read-only',
    selected: 'Sector selectat', empiricalStatus: 'Stare empirică', evidence: 'Starea dovezilor',
    sources: 'Surse', limitations: 'Limitări',
    months: 'luni', validatedMechanisms: 'mecanisme comportamentale validate', mechanismAudit: 'Mecanisme Alpha 0.4',
    calibration: 'Calibrare', structuralSelection: 'Selecție structurală', holdout: 'Holdout final',
    noValidated: 'Niciun mecanism comportamental validat',
    passThrough: 'Pass-through monetar', refinancing: 'Refinanțare publică'
  }
};

function t(key) { return strings[state.lang][key] ?? key; }

function applyLanguage() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (strings[state.lang][key]) el.textContent = strings[state.lang][key];
  });
  document.querySelectorAll('.language-switch button').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.lang === state.lang));
  });
  document.getElementById('mode-badge').textContent = t('readOnlyMode');
  renderAll();
}

function renderTheory() {
  if (!state.data) return;
  const sector = state.data.sectors.find(item => item.id === state.selectedSector) ?? state.data.sectors[0];
  const html = `
    <h3 class="context-title">${sector.id} · ${sector.label[state.lang]}</h3>
    <p class="context-meta">${t('selected')}</p>
    <p>${sector.theory[state.lang]}</p>
    <div class="model-note">
      <strong>${t('evidence')}:</strong>
      ${state.data.validation.headline[state.lang]}
    </div>`;
  document.getElementById('theory-content').innerHTML = html;
}

function metric(value, label, detail='') {
  return `<article class="metric-card"><span class="value">${value}</span><span class="label">${label}</span>${detail ? `<span class="detail">${detail}</span>` : ''}</article>`;
}

function renderDashboard() {
  if (!state.data) return;
  const d = state.data.empirical_dashboard;
  const cards = [
    metric(d.monetary_sample_months, t('months'), `${t('calibration')} ${d.calibration_months} · ${t('structuralSelection')} ${d.structural_selection_months} · ${t('holdout')} ${d.evaluation_holdout_months}`),
    metric(d.validated_behavioural_mechanisms, t('validatedMechanisms'), t('noValidated')),
    metric(`${d.alpha_0_4_mechanism_counts.ACTIVATED}/${d.alpha_0_4_mechanism_counts.CANDIDATE}`, t('mechanismAudit'), 'ACTIVATED / CANDIDATE'),
    metric(state.data.validation.monetary_pass_through.calibration_rank, t('passThrough'), state.data.validation.monetary_pass_through.structural_selection)
  ];
  document.getElementById('dashboard-cards').innerHTML = cards.join('');
  document.getElementById('validation-note').textContent = state.data.validation.headline[state.lang];
}

function renderAuxiliary() {
  if (!state.data) return;
  const selected = state.selectedSector;
  const disposition = selected === 'G'
    ? state.data.empirical_dashboard.alpha_0_5_dispositions.government_refinancing_effective_rate
    : state.data.empirical_dashboard.alpha_0_5_dispositions.monetary_policy_lending_rate_pass_through;
  const interpretation = selected === 'G'
    ? state.data.validation.government_refinancing.interpretation[state.lang]
    : state.data.validation.monetary_pass_through.interpretation[state.lang];
  const sources = state.data.sources.map(source => `<li><a href="${source.href}" rel="noreferrer">${source.label}</a></li>`).join('');
  const limits = state.data.limitations.map(item => `<li>${item[state.lang]}</li>`).join('');
  document.getElementById('auxiliary-content').innerHTML = `
    <div class="aux-block">
      <h3>${t('empiricalStatus')} <span class="status-chip">${disposition}</span></h3>
      <p>${interpretation}</p>
    </div>
    <div class="aux-block"><h3>${t('sources')}</h3><ul class="context-list">${sources}</ul></div>
    <div class="aux-block"><h3>${t('limitations')}</h3><ul class="context-list">${limits}</ul></div>`;
}

function renderAll() {
  if (!state.data) return;
  document.getElementById('stage-label').textContent = `${state.data.stage.name[state.lang]} · ${state.data.software_version}`;
  document.querySelectorAll('.sector').forEach(node => node.classList.toggle('selected', node.dataset.sector === state.selectedSector));
  renderTheory(); renderDashboard(); renderAuxiliary();
}

function selectSector(id) {
  state.selectedSector = id;
  renderAll();
}

async function boot() {
  try {
    const response = await fetch('public/model-stage.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
    renderAll();
  } catch (error) {
    document.getElementById('stage-label').textContent = 'Scientific stage snapshot unavailable';
    document.getElementById('validation-note').textContent = `Cannot load canonical web snapshot: ${error.message}`;
  }
}

document.querySelectorAll('.language-switch button').forEach(button => button.addEventListener('click', () => {
  state.lang = button.dataset.lang;
  localStorage.setItem('infoclar-language', state.lang);
  applyLanguage();
}));

document.querySelectorAll('.sector').forEach(node => {
  node.addEventListener('click', () => selectSector(node.dataset.sector));
  node.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectSector(node.dataset.sector); }
  });
});

const storedLanguage = localStorage.getItem('infoclar-language');
if (storedLanguage === 'ro' || storedLanguage === 'en') state.lang = storedLanguage;
applyLanguage();
boot();
