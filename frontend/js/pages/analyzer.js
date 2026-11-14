(function () {
  const $ = id => document.getElementById(id);
  let current = null;
  let samples = {};

  function renderAnalysis(res, code) {
    current = { res, code };
    const catChips = Object.entries(res.categories).sort((a, b) => b[1] - a[1]).map(([c, n]) => `<span class="chip">${esc(c)} · ${n}</span>`).join('');
    $('an-summary').innerHTML =
      `<div class="label">Quality score</div><div class="score-row"><span class="score">${res.score}</span><span class="grade">Grade ${res.grade}</span></div>` +
      `<p class="sub" style="margin-top:6px">${res.findings.length} issue${res.findings.length === 1 ? '' : 's'} in ${res.loc} lines of ${langName(res.language)}</p>` +
      `<div class="chips">${SEV.map(s => `<span class="pill sev-${s}">${LBL[s]} ${res.counts[s]}</span>`).join('')}</div>` +
      `<div class="chips">${catChips || '<span class="chip">No categories</span>'}</div>` +
      `<div class="kv"><div><b>${res.loc}</b><span>lines of code</span></div><div><b>${res.decisions}</b><span>decision points</span></div><div><b>${res.density}</b><span>per 100 lines</span></div></div>`;
    const flagged = {};
    res.findings.forEach(f => { const cur = flagged[f.line]; if (!cur || SEV.indexOf(f.severity) < SEV.indexOf(cur)) flagged[f.line] = f.severity; });
    $('an-annotated').innerHTML = code.replace(/\r\n?/g, '\n').split('\n').map((l, i) => {
      const s = flagged[i + 1];
      return `<div class="cl${s ? ' flag sev-' + s : ''}"><span class="ln">${i + 1}</span><span>${esc(l) || ' '}</span></div>`;
    }).join('');
    $('an-count').textContent = res.findings.length ? `Findings (${res.findings.length}), highest risk first` : 'Findings';
    $('an-findings').innerHTML = res.findings.length
      ? res.findings.map(f => findingHTML(f, false)).join('')
      : '<li class="empty">No issues found by the detection rules. That does not prove the code is bug-free.</li>';
  }

  function clearResults(message) {
    $('an-summary').innerHTML = `<div class="empty">${message}</div>`;
    $('an-annotated').innerHTML = '';
    $('an-findings').innerHTML = '';
    $('an-count').textContent = 'Findings';
    current = null;
  }

  async function runAnalyzer() {
    const code = $('code-input').value;
    if (!code.trim()) { clearResults('Paste some code, or load a sample, then press Analyze.'); return; }
    try {
      renderAnalysis(await api.post('/api/analyze', { code, language: $('lang-select').value }), code);
    } catch (e) {
      if (!e.offline) $('an-summary').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  }

  function loadSample(key) {
    if (!samples[key]) return;
    $('code-input').value = samples[key].code;
    $('lang-select').value = 'auto';
    return runAnalyzer();
  }

  $('btn-analyze').addEventListener('click', runAnalyzer);
  $('btn-sample-js').addEventListener('click', () => loadSample('checkout'));
  $('btn-sample-py').addEventListener('click', () => loadSample('auth'));
  $('btn-clear').addEventListener('click', () => {
    $('code-input').value = '';
    $('lang-select').value = 'auto';
    runAnalyzer();
    $('code-input').focus();
  });
  $('code-input').addEventListener('paste', () => { $('lang-select').value = 'auto'; });

  $('btn-add-dash').addEventListener('click', async e => {
    const btn = e.currentTarget;
    const code = $('code-input').value;
    if (!code.trim()) { clearResults('Paste some code first, then add it to the dashboard.'); return; }
    try {
      const added = await api.post('/api/project/files', { code, language: $('lang-select').value });
      const note = $('added-note');
      note.hidden = false;
      note.innerHTML = `Added <code>${esc(added.name)}</code> to the project (${added.issues} issue${added.issues === 1 ? '' : 's'}). <a href="dashboard.html">Open the dashboard</a> or <a href="report.html">view the report</a>.`;
      flash(btn, 'Added');
    } catch (err) {
      if (!err.offline) { const note = $('added-note'); note.hidden = false; note.innerHTML = `<span class="err">${esc(err.message)}</span>`; }
    }
  });

  (async function start() {
    try {
      const list = await api.get('/api/samples');
      list.forEach(s => { samples[s.key] = s; });
      await loadSample('checkout');
    } catch (e) {
      if (!e.offline) clearResults(esc(e.message));
    }
  })();
})();
