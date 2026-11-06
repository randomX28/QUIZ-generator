/* grading.js — TA answer entry and grading flow */

let loadedPaper = null;   // current paper loaded for grading
let currentPaperUid = ''; // UID of loaded paper
let activeQIndex = 0;     // currently focused question index for keyboard entry

function getNextPaperUid(uid) {
  const m = String(uid).match(/^(.*?)(\d+)$/);
  if (m) {
    const nextNum = parseInt(m[2]) + 1;
    return `${m[1]}${nextNum}`;
  }
  return '';
}

function updateActiveQuestionFocus(newIdx) {
  if (!loadedPaper || !loadedPaper.questions) return;
  const total = loadedPaper.questions.length;
  activeQIndex = Math.max(0, Math.min(newIdx, total - 1));

  document.querySelectorAll('.grade-question').forEach((card, idx) => {
    const isActive = (idx === activeQIndex);
    card.classList.toggle('active-grade-q', isActive);
    if (isActive) {
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  });
}

function selectOptionForActiveQuestion(key) {
  if (!loadedPaper || !loadedPaper.questions) return;
  const keyMap = { '1': 'a', '2': 'b', '3': 'c', '4': 'd', 'a': 'a', 'b': 'b', 'c': 'c', 'd': 'd' };
  const lbl = keyMap[key];
  if (!lbl) return;

  const q = loadedPaper.questions[activeQIndex];
  if (!q) return;

  const targetLabel = document.getElementById(`opt-${q.q_index}-${lbl}`);
  if (targetLabel) {
    document.querySelectorAll(`.grade-option[data-q="${q.q_index}"]`).forEach(l => l.classList.remove('selected'));
    targetLabel.classList.add('selected');
    const input = targetLabel.querySelector('input');
    if (input) input.checked = true;

    // Auto-advance to next question
    if (activeQIndex < loadedPaper.questions.length - 1) {
      updateActiveQuestionFocus(activeQIndex + 1);
    }
  }
}

// Global keyboard shortcuts for rapid grading
window.addEventListener('keydown', (e) => {
  // Only active when grading tab is visible and paper is loaded
  const tabGrading = document.getElementById('tab-grading');
  if (!tabGrading || !tabGrading.classList.contains('active') || !loadedPaper) return;

  // Don't intercept if user is actively typing in a text field
  const activeEl = document.activeElement;
  const isInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');

  if (isInput) {
    if (e.key === 'Enter' && activeEl.id === 'grade-roll-no') {
      // Focus the questions form on roll number enter
      updateActiveQuestionFocus(0);
      activeEl.blur();
    }
    return;
  }

  const k = e.key.toLowerCase();
  if (['1', '2', '3', '4', 'a', 'b', 'c', 'd'].includes(k)) {
    e.preventDefault();
    selectOptionForActiveQuestion(k);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    submitGrade();
  } else if (e.key === 'ArrowDown') {
    e.preventDefault();
    updateActiveQuestionFocus(activeQIndex + 1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    updateActiveQuestionFocus(activeQIndex - 1);
  }
});

// ── Step 1: Load paper by code ─────────────────────────────────────────────
document.getElementById('btn-load-paper').addEventListener('click', loadPaperForGrading);
document.getElementById('grade-paper-code').addEventListener('keydown', e => {
  if (e.key === 'Enter') loadPaperForGrading();
});
document.getElementById('btn-view-loaded-paper')?.addEventListener('click', () => {
  if (currentPaperUid) window.viewPaper?.(currentPaperUid);
});
document.getElementById('btn-view-loaded-key')?.addEventListener('click', () => {
  if (currentPaperUid) window.viewSolutionSheet?.(currentPaperUid);
});

async function loadPaperForGrading() {
  const rawUid = document.getElementById('grade-paper-code').value.trim().toUpperCase();
  if (!rawUid) return;

  const errEl = document.getElementById('load-error');
  errEl.classList.add('hidden');

  try {
    const paper = await apiFetch(`/api/grade/paper/${rawUid}`);
    loadedPaper = paper;
    currentPaperUid = rawUid;
    renderGradingForm(paper);
    // Show step 2
    document.getElementById('step-enter-answers').classList.remove('hidden');
    document.getElementById('step-result').classList.add('hidden');
    document.getElementById('loaded-paper-badge').textContent = rawUid;
    document.getElementById('grade-roll-no').value = '';
    document.getElementById('grade-roll-no').focus();
    toast(`Paper ${rawUid} loaded — ${paper.questions.length} questions`, 'success');
  } catch (e) {
    errEl.textContent = `✕ ${e.message}`;
    errEl.classList.remove('hidden');
  }
}

// ── Render question form ───────────────────────────────────────────────────
function renderGradingForm(paper) {
  const form = document.getElementById('questions-form');
  form.innerHTML = paper.questions.map(q => `
    <div class="grade-question" data-q="${q.q_index}">
      <div class="grade-q-num">Question ${q.q_index + 1}</div>
      <div class="grade-q-text">${esc(q.text)}</div>
      <div class="grade-options">
        ${['a', 'b', 'c', 'd'].map(lbl => `
          <label class="grade-option" id="opt-${q.q_index}-${lbl}" data-q="${q.q_index}" data-lbl="${lbl}">
            <input type="radio" name="q${q.q_index}" value="${lbl}" />
            <span class="opt-label">${lbl.toUpperCase()}</span>
            <span>${esc(q.options[lbl])}</span>
          </label>
        `).join('')}
      </div>
    </div>
  `).join('');

  // Radio click handlers — highlight selected option
  form.querySelectorAll('.grade-option').forEach(label => {
    label.addEventListener('click', () => {
      const qIdx = label.dataset.q;
      form.querySelectorAll(`.grade-option[data-q="${qIdx}"]`).forEach(l => l.classList.remove('selected'));
      label.classList.add('selected');
      label.querySelector('input').checked = true;
      updateActiveQuestionFocus(parseInt(qIdx));
    });
  });

  form.querySelectorAll('.grade-question').forEach((card, idx) => {
    card.addEventListener('click', () => updateActiveQuestionFocus(idx));
  });
  updateActiveQuestionFocus(0);
}

// ── Step 2: Submit and grade ───────────────────────────────────────────────
document.getElementById('btn-submit-grade').addEventListener('click', submitGrade);

const ROLL_NO_REGEX = /^[0-9]{2}[A-Z]{2}[0-9]{4}$/;

document.getElementById('grade-roll-no')?.addEventListener('input', (e) => {
  e.target.value = e.target.value.toUpperCase();
});

async function submitGrade() {
  const rollNo = document.getElementById('grade-roll-no').value.trim().toUpperCase();
  if (!rollNo) {
    toast('Please enter the student Roll Number.', 'error');
    document.getElementById('grade-roll-no').focus();
    return;
  }
  if (!ROLL_NO_REGEX.test(rollNo)) {
    toast('Invalid Roll Number! Format must be: 2 digits, 2 uppercase letters, 4 digits (e.g. 21CS0001)', 'error', 4000);
    document.getElementById('grade-roll-no').focus();
    return;
  }
  if (!loadedPaper) {
    toast('No paper loaded.', 'error');
    return;
  }

  // Collect selected options
  const responses = {};
  let unanswered = 0;
  loadedPaper.questions.forEach(q => {
    const checked = document.querySelector(`input[name="q${q.q_index}"]:checked`);
    if (checked) {
      responses[q.q_index] = checked.value;
    } else {
      unanswered++;
    }
  });

  if (unanswered > 0) {
    if (!confirm(`${unanswered} question(s) not answered. Unanswered questions will be marked wrong. Continue?`)) return;
  }

  const btn = document.getElementById('btn-submit-grade');
  btn.disabled = true;
  btn.textContent = 'Grading…';

  try {
    const result = await apiFetch('/api/grade', {
      method: 'POST',
      body: JSON.stringify({
        roll_no: rollNo,
        paper_uid: currentPaperUid,
        responses,
        entered_by: 'TA',
      })
    });
    renderResult(result);
    document.getElementById('step-result').classList.remove('hidden');
    document.getElementById('step-result').scrollIntoView({ behavior: 'smooth' });
    toast(`Graded: ${rollNo} scored ${result.score}/${result.total}`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '✓ Grade Student';
  }
}

// ── Render result ──────────────────────────────────────────────────────────
function renderResult(result) {
  const total = result.total || 10;
  const pass = result.score >= (total * 0.5);
  const pct = Math.round((result.score / total) * 100);

  const breakdownHtml = result.breakdown.map(item => `
    <div class="breakdown-item ${item.is_correct ? 'correct' : 'wrong'}">
      <span class="bd-icon">${item.is_correct ? '✓' : '✕'}</span>
      <div class="bd-body">
        <div class="bd-q">${esc(item.question_text)}</div>
        <div class="bd-ans">
          <span class="bd-chosen">Chosen: <strong>${esc(item.chosen_text)}</strong></span>
          ${!item.is_correct ? `<span class="bd-correct">✓ Correct: <strong>${esc(item.correct_text)}</strong></span>` : ''}
        </div>
      </div>
    </div>
  `).join('');

  document.getElementById('grade-result-display').innerHTML = `
    <div class="result-score">
      <div class="score-ring ${pass ? 'pass' : 'fail'}">
        <span>${result.score}/${result.total}</span>
      </div>
      <div class="score-meta">
        <div class="roll">${esc(result.roll_no)}</div>
        <div class="paper-code">Paper: ${esc(result.paper_uid)}</div>
        <div class="verdict" style="color:${pass ? 'var(--accent-green)' : 'var(--accent-red)'}">
          ${pass ? '✓ PASS' : '✕ FAIL'} — ${pct}%
        </div>
      </div>
    </div>
    <div class="breakdown-list">${breakdownHtml}</div>
  `;

  const nextBtn = document.getElementById('btn-grade-next');
  const nextUid = getNextPaperUid(result.paper_uid);
  if (nextBtn) {
    if (nextUid) {
      nextBtn.textContent = `⏭ Grade Next Paper (${nextUid})`;
      nextBtn.style.display = 'inline-flex';
      nextBtn.onclick = () => {
        document.getElementById('grade-paper-code').value = nextUid;
        loadPaperForGrading();
      };
    } else {
      nextBtn.style.display = 'none';
    }
  }
}

// ── "Grade Another" — keep same paper, reset form ─────────────────────────
document.getElementById('btn-grade-another').addEventListener('click', () => {
  document.getElementById('step-result').classList.add('hidden');
  document.getElementById('grade-roll-no').value = '';
  // Reset all radio buttons
  document.querySelectorAll('.grade-option').forEach(l => l.classList.remove('selected'));
  document.querySelectorAll('input[type=radio]').forEach(r => r.checked = false);
  document.getElementById('grade-roll-no').focus();
});

// ── "Change Paper" — reset everything ────────────────────────────────────
document.getElementById('btn-new-paper').addEventListener('click', () => {
  loadedPaper = null;
  currentPaperUid = '';
  document.getElementById('grade-paper-code').value = '';
  document.getElementById('step-enter-answers').classList.add('hidden');
  document.getElementById('step-result').classList.add('hidden');
  document.getElementById('load-error').classList.add('hidden');
  document.getElementById('grade-paper-code').focus();
});

// ── Clear answers ─────────────────────────────────────────────────────────
document.getElementById('btn-clear-grade').addEventListener('click', () => {
  document.getElementById('grade-roll-no').value = '';
  document.querySelectorAll('.grade-option').forEach(l => l.classList.remove('selected'));
  document.querySelectorAll('input[type=radio]').forEach(r => r.checked = false);
});

// ── Bulk Excel Upload ──────────────────────────────────────────────────────
const bulkFileInput = document.getElementById('bulk-grade-file-input');
if (bulkFileInput) {
  bulkFileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const banner = document.getElementById('bulk-grade-result');
    const content = document.getElementById('bulk-grade-content');
    banner.classList.remove('hidden');
    content.innerHTML = '<div class="loading-state">Evaluating Excel submissions…</div>';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/grade/upload-excel', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      let html = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
          <div style="font-weight:600; font-size:1.1rem; color:var(--text-primary);">
            📊 Bulk Evaluation Report
          </div>
          <button class="btn btn-ghost btn-sm" onclick="document.getElementById('bulk-grade-result').classList.add('hidden')">✕ Close</button>
        </div>
        <div style="display:flex; gap:1.5rem; margin-bottom:1rem; flex-wrap:wrap; font-size:0.95rem;">
          <div>Total Rows: <strong>${data.total_processed}</strong></div>
          <div style="color:var(--accent-green);">✓ Graded: <strong>${data.success_count}</strong></div>
          ${data.error_count > 0 ? `<div style="color:var(--accent-red);">✕ Issues: <strong>${data.error_count}</strong></div>` : ''}
        </div>
      `;

      if (data.results && data.results.length > 0) {
        html += `
          <div style="margin-top:0.5rem; margin-bottom:0.8rem;">
            <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.4rem;">Graded Students:</div>
            <div style="max-height:180px; overflow-y:auto; font-family:'JetBrains Mono', monospace; font-size:0.85rem; background:var(--bg-surface-high); border:1px solid var(--glass-border); padding:0.6rem 0.8rem; border-radius:var(--radius-sm); line-height:1.6; color:var(--text-primary);">
              ${data.results.map(r => `<div style="display:flex; justify-content:space-between; border-bottom:1px solid var(--glass-border); padding:2px 0;"><span>✓ Row ${r.row}: <strong>${esc(r.roll_no)}</strong> (${esc(r.paper_uid)})</span><span style="color:var(--accent-green);"><strong>${r.score}/${r.total}</strong></span></div>`).join('')}
            </div>
          </div>
        `;
      }

      if (data.errors && data.errors.length > 0) {
        html += `
          <div style="margin-top:0.8rem;">
            <div style="font-size:0.85rem; color:var(--accent-red); margin-bottom:0.4rem; font-weight:600;">⚠ Row Errors:</div>
            <div style="max-height:140px; overflow-y:auto; font-family:'JetBrains Mono', monospace; font-size:0.85rem; background:#fef2f2; border:1px solid #fecaca; padding:0.6rem 0.8rem; border-radius:var(--radius-sm); color:#b91c1c; line-height:1.6;">
              ${data.errors.map(err => `<div>• Row ${err.row} [${esc(err.roll_no || '—')}]: ${esc(err.error)}</div>`).join('')}
            </div>
          </div>
        `;
      }

      content.innerHTML = html;
      toast(`Evaluated ${data.success_count} student(s) successfully!`, 'success');
      window.loadResults?.();
    } catch (err) {
      content.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="color:var(--accent-red); font-weight:600;">✕ Upload Failed: ${esc(err.message)}</div>
          <button class="btn btn-ghost btn-sm" onclick="document.getElementById('bulk-grade-result').classList.add('hidden')">✕ Close</button>
        </div>
      `;
      toast(err.message, 'error');
    } finally {
      bulkFileInput.value = '';
    }
  });
}
