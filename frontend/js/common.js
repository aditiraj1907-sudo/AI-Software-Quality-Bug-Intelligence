// Helpers shared by every page: formatting, severity pills, bars, the trend chart, Markdown rendering.
const SEV = ['critical', 'high', 'medium', 'low'];
const LBL = { critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low' };

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function pct(x) { return Math.round((x || 0) * 100); }
function langName(l) { return l === 'py' ? 'Python' : l === 'js' ? 'JavaScript' : 'JS + Python'; }
function sevPill(s) { return `<span class="pill sev-${s}">${LBL[s]}</span>`; }

// One finding as an expandable list item. `f` has the shape returned by /api/findings and /api/analyze.
function findingHTML(f, showFile) {
  const probs = SEV.map(c => `${LBL[c]} ${pct(f.probs[c])}%`).join(' · ');
  return `<li class="finding sev-${f.severity}"><details><summary>${sevPill(f.severity)}<span class="ftitle">${esc(f.title)}</span><span class="frisk">risk ${f.risk}</span>` +
    `<span class="fmeta">${showFile ? esc(f.file) + ':' : 'line '}${f.line} · ${esc(f.category)}</span></summary>` +
    `<div class="fbody"><pre><code>${esc(f.code)}</code></pre>` +
    `<p><strong>Why it matters.</strong> ${esc(f.why)}</p>` +
    `<p><strong>Suggested fix.</strong> ${esc(f.fix)}</p><pre class="fix"><code>${esc(f.fixCode)}</code></pre>` +
    `<p class="model">Predicted ${LBL[f.severity]} (${pct(f.confidence)}% confidence) · ${probs}</p></div></details></li>`;
}

// Horizontal bars. entries: [label, count, cssClass]
function barRows(entries, max) {
  return entries.map(([label, n, cls]) =>
    `<div class="bar-row ${cls || ''}"><span class="lab" title="${esc(label)}">${esc(label)}</span><div class="track"><div class="fill" style="width:0" data-w="${max ? Math.round(n / max * 100) : 0}"></div></div><b>${n}</b></div>`).join('');
}
function animateBars(root) {
  const go = () => root.querySelectorAll('.fill[data-w]').forEach(el => { el.style.width = el.dataset.w + '%'; });
  (window.requestAnimationFrame || (f => setTimeout(f, 0)))(go);
}

function trendSVG(points) {
  if (points.length < 2) return '<p class="sub">The trend appears after the second scan.</p>';
  const W = 360, H = 160, pl = 30, pr = 16, pt = 18, pb = 24;
  const xs = i => pl + i * (W - pl - pr) / (points.length - 1);
  const ys = v => pt + (100 - v) / 100 * (H - pt - pb);
  const pts = points.map((v, i) => [xs(i), ys(v)]);
  const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const area = line + ` L${pts[pts.length - 1][0].toFixed(1)} ${ys(0)} L${pts[0][0].toFixed(1)} ${ys(0)} Z`;
  const grid = [0, 25, 50, 75, 100].map(v => `<path class="tg" d="M${pl} ${ys(v)} H${W - pr}"></path><text class="tt" x="${pl - 6}" y="${ys(v) + 3}" text-anchor="end">${v}</text>`).join('');
  const xl = points.map((v, i) => `<text class="tt" x="${xs(i).toFixed(1)}" y="${H - 6}" text-anchor="middle">${i === points.length - 1 ? 'Now' : i + 1}</text>`).join('');
  const last = pts[pts.length - 1];
  return `<svg class="trend" viewBox="0 0 ${W} ${H}" role="img" aria-label="Project quality score after each of the last ${points.length} changes, now ${points[points.length - 1]}">${grid}<path class="ta" d="${area}"></path><path class="tl" d="${line}"></path>${pts.slice(0, -1).map(p => `<circle class="tp" cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.5"></circle>`).join('')}<circle class="tp" cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="5"></circle><text class="tt" x="${last[0].toFixed(1)}" y="${(last[1] - 10).toFixed(1)}" text-anchor="middle" style="font-weight:600">${points[points.length - 1]}</text>${xl}</svg>`;
}

// Replace a <select>'s options, keeping the current choice when it still exists. pairs: [[value, label]]
function fillSelect(sel, pairs, label) {
  const keep = sel.value;
  sel.innerHTML = `<option value="">${esc(label)}</option>` + pairs.map(([v, t]) => `<option value="${esc(v)}">${esc(t)}</option>`).join('');
  if (pairs.some(p => p[0] === keep)) sel.value = keep;
}

function flash(btn, text) {
  const old = btn.dataset.label || btn.textContent;
  btn.dataset.label = old;
  btn.textContent = text;
  setTimeout(() => { btn.textContent = old; }, 1600);
}

// Minimal Markdown to HTML for the report: headings, tables, bullet lists, bold, inline code.
function md2html(md) {
  const L = md.split('\n'), out = [];
  let i = 0;
  const inl = s => esc(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, '<code>$1</code>');
  const cells = r => r.replace(/^\||\|$/g, '').split('|').map(s => s.trim());
  while (i < L.length) {
    const l = L[i];
    if (/^# /.test(l)) { out.push('<h3>' + inl(l.slice(2)) + '</h3>'); i++; }
    else if (/^## /.test(l)) { out.push('<h4>' + inl(l.slice(3)) + '</h4>'); i++; }
    else if (/^\|/.test(l)) {
      const rows = [];
      while (i < L.length && /^\|/.test(L[i])) { rows.push(L[i]); i++; }
      out.push('<div class="tw"><table><thead><tr>' + cells(rows[0]).map(h => '<th>' + inl(h) + '</th>').join('') + '</tr></thead><tbody>' +
        rows.slice(2).map(r => '<tr>' + cells(r).map(c => '<td>' + inl(c) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
    } else if (/^- /.test(l)) {
      const items = [];
      while (i < L.length && /^- /.test(L[i])) { items.push(L[i].slice(2)); i++; }
      out.push('<ul>' + items.map(x => '<li>' + inl(x) + '</li>').join('') + '</ul>');
    } else if (!l.trim()) { i++; }
    else { out.push('<p>' + inl(l) + '</p>'); i++; }
  }
  return out.join('');
}
