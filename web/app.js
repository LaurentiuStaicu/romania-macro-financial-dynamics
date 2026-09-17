const state = { lang: 'en', data: null, selectedSector: 'G' };

const strings = {
  en: {
    navModel: 'Model', navTheory: 'Theory / Learn', navDashboard: 'Dashboard', navAuxiliary: 'Sources & limits',
    modelEyebrow: 'Macro-financial stock-flow system', modelHeading: 'Sector network and financial positions',
    positions: 'Positions', candidate: 'Candidate feedback',
    modelIntro: 'Select a sector to connect the diagram with its theory, evidence and current empirical status.',
    readOnlyTitle: 'Current capability:', readOnlyBody: 'structural and empirical inspection only. Behavioural simulation remains disabled while the Alpha 0.6 gate is NO-GO.',
    theoryEyebrow: 'Contextual explanation', theoryHeading: 'Theory / Learn',
    dashboardEyebrow: 'Empirical status before engine metadata', dashboardHeading: 'Scientific validation dashboard',
    auxiliaryEyebrow: 'Evidence, provenance and limitations', auxiliaryHeading: 'Auxiliary',
    footerText: 'InfoClar is the reference web interface. Native packaging remains deferred until the web product is mature near v1.',
    readOnlyMode: 'Read-only scientific interface',
    selected: 'Selected sector', empiricalStatus: 'Empirical status', evidence: 'Evidence status',
    sources: 'Sources', limitations: 'Limitations', months: 'months',
    validatedMechanisms: 'validated behavioural mechanisms', mechanismAudit: 'Alpha 0.4 mechanisms',
    calibration: 'Calibration', structuralSelection: 'Structural selection', holdout: 'Fresh holdout',
    noValidated: 'No validated behavioural mechanism',
    passThrough: 'Household pass-through', refinancing: 'Government refinancing',
    policyHistory: 'policy-rate observations', mirHistory: 'observations / lending target',
    selectionSignal: 'selection RMSE', finalHoldout: 'final holdout RMSE', alpha06: 'Alpha 0.6 gate',
    ledgerRows: 'audited ledger rows', openingPrincipal: 'opening-principal rows', matchedRepricing: 'matched repricing rows',
    maturityVsRefixing: 'maturity / refixing <1y', completenessGate: 'ledger completeness gate'
  },
  ro: {
    navModel: 'Model', navTheory: 'Teorie / Învățare', navDashboard: 'Dashboard', navAuxiliary: 'Surse și limite',
    modelEyebrow: 'Sistem macro-financiar stock-flow', modelHeading: 'Rețea sectorială și poziții financiare',
    positions: 'Poziții', candidate: 'Feedback candidat',
    modelIntro: 'Selectează un sector pentru a conecta diagrama cu teoria, dovezile și starea empirică actuală.',
    readOnlyTitle: 'Capabilitate curentă:', readOnlyBody: 'doar inspecție structurală și empirică. Simularea comportamentală rămâne dezactivată cât timp poarta Alpha 0.6 este NO-GO.',
    theoryEyebrow: 'Explicație contextuală', theoryHeading: 'Teorie / Învățare',
    dashboardEyebrow: 'Starea empirică înaintea metadatelor motorului', dashboardHeading: 'Dashboard de validare științifică',
    auxiliaryEyebrow: 'Dovezi, proveniență și limitări', auxiliaryHeading: 'Auxiliar',
    footerText: 'InfoClar este interfața web de referință. Împachetarea nativă rămâne amânată până când produsul web se maturizează aproape de v1.',
    readOnlyMode: 'Interfață științifică read-only',
    selected: 'Sector selectat', empiricalStatus: 'Stare empirică', evidence: 'Starea dovezilor',
    sources: 'Surse', limitations: 'Limitări', months: 'luni',
    validatedMechanisms: 'mecanisme comportamentale validate', mechanismAudit: 'Mecanisme Alpha 0.4',
    calibration: 'Calibrare', structuralSelection: 'Selecție structurală', holdout: 'Holdout nou',
    noValidated: 'Niciun mecanism comportamental validat',
    passThrough: 'Pass-through gospodării', refinancing: 'Refinanțare publică',
    policyHistory: 'observații rata de politică', mirHistory: 'observații / țintă creditare',
    selectionSignal: 'RMSE selecție', finalHoldout: 'RMSE holdout final', alpha06: 'Poarta Alpha 0.6',
    ledgerRows: 'rânduri auditate în ledger', openingPrincipal: 'rânduri cu principal de deschidere', matchedRepricing: 'rânduri cu repricing potrivit',
    maturityVsRefixing: 'maturitate / refixare <1 an', completenessGate: 'poarta de completitudine a ledgerului'
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
  const v = state.data.validation.monetary_pass_through;
  const g = state.data.validation.government_refinancing;
  let cards;

  if (state.selectedSector === 'G') {
    cards = [
      metric(d.government_ledger_rows, t('ledgerRows'), `${d.government_ledger_currencies} currencies · fixed-rate public subset`),
      metric(d.government_rows_with_opening_outstanding_principal, t('openingPrincipal'), `required coverage ≥ ${g.minimum_opening_principal_coverage_pct}%`),
      metric(d.government_rows_with_matched_repricing, t('matchedRepricing'), `required event-principal coverage ≥ ${g.minimum_repricing_event_principal_coverage_pct}%`),
      metric(`${d.government_2024_12_maturing_1y_pct.toFixed(0)}% / ${d.government_2024_12_refixing_1y_pct.toFixed(0)}%`, t('maturityVsRefixing'), 'MoF 2024-12 · distinct concepts'),
      metric(g.gate_1, t('completenessGate'), `cost reconstruction ${g.gate_3} · estimation ${g.estimation_run ? 'RUN' : 'NOT RUN'}`),
      metric(state.data.validation.alpha_0_6_gate.replace('_FOR_BEHAVIOURAL_SIMULATION', ''), t('alpha06'), `${d.validated_behavioural_mechanisms} ${t('validatedMechanisms')}`)
    ];
  } else {
    cards = [
      metric(d.policy_rate_observations, t('policyHistory'), d.policy_rate_coverage),
      metric(d.mir_target_observations_each, t('mirHistory'), d.mir_target_coverage),
      metric(d.validated_behavioural_mechanisms, t('validatedMechanisms'), t('noValidated')),
      metric(v.household_selection_rmse.toFixed(3), t('selectionSignal'), `persistence ${v.household_persistence_rmse.toFixed(3)} · ${v.household_selection}`),
      metric(v.household_candidate_holdout_rmse.toFixed(3), t('finalHoldout'), `persistence ${v.household_persistence_holdout_rmse.toFixed(3)} · Δpolicy events ${v.household_holdout_policy_changes}`),
      metric(state.data.validation.alpha_0_6_gate.replace('_FOR_BEHAVIOURAL_SIMULATION', ''), t('alpha06'), `${t('calibration')} ${d.calibration_months} · ${t('structuralSelection')} ${d.structural_selection_months} · ${t('holdout')} ${d.fresh_household_holdout_months}`)
    ];
  }
  document.getElementById('dashboard-cards').innerHTML = cards.join('');
  document.getElementById('validation-note').textContent = state.data.validation.headline[state.lang];
}

function dispositionForSector() {
  const d = state.data.empirical_dashboard.alpha_0_5x_dispositions;
  if (state.selectedSector === 'G') return d.government_refinancing_effective_rate;
  if (state.selectedSector === 'C') return d.nfc_monetary_pass_through;
  return d.household_monetary_pass_through;
}

function interpretationForSector() {
  if (state.selectedSector === 'G') return state.data.validation.government_refinancing.interpretation[state.lang];
  return state.data.validation.monetary_pass_through.interpretation[state.lang];
}

function renderAuxiliary() {
  if (!state.data) return;
  const sources = state.data.sources.map(source => `<li><a href="${source.href}" rel="noreferrer">${source.label}</a></li>`).join('');
  const limits = state.data.limitations.map(item => `<li>${item[state.lang]}</li>`).join('');
  document.getElementById('auxiliary-content').innerHTML = `
    <div class="aux-block">
      <h3>${t('empiricalStatus')} <span class="status-chip">${dispositionForSector()}</span></h3>
      <p>${interpretationForSector()}</p>
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
