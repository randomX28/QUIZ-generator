/* answers.js — Master Answer Keys & Solution Sheets for TAs */

let allAnswerKeys = [];

function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function loadAnswerKeys() {
  const container = document.getElementById('answers-table-container');
  const countEl = document.getElementById('answers-count-badge');
  if (container) {
    container.innerHTML = '<div class="loading-state">Loading master answer keys…</div>';
  }
  if (window.withBank) {
    const akPdf = document.getElementById('link-ak-pdf');
    const akXls = document.getElementById('link-ak-excel');
    const akCsv = document.getElementById('link-ak-csv');
    if (akPdf) akPdf.href = window.withBank('/api/papers/answer-keys/pdf');
    if (akXls) akXls.href = window.withBank('/api/papers/answer-keys/export/excel');
    if (akCsv) akCsv.href = window.withBank('/api/papers/answer-keys/export/csv');
  }

  try {
    allAnswerKeys = await apiFetch(window.withBank ? window.withBank('/api/papers/answer-keys') : '/api/papers/answer-keys');
    if (countEl) {
      countEl.textContent = `${allAnswerKeys.length} Papers`;
    }
    renderAnswerKeysTable(allAnswerKeys);
    populateQuickCheckerPapers(allAnswerKeys);
  } catch (err) {
    if (container) {
      container.innerHTML = `<div class="error-msg">✕ Failed to load answer keys: ${esc(err.message)}</div>`;
    }
  }
}
window.loadAnswerKeys = loadAnswerKeys;

function getBadgeClass(letter) {
  const l = (letter || '').toUpperCase();
  if (l === 'A') return 'key-badge key-badge-a';
  if (l === 'B') return 'key-badge key-badge-b';
  if (l === 'C') return 'key-badge key-badge-c';
  if (l === 'D') return 'key-badge key-badge-d';
  return 'key-badge';
}

function renderAnswerKeysTable(papers) {
  const container = document.getElementById('answers-table-container');
  if (!container) return;

  if (!papers || papers.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔑</div>
        <div class="empty-title">No Answer Keys Found</div>
        <div class="empty-sub">Generate papers first in the "Papers" tab to view and export their answer keys.</div>
      </div>
    `;
    return;
  }

  const maxQ = Math.max(
    ...papers.map(p => (p.questions || []).length || Object.keys(p.keys || {}).length),
    5
  );
  const qIndices = Array.from({ length: maxQ }, (_, i) => i);

  const html = `
    <div class="table-responsive">
      <table class="data-table master-key-table">
        <thead>
          <tr>
            <th style="width:70px;text-align:center">#</th>
            <th style="width:140px">Paper Code</th>
            ${qIndices.map(i => `<th style="width:55px;text-align:center">Q${i + 1}</th>`).join('')}
            <th style="min-width:130px;text-align:center">Quick Key</th>
            <th style="text-align:right">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${papers.map(p => {
            const keys = p.keys || {};
            const pCount = (p.questions || []).length || Object.keys(keys).length || maxQ;
            const seqArr = [];
            for (let i = 0; i < pCount; i++) {
              seqArr.push(keys[String(i)] || '—');
            }
            const seq = seqArr.join(' ');

            return `
              <tr id="ak-row-${esc(p.uid)}">
                <td style="text-align:center;font-weight:600;color:var(--text-muted)">${p.paper_no}</td>
                <td>
                  <span class="paper-code-tag">${esc(p.uid)}</span>
                </td>
                ${qIndices.map(i => {
                  const ans = keys[String(i)] || '—';
                  return `<td style="text-align:center"><span class="${getBadgeClass(ans)}">${ans}</span></td>`;
                }).join('')}
                <td style="text-align:center">
                  <button class="btn btn-ghost btn-xs btn-copy-seq" data-seq="${esc(seq)}" title="Copy key sequence: ${seq}">
                    📋 ${seq}
                  </button>
                </td>
                <td style="text-align:right">
                  <div style="display:inline-flex;gap:0.4rem;align-items:center">
                    <button class="btn btn-ghost btn-sm" onclick="viewSolutionSheet('${esc(p.uid)}')">
                      👁 Solutions
                    </button>
                    <a class="btn btn-ghost btn-sm" href="/api/papers/${esc(p.uid)}/pdf" target="_blank" title="View Student Paper PDF">
                      📄 Paper
                    </a>
                  </div>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = html;

  // Hook up copy buttons
  container.querySelectorAll('.btn-copy-seq').forEach(btn => {
    btn.addEventListener('click', () => {
      const seq = btn.dataset.seq;
      navigator.clipboard?.writeText(seq).then(() => {
        toast(`Copied key: ${seq}`, 'success', 2000);
      }).catch(() => {
        toast(`Key: ${seq}`, 'info');
      });
    });
  });
}

function filterAnswerKeys() {
  const query = (document.getElementById('search-answers')?.value || '').trim().toLowerCase();
  if (!query) {
    renderAnswerKeysTable(allAnswerKeys);
    return;
  }

  const filtered = allAnswerKeys.filter(p => {
    const uid = (p.uid || '').toLowerCase();
    const no = String(p.paper_no || '');
    return uid.includes(query) || no === query;
  });

  renderAnswerKeysTable(filtered);
}

async function viewSolutionSheet(uid) {
  const modalBackdrop = document.getElementById('modal-solution-backdrop');
  const modalContent = document.getElementById('solution-modal-content');
  const titleUid = document.getElementById('solution-modal-uid');

  if (titleUid) titleUid.textContent = uid;
  if (modalContent) modalContent.innerHTML = '<div class="loading-state">Loading full solution sheet…</div>';
  if (modalBackdrop) modalBackdrop.classList.remove('hidden');

  try {
    const paper = await apiFetch(`/api/papers/${uid}/answer-key`);
    const questions = paper.questions || [];

    let questionsHtml = questions.map((q, idx) => {
      const opts = q.shuffled_options || {};
      const correctLabel = (q.correct_label || 'A').toLowerCase();

      return `
        <div class="solution-q-card">
          <div class="solution-q-header">
            <span class="solution-q-num">Question ${idx + 1}</span>
            <span class="solution-correct-badge">Correct: Option (${q.correct_label})</span>
          </div>
          <div class="solution-q-text">${(window.formatRichText || esc)(q.text)}</div>
          <div class="solution-options-grid">
            ${['a', 'b', 'c', 'd'].map(optKey => {
              const isCorrect = optKey === correctLabel;
              return `
                <div class="solution-opt-item ${isCorrect ? 'solution-opt-correct' : ''}">
                  <span class="opt-label">${optKey.toUpperCase()})</span>
                  <span class="opt-text">${(window.formatRichText || esc)(opts[optKey] || '')}</span>
                  ${isCorrect ? '<span class="correct-tag">✓ Correct Answer</span>' : ''}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');

    if (modalContent) {
      const subj = paper.subject_name || 'Compiler Design';
      const code = paper.course_code || 'NCSC302';
      const title = paper.exam_title || 'Quiz 1';
      const maxM = paper.max_marks || `${questions.length * 2} (2 marks per question)`;
      modalContent.innerHTML = `
        <div class="solution-sheet-container">
          <div class="solution-sheet-meta-bar">
            <div><strong>Subject:</strong> ${esc(subj)} (${esc(code)}) &nbsp;|&nbsp; <strong>${esc(title)}</strong></div>
            <div><strong>Paper Code:</strong> <span class="paper-code-tag">${esc(paper.uid)}</span></div>
            <div><strong>Total Marks:</strong> ${esc(maxM)}</div>
          </div>
          <div class="solution-questions-list">
            ${questionsHtml}
          </div>
        </div>
      `;
      if (window.renderMathInPage) {
        window.renderMathInPage(modalContent);
      }
    }
  } catch (err) {
    if (modalContent) {
      modalContent.innerHTML = `<div class="error-msg">✕ Failed to load solution sheet: ${esc(err.message)}</div>`;
    }
  }
}
window.viewSolutionSheet = viewSolutionSheet;

function closeSolutionModal() {
  document.getElementById('modal-solution-backdrop')?.classList.add('hidden');
}
window.closeSolutionModal = closeSolutionModal;

// Quick Checker functions
function populateQuickCheckerPapers(papers) {
  const select = document.getElementById('qc-paper-select');
  if (!select) return;

  const current = select.value;
  select.innerHTML = '<option value="">-- Select Paper Code --</option>';
  papers.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.uid;
    opt.textContent = `${p.uid} (Paper #${p.paper_no})`;
    select.appendChild(opt);
  });
  if (current) select.value = current;
}

function handleQuickChecker() {
  const select = document.getElementById('qc-paper-select');
  const resultEl = document.getElementById('qc-result-display');
  if (!select || !resultEl) return;

  const uid = select.value;
  if (!uid) {
    resultEl.innerHTML = '<div class="info-text">Select a paper code above to view its instant grading key.</div>';
    return;
  }

  const paper = allAnswerKeys.find(p => p.uid === uid);
  if (!paper) {
    resultEl.innerHTML = '<div class="error-msg">Paper not found.</div>';
    return;
  }

  const keys = paper.keys || {};
  const qCount = (paper.questions || []).length || Object.keys(keys).length || 5;
  const badgesHtml = Array.from({ length: qCount }, (_, i) => {
    const ans = keys[String(i)] || '—';
    return `<div class="qc-item"><span class="qc-label">Q${i + 1}</span><span class="${getBadgeClass(ans)}">${ans}</span></div>`;
  }).join('');

  resultEl.innerHTML = `
    <div class="qc-key-card">
      <div class="qc-key-title">Answer Key for <strong>${esc(paper.uid)}</strong> (Paper #${paper.paper_no} — ${qCount} Questions)</div>
      <div class="qc-badges-row" style="flex-wrap:wrap">
        ${badgesHtml}
      </div>
      <div style="margin-top:0.8rem;text-align:right">
        <button class="btn btn-ghost btn-sm" onclick="viewSolutionSheet('${esc(paper.uid)}')">👁 View Full Solutions</button>
      </div>
    </div>
  `;
}

// ── Initialization & Event Listeners ───────────────────────────────────────
function initAnswers() {
  document.getElementById('search-answers')?.addEventListener('input', filterAnswerKeys);
  document.getElementById('btn-refresh-answers')?.addEventListener('click', loadAnswerKeys);
  document.getElementById('modal-solution-close')?.addEventListener('click', closeSolutionModal);
  document.getElementById('btn-close-solution-modal')?.addEventListener('click', closeSolutionModal);
  document.getElementById('modal-solution-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'modal-solution-backdrop') closeSolutionModal();
  });
  document.getElementById('qc-paper-select')?.addEventListener('change', handleQuickChecker);

  if (document.getElementById('tab-answers')?.classList.contains('active')) {
    loadAnswerKeys();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnswers);
} else {
  initAnswers();
}



