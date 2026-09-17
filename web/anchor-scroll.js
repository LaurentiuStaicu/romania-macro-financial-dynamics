(() => {
  function revealTarget(target) {
    if (!target) return;
    if (target.tagName === 'DETAILS') target.open = true;
    const parentDetails = target.closest?.('details');
    if (parentDetails) parentDetails.open = true;
  }

  function scrollToRequestedSection() {
    if (!location.hash) return;
    const target = document.querySelector(location.hash);
    if (!target) return;
    revealTarget(target);
    target.scrollIntoView({behavior: 'auto', block: 'start'});
  }

  function rectanglesOverlap(a, b) {
    return a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  }

  function runVisualAudit() {
    if (!new URLSearchParams(location.search).has('visual-audit')) return;
    const panels = [...document.querySelectorAll('.panel')].filter(el => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.display !== 'none' && rect.width > 0 && rect.height > 0;
    });
    const overlaps = [];
    for (let i = 0; i < panels.length; i += 1) {
      for (let j = i + 1; j < panels.length; j += 1) {
        const a = panels[i];
        const b = panels[j];
        if (a.contains(b) || b.contains(a)) continue;
        if (rectanglesOverlap(a.getBoundingClientRect(), b.getBoundingClientRect())) {
          overlaps.push([a.id || a.className, b.id || b.className]);
        }
      }
    }
    const smallControls = [...document.querySelectorAll('button, select, input')]
      .filter(el => !el.closest('[hidden]') && getComputedStyle(el).display !== 'none')
      .filter(el => el.getBoundingClientRect().height > 0 && el.getBoundingClientRect().height < 34)
      .map(el => el.id || el.textContent.trim().slice(0, 40) || el.tagName);
    const result = {
      viewport: [innerWidth, innerHeight],
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
      panelOverlaps: overlaps,
      smallControls,
    };
    const pre = document.createElement('pre');
    pre.id = 'visual-audit-result';
    pre.hidden = true;
    pre.textContent = JSON.stringify(result);
    document.body.appendChild(pre);
  }

  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href^="#"]');
    if (!link) return;
    const target = document.querySelector(link.getAttribute('href'));
    revealTarget(target);
  });

  window.addEventListener('load', () => {
    setTimeout(scrollToRequestedSection, 1800);
    setTimeout(runVisualAudit, 2200);
  });
  window.addEventListener('hashchange', () => setTimeout(scrollToRequestedSection, 50));
})();
