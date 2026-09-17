(() => {
  function scrollToRequestedSection() {
    if (!location.hash) return;
    const target = document.querySelector(location.hash);
    if (target) target.scrollIntoView({behavior: 'auto', block: 'start'});
  }
  window.addEventListener('load', () => {
    setTimeout(scrollToRequestedSection, 1800);
  });
  window.addEventListener('hashchange', () => {
    setTimeout(scrollToRequestedSection, 50);
  });
})();
