const INTERNAL_SCIENCE_GATE='NO_GO_FOR_BEHAVIOURAL_SIMULATION';
const LEGACY_THEORY_PATH='public/theory-corpus.json';
const SVG_NS='http://www.w3.org/2000/svg';
const state={lang:'en',architecture:null,contract:null,theory:null,science:null,perspective:'stock',activeLayer:'balance',selection:null,diagnostic:null,readerMode:null,stockSubview:'map'};

const ui={
  en:{
    central:"How do finances circulate through Romania's economy, who funds whom, who owes whom, where do vulnerabilities accumulate, and how can shocks transmit?",
    modelHeading:'Who funds whom? Who owes whom? Through which instrument?',
    modelIntro:'Start from the balance sheet or from flows, then activate one layer at a time. Missing bilateral values stay unresolved rather than becoming zero.',
    stock:'STOCK / BALANCE-SHEET VIEW',flow:'FLOW VIEW',map:'Relationship map',matrix:'Holder × issuer matrix',reset:'Reset',
    overview:'Select a sector to answer who funds it, whom it funds, what it owns, what it owes, through which instrument, how much is observed and how positions have changed.',
    unavailable:'Unavailable / unresolved',none:'None represented on this boundary.',notForecast:'Not a forecast.',
    whoFunds:'WHO FUNDS IT?',whoFunded:'WHO DOES IT FUND?',whatOwns:'WHAT DOES IT OWN?',whatOwes:'WHAT DOES IT OWE?',counterparties:'MAJOR COUNTERPARTIES',
    incoming:'Incoming relations',outgoing:'Outgoing relations',assets:'Assets / claims represented',liabilities:'Liabilities / funding represented',vulnerability:'Vulnerability channels',
    definition:'Definition',direction:'Direction',instrument:'Instrument',accounting:'Accounting class',epistemic:'Epistemic role',value:'Value',period:'Period',unit:'Unit',holder:'Holder / creditor',issuer:'Issuer / debtor',propagation:'Propagation / affected sectors',sources:'Sources',limitations:'Limitations',
    observed:'Observed',accountingRel:'Accounting relation',conceptual:'Conceptual / unquantified',candidate:'Behavioural candidate',deferred:'Deferred / not identified',
    relevantChapter:'Relevant theory',openChapter:'Open relevant chapter',openManual:'Open complete manual',glossary:'Glossary',references:'References',
    problem:'WHAT IS THE PROBLEM?',current:'CURRENT VALUE / DIRECTION',why:'WHY IT MATTERS',exposed:'WHO IS EXPOSED?',how:'HOW CAN IT PROPAGATE?',evidence:'EVIDENCE',uncertainty:'UNCERTAINTY',
    feedbackMechanism:'Mechanism',feedbackSign:'Hypothetical sign',evidenceStatus:'Evidence status',parameterStatus:'Parameter status',validationStatus:'Validation status',requiredValidation:'Required before simulation',
    technical:'Research / technical provenance',unknownZero:'Unknown is not zero. A missing bilateral value is not treated as zero or synthetically allocated.'
  },
  ro:{
    central:'Cum circulă finanțele în economia României, cine finanțează pe cine, cine datorează cui, unde se acumulează vulnerabilități și cum se pot transmite șocurile?',
    modelHeading:'Cine finanțează pe cine? Cine datorează cui? Prin ce instrument?',
    modelIntro:'Pornește de la bilanț sau de la fluxuri, apoi activează câte un singur layer. Valorile bilaterale lipsă rămân nerezolvate, nu devin zero.',
    stock:'STOC / VEDERE BILANȚIERĂ',flow:'VEDERE FLUXURI',map:'Hartă de relații',matrix:'Matrice deținător × emitent',reset:'Resetare',
    overview:'Selectează un sector pentru a vedea cine îl finanțează, pe cine finanțează, ce active deține, ce pasive are, prin ce instrument, cât este observat și cum s-au modificat pozițiile.',
    unavailable:'Indisponibil / nerezolvat',none:'Nimic reprezentat pe acest boundary.',notForecast:'Nu este prognoză.',
    whoFunds:'CINE ÎL FINANȚEAZĂ?',whoFunded:'PE CINE FINANȚEAZĂ?',whatOwns:'CE ACTIVE DEȚINE?',whatOwes:'CE PASIVE ARE?',counterparties:'CONTRAPĂRȚI PRINCIPALE',
    incoming:'Relații de intrare',outgoing:'Relații de ieșire',assets:'Active / creanțe reprezentate',liabilities:'Pasive / finanțare reprezentată',vulnerability:'Canale de vulnerabilitate',
    definition:'Definiție',direction:'Direcție',instrument:'Instrument',accounting:'Clasă contabilă',epistemic:'Statut epistemic',value:'Valoare',period:'Perioadă',unit:'Unitate',holder:'Deținător / creditor',issuer:'Emitent / debitor',propagation:'Propagare / sectoare afectate',sources:'Surse',limitations:'Limitări',
    observed:'Observat',accountingRel:'Relație contabilă',conceptual:'Conceptual / necuantificat',candidate:'Mecanism comportamental candidat',deferred:'Amânat / neidentificat',
    relevantChapter:'Teorie relevantă',openChapter:'Deschide capitolul relevant',openManual:'Deschide manualul complet',glossary:'Glosar',references:'Referințe',
    problem:'CARE ESTE PROBLEMA?',current:'VALOARE / DIRECȚIE CURENTĂ',why:'DE CE CONTEAZĂ',exposed:'CINE ESTE EXPUS?',how:'CUM SE POATE PROPAGA?',evidence:'DOVEZI',uncertainty:'INCERTITUDINE',
    feedbackMechanism:'Mecanism',feedbackSign:'Semn ipotetic',evidenceStatus:'Statut dovezi',parameterStatus:'Statut parametru',validationStatus:'Statut validare',requiredValidation:'Necesar înainte de simulare',
    technical:'Proveniență de cercetare / tehnică',unknownZero:'Necunoscut nu înseamnă zero. O valoare bilaterală lipsă nu este tratată ca zero și nu este alocată sintetic.'
  }
};

const U=key=>ui[state.lang][key]??key;
const L=value=>value?.[state.lang]??value?.en??value??'';
const nodeById=id=>state.architecture?.nodes.find(item=>item.id===id);
const edgeById=id=>state.architecture?.edges.find(item=>item.id===id);
const sourceById=id=>state.architecture?.sources.find(item=>item.id===id);
const chapterById=id=>state.theory?.chapters.find(item=>item.id===id);
const fmt=value=>value===null||value===undefined||value===''?U('unavailable'):String(value);
const friendlyNode=id=>L(nodeById(id)?.label)||'Unresolved counterparty';
const instrumentLabel=edge=>edge.instrument||edge.esa_instrument||'—';
const accountingLabel=edge=>({STOCK:state.lang==='ro'?'Stoc':'Stock',FLOW:state.lang==='ro'?'Flux':'Flow',REVALUATION_OTHER_FLOW:state.lang==='ro'?'Reevaluare / alte modificări':'Revaluation / other changes',BEHAVIOURAL_CANDIDATE:state.lang==='ro'?'Mecanism comportamental candidat':'Behavioural candidate'})[edge.accounting_class]||edge.object_kind||'—';

function epistemicKind(object){
  const role=object?.epistemic_role||'';
  if(/DEFERRED/.test(role))return'DEFERRED';
  if(/CANDIDATE/.test(role))return'CANDIDATE';
  if(object?.value!==null&&object?.value!==undefined&&!/CONCEPTUAL/.test(role))return'OBSERVED';
  if(/CONCEPTUAL/.test(role))return'CONCEPTUAL';
  if(/ACCOUNTING|ESA|CENTRAL_BANK|PARTIAL_SOURCE|RELATION/.test(role))return'ACCOUNTING';
  return'ACCOUNTING';
}
function epistemicClass(object){const kind=epistemicKind(object);return kind==='CANDIDATE'||kind==='DEFERRED'?'candidate':kind==='CONCEPTUAL'?'conceptual':'established'}
function epistemicLabel(object){return({OBSERVED:U('observed'),ACCOUNTING:U('accountingRel'),CONCEPTUAL:U('conceptual'),CANDIDATE:U('candidate'),DEFERRED:U('deferred')})[epistemicKind(object)]}

function perspectiveClasses(){return state.perspective==='stock'?new Set(['STOCK']):new Set(['FLOW','REVALUATION_OTHER_FLOW'])}
function visibleEdges(){
  if(state.diagnostic){const ids=new Set(state.diagnostic.map_objects||[]);return state.architecture.edges.filter(edge=>ids.has(edge.id));}
  if(state.activeLayer==='feedback')return state.architecture.edges.filter(edge=>edge.layer==='feedback');
  const classes=perspectiveClasses();
  return state.architecture.edges.filter(edge=>edge.layer===state.activeLayer&&classes.has(edge.accounting_class));
}
function sectorRelations(id,{all=false}={}){const base=all?state.architecture.edges:visibleEdges();return base.filter(edge=>edge.from===id||edge.to===id||edge.holder===id||edge.issuer===id)}
function financialPositions(){return state.architecture.edges.filter(edge=>edge.accounting_class==='STOCK'&&edge.is_financial_position)}
function pathForEdge(edge){
  const from=nodeById(edge.from),to=nodeById(edge.to);if(!from||!to)return{d:'',lx:0,ly:0};
  if(edge.from===edge.to){return{d:`M ${from.x+42} ${from.y-20} C ${from.x+130} ${from.y-115}, ${from.x-130} ${from.y-115}, ${from.x-42} ${from.y-20}`,lx:from.x,ly:from.y-120};}
  const dx=to.x-from.x,dy=to.y-from.y,d=Math.max(1,Math.hypot(dx,dy)),ux=dx/d,uy=dy/d,trim=72,x1=from.x+ux*trim,y1=from.y+uy*trim,x2=to.x-ux*trim,y2=to.y-uy*trim,mx=(x1+x2)/2,my=(y1+y2)/2,curve=edge.curve||0,cx=mx-uy*curve,cy=my+ux*curve;
  return{d:`M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`,lx:.25*x1+.5*cx+.25*x2,ly:.25*y1+.5*cy+.25*y2-6};
}
function highlighted(){
  const nodes=new Set(),edges=new Set();
  if(state.diagnostic){(state.diagnostic.map_objects||[]).forEach(id=>{const edge=edgeById(id);if(edge){edges.add(id);nodes.add(edge.from);nodes.add(edge.to);}else if(nodeById(id))nodes.add(id);});return{nodes,edges,active:true};}
  if(!state.selection)return{nodes,edges,active:false};
  if(state.selection.kind==='node'){
    nodes.add(state.selection.id);visibleEdges().forEach(edge=>{if(edge.from===state.selection.id||edge.to===state.selection.id||edge.holder===state.selection.id||edge.issuer===state.selection.id){edges.add(edge.id);nodes.add(edge.from);nodes.add(edge.to);}});
  }else{const edge=edgeById(state.selection.id);if(edge){edges.add(edge.id);nodes.add(edge.from);nodes.add(edge.to);}}
  return{nodes,edges,active:true};
}

function renderLayerToolbar(){
  const root=document.getElementById('layer-toolbar');root.innerHTML='';
  state.contract.layer_order.forEach(id=>{const button=document.createElement('button');button.type='button';button.className='layer-button';button.dataset.layer=id;button.textContent=L(state.contract.layer_labels[id]);button.setAttribute('aria-pressed',String(id===state.activeLayer));button.onclick=()=>{
    state.activeLayer=id;state.selection=null;state.diagnostic=null;state.stockSubview='map';
    if(['real','fiscal','financial'].includes(id))state.perspective='flow';
    if(id==='balance')state.perspective='stock';
    renderAll();
  };root.appendChild(button);});
}
function bindActivation(element,kind,id){const run=()=>selectMapObject(kind,id);element.onclick=run;element.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();run();}}}
function renderMap(){
  const edgesRoot=document.getElementById('map-edges'),nodesRoot=document.getElementById('map-nodes'),highlights=highlighted();edgesRoot.innerHTML='';nodesRoot.innerHTML='';
  visibleEdges().forEach(edge=>{const p=pathForEdge(edge),group=document.createElementNS(SVG_NS,'g');group.classList.add('edge-group');group.setAttribute('tabindex','0');group.setAttribute('role','button');group.setAttribute('aria-label',L(edge.label));const path=document.createElementNS(SVG_NS,'path');path.setAttribute('d',p.d);path.classList.add('map-edge',`epistemic-${epistemicClass(edge)}`);const hit=document.createElementNS(SVG_NS,'path');hit.setAttribute('d',p.d);hit.classList.add('edge-hit');const label=document.createElementNS(SVG_NS,'text');label.setAttribute('x',p.lx);label.setAttribute('y',p.ly);label.setAttribute('text-anchor','middle');label.classList.add('edge-label');label.textContent=L(edge.label);if(highlights.active&&!highlights.edges.has(edge.id)){path.classList.add('dimmed');label.classList.add('dimmed');}if(highlights.edges.has(edge.id))path.classList.add('related');group.append(path,hit,label);bindActivation(group,'edge',edge.id);edgesRoot.appendChild(group);});
  state.architecture.nodes.forEach(node=>{const group=document.createElementNS(SVG_NS,'g');group.classList.add('node');group.setAttribute('tabindex','0');group.setAttribute('role','button');group.setAttribute('aria-label',L(node.label));if(highlights.active&&!highlights.nodes.has(node.id))group.classList.add('dimmed');if(highlights.nodes.has(node.id))group.classList.add('related');if(state.selection?.kind==='node'&&state.selection.id===node.id)group.classList.add('selected');const rect=document.createElementNS(SVG_NS,'rect');rect.setAttribute('x',node.x-78);rect.setAttribute('y',node.y-38);rect.setAttribute('width',156);rect.setAttribute('height',76);const name=document.createElementNS(SVG_NS,'text');name.setAttribute('x',node.x);name.setAttribute('y',node.y+4);name.classList.add('node-name');name.textContent=L(node.short_label||node.label);group.append(rect,name);bindActivation(group,'node',node.id);nodesRoot.appendChild(group);});
  const empty=document.getElementById('map-empty-state');if(empty)empty.remove();if(!visibleEdges().length){const wrap=document.querySelector('.diagram-wrap'),p=document.createElement('p');p.id='map-empty-state';p.className='map-empty-state';p.textContent=state.lang==='ro'?'Nu există relații susținute pentru această combinație de vedere și layer.':'No supported relationships for this perspective and layer combination.';wrap.appendChild(p);}
}
function setPerspective(id){state.perspective=id;state.selection=null;state.diagnostic=null;state.stockSubview='map';if(id==='stock')state.activeLayer='balance';else state.activeLayer='financial';renderAll();}
function setView(view){state.stockSubview=view;document.getElementById('network-view').hidden=view!=='map';document.getElementById('matrix-view').hidden=view!=='matrix';document.getElementById('map-tab').setAttribute('aria-selected',String(view==='map'));document.getElementById('matrix-tab').setAttribute('aria-selected',String(view==='matrix'));if(view==='matrix')renderMatrix();}
function selectMapObject(kind,id){state.selection={kind,id};state.diagnostic=null;state.stockSubview='map';setView('map');renderMap();renderInspector();renderTheory();renderAuxiliary();document.getElementById('model-panel').scrollIntoView({behavior:'smooth',block:'start'});}

function relationButton(edge){return`<button class="link-button" data-edge="${edge.id}">${L(edge.label)} <small>${instrumentLabel(edge)} · ${fmt(edge.value)}${edge.value!==null&&edge.unit?` ${edge.unit}`:''}</small></button>`}
function relationList(edges){return edges.length?`<ul class="relation-list">${edges.map(edge=>`<li>${relationButton(edge)}</li>`).join('')}</ul>`:`<p class="empty-note">${U('none')}</p>`}
function uniqueCounterparties(id){const ids=new Set();financialPositions().forEach(edge=>{if(edge.holder===id&&edge.issuer)ids.add(edge.issuer);if(edge.issuer===id&&edge.holder)ids.add(edge.holder);});return[...ids].map(friendlyNode)}
function renderInspector(){
  const root=document.getElementById('map-inspector');
  if(!state.selection){root.innerHTML=`<p class="object-kicker">${state.perspective==='stock'?U('stock'):U('flow')}</p><h3>${state.lang==='ro'?'Ansamblul sistemului':'System overview'}</h3><p>${U('overview')}</p><p class="limit-note">${U('unknownZero')}</p>`;return;}
  if(state.selection.kind==='edge'){
    const edge=edgeById(state.selection.id),sources=(edge.sources||[]).map(sourceById).filter(Boolean),feedback=state.contract.feedback_overrides[edge.id];
    root.innerHTML=`<p class="object-kicker">${edge.layer==='feedback'?(state.lang==='ro'?'FEEDBACK CANDIDAT':'CANDIDATE FEEDBACK'):(state.lang==='ro'?'RELAȚIE':'RELATIONSHIP')}</p><h3>${L(edge.label)}</h3><dl>
      <dt>${U('definition')}</dt><dd>${L(edge.definition)}</dd>
      <dt>${U('direction')}</dt><dd>${friendlyNode(edge.from)} → ${friendlyNode(edge.to)}</dd>
      <dt>${U('holder')}</dt><dd>${edge.holder?friendlyNode(edge.holder):'—'}</dd>
      <dt>${U('issuer')}</dt><dd>${edge.issuer?friendlyNode(edge.issuer):'—'}</dd>
      <dt>${U('instrument')}</dt><dd>${instrumentLabel(edge)}</dd>
      <dt>${U('accounting')}</dt><dd>${accountingLabel(edge)}</dd>
      <dt>${U('epistemic')}</dt><dd><span class="status-pill status-${epistemicKind(edge).toLowerCase()}">${epistemicLabel(edge)}</span></dd>
      <dt>${U('value')}</dt><dd>${fmt(edge.value)}</dd>
      <dt>${U('period')}</dt><dd>${edge.period||'—'}</dd>
      <dt>${U('unit')}</dt><dd>${edge.unit||'—'}</dd>
      <dt>${U('propagation')}</dt><dd>${(edge.affects||[edge.from,edge.to]).map(friendlyNode).join(', ')}</dd>
      <dt>${U('limitations')}</dt><dd>${L(edge.limit)}</dd>
    </dl>
    ${feedback?`<section class="feedback-detail"><h4>${state.lang==='ro'?'Fișa mecanismului candidat':'Candidate mechanism record'}</h4><dl><dt>${U('feedbackMechanism')}</dt><dd>${L(feedback.mechanism)}</dd><dt>${U('feedbackSign')}</dt><dd>${L(feedback.hypothetical_sign)}</dd><dt>${U('evidenceStatus')}</dt><dd>${L(feedback.evidence_status)}</dd><dt>${U('parameterStatus')}</dt><dd>${L(feedback.parameter_status)}</dd><dt>${U('validationStatus')}</dt><dd>${L(feedback.validation_status)}</dd><dt>${U('requiredValidation')}</dt><dd>${L(feedback.required_before_simulation)}</dd></dl></section>`:''}
    <h4>${U('sources')}</h4>${sources.length?sources.map(source=>`<p><a href="${source.href}" target="_blank" rel="noreferrer">${L(source.label)}</a></p>`).join(''):`<p>${state.lang==='ro'?'Nicio sursă empirică potrivită atașată.':'No matched empirical source attached.'}</p>`}`;
    bindInspectorLinks();return;
  }
  const node=nodeById(state.selection.id),all=state.architecture.edges,positions=financialPositions(),funders=positions.filter(edge=>edge.issuer===node.id),funded=positions.filter(edge=>edge.holder===node.id),incoming=all.filter(edge=>edge.accounting_class!=='STOCK'&&edge.to===node.id),outgoing=all.filter(edge=>edge.accounting_class!=='STOCK'&&edge.from===node.id),counterparties=uniqueCounterparties(node.id);
  root.innerHTML=`<p class="object-kicker">${state.lang==='ro'?'SECTOR':'SECTOR'}</p><h3>${L(node.label)}</h3><p>${L(node.definition)}</p>
    <div class="sector-question"><h4>${U('whoFunds')}</h4>${relationList(funders)}</div>
    <div class="sector-question"><h4>${U('whoFunded')}</h4>${relationList(funded)}</div>
    <div class="sector-question"><h4>${U('whatOwns')} <small>${U('assets')}</small></h4>${relationList(funded)}</div>
    <div class="sector-question"><h4>${U('whatOwes')} <small>${U('liabilities')}</small></h4>${relationList(funders)}</div>
    <div class="net-position"><strong>${state.lang==='ro'?'Poziție financiară netă':'Net financial position'}:</strong> ${L(node.net_position)}</div>
    <div class="sector-question"><h4>${U('counterparties')}</h4><p>${counterparties.length?counterparties.join(', '):U('none')}</p></div>
    <div class="sector-question"><h4>${U('incoming')}</h4>${relationList(incoming)}</div>
    <div class="sector-question"><h4>${U('outgoing')}</h4>${relationList(outgoing)}</div>
    <div class="sector-question"><h4>${U('vulnerability')}</h4><p>${L(node.vulnerability)}</p><p class="limit-note">${L(node.limit)}</p></div>`;
  bindInspectorLinks();
}
function bindInspectorLinks(){document.querySelectorAll('#map-inspector [data-edge]').forEach(button=>button.onclick=()=>selectMapObject('edge',button.dataset.edge));}

function renderMatrix(){
  const select=document.getElementById('matrix-instrument'),thead=document.querySelector('#flow-matrix thead'),tbody=document.querySelector('#flow-matrix tbody'),positions=financialPositions(),instruments=[...new Set(positions.map(edge=>edge.instrument).filter(Boolean))].sort();
  if(!select.options.length){select.innerHTML=`<option value="ALL">${state.lang==='ro'?'Toate instrumentele reprezentate':'All represented instruments'}</option>`+instruments.map(value=>`<option value="${value}">${value}</option>`).join('');select.onchange=renderMatrix;}
  const selected=select.value||'ALL',sectors=state.architecture.nodes;
  thead.innerHTML=`<tr><th>Holder / creditor ↓<br>Issuer / debtor →</th>${sectors.map(node=>`<th>${L(node.short_label||node.label)}</th>`).join('')}</tr>`;tbody.innerHTML='';
  sectors.forEach(holder=>{const row=document.createElement('tr');row.innerHTML=`<th>${L(holder.short_label||holder.label)}</th>`;sectors.forEach(issuer=>{const matches=positions.filter(edge=>edge.holder===holder.id&&edge.issuer===issuer.id&&(selected==='ALL'||edge.instrument===selected)),cell=document.createElement('td');if(matches.length){cell.innerHTML=matches.map(edge=>`<button class="matrix-link" data-edge="${edge.id}"><strong>${instrumentLabel(edge)}</strong><br>${L(edge.label)}<br><span>${fmt(edge.value)}${edge.value!==null&&edge.unit?` ${edge.unit}`:''}</span></button>`).join('');}else cell.innerHTML=`<span class="matrix-missing">${state.lang==='ro'?'nerezolvat / nereprezentat':'unresolved / not represented'}</span>`;row.appendChild(cell);});tbody.appendChild(row);});
  tbody.querySelectorAll('[data-edge]').forEach(button=>button.onclick=()=>selectMapObject('edge',button.dataset.edge));document.getElementById('matrix-note').textContent=state.lang==='ro'?'Celulele arată numai creanțe bilaterale reprezentate. Nerezolvat nu înseamnă zero.':'Cells show only represented bilateral claims. Unresolved is not zero.';
}

function exposedSectors(diagnostic){const ids=new Set();(diagnostic.map_objects||[]).forEach(id=>{const node=nodeById(id),edge=edgeById(id);if(node)ids.add(node.id);if(edge){ids.add(edge.from);ids.add(edge.to);}});return[...ids].map(friendlyNode);}
function selectDiagnostic(id){
  state.diagnostic=state.architecture.diagnostics.find(item=>item.id===id);state.selection=null;state.stockSubview='map';const firstEdge=(state.diagnostic.map_objects||[]).map(edgeById).find(Boolean);if(firstEdge){state.activeLayer=firstEdge.layer;state.perspective=firstEdge.accounting_class==='STOCK'?'stock':'flow';}setView('map');renderAll();document.getElementById('model-panel').scrollIntoView({behavior:'smooth',block:'start'});
}
function renderDiagnostics(){
  const root=document.getElementById('diagnostic-cards');root.innerHTML='';state.architecture.diagnostics.forEach(diagnostic=>{const card=document.createElement('button');card.type='button';card.className='diagnostic-card'+(state.diagnostic?.id===diagnostic.id?' active':'');const benchmark=diagnostic.benchmark?`<p><strong>${state.lang==='ro'?'Benchmark compatibil':'Compatible benchmark'}:</strong> ${L(diagnostic.benchmark)}</p>`:'';card.innerHTML=`<span class="diag-state ${diagnostic.state_code||'info'}">${L(diagnostic.state)}</span><h3>${L(diagnostic.problem)}</h3><div class="diag-block"><strong>${U('current')}</strong><p class="diag-value">${L(diagnostic.value_trend)}</p></div>${benchmark}<div class="diag-block"><strong>${U('why')}</strong><p>${L(diagnostic.why)}</p></div><div class="diag-block"><strong>${U('exposed')}</strong><p>${exposedSectors(diagnostic).join(', ')}</p></div><div class="diag-block"><strong>${U('how')}</strong><p>${L(diagnostic.propagation)}</p></div><div class="diag-block"><strong>${U('evidence')}</strong><p>${L(diagnostic.source_note)}</p></div><div class="diag-block"><strong>${U('uncertainty')}</strong><p>${L(diagnostic.uncertainty)}</p></div>`;card.onclick=()=>selectDiagnostic(diagnostic.id);root.appendChild(card);});
}

const theoryAliases={'money-circuit':'money','credit-deposits':'credit','bnr-monetary-policy':'bnr','monetary-transmission':'feedback-loops','fiscal-debt':'public-debt','government-securities':'securities','feedback-delays':'feedback-loops','macro-imbalances':'macro-financial-imbalances','data-provenance':'model-limits','calibration-validation':'validation'};
function relevantChapterId(){if(state.selection){const object=state.selection.kind==='node'?nodeById(state.selection.id):edgeById(state.selection.id),raw=object?.theory||'money';return theoryAliases[raw]||raw;}if(state.diagnostic){const raw=state.diagnostic.theory||'macro-financial-imbalances';return theoryAliases[raw]||raw;}return state.perspective==='stock'?'flow-of-funds':'stocks-flows';}
function renderTheory(){const chapter=chapterById(relevantChapterId())||state.theory.chapters[0],root=document.getElementById('theory-context');root.innerHTML=`<p class="context-tag">${U('relevantChapter')}</p><h3>${L(chapter.title)}</h3><p>${L(chapter.summary)}</p>`;if(!state.readerMode)document.getElementById('theory-reader').hidden=true;}
function chapterHtml(chapter){return`<article class="manual-chapter" data-chapter="${chapter.id}"><h3>${L(chapter.title)}</h3><p class="chapter-summary">${L(chapter.summary)}</p>${chapter.sections.map(section=>`<section><h4>${L(section.heading)}</h4>${(section.paragraphs?.[state.lang]||section.paragraphs?.en||[]).map(p=>`<p>${p}</p>`).join('')}</section>`).join('')}</article>`}
function showReader(mode){state.readerMode=mode;const root=document.getElementById('theory-reader');root.hidden=false;if(mode==='chapter'){const chapter=chapterById(relevantChapterId())||state.theory.chapters[0];root.innerHTML=chapterHtml(chapter);}else if(mode==='manual'){root.innerHTML=`<div class="manual-index"><h3>${state.lang==='ro'?'Cuprins':'Contents'}</h3>${state.theory.chapters.map(chapter=>`<button type="button" data-jump="${chapter.id}">${L(chapter.title)}</button>`).join('')}</div>${state.theory.chapters.map(chapterHtml).join('')}`;root.querySelectorAll('[data-jump]').forEach(button=>button.onclick=()=>root.querySelector(`[data-chapter="${button.dataset.jump}"]`)?.scrollIntoView({behavior:'smooth',block:'start'}));}else if(mode==='glossary'){root.innerHTML=`<h3>${U('glossary')}</h3>`+state.theory.glossary.map(item=>`<p><strong>${L(item.term)}</strong> — ${L(item.definition)}</p>`).join('');}else{root.innerHTML=`<h3>${U('references')}</h3>`+state.theory.references.map(item=>`<p><a href="${item.href}" target="_blank" rel="noreferrer">${L(item.label)}</a></p>`).join('');}}

function renderAuxiliary(){
  const root=document.getElementById('auxiliary-content');
  if(state.diagnostic){const d=state.diagnostic;root.innerHTML=`<h3>${L(d.problem)}</h3><dl><dt>${U('evidence')}</dt><dd>${L(d.source_note)}</dd><dt>${U('uncertainty')}</dt><dd>${L(d.uncertainty)}</dd><dt>${U('exposed')}</dt><dd>${exposedSectors(d).join(', ')}</dd><dt>${U('how')}</dt><dd>${L(d.propagation)}</dd></dl>`;}
  else if(state.selection){const object=state.selection.kind==='node'?nodeById(state.selection.id):edgeById(state.selection.id);root.innerHTML=`<h3>${state.lang==='ro'?'Interpretarea selecției':'Selection interpretation'}</h3><p><strong>${U('epistemic')}:</strong> ${epistemicLabel(object)}</p><p><strong>${U('limitations')}:</strong> ${L(object.limit)}</p><p>${U('unknownZero')}</p>`;}
  else root.innerHTML=`<h3>${state.lang==='ro'?'Contract de dovezi':'Evidence contract'}</h3><p>${U('unknownZero')}</p><p>${state.lang==='ro'?'Pragurile instituționale sunt aplicate numai seriilor cu definiție, boundary, frecvență și transformare compatibile.':'Institutional thresholds are applied only to series with compatible definition, boundary, frequency and transformation.'}</p>`;
  renderTechnicalProvenance();
}
function renderTechnicalProvenance(){const root=document.getElementById('technical-provenance-content');if(!root)return;const object=state.selection?(state.selection.kind==='node'?nodeById(state.selection.id):edgeById(state.selection.id)):null;root.innerHTML=`<p>This collapsed section contains implementation provenance intentionally excluded from the normal product surface.</p><p><strong>Internal scientific gate:</strong> ${INTERNAL_SCIENCE_GATE}</p><p><strong>Validated behavioural reference mechanisms:</strong> ${state.contract.validated_behavioural_reference_mechanisms}</p>${object?`<p><strong>Internal object id:</strong> ${object.id}</p><p><strong>Raw epistemic role:</strong> ${object.epistemic_role}</p>`:''}<p><strong>Prospective Monetary Confirmation unchanged:</strong> ${state.contract.prospective_monetary_confirmation_unchanged}</p>`;}

function renderStressTests(){const root=document.getElementById('stress-tests');root.innerHTML='';state.architecture.stress_tests.forEach(test=>{const card=document.createElement('div');card.className='stress-card';card.innerHTML=`<span class="stress-label">ACCOUNTING / EXPOSURE STRESS TEST</span><h3>${L(test.name)}</h3><p>${L(test.description)}</p><label>${L(test.input_label)}<input type="number" step="${test.step}" value="${test.default_input}" min="${test.min}" max="${test.max}" data-stress-input="${test.id}"></label><button type="button" data-stress-run="${test.id}">${state.lang==='ro'?'Rulează testul mecanic':'Run mechanical test'}</button><p class="limit-note">${L(test.limit)}</p>`;root.appendChild(card);});root.querySelectorAll('[data-stress-run]').forEach(button=>button.onclick=()=>runStress(button.dataset.stressRun));}
function revealEdge(edgeId){const edge=edgeById(edgeId);if(!edge)return;state.selection={kind:'edge',id:edge.id};state.diagnostic=null;state.activeLayer=edge.layer;state.perspective=edge.accounting_class==='STOCK'?'stock':'flow';state.stockSubview='map';setView('map');renderAll();}
function runStress(id){
  const test=state.architecture.stress_tests.find(item=>item.id===id),input=Number(document.querySelector(`[data-stress-input="${id}"]`).value),output=document.getElementById('stress-output');let result='';
  if(test.formula==='fx_share_revaluation'){const gross=(test.exposure_share_pct*input/100).toFixed(2);result=state.lang==='ro'?`O variație FX de ${input}% aplicată mecanic ponderii observate de ${test.exposure_share_pct}% produce o modificare brută echivalentă cu ${gross}% din stocul total Maastricht, înainte de active valutare, hedging sau reacții.`:`A ${input}% FX move mechanically applied to the observed ${test.exposure_share_pct}% foreign-currency share gives a gross revaluation equivalent to ${gross}% of the total Maastricht debt stock, before FX assets, hedges or reactions.`;}
  else if(test.formula==='rollover_share'){const exposed=(test.base_share_pct*input/100).toFixed(2);result=state.lang==='ro'?`${exposed}% din portofoliul de referință este marcat mecanic ca principal supus rollover în banda de un an. Nu este generat un randament nou.`:`${exposed}% of the reference portfolio is mechanically marked as principal subject to one-year rollover. No new refinancing yield is generated.`;}
  else if(test.formula==='market_value'){result=state.lang==='ro'?`Șoc de valoare de ${input}% aplicat poziției selectate. Valoarea bilaterală a deținerii este nerezolvată, deci nu se fabrică o pierdere în RON și nu se simulează efect asupra capitalului.`:`A ${input}% value shock is applied to the selected exposure. The bilateral holding amount is unresolved, so no RON loss is fabricated and no capital response is simulated.`;}
  else if(test.formula==='bilateral_stock'){result=state.lang==='ro'?`Modificare directă de ${input}% asupra unui stoc bilateral: activul deținătorului și pasivul emitentului se modifică în aceeași magnitudine pe boundary-ul reprezentat. Baseline-ul monetar este nerezolvat, deci nu se inventează o sumă.`:`Direct ${input}% change to a bilateral stock: the holder asset and issuer liability move by the same magnitude on the represented boundary. The monetary baseline is unresolved, so no amount is invented.`;}
  output.innerHTML=`<span class="stress-label">ACCOUNTING / EXPOSURE STRESS TEST</span><h3>${L(test.name)}</h3><p>${result}</p><p><strong>${U('notForecast')}</strong> ${L(test.limit)}</p>`;revealEdge(test.map_edge);
}

function applyLanguage(){
  document.documentElement.lang=state.lang;document.getElementById('central-question').textContent=U('central');document.getElementById('model-heading').textContent=U('modelHeading');document.getElementById('model-intro').textContent=U('modelIntro');document.getElementById('stock-tab').textContent=U('stock');document.getElementById('flow-tab').textContent=U('flow');document.getElementById('map-tab').textContent=U('map');document.getElementById('matrix-tab').textContent=U('matrix');document.getElementById('reset-map').textContent=U('reset');document.getElementById('open-chapter').textContent=U('openChapter');document.getElementById('open-manual').textContent=U('openManual');document.getElementById('open-glossary').textContent=U('glossary');document.getElementById('open-references').textContent=U('references');document.querySelectorAll('[data-lang]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.lang===state.lang)));
}
function renderPerspectiveControls(){document.getElementById('stock-tab').setAttribute('aria-selected',String(state.perspective==='stock'));document.getElementById('flow-tab').setAttribute('aria-selected',String(state.perspective==='flow'));document.getElementById('perspective-description').textContent=L(state.contract.perspectives.find(item=>item.id===state.perspective).description);document.getElementById('stock-subview-controls').hidden=state.perspective!=='stock'||state.activeLayer==='feedback';if(state.perspective!=='stock'&&state.stockSubview==='matrix')state.stockSubview='map';setView(state.stockSubview);}
function renderAll(){applyLanguage();renderPerspectiveControls();renderLayerToolbar();renderMap();renderInspector();renderDiagnostics();renderTheory();renderAuxiliary();renderStressTests();}

async function loadJson(path){const response=await fetch(path);if(!response.ok)throw new Error(`Failed to load ${path}`);return response.json();}
async function init(){
  try{
    const [architecture,contract,theory,science]=await Promise.all([loadJson('public/product-architecture.json'),loadJson('public/product-contract-v2.json'),loadJson('public/theory-corpus-v2.json').catch(()=>loadJson(LEGACY_THEORY_PATH)),loadJson('public/model-stage.json')]);
    state.architecture=architecture;state.contract=contract;state.theory=theory;state.science=science;state.perspective=contract.default_perspective;state.activeLayer=contract.default_layer;
    document.getElementById('stock-tab').onclick=()=>setPerspective('stock');document.getElementById('flow-tab').onclick=()=>setPerspective('flow');document.getElementById('map-tab').onclick=()=>setView('map');document.getElementById('matrix-tab').onclick=()=>setView('matrix');document.getElementById('reset-map').onclick=()=>{state.selection=null;state.diagnostic=null;state.perspective=contract.default_perspective;state.activeLayer=contract.default_layer;state.stockSubview='map';renderAll();};document.getElementById('open-chapter').onclick=()=>showReader('chapter');document.getElementById('open-manual').onclick=()=>showReader('manual');document.getElementById('open-glossary').onclick=()=>showReader('glossary');document.getElementById('open-references').onclick=()=>showReader('references');document.querySelectorAll('[data-lang]').forEach(button=>button.onclick=()=>{state.lang=button.dataset.lang;state.readerMode=null;renderAll();});renderAll();
  }catch(error){document.getElementById('workspace').innerHTML=`<section class="panel"><h2>Product data failed to load</h2><p>${error.message}</p></section>`;console.error(error);}
}
init();
