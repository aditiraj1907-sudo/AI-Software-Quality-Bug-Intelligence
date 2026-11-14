(function () {
  const $ = id => document.getElementById(id);

  async function renderList() {
    const qs = new URLSearchParams();
    if ($('flt-sev').value) qs.set('severity', $('flt-sev').value);
    if ($('flt-cat').value) qs.set('category', $('flt-cat').value);
    if ($('flt-file').value) qs.set('file', $('flt-file').value);
    try {
      const [rows, project] = await Promise.all([api.get('/api/findings?' + qs), api.get('/api/project')]);
      $('dash-count').textContent = `Showing ${rows.length} of ${project.stats.issues}`;
      $('dash-list').innerHTML = rows.length ? rows.map(f => findingHTML(f, true)).join('') : '<li class="empty">No issues match these filters.</li>';
    } catch (e) { /* the banner already explains an unreachable backend */ }
  }

  function render(data) {
    const { files, stats, history } = data;
    $('dash-empty').hidden = files.length > 0;
    $('dash-body').hidden = files.length === 0;
    if (!files.length) return;

    $('dash-metrics').innerHTML =
      `<div class="metric"><small>Project quality</small><b>${stats.score}<span class="sub" style="font:600 15px var(--font-mono)"> ${stats.grade}</span></b></div>` +
      `<div class="metric"><small>Issues found</small><b>${stats.issues}</b></div>` +
      `<div class="metric sev-critical"><small>Critical + high</small><b style="color:var(--c)">${stats.counts.critical + stats.counts.high}</b></div>` +
      `<div class="metric"><small>Files · lines</small><b>${files.length}<span class="sub" style="font:500 15px var(--font-mono)"> · ${stats.loc}</span></b></div>`;

    const mx = Math.max(1, ...SEV.map(c => stats.counts[c]));
    $('dash-sev').innerHTML = barRows(SEV.map(c => [LBL[c], stats.counts[c], 'sev-' + c]), mx);
    const cats = Object.entries(stats.categories);
    $('dash-cat').innerHTML = cats.length ? barRows(cats.map(([c, n]) => [c, n, '']), Math.max(1, cats[0][1])) : '<p class="sub">No issues to categorize.</p>';
    $('dash-trend').innerHTML = trendSVG(history);

    $('dash-files').innerHTML =
      '<thead><tr><th>File</th><th>Language</th><th>Lines</th><th>Issues</th><th>Decisions / 100 lines</th><th>Score</th><th><span style="position:absolute;left:-9999px">Remove</span></th></tr></thead><tbody>' +
      files.map(f => {
        const col = f.score >= 80 ? 'sev-low' : f.score >= 55 ? 'sev-medium' : 'sev-critical';
        return `<tr><td class="mono">${esc(f.name)}</td><td>${langName(f.language)}</td><td class="num">${f.loc}</td><td class="num">${f.issues}</td><td class="num">${f.density}</td>` +
          `<td class="num ${col}"><span class="mini"><i style="width:${f.score}%"></i></span>${f.score} ${f.grade}</td>` +
          `<td><button class="x" type="button" data-rm="${f.id}" aria-label="Remove ${esc(f.name)} from the project">×</button></td></tr>`;
      }).join('') + '</tbody>';

    fillSelect($('flt-sev'), SEV.filter(c => stats.counts[c]).map(c => [c, LBL[c]]), 'All severities');
    fillSelect($('flt-cat'), cats.map(c => [c[0], c[0]]), 'All categories');
    fillSelect($('flt-file'), [...new Set(files.map(f => f.name))].map(n => [n, n]), 'All files');
    animateBars($('dash-body'));
    return renderList();
  }

  async function load() {
    try { await render(await api.get('/api/project')); } catch (e) { /* banner shown */ }
  }
  async function restore() {
    try { await render(await api.post('/api/project/reset')); } catch (e) { /* banner shown */ }
  }

  ['flt-sev', 'flt-cat', 'flt-file'].forEach(id => $(id).addEventListener('change', renderList));
  $('btn-reset').addEventListener('click', restore);
  $('btn-reset-empty').addEventListener('click', restore);
  $('dash-files').addEventListener('click', async e => {
    const b = e.target.closest('[data-rm]');
    if (!b) return;
    try { await api.del('/api/project/files/' + b.dataset.rm); await load(); } catch (err) { /* banner shown */ }
  });
  load();
})();
