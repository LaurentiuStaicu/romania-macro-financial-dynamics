(() => {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const response = await nativeFetch(input, init);
    if (!url.endsWith('public/theory-corpus.json')) return response;
    const base = await response.clone().json();
    const supplement = await nativeFetch('public/theory-supplement.json').then(r => {
      if (!r.ok) throw new Error('Theory supplement unavailable');
      return r.json();
    });
    const merged = {...base, chapters:[...base.chapters, ...supplement.chapters]};
    return new Response(JSON.stringify(merged), {status:200, headers:{'Content-Type':'application/json'}});
  };
})();