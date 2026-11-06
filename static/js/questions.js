/* questions.js — Question bank CRUD, search/filtering, KaTeX rendering, and file imports */

window.allQuestions = [];
window.editingId = null;
window.currentPool = 'all';
let pendingLatexFile = null;

// ── Rich Text & Math Rendering Helpers ─────────────────────────────────────
function formatRichText(raw) {
  if (!raw) return '';
  let str = (window.esc || esc)(raw);

  // 1. Code blocks: \begin{lstlisting} ... \end{lstlisting}
  str = str.replace(/\\begin\{lstlisting\}([\s\S]*?)\\end\{lstlisting\}/g, (_, code) => {
    return `<pre class="q-code-snippet"><code>${code.trim()}</code></pre>`;
  });

  // 2. Inline verbatim / code: \verb|...| and \texttt{...}
  str = str.replace(/\\verb([^\w\s])(.*?)\1/g, (_, delim, code) => {
    return `<code class="q-inline-code">${code}</code>`;
  });
  str = str.replace(/\\texttt\{([^}]+)\}/g, (_, inner) => {
    return `<code class="q-inline-code">${inner}</code>`;
  });

  // 3. LaTeX text styling macros: \emph, \textit, \textbf, \underline
  str = str.replace(/\\emph\{([^}]+)\}/g, '<em>$1</em>');
  str = str.replace(/\\textit\{([^}]+)\}/g, '<em>$1</em>');
  str = str.replace(/\\textbf\{([^}]+)\}/g, '<strong>$1</strong>');
  str = str.replace(/\\underline\{([^}]+)\}/g, '<u>$1</u>');
  str = str.replace(/\\textsf\{([^}]+)\}/g, '<span style="font-family:sans-serif">$1</span>');
  str = str.replace(/\\textsc\{([^}]+)\}/g, '<span style="font-variant:small-caps">$1</span>');

  // 4. LaTeX quotation marks & dashes
  str = str.replace(/``([^'']+)''/g, '“$1”');
  str = str.replace(/`([^']*)'/g, '‘$1’');
  str = str.replace(/---/g, '—');
  str = str.replace(/--/g, '–');
  str = str.replace(/\\ldots/g, '…');
  str = str.replace(/\\dots/g, '…');

  // 5. LaTeX spacing macros outside / between math blocks
  // e.g. $S \rightarrow Aa \mid b$, \quad $A \rightarrow Sc \mid d$
  str = str.replace(/\\qquad\b/g, '&emsp;&emsp;');
  str = str.replace(/\\quad\b/g, '&emsp;');
  str = str.replace(/\\,\b/g, '&thinsp;');
  str = str.replace(/\\;\b/g, '&ensp;');
  str = str.replace(/\\:\b/g, '&ensp;');
  str = str.replace(/\\ /g, '&nbsp;');

  // 6. Stray arrow or separator macros
  str = str.replace(/\\rightarrow\b/g, '→');
  str = str.replace(/\\to\b/g, '→');
  str = str.replace(/\\Rightarrow\b/g, '⇒');

  return str;
}
window.formatRichText = formatRichText;

function renderMathInPage(targetEl) {
  if (typeof renderMathInElement === 'function') {
    try {
      renderMathInElement(targetEl || document.body, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false }
        ],
        throwOnError: false,
        ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"]
      });
    } catch (e) {
      console.warn("KaTeX render error:", e);
    }
  }
}
window.renderMathInPage = renderMathInPage;

// ── Load Questions ─────────────────────────────────────────────────────────
async function loadQuestions() {
  const list = document.getElementById('question-list');
  if (!list) return;
  list.innerHTML = '<div class="loading-state">Loading…</div>';
  try {
    window.allQuestions = await apiFetch(window.withBank ? window.withBank('/api/questions') : '/api/questions');
    window.renderPoolTabs?.();
    renderQuestions();
    window.refreshPoolStatus?.();
  } catch (e) {
    list.innerHTML = `<div class="error-msg">${e.message}</div>`;
  }
}
window.loadQuestions = loadQuestions;

// ── Render Questions List ──────────────────────────────────────────────────
function renderQuestions() {
  const list = document.getElementById('question-list');
  if (!list) return;
  const searchInput = document.getElementById('q-search-input');
  const filterTypeEl = document.getElementById('q-filter-type');
  const filterDiffEl = document.getElementById('q-filter-difficulty');
  const countIndicator = document.getElementById('q-count-indicator');
  const clearBtn = document.getElementById('q-search-clear');

  const query = (searchInput?.value || '').trim().toLowerCase();
  const filterType = filterTypeEl?.value || 'all';
  const filterDiff = filterDiffEl?.value || 'all';
  const curPool = window.currentPool || 'all';

  if (clearBtn) {
    clearBtn.classList.toggle('hidden', !query);
  }

  let filtered = curPool === 'all'
    ? window.allQuestions
    : window.allQuestions.filter(q => q.pool_id === parseInt(curPool));

  if (filterType !== 'all') {
    filtered = filtered.filter(q => (q.question_type || 'objective') === filterType);
  }

  if (filterDiff !== 'all') {
    filtered = filtered.filter(q => (q.difficulty || 'MEDIUM').toUpperCase() === filterDiff);
  }

  if (query) {
    filtered = filtered.filter(q => {
      const textMatch = (q.text || '').toLowerCase().includes(query);
      const optMatch = [q.option_a, q.option_b, q.option_c, q.option_d].some(o => (o || '').toLowerCase().includes(query));
      const topicMatch = (q.topic || '').toLowerCase().includes(query);
      return textMatch || optMatch || topicMatch;
    });
  }

  if (countIndicator) {
    const totalInPool = curPool === 'all'
      ? window.allQuestions.length
      : window.allQuestions.filter(q => q.pool_id === parseInt(curPool)).length;
    countIndicator.textContent = query || filterType !== 'all'
      ? `Showing ${filtered.length} of ${totalInPool}`
      : `${totalInPool} question${totalInPool === 1 ? '' : 's'}`;
  }

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🔍</div>
      <div class="empty-text">
        ${query ? `No questions match "<strong>${esc(query)}</strong>".` : `No questions in ${curPool === 'all' ? 'the bank' : `Pool ${curPool}`} yet.<br>Click <strong>Add Question</strong> to get started.`}
      </div>
    </div>`;
    return;
  }

  list.innerHTML = filtered.map(q => {
    const isSubj = q.question_type === 'subjective';
    let optHtml = '';
    if (!isSubj && (q.option_a || q.option_b || q.option_c || q.option_d)) {
      const opts = [
        { label: 'A', text: q.option_a },
        { label: 'B', text: q.option_b },
        { label: 'C', text: q.option_c },
        { label: 'D', text: q.option_d },
      ];
      optHtml = `
        <div class="q-options-grid">
          ${opts.map(o => {
            const isCorrect = (o.text && o.text === q.correct_opt) || (q.correct_opt && o.label.toLowerCase() === q.correct_opt.toLowerCase());
            return `
              <div class="q-option-card ${isCorrect ? 'correct' : ''}">
                <span class="q-option-letter">${o.label}</span>
                <span class="q-option-text">${formatRichText(o.text)}</span>
                ${isCorrect ? '<span class="q-option-correct-badge">✓ Correct</span>' : ''}
              </div>
            `;
          }).join('')}
        </div>
      `;
    }
    const diff = (q.difficulty || 'MEDIUM').toUpperCase();
    const diffColors = {
      EASY: 'background:rgba(16,185,129,0.12);color:#059669',
      MEDIUM: 'background:rgba(245,158,11,0.12);color:#d97706',
      HARD: 'background:rgba(239,68,68,0.12);color:#dc2626'
    };
    const diffBadge = `<span class="q-tag" style="${diffColors[diff] || diffColors.MEDIUM};font-weight:600">${diff}</span>`;
    const coBadge = q.co_tag ? `<span class="q-tag" style="background:rgba(99,102,241,0.12);color:#4f46e5;font-weight:600">${esc(q.co_tag)}</span>` : '';

    return `
    <div class="question-card" data-id="${q.id}">
      <div class="q-pool-badge pool-${((q.pool_id - 1) % 5) + 1}">P${q.pool_id}</div>
      <div class="q-body">
        <div class="q-text">
          ${formatRichText(q.text)}
          ${isSubj ? '<span class="badge-subjective" style="margin-left:0.5rem;font-size:0.68rem">Subjective</span>' : ''}
        </div>
        ${optHtml}
        <div class="q-meta">
          <span class="q-tag" style="background:rgba(59,130,246,0.12);color:var(--accent-blue);font-weight:600">${q.marks || (isSubj ? 10 : 2)} Marks</span>
          ${diffBadge}
          ${coBadge}
          ${q.topic ? `<span class="q-tag">${esc(q.topic)}</span>` : ''}
          <span class="q-used">Used ${q.times_used}×</span>
        </div>
      </div>
      <div class="q-actions">
        <button class="btn btn-ghost btn-sm" onclick="openEditModal(${q.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteQuestion(${q.id})">Delete</button>
      </div>
    </div>`;
  }).join('');

  renderMathInPage(list);
}
window.renderQuestions = renderQuestions;

// ── Modal Question Controls ────────────────────────────────────────────────
function setQuestionType(type) {
  const isObj = (type === 'objective');
  document.getElementById('f-question-type').value = isObj ? 'objective' : 'subjective';
  document.getElementById('q-toggle-objective')?.classList.toggle('active', isObj);
  document.getElementById('q-toggle-subjective')?.classList.toggle('active', !isObj);
  const mcqWrap = document.getElementById('mcq-options-container');
  if (mcqWrap) mcqWrap.style.display = isObj ? 'block' : 'none';

  const marksEl = document.getElementById('f-marks');
  if (marksEl) {
    const cur = parseInt(marksEl.value);
    if (!cur || cur === 2 || cur === 10) {
      marksEl.value = isObj ? 2 : 10;
    }
  }
}

function syncCorrectOption(opt) {
  const norm = (opt || '').toLowerCase();
  const selectEl = document.getElementById('f-correct');
  if (selectEl) selectEl.value = norm;
  ['a', 'b', 'c', 'd'].forEach(letter => {
    const row = document.getElementById(`opt-row-${letter}`);
    const radio = document.querySelector(`input[name="opt-correct-radio"][value="${letter}"]`);
    const isThis = (letter === norm);
    if (row) row.classList.toggle('is-correct', isThis);
    if (radio) radio.checked = isThis;
  });
}

function openAddModal() {
  window.editingId = null;
  document.getElementById('modal-title').textContent = 'Add Question';
  document.getElementById('question-form').reset();
  window.renderPoolSelects?.();
  if (window.currentPool !== 'all') {
    document.getElementById('f-pool').value = String(window.currentPool);
  }
  setQuestionType('objective');
  syncCorrectOption('');
  const marksEl = document.getElementById('f-marks');
  if (marksEl) marksEl.value = 2;
  const diffEl = document.getElementById('f-difficulty');
  if (diffEl) diffEl.value = 'MEDIUM';
  const coEl = document.getElementById('f-co-tag');
  if (coEl) coEl.value = '';
  document.getElementById('form-error').classList.add('hidden');
  document.getElementById('modal-backdrop').classList.remove('hidden');
  document.getElementById('f-text').focus();
}

function openEditModal(id) {
  const q = window.allQuestions.find(x => x.id === id);
  if (!q) return;
  window.editingId = id;
  document.getElementById('modal-title').textContent = 'Edit Question';
  window.renderPoolSelects?.();
  setQuestionType(q.question_type || 'objective');
  document.getElementById('f-pool').value = q.pool_id;
  document.getElementById('f-topic').value = q.topic || '';
  document.getElementById('f-text').value = q.text;
  const marksEl = document.getElementById('f-marks');
  if (marksEl) marksEl.value = (q.marks !== undefined && q.marks !== null) ? q.marks : (q.question_type === 'subjective' ? 10 : 2);
  const diffEl = document.getElementById('f-difficulty');
  if (diffEl) diffEl.value = (q.difficulty || 'MEDIUM').toUpperCase();
  const coEl = document.getElementById('f-co-tag');
  if (coEl) coEl.value = q.co_tag || '';
  document.getElementById('f-opt-a').value = q.option_a || '';
  document.getElementById('f-opt-b').value = q.option_b || '';
  document.getElementById('f-opt-c').value = q.option_c || '';
  document.getElementById('f-opt-d').value = q.option_d || '';
  // Set correct option selector
  const labelMap = { a: q.option_a, b: q.option_b, c: q.option_c, d: q.option_d };
  let correctLabel = Object.entries(labelMap).find(([, v]) => v && v === q.correct_opt)?.[0] || '';
  if (!correctLabel && q.correct_opt && ['a', 'b', 'c', 'd'].includes(q.correct_opt.toLowerCase())) {
    correctLabel = q.correct_opt.toLowerCase();
  }
  syncCorrectOption(correctLabel);
  document.getElementById('form-error').classList.add('hidden');
  document.getElementById('modal-backdrop').classList.remove('hidden');
}
window.openEditModal = openEditModal;

function closeModal() {
  document.getElementById('modal-backdrop').classList.add('hidden');
}

async function deleteQuestion(id) {
  if (!confirm('Delete this question?')) return;
  try {
    await apiFetch(`/api/questions/${id}`, { method: 'DELETE' });
    toast('Question deleted', 'info');
    await window.loadPools?.();
    loadQuestions();
  } catch (e) {
    toast(e.message, 'error');
  }
}
window.deleteQuestion = deleteQuestion;

// ── Clear Bank Modal ───────────────────────────────────────────────────────
function openClearBankModal() {
  window.renderPoolSelects?.();
  const scopeSelect = document.getElementById('clear-scope-select');
  if (scopeSelect) {
    scopeSelect.value = (window.currentPool && window.currentPool !== 'all') ? window.currentPool : 'all';
  }
  const chk = document.getElementById('confirm-clear-checkbox');
  if (chk) chk.checked = false;

  const btnConfirm = document.getElementById('btn-confirm-clear');
  if (btnConfirm) {
    btnConfirm.disabled = true;
    btnConfirm.style.opacity = '0.5';
    btnConfirm.style.cursor = 'not-allowed';
    btnConfirm.innerHTML = '<span>🗑️</span> Yes, Clear Questions';
  }

  const errEl = document.getElementById('clear-error');
  if (errEl) {
    errEl.textContent = '';
    errEl.classList.add('hidden');
  }

  document.getElementById('modal-clear-bank-backdrop')?.classList.remove('hidden');
}

function closeClearBankModal() {
  document.getElementById('modal-clear-bank-backdrop')?.classList.add('hidden');
}

// ── Master LaTeX Import Modal ──────────────────────────────────────────────
function openLatexImportModal(file) {
  pendingLatexFile = file;
  const fnEl = document.getElementById('latex-import-filename');
  if (fnEl) fnEl.textContent = file.name;

  const poolsList = window.getPools?.() || [];
  const wrap = document.getElementById('latex-existing-pools-wrap');
  if (wrap) {
    if (poolsList.length) {
      wrap.innerHTML = poolsList.map(p => `
        <label class="checkbox-label" style="font-size:0.82rem;cursor:pointer">
          <input type="checkbox" class="latex-target-pool-chk" value="${p.pool_no}" checked />
          <span>${esc(window.poolName ? window.poolName(p.pool_no) : `Pool ${p.pool_no}`)} <span style="color:var(--text-muted)">(${p.count})</span></span>
        </label>
      `).join('');
    } else {
      wrap.innerHTML = '<div style="font-size:0.8rem;color:var(--text-muted)">No existing pools — will create new pools.</div>';
    }
  }

  const modeExisting = document.getElementById('latex-mode-existing');
  const modeNew = document.getElementById('latex-mode-new');
  const newWrap = document.getElementById('latex-new-pools-wrap');
  if (poolsList.length > 0) {
    if (modeExisting) modeExisting.checked = true;
    if (newWrap) newWrap.classList.add('hidden');
    if (wrap) wrap.classList.remove('hidden');
  } else {
    if (modeNew) modeNew.checked = true;
    if (newWrap) newWrap.classList.remove('hidden');
    if (wrap) wrap.classList.add('hidden');
  }

  document.getElementById('modal-latex-import-backdrop')?.classList.remove('hidden');
}

function closeLatexImportModal() {
  pendingLatexFile = null;
  document.getElementById('modal-latex-import-backdrop')?.classList.add('hidden');
}

// ── Interactive Staging & Dry-Run Preview Modal ────────────────────────────
let stagedConfirmCallback = null;

function openImportPreviewModal(previewData, onConfirm) {
  const backdrop = document.getElementById('modal-import-preview-backdrop');
  if (!backdrop) return;

  const chipsWrap = document.getElementById('preview-stat-chips');
  const warnBox = document.getElementById('preview-warnings-box');
  const listWrap = document.getElementById('preview-question-list');
  const countLabel = document.getElementById('preview-count-label');

  if (chipsWrap) {
    chipsWrap.innerHTML = `
      <span class="badge-objective" style="font-size:0.75rem;padding:0.3rem 0.75rem">
        Total Found: <strong>${previewData.total_found ?? 0}</strong>
      </span>
      <span style="font-size:0.75rem;padding:0.3rem 0.75rem;border-radius:var(--radius-full);background:var(--primary-container);color:var(--on-primary-container);font-weight:700">
        Objective (MCQ): ${previewData.objective_count ?? 0}
      </span>
      <span style="font-size:0.75rem;padding:0.3rem 0.75rem;border-radius:var(--radius-full);background:var(--tertiary-container);color:var(--on-tertiary-container);font-weight:700">
        Subjective: ${previewData.subjective_count ?? 0}
      </span>
      ${(previewData.duplicates || 0) > 0 ? `
        <span style="font-size:0.75rem;padding:0.3rem 0.75rem;border-radius:var(--radius-full);background:rgba(239,68,68,0.15);color:var(--accent-red);font-weight:700">
          Duplicates in DB: ${previewData.duplicates}
        </span>
      ` : ''}
      ${(previewData.missing_answers || 0) > 0 ? `
        <span style="font-size:0.75rem;padding:0.3rem 0.75rem;border-radius:var(--radius-full);background:rgba(245,158,11,0.2);color:var(--accent-gold);font-weight:700">
          Missing Answers: ${previewData.missing_answers}
        </span>
      ` : ''}
    `;
  }

  if (warnBox) {
    if ((previewData.warnings || []).length > 0) {
      warnBox.classList.remove('hidden');
      warnBox.textContent = previewData.warnings.map(w => '⚠ ' + w).join('\n');
    } else {
      warnBox.classList.add('hidden');
      warnBox.textContent = '';
    }
  }

  const questions = previewData.questions || [];
  if (countLabel) countLabel.textContent = `Showing ${questions.length} question(s) staged`;

  if (listWrap) {
    listWrap.innerHTML = questions.map((q, idx) => {
      const isSubj = q.question_type === 'subjective';
      const isDup = q.is_duplicate;
      return `
        <div style="background:var(--bg-surface);border:1px solid ${isDup ? 'rgba(239,68,68,0.4)' : 'var(--glass-border)'};border-radius:var(--radius-md);padding:0.75rem 1rem;display:flex;flex-direction:column;gap:0.4rem;box-shadow:var(--elevation-1)">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;flex-wrap:wrap">
            <div style="display:flex;align-items:center;gap:0.4rem;flex-wrap:wrap">
              <span style="font-weight:800;font-size:0.8rem;color:var(--text-muted)">#${idx + 1}</span>
              <span class="${isSubj ? 'badge-subjective' : 'badge-objective'}" style="font-size:0.7rem;padding:0.15rem 0.5rem">
                ${isSubj ? 'Subjective' : 'Objective'}
              </span>
              <span style="font-size:0.7rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--bg-surface-high);color:var(--text-secondary);font-weight:600">
                Pool ${q.pool_id || 1}
              </span>
              <span style="font-size:0.7rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--bg-surface-high);color:var(--text-secondary);font-weight:600">
                ${q.marks || (isSubj ? 5 : 2)} Marks
              </span>
              <span style="font-size:0.7rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--bg-surface-high);color:var(--accent-blue);font-weight:700">
                ${q.difficulty || 'MEDIUM'}
              </span>
              ${q.co_tag ? `<span style="font-size:0.7rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--tertiary-container);color:var(--on-tertiary-container);font-weight:700">${esc(q.co_tag)}</span>` : ''}
              ${q.topic ? `<span style="font-size:0.7rem;padding:0.15rem 0.5rem;border-radius:var(--radius-full);background:var(--bg-surface-high);color:var(--text-muted)">${esc(q.topic)}</span>` : ''}
            </div>
            ${isDup ? `<span style="font-size:0.72rem;font-weight:700;color:var(--accent-red);background:rgba(239,68,68,0.12);padding:0.15rem 0.5rem;border-radius:var(--radius-full)">⚠ Duplicate in Bank</span>` : ''}
          </div>
          <div style="font-size:0.88rem;font-weight:600;color:var(--text-primary);line-height:1.45">
            ${formatRichText(q.text)}
          </div>
          ${!isSubj ? `
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0.35rem;font-size:0.78rem;margin-top:0.2rem">
              ${['a', 'b', 'c', 'd'].map(optKey => {
                const optVal = q['option_' + optKey] || '';
                const isCorrect = (q.correct_label || '').toLowerCase() === optKey || (q.correct_opt && q.correct_opt === optVal);
                return `
                  <div style="display:flex;align-items:center;gap:0.35rem;padding:0.25rem 0.45rem;border-radius:var(--radius-xs);background:${isCorrect ? 'rgba(16,185,129,0.15)' : 'var(--bg-surface-high)'};border:1px solid ${isCorrect ? 'rgba(16,185,129,0.4)' : 'transparent'};color:${isCorrect ? 'var(--accent-green)' : 'var(--text-secondary)'};font-weight:${isCorrect ? '700' : '500'}">
                    <span style="font-family:'JetBrains Mono',monospace;font-weight:700">(${optKey.toUpperCase()})</span>
                    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${formatRichText(optVal)}</span>
                    ${isCorrect ? `<span style="margin-left:auto;font-size:0.68rem">✓ Correct</span>` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    if (window.renderMathInElement) {
      try {
        renderMathInElement(listWrap, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '$',  right: '$',  display: false },
          ],
          throwOnError: false,
        });
      } catch(e) {}
    }
  }

  stagedConfirmCallback = onConfirm;
  backdrop.classList.remove('hidden');
}

function closeImportPreviewModal() {
  document.getElementById('modal-import-preview-backdrop')?.classList.add('hidden');
  stagedConfirmCallback = null;
}

// ── Event Bindings ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Live search and filter
  const searchInput = document.getElementById('q-search-input');
  const filterTypeEl = document.getElementById('q-filter-type');
  const filterDiffEl = document.getElementById('q-filter-difficulty');
  const clearBtn = document.getElementById('q-search-clear');

  searchInput?.addEventListener('input', renderQuestions);
  filterTypeEl?.addEventListener('change', renderQuestions);
  filterDiffEl?.addEventListener('change', renderQuestions);
  clearBtn?.addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    renderQuestions();
    searchInput?.focus();
  });

  // Modal actions
  document.getElementById('btn-add-question')?.addEventListener('click', openAddModal);
  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('btn-cancel')?.addEventListener('click', closeModal);
  document.getElementById('modal-backdrop')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-backdrop')) closeModal();
  });

  document.getElementById('q-toggle-objective')?.addEventListener('click', () => setQuestionType('objective'));
  document.getElementById('q-toggle-subjective')?.addEventListener('click', () => setQuestionType('subjective'));

  // Option radio selection sync
  document.querySelectorAll('input[name="opt-correct-radio"]').forEach(radio => {
    radio.addEventListener('change', () => {
      if (radio.checked) syncCorrectOption(radio.value);
    });
  });
  document.getElementById('f-correct')?.addEventListener('change', (e) => {
    syncCorrectOption(e.target.value);
  });

  // Save question
  document.getElementById('btn-save-question')?.addEventListener('click', async () => {
    const errEl = document.getElementById('form-error');
    errEl.classList.add('hidden');

    const pool_id = parseInt(document.getElementById('f-pool').value);
    const topic = document.getElementById('f-topic').value.trim() || null;
    const text = document.getElementById('f-text').value.trim();
    const question_type = document.getElementById('f-question-type')?.value || 'objective';
    const marks = parseInt(document.getElementById('f-marks').value) || (question_type === 'subjective' ? 10 : 2);
    const difficulty = (document.getElementById('f-difficulty')?.value || 'MEDIUM').toUpperCase();
    const co_tag = (document.getElementById('f-co-tag')?.value || '').trim();

    let option_a = '', option_b = '', option_c = '', option_d = '', correct_opt = '';

    if (question_type === 'objective') {
      option_a = document.getElementById('f-opt-a').value.trim();
      option_b = document.getElementById('f-opt-b').value.trim();
      option_c = document.getElementById('f-opt-c').value.trim();
      option_d = document.getElementById('f-opt-d').value.trim();
      const correctLabel = document.getElementById('f-correct').value;

      if (!text || !option_a || !option_b || !option_c || !option_d || !correctLabel) {
        errEl.textContent = 'Please fill in question text, all 4 options, and select the correct option.';
        errEl.classList.remove('hidden');
        return;
      }
      const labelMap = { a: option_a, b: option_b, c: option_c, d: option_d };
      correct_opt = labelMap[correctLabel];
    } else {
      if (!text) {
        errEl.textContent = 'Please enter the question text.';
        errEl.classList.remove('hidden');
        return;
      }
    }

    const bank_id = window.getBankId ? window.getBankId() : 1;
    const body = { text, option_a, option_b, option_c, option_d, correct_opt, pool_id, topic, question_type, marks, bank_id, difficulty, co_tag };

    try {
      if (window.editingId) {
        await apiFetch(`/api/questions/${window.editingId}`, { method: 'PUT', body: JSON.stringify(body) });
        toast('Question updated', 'success');
      } else {
        await apiFetch('/api/questions', { method: 'POST', body: JSON.stringify(body) });
        toast('Question added', 'success');
      }
      closeModal();
      await window.loadPools?.();
      loadQuestions();
    } catch (e) {
      errEl.textContent = e.message;
      errEl.classList.remove('hidden');
    }
  });

  // Clear bank modal
  document.getElementById('btn-open-clear-modal')?.addEventListener('click', openClearBankModal);
  document.getElementById('modal-clear-bank-close')?.addEventListener('click', closeClearBankModal);
  document.getElementById('btn-cancel-clear')?.addEventListener('click', closeClearBankModal);
  document.getElementById('modal-clear-bank-backdrop')?.addEventListener('click', e => {
    if (e.target === document.getElementById('modal-clear-bank-backdrop')) closeClearBankModal();
  });

  document.getElementById('confirm-clear-checkbox')?.addEventListener('change', function () {
    const btnConfirm = document.getElementById('btn-confirm-clear');
    if (btnConfirm) {
      btnConfirm.disabled = !this.checked;
      btnConfirm.style.opacity = this.checked ? '1' : '0.5';
      btnConfirm.style.cursor = this.checked ? 'pointer' : 'not-allowed';
    }
  });

  document.getElementById('btn-confirm-clear')?.addEventListener('click', async () => {
    const chk = document.getElementById('confirm-clear-checkbox');
    if (!chk || !chk.checked) return;

    const btnConfirm = document.getElementById('btn-confirm-clear');
    const errEl = document.getElementById('clear-error');
    errEl?.classList.add('hidden');

    btnConfirm.disabled = true;
    btnConfirm.innerHTML = '<span>⏳</span> Clearing...';

    const scope = document.getElementById('clear-scope-select')?.value || 'all';
    const base = scope === 'all' ? '/api/questions/clear' : `/api/questions/clear?pool_id=${scope}`;
    const url = window.withBank ? window.withBank(base) : base;

    try {
      const res = await apiFetch(url, { method: 'DELETE' });
      toast(res.message || 'Question bank cleared', 'success');
      closeClearBankModal();
      await window.loadPools?.();
      loadQuestions();
    } catch (e) {
      if (errEl) {
        errEl.textContent = e.message || 'Failed to clear questions';
        errEl.classList.remove('hidden');
      } else {
        toast(e.message, 'error');
      }
      btnConfirm.disabled = false;
      btnConfirm.innerHTML = '<span>🗑️</span> Yes, Clear Questions';
    }
  });

  // Excel import (with dry-run preview staging)
  document.getElementById('import-file-input')?.addEventListener('change', async function () {
    const file = this.files[0];
    if (!file) return;
    this.value = '';

    const banner = document.getElementById('import-banner');
    if (banner) {
      banner.className = 'gen-result';
      banner.textContent = '⏳ Inspecting & parsing Excel workbook…';
      banner.classList.remove('hidden');
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_id', window.getBankId ? window.getBankId() : 1);
    formData.append('preview', 'true');

    try {
      const res = await fetch('/api/questions/import', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok) {
        if (banner) {
          banner.className = 'gen-result error';
          banner.textContent = `✕ ${data.detail || 'Import failed'}`;
        }
        toast(data.detail || 'Import failed', 'error');
        return;
      }

      if (banner) banner.classList.add('hidden');

      // Open Interactive Staging & Dry-run Review Modal
      openImportPreviewModal(data, async (onDuplicateMode) => {
        const commitData = new FormData();
        commitData.append('file', file);
        commitData.append('bank_id', window.getBankId ? window.getBankId() : 1);
        commitData.append('preview', 'false');
        commitData.append('on_duplicate', onDuplicateMode);

        if (banner) {
          banner.className = 'gen-result';
          banner.textContent = '⏳ Writing questions to database…';
          banner.classList.remove('hidden');
        }

        try {
          const commitRes = await fetch('/api/questions/import', { method: 'POST', body: commitData });
          const commitJson = await commitRes.json();
          if (!commitRes.ok) {
            if (banner) {
              banner.className = 'gen-result error';
              banner.textContent = `✕ ${commitJson.detail || 'Ingestion failed'}`;
            }
            toast(commitJson.detail || 'Ingestion failed', 'error');
          } else {
            if (banner) {
              banner.className = 'gen-result';
              banner.textContent = `✓ Ingested ${commitJson.total_imported || commitJson.imported} question(s) successfully (${commitJson.total_duplicates || 0} duplicates handled).`;
            }
            toast(`Ingested ${commitJson.total_imported || commitJson.imported} questions`, 'success');
            await window.loadPools?.();
            loadQuestions();
          }
        } catch (err) {
          if (banner) {
            banner.className = 'gen-result error';
            banner.textContent = `✕ ${err.message}`;
          }
          toast(err.message, 'error');
        }
      });

    } catch (e) {
      if (banner) {
        banner.className = 'gen-result error';
        banner.textContent = `✕ ${e.message}`;
      }
      toast(e.message, 'error');
    }
  });

  // LaTeX import
  document.getElementById('latex-mode-existing')?.addEventListener('change', () => {
    document.getElementById('latex-existing-pools-wrap')?.classList.remove('hidden');
    document.getElementById('latex-new-pools-wrap')?.classList.add('hidden');
  });
  document.getElementById('latex-mode-new')?.addEventListener('change', () => {
    document.getElementById('latex-existing-pools-wrap')?.classList.add('hidden');
    document.getElementById('latex-new-pools-wrap')?.classList.remove('hidden');
  });
  document.getElementById('modal-latex-import-close')?.addEventListener('click', closeLatexImportModal);
  document.getElementById('btn-cancel-latex-import')?.addEventListener('click', closeLatexImportModal);
  document.getElementById('modal-latex-import-backdrop')?.addEventListener('click', e => {
    if (e.target.id === 'modal-latex-import-backdrop') closeLatexImportModal();
  });

  document.getElementById('modal-import-preview-close')?.addEventListener('click', closeImportPreviewModal);
  document.getElementById('btn-cancel-import-preview')?.addEventListener('click', closeImportPreviewModal);
  document.getElementById('modal-import-preview-backdrop')?.addEventListener('click', e => {
    if (e.target.id === 'modal-import-preview-backdrop') closeImportPreviewModal();
  });

  // Confirm Ingest button inside Staging Modal
  document.getElementById('btn-confirm-import-staging')?.addEventListener('click', () => {
    if (typeof stagedConfirmCallback === 'function') {
      const mode = document.getElementById('preview-duplicate-mode')?.value || 'skip';
      const cb = stagedConfirmCallback;
      closeImportPreviewModal();
      cb(mode);
    }
  });

  document.getElementById('import-latex-input')?.addEventListener('change', function () {
    const file = this.files[0];
    this.value = '';
    if (!file) return;
    openLatexImportModal(file);
  });

  // Click "Preview & Review" in LaTeX options modal
  document.getElementById('btn-confirm-latex-import')?.addEventListener('click', async () => {
    if (!pendingLatexFile) return;
    const file = pendingLatexFile;
    const isNewMode = document.getElementById('latex-mode-new')?.checked;
    const initialDupMode = document.getElementById('latex-dup-overwrite')?.checked ? 'overwrite' : 'skip';

    const formData = new FormData();
    formData.append('file', file);
    formData.append('bank_id', window.getBankId ? window.getBankId() : 1);
    formData.append('preview', 'true');

    let poolIdsStr = '';
    let newPoolsCount = 0;

    if (isNewMode) {
      newPoolsCount = parseInt(document.getElementById('latex-new-pools-count')?.value) || 5;
      formData.append('new_pools', Math.max(1, Math.min(newPoolsCount, 50)));
    } else {
      const checked = Array.from(document.querySelectorAll('.latex-target-pool-chk:checked')).map(el => el.value);
      if (!checked.length) {
        toast('Please select at least one target pool.', 'error');
        return;
      }
      poolIdsStr = checked.join(',');
      formData.append('pool_ids', poolIdsStr);
    }

    closeLatexImportModal();

    const banner = document.getElementById('import-banner');
    if (banner) {
      banner.className = 'gen-result';
      banner.style.whiteSpace = 'pre-wrap';
      banner.textContent = '⏳ Parsing master LaTeX & preparing preview…';
      banner.classList.remove('hidden');
    }

    try {
      const res = await fetch('/api/questions/import-latex', { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) {
        if (banner) {
          banner.className = 'gen-result error';
          banner.textContent = `✕ ${data.detail || 'Parse failed'}`;
        }
        toast(data.detail || 'Parse failed', 'error');
        return;
      }

      if (banner) banner.classList.add('hidden');

      // Set initial duplicate mode dropdown to match user's prior choice
      const dupSelect = document.getElementById('preview-duplicate-mode');
      if (dupSelect) dupSelect.value = initialDupMode;

      // Open interactive staging & review modal
      openImportPreviewModal(data, async (chosenDupMode) => {
        const commitData = new FormData();
        commitData.append('file', file);
        commitData.append('bank_id', window.getBankId ? window.getBankId() : 1);
        commitData.append('preview', 'false');
        commitData.append('on_duplicate', chosenDupMode);
        if (isNewMode) {
          commitData.append('new_pools', newPoolsCount);
        } else {
          commitData.append('pool_ids', poolIdsStr);
        }

        if (banner) {
          banner.className = 'gen-result';
          banner.style.whiteSpace = 'pre-wrap';
          banner.textContent = '⏳ Ingesting questions into database…';
          banner.classList.remove('hidden');
        }

        try {
          const commitRes = await fetch('/api/questions/import-latex', { method: 'POST', body: commitData });
          const commitJson = await commitRes.json();
          if (!commitRes.ok) {
            if (banner) {
              banner.className = 'gen-result error';
              banner.textContent = `✕ ${commitJson.detail || 'Import failed'}`;
            }
            toast(commitJson.detail || 'Import failed', 'error');
          } else {
            const warn = (commitJson.warnings || []).length > 0;
            if (banner) {
              banner.className = warn ? 'gen-result error' : 'gen-result';
              const poolsStr = Object.entries(commitJson.per_pool || {}).map(([p, n]) => `P${p}: ${n}`).join('  ');
              banner.textContent =
                `✓ Ingested ${commitJson.imported} question(s) successfully (${commitJson.duplicates || 0} duplicates handled).\n` +
                `Distribution → ${poolsStr}` +
                (warn ? '\n\n' + commitJson.warnings.map(w => `⚠ ${w}`).join('\n') : '');
            }
            toast(`Ingested ${commitJson.imported} question(s)`, warn ? 'info' : 'success');
            await window.loadPools?.();
            loadQuestions();
          }
        } catch (err) {
          if (banner) {
            banner.className = 'gen-result error';
            banner.textContent = `✕ ${err.message}`;
          }
          toast(err.message, 'error');
        }
      });

    } catch (e) {
      if (banner) {
        banner.className = 'gen-result error';
        banner.textContent = `✕ ${e.message}`;
      }
      toast(e.message, 'error');
    }
  });
});
