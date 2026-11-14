(function () {
  const $ = id => document.getElementById(id);

  function metricsBlock(title, m) {
    const rows = Object.entries(m.per_class).sort((a, b) => b[1].support - a[1].support)
      .map(([name, v]) => `<tr><td>${esc(name)}</td><td class="num">${v.support}</td><td class="num">${v.precision.toFixed(2)}</td><td class="num">${v.recall.toFixed(2)}</td><td class="num">${v.f1.toFixed(2)}</td></tr>`).join('');
    return `<h4 style="margin:18px 0 6px;font-size:15px">${title}: accuracy ${pct(m.accuracy)}%, macro F1 ${m.macro_f1.toFixed(2)}</h4>` +
      `<div class="tw"><table><thead><tr><th>Class</th><th>Reports</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  (async function start() {
    try {
      const [rules, model] = await Promise.all([api.get('/api/rules'), api.get('/api/model')]);
      $('n-rules').textContent = rules.length;
      $('n-train').textContent = model.samples;
      $('rules-body').innerHTML = rules
        .sort((a, b) => a.category.localeCompare(b.category) || SEV.indexOf(a.defaultSeverity) - SEV.indexOf(b.defaultSeverity))
        .map(r => `<tr><td>${esc(r.title)}</td><td>${langName(r.language)}</td><td>${esc(r.category)}</td><td>${sevPill(r.defaultSeverity)}</td><td>${sevPill(r.predictedSeverity)} <span class="sub mono">${pct(r.confidence)}%</span></td></tr>`).join('');
      $('model-card').innerHTML =
        `<p style="font-size:14px">${esc(model.algorithm)}, trained on ${model.samples} labelled bug reports. ` +
        `Scores below come from ${model.severity.folds}-fold cross-validation, so each report was predicted by a model that had not seen it.</p>` +
        metricsBlock('Severity', model.severity) + metricsBlock('Category', model.category) +
        `<p class="sub" style="margin-top:12px">With about ${model.samples} reports and subjective labels, these scores are modest. Add rows to <code>ml/data/bug_reports.csv</code> and run <code>python -m ml.train</code> to improve them.</p>`;
    } catch (e) {
      if (!e.offline) $('model-card').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  })();
})();
