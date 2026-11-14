(function () {
  const $ = id => document.getElementById(id);

  $('btn-copy').addEventListener('click', async e => {
    const btn = e.currentTarget, ta = $('report-md');
    try { await navigator.clipboard.writeText(ta.value); flash(btn, 'Copied'); }
    catch (err) { $('report-src').open = true; ta.focus(); ta.select(); flash(btn, 'Press Ctrl+C to copy'); }
  });

  (async function start() {
    try {
      const r = await api.get('/api/report');
      $('report-md').value = r.markdown;
      $('report-view').innerHTML = md2html(r.markdown);
      $('report-basis').innerHTML = `Based on ${r.files} file${r.files === 1 ? '' : 's'}. <a href="dashboard.html">Manage files</a> · <a href="analyzer.html">Analyze more code</a>`;
    } catch (e) {
      if (!e.offline) $('report-view').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  })();
})();
