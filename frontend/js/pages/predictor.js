(function () {
  const $ = id => document.getElementById(id);

  async function runPrediction() {
    const text = $('triage-input').value.trim();
    if (!text) { $('triage-out').innerHTML = '<div class="empty">Describe a bug, or pick an example.</div>'; return; }
    try {
      const r = await api.post('/api/predict', { text });
      const best = r.severity;
      const cats = Object.entries(r.categoryProbabilities).slice(0, 4);
      const note = r.topTerms.length
        ? `Words that pushed it toward ${LBL[best]}: ${r.topTerms.map(w => `<code>${esc(w)}</code>`).join(', ')}.`
        : 'None of the words in this report were seen in training, so this is close to a guess from how common each severity is.';
      const caution = r.knownTerms && r.knownTerms < 3 ? ` Only ${r.knownTerms} known term${r.knownTerms === 1 ? '' : 's'}, so treat this with caution.` : '';
      $('triage-out').innerHTML =
        `<div class="label">Predicted severity</div><div class="big sev-${best}">${LBL[best]} <span class="sub" style="font:500 14px var(--font-mono)">${pct(r.confidence)}%</span></div>` +
        `<div class="tri-out">${barRows(SEV.map(c => [LBL[c], pct(r.severityProbabilities[c]), 'sev-' + c]), 100)}</div>` +
        `<div class="label" style="margin-top:16px">Predicted category</div><div class="big" style="font-size:22px;color:var(--ink)">${esc(r.category)} <span class="sub" style="font:500 14px var(--font-mono)">${pct(r.categoryConfidence)}%</span></div>` +
        `<div class="tri-out">${barRows(cats.map(([c, p]) => [c, pct(p), '']), 100)}</div>` +
        `<p class="sub" style="margin-top:10px">${note}${caution}</p>`;
      animateBars($('triage-out'));
    } catch (e) {
      if (!e.offline) $('triage-out').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    }
  }

  $('btn-triage').addEventListener('click', runPrediction);
  $('triage-chips').addEventListener('click', e => {
    const b = e.target.closest('[data-text]');
    if (!b) return;
    $('triage-input').value = b.dataset.text;
    runPrediction();
  });

  (async function start() {
    try {
      const m = await api.get('/api/model');
      $('model-info').textContent = `Trained on ${m.samples} labelled bug reports. Cross-validated accuracy: severity ${pct(m.severity.accuracy)}%, category ${pct(m.category.accuracy)}% (random guessing would score 25% and 14%). Treat the result as a triage hint.`;
      $('triage-input').value = 'Checkout crashes with a null pointer when the customer profile is missing';
      await runPrediction();
    } catch (e) { /* banner shown */ }
  })();
})();
