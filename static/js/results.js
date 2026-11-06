/* results.js — Results dashboard, stats, distribution chart, CSV export, nullify */

// ── Load all results & stats ───────────────────────────────────────────────
async function loadResults(silent = false) {
  try {
    await Promise.all([loadStats(), loadResultsTable()]);
    if (!silent) {
      toast('Results and statistics refreshed', 'info', 2000);
    }
  } catch (e) {
    console.error('Failed to refresh results:', e);
  }
}
window.loadResults = loadResults;

// ── Stats ──────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const stats = await apiFetch(window.withBank ? window.withBank('/api/results/stats') : '/api/results/stats');
    const totalMarks = stats.total_marks || 10;
    document.getElementById('stat-count').textContent = stats.count ?? '0';
    document.getElementById('stat-avg').textContent   = stats.count ? `${stats.average}/${totalMarks}` : '—';
    document.getElementById('stat-pass').textContent  = stats.count ? `${stats.pass_rate}%` : '—';
    document.getElementById('stat-max').textContent   = stats.count ? `${stats.max}/${totalMarks}` : '—';

    renderDistribution(stats.distribution || {}, stats.count || 0, totalMarks);
  } catch (e) {
    console.warn('Stats load failed:', e.message);
  }
}

// ── Distribution chart ─────────────────────────────────────────────────────
function renderDistribution(dist, total, totalMarks = 10) {
  const chart = document.getElementById('distribution-chart');
  if (!chart) return;

  if (!total) {
    chart.innerHTML = '<div style="color:var(--text-muted);font-size:0.85rem;align-self:center;padding:1.5rem">No results recorded yet</div>';
    return;
  }

  const step = totalMarks <= 12 ? 2 : Math.max(2, Math.ceil(totalMarks / 10));
  const scoreBuckets = [];
  for (let s = 0; s <= totalMarks; s += step) {
    scoreBuckets.push(s);
  }
  if (scoreBuckets[scoreBuckets.length - 1] !== totalMarks) {
    scoreBuckets.push(totalMarks);
  }

  const maxVal = Math.max(...Object.values(dist).map(v => Number(v) || 0), 1);

  chart.innerHTML = scoreBuckets.map(score => {
    const count = dist[String(score)] || 0;
    const heightPct = Math.max(Math.round((count / maxVal) * 100), count > 0 ? 8 : 0);
    const ratio = totalMarks > 0 ? (score / totalMarks) : 0;
    const color = ratio >= 0.8 ? 'var(--accent-green)'
                : ratio >= 0.6 ? 'var(--accent-cyan)'
                : ratio >= 0.4 ? 'var(--accent-amber)'
                : 'var(--accent-red)';

    return `
      <div class="dist-bar-col">
        <div class="dist-count">${count}</div>
        <div class="dist-bar-wrap">
          <div class="dist-bar" style="height:${heightPct}%;background:${color}" title="${count} students scored ${score}/${totalMarks}"></div>
        </div>
        <div class="dist-label">${score}</div>
      </div>
    `;
  }).join('');
}

// ── Results table ──────────────────────────────────────────────────────────
async function loadResultsTable() {
  const wrap = document.getElementById('results-table-wrap');
  if (!wrap) return;

  wrap.innerHTML = '<div class="loading-state">Loading results…</div>';
  try {
    const results = await apiFetch(window.withBank ? window.withBank('/api/results') : '/api/results');
    if (!results.length) {
      wrap.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📊</div>
          <div class="empty-title">No Results Yet</div>
          <div class="empty-sub">Use the <strong>TA Grading</strong> tab to enter single answers or bulk-upload an Excel sheet.</div>
        </div>
      `;
      return;
    }

    wrap.innerHTML = `
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:70px;text-align:center">#</th>
              <th>Roll Number</th>
              <th>Paper Code</th>
              <th style="text-align:center">Score</th>
              <th>Graded By</th>
              <th>Date & Time</th>
              <th style="text-align:right">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${results.map((r, idx) => {
              const total = r.total || 10;
              const scoreClass = r.score >= (total * 0.8) ? 'score-high'
                               : r.score >= (total * 0.5) ? 'score-mid'
                               : 'score-low';
              return `
                <tr id="result-row-${r.id}">
                  <td style="text-align:center;color:var(--text-muted);font-weight:600">${idx + 1}</td>
                  <td><span class="mono" style="font-weight:600">${esc(r.roll_no)}</span></td>
                  <td>
                    <button class="btn btn-ghost btn-sm mono" style="padding:0.2rem 0.5rem;font-size:0.78rem;" onclick="window.viewPaper('${esc(r.paper_uid)}')">
                      👁 ${esc(r.paper_uid)}
                    </button>
                  </td>
                  <td style="text-align:center">
                    <span class="score-pill ${scoreClass}">${r.score}/${total}</span>
                  </td>
                  <td style="color:var(--text-secondary)">${esc(r.entered_by || 'TA')}</td>
                  <td style="color:var(--text-muted);font-size:0.78rem">${new Date(r.entered_at).toLocaleString()}</td>
                  <td style="text-align:right">
                    <div style="display:inline-flex;gap:0.4rem;align-items:center">
                      <button class="btn btn-ghost btn-sm" onclick="quickViewBreakdown('${esc(r.roll_no)}')">
                        🔍 Details
                      </button>
                      <button class="btn btn-danger btn-sm" onclick="deleteSingleResult(${r.id}, '${esc(r.roll_no)}')">
                        🗑 Delete
                      </button>
                    </div>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    wrap.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
  }
}

// ── Nullify All Results ────────────────────────────────────────────────────
async function nullifyAllResults() {
  const confirmed = confirm(
    '⚠️ NULLIFY ALL RESULTS?\n\n' +
    'Are you sure you want to delete and reset ALL graded student results?\n' +
    'This will erase all scores and statistics permanently.\n\n' +
    'Click OK to proceed with nullifying all results.'
  );

  if (!confirmed) return;

  try {
    const res = await apiFetch(window.withBank ? window.withBank('/api/results') : '/api/results', { method: 'DELETE' });
    toast(res.message || 'All results have been nullified', 'success', 3500);
    // Clear lookup search
    const lookupRes = document.getElementById('lookup-result');
    if (lookupRes) {
      lookupRes.innerHTML = '';
      lookupRes.classList.add('hidden');
    }
    await loadResults(true);
  } catch (e) {
    toast(`Failed to nullify results: ${e.message}`, 'error');
  }
}
window.nullifyAllResults = nullifyAllResults;

// ── Delete Single Student Result ───────────────────────────────────────────
async function deleteSingleResult(id, rollNo) {
  const confirmed = confirm(`Delete graded result for student ${rollNo}?`);
  if (!confirmed) return;

  try {
    await apiFetch(`/api/results/${id}`, { method: 'DELETE' });
    toast(`Result for ${rollNo} deleted`, 'info', 2500);
    await loadResults(true);
  } catch (e) {
    toast(`Failed to delete result: ${e.message}`, 'error');
  }
}
window.deleteSingleResult = deleteSingleResult;

// ── Roll number lookup ─────────────────────────────────────────────────────
async function lookupRoll() {
  const rollNo = (document.getElementById('lookup-roll')?.value || '').trim();
  if (!rollNo) return;
  const resultEl = document.getElementById('lookup-result');
  if (!resultEl) return;

  resultEl.classList.add('hidden');
  resultEl.innerHTML = '<div class="loading-state">Searching…</div>';
  resultEl.classList.remove('hidden');

  try {
    const baseRollUrl = `/api/results/roll/${encodeURIComponent(rollNo)}`;
    const results = await apiFetch(window.withBank ? window.withBank(baseRollUrl) : baseRollUrl);
    if (!results || !results.length) {
      resultEl.innerHTML = `<div class="empty-state" style="padding:1rem"><div class="empty-text">No results found for roll number <strong>${esc(rollNo)}</strong>.</div></div>`;
      return;
    }

    resultEl.innerHTML = results.map(r => {
      const total = r.total || 10;
      const pass = r.score >= (total * 0.5);
      const breakdownHtml = (r.breakdown || []).map(item => {
        const maxM = item.max_marks ?? 2;
        return `
        <div class="breakdown-item ${item.is_correct ? 'correct' : 'wrong'}" style="margin-bottom:0.4rem">
          <span class="bd-icon">${item.is_correct ? '✓' : '✕'}</span>
          <div class="bd-body">
            <div class="bd-q" style="font-size:0.84rem"><strong>Q${(item.q_index ?? 0) + 1}:</strong> ${esc(item.question_text)}</div>
            <div class="bd-ans" style="font-size:0.8rem;margin-top:0.2rem">
              <span class="bd-chosen">Chosen: <strong>${esc(item.chosen_text)}</strong></span>
              ${!item.is_correct ? `<span class="bd-correct" style="margin-left:0.75rem">✓ Correct: <strong>${esc(item.correct_text)}</strong></span>` : ''}
              <span style="margin-left:auto;font-weight:600;color:${item.is_correct ? 'var(--accent-green)' : 'var(--accent-red)'}">
                ${item.marks ?? (item.is_correct ? maxM : 0)}/${maxM} marks
              </span>
            </div>
          </div>
        </div>
      `;
      }).join('');

      return `
        <div class="glass-card" style="margin-top:1rem;padding:1.25rem">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:1rem;flex-wrap:wrap">
            <div style="display:flex;align-items:center;gap:1rem">
              <div class="score-ring ${pass ? 'pass' : 'fail'}" style="width:60px;height:60px;font-size:1.15rem">
                ${r.score}/${total}
              </div>
              <div>
                <div style="font-weight:700;font-size:1.05rem;font-family:'JetBrains Mono',monospace">${esc(r.roll_no)}</div>
                <div style="font-size:0.82rem;color:var(--text-muted)">Paper: <span class="paper-code-tag">${esc(r.paper_uid)}</span></div>
                <div style="font-size:0.84rem;font-weight:600;margin-top:0.15rem;color:${pass ? 'var(--accent-green)' : 'var(--accent-red)'}">
                  ${pass ? '✓ PASS' : '✕ FAIL'}
                </div>
              </div>
            </div>
            <div style="display:flex;gap:0.5rem">
              <button class="btn btn-ghost btn-sm" onclick="window.viewSolutionSheet('${esc(r.paper_uid)}')">🔑 Solution Sheet</button>
              <button class="btn btn-danger btn-sm" onclick="deleteSingleResult(${r.id}, '${esc(r.roll_no)}')">🗑 Delete</button>
            </div>
          </div>
          <div class="breakdown-list">${breakdownHtml}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    resultEl.innerHTML = `<div class="error-msg">✕ ${esc(e.message)}</div>`;
  }
}
window.lookupRoll = lookupRoll;

function quickViewBreakdown(rollNo) {
  const input = document.getElementById('lookup-roll');
  if (input) {
    input.value = rollNo;
    lookupRoll();
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
window.quickViewBreakdown = quickViewBreakdown;

// ── Initialization & Event Listeners ───────────────────────────────────────
function initResults() {
  document.getElementById('btn-refresh-results')?.addEventListener('click', () => loadResults());
  document.getElementById('btn-refresh-results-top')?.addEventListener('click', () => loadResults());
  document.getElementById('btn-nullify-all-results')?.addEventListener('click', nullifyAllResults);
  document.getElementById('btn-nullify-all-results-tbl')?.addEventListener('click', nullifyAllResults);
  document.getElementById('btn-export-csv')?.addEventListener('click', () => {
    window.open(window.withBank ? window.withBank('/api/results/export/csv') : '/api/results/export/csv', '_blank');
  });

  document.getElementById('lookup-roll')?.addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
  });
  document.getElementById('btn-lookup')?.addEventListener('click', lookupRoll);
  document.getElementById('lookup-roll')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') lookupRoll();
  });

  if (document.getElementById('tab-results')?.classList.contains('active')) {
    loadResults(true);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initResults);
} else {
  initResults();
}
