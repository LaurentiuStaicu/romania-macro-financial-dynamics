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

  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href^="#"]');
    if (!link) return;
    const target = document.querySelector(link.getAttribute('href'));
    revealTarget(target);
  });

  window.addEventListener('load', () => setTimeout(scrollToRequestedSection, 1800));
  window.addEventListener('hashchange', () => setTimeout(scrollToRequestedSection, 50));
})();
