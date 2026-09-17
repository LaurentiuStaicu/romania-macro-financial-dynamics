const state = {
  lang: 'en',
  science: null,
  architecture: null,
  theory: null,
  activeLayer: 'overview',
  selection: null,
  hover: null,
  diagnostic: null,
  readerMode: null
};

const strings = {
  en: {
    productSubtitle: 'Explore how money, financial claims and vulnerabilities connect across the Romanian macro-financial system.',
    navModel: 'Model', navTheory: 'Theory / Learn', navDashboard: 'Dashboard', navAuxiliary: 'Evidence & limits',
    modelEyebrow: 'Explorable macro-financial system', modelHeading: 'How money and financial claims move through the economy',
    modelIntro: 'Start with the whole system, filter a layer, then select a sector or relationship for details. Missing values remain explicitly unavailable.',
    resetMap: 'Reset view', establishedRelation: 'Accounting / observed-domain relation', conceptualRelation: 'Conceptual relation', candidateRelation: 'Candidate / deferred mechanism',
    guardrailTitle: 'Scientific guardrail:', guardrailBody: 'this is an evidence-aware explanatory map, not a behavioural simulator. Candidate and deferred mechanisms cannot generate simulated outcomes.',
    theoryEyebrow: 'Contextual theory', theoryHeading: 'Theory / Learn', openChapter: 'Open full chapter', glossary: 'Glossary', references: 'References',
    dashboardEyebrow: 'Macro-financial diagnosis', dashboardHeading: 'Problems, imbalances and vulnerabilities', dashboardIntro: 'These cards use official institutional assessments, observed composition or explicit model-evidence status. No private severity thresholds are invented.',
    auxiliaryEyebrow: 'Evidence and interpretation', auxiliaryHeading: 'Sources, provenance & limits',
    footerText: 'InfoClar organizes scientific complexity for inspection. Unresolved data stay unresolved, and behavioural simulation stays disabled until its scientific gate is met.',
    selectedObject: 'Selected object', mapOverview: 'System overview', mapOverviewBody: 'Filter a layer or select any sector or relationship. Selection highlights incoming and outgoing links, neighbours, evidence and contextual theory.',
    definition: 'Definition', kind: 'Object type', role: 'Epistemic role', unit: 'Unit', period: 'Period', value: 'Value', sources: 'Sources', limitation: 'Interpretation limit',
    unavailable: 'Unavailable / not asserted', noSources: 'No external source attached; structural hypothesis only.',
    evidenceBasis: 'Empirical basis', uncertainty: 'Uncertainty', direction: 'Direction / trend', why: 'Why it matters', problem: 'Problem', state: 'State', criterion: 'Assessment basis',
    clickToTrace: 'Select to trace this diagnosis on the system map', chapterForSelection: 'Relevant chapter', fullChapter: 'Full chapter',
    provenance: 'Provenance & evidence', methodologicalStatus: 'Methodological status', technicalDefinition: 'Technical definition',
    observedValueRule: 'A missing value is not zero. Values appear only when the represented boundary, unit and period are definitionally matched.',
    scienceStatus: 'Scientific guardrails', scienceStatusBody: '0 validated behavioural reference mechanisms; Alpha 0.6 remains NO-GO; the household delta-policy form remains frozen for prospective confirmation.',
    layerShowing: 'Showing layer', allRelations: 'all supported relationships', relation: 'relationship', sector: 'sector',
    openSource: 'Open source'
  },
  ro: {
    productSubtitle: 'Explorează cum se conectează banii, creanțele financiare și vulnerabilitățile în sistemul macro-financiar al României.',
    navModel: 'Model', navTheory: 'Teorie / Învățare', navDashboard: 'Dashboard', navAuxiliary: 'Dovezi și limite',
    modelEyebrow: 'Sistem macro-financiar explorabil', modelHeading: 'Cum circulă banii și creanțele financiare prin economie',
    modelIntro: 'Pornește de la întregul sistem, filtrează un strat, apoi selectează un sector sau o relație pentru detalii. Valorile lipsă rămân explicit indisponibile.',
    resetMap: 'Resetează harta', establishedRelation: 'Relație contabilă / domeniu observat', conceptualRelation: 'Relație conceptuală', candidateRelation: 'Mecanism candidat / deferred',
    guardrailTitle: 'Gardă științifică:', guardrailBody: 'aceasta este o hartă explicativă orientată pe dovezi, nu un simulator comportamental. Mecanismele candidate și deferred nu pot genera rezultate simulate.',
    theoryEyebrow: 'Teorie contextuală', theoryHeading: 'Teorie / Învățare', openChapter: 'Deschide capitolul complet', glossary: 'Glosar', references: 'Referințe',
    dashboardEyebrow: 'Diagnostic macro-financiar', dashboardHeading: 'Probleme, dezechilibre și vulnerabilități', dashboardIntro: 'Cardurile folosesc evaluări instituționale oficiale, compoziție observată sau statut explicit al dovezilor modelului. Nu sunt inventate praguri private de severitate.',
    auxiliaryEyebrow: 'Dovezi și interpretare', auxiliaryHeading: 'Surse, proveniență și limite',
    footerText: 'InfoClar organizează complexitatea științifică pentru inspecție. Datele nerezolvate rămân nerezolvate, iar simularea comportamentală rămâne dezactivată până la trecerea porții științifice.',
    selectedObject: 'Obiect selectat', mapOverview: 'Ansamblul sistemului', mapOverviewBody: 'Filtrează un strat sau selectează orice sector ori relație. Selecția evidențiază intrările, ieșirile, vecinii, dovezile și teoria contextuală.',
    definition: 'Definiție', kind: 'Tip obiect', role: 'Rol epistemic', unit: 'Unitate', period: 'Perioadă', value: 'Valoare', sources: 'Surse', limitation: 'Limită de interpretare',
    unavailable: 'Indisponibil / neafirmat', noSources: 'Nicio sursă externă atașată; doar ipoteză structurală.',
    evidenceBasis: 'Bază empirică', uncertainty: 'Incertitudine', direction: 'Direcție / trend', why: 'De ce contează', problem: 'Problemă', state: 'Stare', criterion: 'Baza evaluării',
    clickToTrace: 'Selectează pentru a urmări diagnosticul pe harta sistemului', chapterForSelection: 'Capitol relevant', fullChapter: 'Capitol complet',
    provenance: 'Proveniență și dovezi', methodologicalStatus: 'Statut metodologic', technicalDefinition: 'Definiție tehnică',
    observedValueRule: 'O valoare lipsă nu este zero. Valorile apar numai când boundary-ul, unitatea și perioada reprezentate sunt potrivite definițional.',
    scienceStatus: 'Gărzi științifice', scienceStatusBody: '0 mecanisme comportamentale de referință validate; Alpha 0.6 rămâne NO-GO; forma household delta-policy rămâne înghețată pentru confirmare prospectivă.',
    layerShowing: 'Strat afișat', allRelations: 'toate relațiile susținute', relation: 'relație', sector: 'sector',
    openSource: 'Deschide sursa'
  }
};

const SVG_NS = 'http://www.w3.org/2000/svg';
function t(key) { return strings[state.lang][key] ?? key; }
function L(value) { return value?.[state.lang] ?? value?.en ?? ''; }
function sourceById(id) { return state.architecture?.sources?.find(source => source.id === id); }
function chapterById(id) { return state.theory?.chapters?.find(chapter => chapter.id === id); }
function nodeById(id) { return state.architecture?.nodes?.find(node => node.id === id); }
function edgeById(id) { return state.architecture?.edges?.find(edge => edge.id === id); }
function selectedObject() {
  if (!state.selection) return null;
  return state.selection.kind === 'node' ? nodeById(state.selection.id) : edgeById(state.selection.id);
}
function inspectedObject() {
  if (state.hover) return state.hover.kind === 'node' ? nodeById(state.hover.id) : edgeById(state.hover.id);
  return selectedObject();
}
function valueText(object) {
  if (object?.value === null || object?.value === undefined || object?.value === '') return t('unavailable');
  return String(object.value);
}
function epistemicClass(edge) {
  const role = edge.epistemic_role || '';
  if (role.includes('CANDIDATE') || role.includes('DEFERRED')) return 'candidate';
  if (role.includes('CONCEPTUAL')) return 'conceptual';
  return 'established';
}
function visibleEdges() {
  if (!state.architecture) return [];
  if (state.activeLayer === 'overview') return state.architecture.edges;
  return state.architecture.edges.filter(edge => edge.layer === state.activeLayer);
}
function pathForEdge(edge) {
  const from = nodeById(edge.from);
  const to = nodeById(edge.to);
  if (!from || !to) return { d: '', lx: 0, ly: 0 };
  if (edge.from === edge.to) {
    const lift = Math.max(66, Math.abs(edge.curve || 70));
    return {
      d: `M ${from.x + 34} ${from.y - 18} C ${from.x + 112} ${from.y - lift - 24}, ${from.x - 112} ${from.y - lift - 24}, ${from.x - 34} ${from.y - 18}`,
      lx: from.x, ly: from.y - lift - 28
    };
  }
  const dx = to.x - from.x, dy = to.y - from.y;
  const distance = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / distance, uy = dy / distance;
  const trim = 56;
  const x1 = from.x + ux * trim, y1 = from.y + uy * trim;
  const x2 = to.x - ux * trim, y2 = to.y - uy * trim;
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const curve = edge.curve || 0;
  const cx = mx - uy * curve, cy = my + ux * curve;
  const lx = .25 * x1 + .5 * cx + .25 * x2;
  const ly = .25 * y1 + .5 * cy + .25 * y2 - 5;
  return { d: `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`, lx, ly };
}
function highlightSets() {
  const edges = new Set(), nodes = new Set();
  if (state.diagnostic) {
    state.diagnostic.map_objects.forEach(id => {
      if (nodeById(id)) nodes.add(id);
      if (edgeById(id)) {
        edges.add(id);
        const edge = edgeById(id); nodes.add(edge.from); nodes.add(edge.to);
      }
    });
    return { edges, nodes, active: true };
  }
  if (!state.selection) return { edges, nodes, active: false };
  if (state.selection.kind === 'node') {
    nodes.add(state.selection.id);
    visibleEdges().forEach(edge => {
      if (edge.from === state.selection.id || edge.to === state.selection.id) {
        edges.add(edge.id); nodes.add(edge.from); nodes.add(edge.to);
      }
    });
  } else {
    const edge = edgeById(state.selection.id);
    if (edge) { edges.add(edge.id); nodes.add(edge.from); nodes.add(edge.to); }
  }
  return { edges, nodes, active: true };
}

function renderLayerToolbar() {
  const toolbar = document.getElementById('layer-toolbar');
  toolbar.innerHTML = '';
  state.architecture.layers.forEach(layer => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'layer-button';
    button.dataset.layer = layer.id;
    button.setAttribute('aria-pressed', String(layer.id === state.activeLayer));
    button.textContent = L(layer.label);
    button.addEventListener('click', () => {
      state.activeLayer = layer.id;
      state.diagnostic = null;
      state.selection = null;
      state.hover = null;
      state.readerMode = null;
      renderAll();
    });
    toolbar.appendChild(button);
  });
}

function bindMapActivation(element, kind, id) {
  const activate = () => selectMapObject(kind, id);
  element.addEventListener('click', activate);
  element.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
  });
  element.addEventListener('pointerenter', () => { state.hover = { kind, id }; renderInspector(); });
  element.addEventListener('pointerleave', () => { state.hover = null; renderInspector(); });
  element.addEventListener('focus', () => { state.hover = { kind, id }; renderInspector(); });
  element.addEventListener('blur', () => { state.hover = null; renderInspector(); });
}

function renderMap() {
  const edgesRoot = document.getElementById('map-edges');
  const nodesRoot = document.getElementById('map-nodes');
  edgesRoot.innerHTML = ''; nodesRoot.innerHTML = '';
  const highlights = highlightSets();
  const edges = visibleEdges();

  edges.forEach(edge => {
    const { d, lx, ly } = pathForEdge(edge);
    const group = document.createElementNS(SVG_NS, 'g');
    group.classList.add('edge-group');
    group.dataset.edge = edge.id;
    group.setAttribute('tabindex', '0');
    group.setAttribute('role', 'button');
    group.setAttribute('aria-label', L(edge.label));

    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d', d);
    path.classList.add('map-edge', `epistemic-${epistemicClass(edge)}`);
    const hit = document.createElementNS(SVG_NS, 'path');
    hit.setAttribute('d', d); hit.classList.add('edge-hit');
    const label = document.createElementNS(SVG_NS, 'text');
    label.setAttribute('x', lx); label.setAttribute('y', ly); label.setAttribute('text-anchor', 'middle');
    label.classList.add('edge-label'); label.textContent = L(edge.label);

    if (highlights.active && !highlights.edges.has(edge.id)) { path.classList.add('dimmed'); label.classList.add('dimmed'); }
    else if (highlights.edges.has(edge.id)) path.classList.add(state.selection?.id === edge.id ? 'selected' : 'related');
    group.append(path, hit, label);
    bindMapActivation(group, 'edge', edge.id);
    edgesRoot.appendChild(group);
  });

  state.architecture.nodes.forEach(node => {
    const group = document.createElementNS(SVG_NS, 'g');
    group.classList.add('node'); group.dataset.sector = node.id;
    group.setAttribute('tabindex', '0'); group.setAttribute('role', 'button'); group.setAttribute('aria-label', L(node.label));
    if (highlights.active && !highlights.nodes.has(node.id)) group.classList.add('dimmed');
    if (highlights.nodes.has(node.id)) group.classList.add(state.selection?.id === node.id ? 'selected' : 'related');

    const rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('x', node.x - 64); rect.setAttribute('y', node.y - 38); rect.setAttribute('width', 128); rect.setAttribute('height', 76);
    const code = document.createElementNS(SVG_NS, 'text');
    code.setAttribute('x', node.x); code.setAttribute('y', node.y - 5); code.classList.add('node-code'); code.textContent = node.id;
    const name = document.createElementNS(SVG_NS, 'text');
    name.setAttribute('x', node.x); name.setAttribute('y', node.y + 17); name.classList.add('node-name');
    const shortName = L(node.label).replace(' & NPISH','').replace(' și NPISH','');
    name.textContent = shortName.length > 23 ? `${shortName.slice(0, 22)}…` : shortName;
    group.append(rect, code, name);
    bindMapActivation(group, 'node', node.id);
    nodesRoot.appendChild(group);
  });
}

function sourceLinks(sourceIds = []) {
  if (!sourceIds.length) return `<p class="theory-meta">${t('noSources')}</p>`;
  const items = sourceIds.map(id => sourceById(id)).filter(Boolean).map(source =>
    `<li><a href="${source.url}" rel="noreferrer">${source.label}</a><br><span class="theory-meta">${source.institution || ''}</span></li>`
  ).join('');
  return `<ul class="source-links">${items}</ul>`;
}

function renderInspector() {
  const panel = document.getElementById('map-inspector');
  const object = inspectedObject();
  if (!object) {
    const layer = state.architecture.layers.find(item => item.id === state.activeLayer);
    panel.innerHTML = `<span class="inspector-kicker">${t('layerShowing')}</span><h3>${L(layer?.label)}</h3><p>${t('mapOverviewBody')}</p>`;
    return;
  }
  const isNode = Boolean(object.x !== undefined);
  panel.innerHTML = `
    <span class="inspector-kicker">${isNode ? t('sector') : t('relation')}</span>
    <h3>${L(object.label)}</h3>
    <p>${L(object.definition)}</p>
    <dl class="inspector-grid">
      <dt>${t('kind')}</dt><dd>${object.object_kind || 'institutional_sector'}</dd>
      <dt>${t('role')}</dt><dd>${object.epistemic_role}</dd>
      <dt>${t('unit')}</dt><dd>${object.unit || t('unavailable')}</dd>
      <dt>${t('period')}</dt><dd>${object.period || t('unavailable')}</dd>
      <dt>${t('value')}</dt><dd>${valueText(object)}</dd>
    </dl>
    <strong>${t('sources')}</strong>${sourceLinks(object.sources)}
    <p class="inspector-limit"><strong>${t('limitation')}:</strong> ${L(object.limit)}</p>`;
}

function relevantChapterId() {
  if (state.diagnostic) return 'macro-imbalances';
  return selectedObject()?.theory || inspectedObject()?.theory || 'money-circuit';
}
function renderTheoryContext() {
  const chapter = chapterById(relevantChapterId()) || state.theory.chapters[0];
  const selected = selectedObject();
  const contextLabel = selected ? L(selected.label) : state.diagnostic ? L(state.diagnostic.title) : t('mapOverview');
  const extra = chapter.sections?.[0]?.paragraphs?.[state.lang]?.[1] || '';
  document.getElementById('theory-context').innerHTML = `
    <p class="theory-meta">${t('chapterForSelection')} · ${contextLabel}</p>
    <h3>${L(chapter.title)}</h3>
    <p>${L(chapter.summary)}</p>
    ${extra ? `<p>${extra}</p>` : ''}`;
  if (state.readerMode) renderTheoryReader();
}
function renderTheoryReader() {
  const reader = document.getElementById('theory-reader');
  if (!state.readerMode) { reader.hidden = true; reader.innerHTML = ''; return; }
  reader.hidden = false;
  if (state.readerMode === 'glossary') {
    reader.innerHTML = `<h3>${t('glossary')}</h3><div class="glossary-list">${state.theory.glossary.map(item => `<div class="glossary-entry"><strong>${L(item.term)}</strong><span>${L(item.definition)}</span></div>`).join('')}</div>`;
    return;
  }
  if (state.readerMode === 'references') {
    reader.innerHTML = `<h3>${t('references')}</h3><ul class="reference-list">${state.theory.references.map(ref => `<li><a href="${ref.url}" rel="noreferrer">${ref.label}</a></li>`).join('')}</ul>`;
    return;
  }
  const chapter = chapterById(relevantChapterId()) || state.theory.chapters[0];
  const sections = chapter.sections.map(section => `<h4>${L(section.heading)}</h4>${section.paragraphs[state.lang].map(paragraph => `<p>${paragraph}</p>`).join('')}`).join('');
  reader.innerHTML = `<h3>${L(chapter.title)} · ${t('fullChapter')}</h3>${sections}`;
}

function renderDashboard() {
  const root = document.getElementById('diagnostic-cards');
  root.innerHTML = state.architecture.diagnostics.map(diagnostic => `
    <button type="button" class="diagnostic-card ${state.diagnostic?.id === diagnostic.id ? 'selected' : ''}" data-diagnostic="${diagnostic.id}" aria-pressed="${state.diagnostic?.id === diagnostic.id}">
      <h3>${L(diagnostic.title)}</h3>
      <span class="diagnostic-state">${L(diagnostic.state)}</span>
      <p class="diagnostic-row"><strong>${t('problem')}:</strong> ${L(diagnostic.problem)}</p>
      <p class="diagnostic-row"><strong>${t('why')}:</strong> ${L(diagnostic.why)}</p>
      <p class="diagnostic-row"><strong>${t('direction')}:</strong> ${L(diagnostic.direction)}</p>
      <p class="diagnostic-row diagnostic-basis"><strong>${t('evidenceBasis')}:</strong> ${L(diagnostic.basis)}</p>
      <p class="diagnostic-row"><strong>${t('uncertainty')}:</strong> ${L(diagnostic.uncertainty)}</p>
      <p class="diagnostic-row"><strong>${t('criterion')}:</strong> ${diagnostic.severity_basis}</p>
      <p class="diagnostic-hint">${t('clickToTrace')} →</p>
    </button>`).join('');
  root.querySelectorAll('[data-diagnostic]').forEach(button => button.addEventListener('click', () => selectDiagnostic(button.dataset.diagnostic)));
}

function renderAuxiliary() {
  const root = document.getElementById('auxiliary-content');
  if (state.diagnostic) {
    root.innerHTML = `
      <div class="aux-block"><h3>${L(state.diagnostic.title)}</h3><span class="status-chip">${state.diagnostic.severity_basis}</span><p>${L(state.diagnostic.uncertainty)}</p></div>
      <div class="aux-block"><h3>${t('provenance')}</h3>${sourceLinks(state.diagnostic.sources)}</div>
      <div class="aux-block"><h3>${t('technicalDefinition')}</h3><div class="technical-definition">${t('observedValueRule')}</div></div>
      <div class="aux-block"><h3>${t('scienceStatus')}</h3><p>${t('scienceStatusBody')}</p></div>`;
    return;
  }
  const object = selectedObject();
  if (!object) {
    root.innerHTML = `
      <div class="aux-block"><h3>${t('methodologicalStatus')}</h3><p>${t('observedValueRule')}</p></div>
      <div class="aux-block"><h3>${t('scienceStatus')}</h3><p>${t('scienceStatusBody')}</p></div>
      <div class="aux-block"><h3>${t('sources')}</h3>${sourceLinks(state.architecture.sources.map(item => item.id))}</div>`;
    return;
  }
  root.innerHTML = `
    <div class="aux-block"><h3>${L(object.label)}</h3><span class="status-chip">${object.epistemic_role}</span><p>${L(object.limit)}</p></div>
    <div class="aux-block"><h3>${t('provenance')}</h3>${sourceLinks(object.sources)}</div>
    <div class="aux-block"><h3>${t('technicalDefinition')}</h3><div class="technical-definition">${L(object.definition)}<br><br>${t('observedValueRule')}</div></div>
    <div class="aux-block"><h3>${t('scienceStatus')}</h3><p>${t('scienceStatusBody')}</p></div>`;
}

function selectMapObject(kind, id) {
  state.selection = { kind, id };
  state.diagnostic = null;
  state.readerMode = null;
  renderAll();
}
function selectDiagnostic(id) {
  state.diagnostic = state.architecture.diagnostics.find(item => item.id === id) || null;
  state.selection = null;
  state.hover = null;
  state.activeLayer = 'overview';
  state.readerMode = null;
  renderAll();
  document.getElementById('model-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function resetMap() {
  state.activeLayer = 'overview';
  state.selection = null;
  state.hover = null;
  state.diagnostic = null;
  state.readerMode = null;
  renderAll();
}
function renderAll() {
  if (!state.architecture || !state.theory || !state.science) return;
  document.documentElement.lang = state.lang;
  document.querySelectorAll('[data-i18n]').forEach(element => { const value = strings[state.lang][element.dataset.i18n]; if (value) element.textContent = value; });
  document.querySelectorAll('.language-switch button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lang === state.lang)));
  renderLayerToolbar();
  renderMap();
  renderInspector();
  renderTheoryContext();
  renderTheoryReader();
  renderDashboard();
  renderAuxiliary();
}

async function boot() {
  try {
    const [scienceResponse, architectureResponse, theoryResponse] = await Promise.all([
      fetch('public/model-stage.json', { cache: 'no-store' }),
      fetch('public/product-architecture.json', { cache: 'no-store' }),
      fetch('public/theory-corpus.json', { cache: 'no-store' })
    ]);
    if (![scienceResponse, architectureResponse, theoryResponse].every(response => response.ok)) throw new Error('One or more canonical product resources could not be loaded.');
    [state.science, state.architecture, state.theory] = await Promise.all([scienceResponse.json(), architectureResponse.json(), theoryResponse.json()]);
    if (state.science.stage.interactive_simulation_enabled !== false || state.science.validation.alpha_0_6_gate !== 'NO_GO_FOR_BEHAVIOURAL_SIMULATION') throw new Error('Scientific simulator gate contract mismatch.');
    renderAll();
  } catch (error) {
    document.getElementById('map-inspector').innerHTML = `<strong>Product data unavailable</strong><p>${error.message}</p>`;
  }
}

document.querySelectorAll('.language-switch button').forEach(button => button.addEventListener('click', () => {
  state.lang = button.dataset.lang;
  localStorage.setItem('infoclar-language', state.lang);
  renderAll();
}));
document.getElementById('reset-map').addEventListener('click', resetMap);
document.getElementById('open-chapter').addEventListener('click', () => { state.readerMode = 'chapter'; renderTheoryReader(); });
document.getElementById('open-glossary').addEventListener('click', () => { state.readerMode = 'glossary'; renderTheoryReader(); });
document.getElementById('open-references').addEventListener('click', () => { state.readerMode = 'references'; renderTheoryReader(); });

const storedLanguage = localStorage.getItem('infoclar-language');
if (storedLanguage === 'ro' || storedLanguage === 'en') state.lang = storedLanguage;
boot();
