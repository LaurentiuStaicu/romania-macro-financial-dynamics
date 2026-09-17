(() => {
  const baseRenderInspector = renderInspector;

  renderInspector = function renderInspectorWithChangeStatus() {
    baseRenderInspector();
    if (!state.selection || state.selection.kind !== 'node') return;

    const root = document.getElementById('map-inspector');
    if (!root || root.querySelector('.sector-change-summary')) return;

    const sectorId = state.selection.id;
    const touching = state.architecture.edges.filter(edge =>
      edge.from === sectorId || edge.to === sectorId || edge.holder === sectorId || edge.issuer === sectorId
    );
    const measuredChanges = touching.filter(edge =>
      ['FLOW', 'REVALUATION_OTHER_FLOW'].includes(edge.accounting_class) && edge.value !== null && edge.value !== undefined
    );
    const representedChangeChannels = touching.filter(edge =>
      ['FLOW', 'REVALUATION_OTHER_FLOW'].includes(edge.accounting_class)
    );

    const section = document.createElement('div');
    section.className = 'sector-question sector-change-summary';
    const title = state.lang === 'ro' ? 'CUM S-A SCHIMBAT?' : 'HOW HAS IT CHANGED?';
    let body;
    if (measuredChanges.length) {
      body = relationList(measuredChanges);
    } else if (representedChangeChannels.length) {
      body = `<p>${state.lang === 'ro'
        ? `Sunt reprezentate ${representedChangeChannels.length} canale de tranzacții/reevaluare, dar nu este afirmată aici o serie bilaterală completă care să cuantifice schimbarea stocului. Folosește FLOW VIEW pentru canalele susținute.`
        : `${representedChangeChannels.length} transaction/revaluation channels are represented, but no complete bilateral time series is asserted here to quantify the stock change. Use FLOW VIEW for the supported change channels.`}</p>`;
    } else {
      body = `<p>${state.lang === 'ro'
        ? 'Nu este integrată o serie bilaterală compatibilă pentru schimbarea acestei poziții. Necunoscut nu înseamnă zero.'
        : 'No compatible bilateral change series is integrated for this position. Unknown does not mean zero.'}</p>`;
    }
    section.innerHTML = `<h4>${title}</h4>${body}`;

    const netPosition = root.querySelector('.net-position');
    if (netPosition) netPosition.insertAdjacentElement('afterend', section);
    else root.appendChild(section);
    bindInspectorLinks();
  };
})();
