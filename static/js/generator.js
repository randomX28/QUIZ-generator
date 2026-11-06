/* generator.js — Paper generation presets, pool selectors, and generate dispatch */

function getFormattedToday() {
  const d = new Date();
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec"];
  const day = String(d.getDate()).padStart(2, '0');
  const mon = months[d.getMonth()];
  const yr = d.getFullYear();
  return `${day}-${mon}-${yr}`;
}

const PAPER_TYPE_PRESETS = {
  objective: {
    exam_title: "Quiz 1",
    max_marks: "10 (2 marks per question)",
    marks_per_question: "2 Marks",
    duration: "30 Minutes",
    count: 30,
    randomize: true,
    instructions: "(i) Tick the correct option for each question (ii) All questions carry 2 marks each",
    randomizeHint: "Each paper draws random questions and shuffles options. Uncheck for standardized sets."
  },
  subjective: {
    exam_title: "End Semester Examination",
    max_marks: "50 Marks",
    marks_per_question: "10 Marks",
    duration: "3 Hours",
    count: 1,
    randomize: false,
    instructions: "(i) Answer all questions (ii) Neat diagrams must be drawn wherever necessary",
    randomizeHint: "Semester papers typically use 1 standardized master paper (randomizer off). Toggle on to generate multiple randomized sets."
  }
};

let currentPaperType = 'objective';

function computeDefaultMaxMarks(type, qPerPaper, marksPerQStr) {
  const nq = parseInt(qPerPaper) || 5;
  const mpqMatch = String(marksPerQStr || '').match(/(\d+)/);
  const mpq = mpqMatch ? parseInt(mpqMatch[1]) : (type === 'subjective' ? 10 : 2);
  const total = nq * mpq;
  return type === 'subjective'
    ? `${total} Marks`
    : `${total} (${mpq} mark${mpq === 1 ? '' : 's'} per question)`;
}

function isAutoMaxMarks(val) {
  if (!val) return true;
  const trimmed = val.trim();
  return /^\d+\s*\(\d+\s*marks?\s*per\s*question\)$/i.test(trimmed) || /^\d+\s*Marks?$/i.test(trimmed);
}

function setPaperType(type) {
  if (type !== 'objective' && type !== 'subjective') return;
  const prevType = currentPaperType;
  currentPaperType = type;

  const btnObj = document.getElementById('toggle-opt-objective');
  const btnSub = document.getElementById('toggle-opt-subjective');
  if (btnObj) btnObj.classList.toggle('active', type === 'objective');
  if (btnSub) btnSub.classList.toggle('active', type === 'subjective');

  const preset = PAPER_TYPE_PRESETS[type];
  const oldPreset = PAPER_TYPE_PRESETS[prevType];

  const examTitleEl = document.getElementById('gen-exam-title');
  const maxMarksEl = document.getElementById('gen-max-marks');
  const marksPerQEl = document.getElementById('gen-marks-per-q');
  const durationEl = document.getElementById('gen-duration');
  const qPerPaperEl = document.getElementById('gen-questions-per-paper');
  const countEl = document.getElementById('gen-count');
  const randomizeEl = document.getElementById('gen-randomize');
  const randomizeHintEl = document.getElementById('gen-randomize-hint');
  const defaultInstrCheck = document.getElementById('gen-default-instructions');
  const instrEl = document.getElementById('gen-instructions');

  if (examTitleEl && (!examTitleEl.value || examTitleEl.value === oldPreset.exam_title)) {
    examTitleEl.value = preset.exam_title;
  }
  if (marksPerQEl && (!marksPerQEl.value || marksPerQEl.value === oldPreset.marks_per_question)) {
    marksPerQEl.value = preset.marks_per_question;
  }
  if (maxMarksEl && (isAutoMaxMarks(maxMarksEl.value) || maxMarksEl.value === oldPreset.max_marks)) {
    maxMarksEl.value = computeDefaultMaxMarks(type, qPerPaperEl?.value || 5, marksPerQEl?.value || preset.marks_per_question);
  }
  if (durationEl && (!durationEl.value || durationEl.value === oldPreset.duration)) {
    durationEl.value = preset.duration;
  }
  if (countEl && (!countEl.value || parseInt(countEl.value) === oldPreset.count)) {
    countEl.value = preset.count;
  }
  if (randomizeEl) {
    randomizeEl.checked = preset.randomize;
  }
  if (randomizeHintEl) {
    randomizeHintEl.textContent = preset.randomizeHint;
  }

  if (defaultInstrCheck && defaultInstrCheck.checked && instrEl) {
    instrEl.value = preset.instructions;
  }

  localStorage.setItem('cd_paper_type', type);
}
window.setPaperType = setPaperType;

function initPaperGeneratorControls() {
  const subjectEl = document.getElementById('gen-subject');
  const courseEl = document.getElementById('gen-course-code');
  const dateEl = document.getElementById('gen-date');
  const maxMarksEl = document.getElementById('gen-max-marks');
  const marksPerQEl = document.getElementById('gen-marks-per-q');
  const durationEl = document.getElementById('gen-duration');
  const qPerPaperEl = document.getElementById('gen-questions-per-paper');
  const defaultInstrCheck = document.getElementById('gen-default-instructions');
  const instrEl = document.getElementById('gen-instructions');

  if (!subjectEl || !defaultInstrCheck || !instrEl) return;

  const btnObj = document.getElementById('toggle-opt-objective');
  const btnSub = document.getElementById('toggle-opt-subjective');
  if (btnObj) btnObj.addEventListener('click', () => setPaperType('objective'));
  if (btnSub) btnSub.addEventListener('click', () => setPaperType('subjective'));

  const savedSubject = localStorage.getItem('cd_subject_name');
  if (savedSubject) subjectEl.value = savedSubject;

  const savedCourse = localStorage.getItem('cd_course_code');
  if (savedCourse) courseEl.value = savedCourse;

  const savedQPerPaper = localStorage.getItem('cd_questions_per_paper');
  if (qPerPaperEl && savedQPerPaper) {
    qPerPaperEl.value = savedQPerPaper;
  }

  const savedType = localStorage.getItem('cd_paper_type');
  if (savedType === 'subjective') {
    setPaperType('subjective');
  } else {
    setPaperType('objective');
  }

  const savedDate = localStorage.getItem('cd_exam_date');
  if (dateEl) {
    dateEl.value = savedDate || getFormattedToday();
  }

  const savedMarksPerQ = localStorage.getItem('cd_marks_per_q');
  if (marksPerQEl && savedMarksPerQ) {
    marksPerQEl.value = savedMarksPerQ;
  }

  if (maxMarksEl && isAutoMaxMarks(maxMarksEl.value)) {
    maxMarksEl.value = computeDefaultMaxMarks(currentPaperType, qPerPaperEl?.value || 5, marksPerQEl?.value);
  }

  const savedDuration = localStorage.getItem('cd_duration');
  if (savedDuration) durationEl.value = savedDuration;

  const savedUseDefault = localStorage.getItem('cd_use_default_instr');
  if (savedUseDefault !== null) {
    defaultInstrCheck.checked = (savedUseDefault === 'true');
  }

  function updateInstrState() {
    const currentPreset = PAPER_TYPE_PRESETS[currentPaperType] || PAPER_TYPE_PRESETS.objective;
    if (defaultInstrCheck.checked) {
      instrEl.value = currentPreset.instructions;
      instrEl.disabled = true;
      instrEl.style.opacity = '0.7';
    } else {
      instrEl.disabled = false;
      instrEl.style.opacity = '1';
      const stored = localStorage.getItem('cd_custom_instr');
      if (stored && stored !== currentPreset.instructions) {
        instrEl.value = stored;
      }
    }
  }

  updateInstrState();

  defaultInstrCheck.addEventListener('change', () => {
    localStorage.setItem('cd_use_default_instr', defaultInstrCheck.checked);
    updateInstrState();
  });

  subjectEl.addEventListener('input', () => {
    localStorage.setItem('cd_subject_name', subjectEl.value);
  });
  if (courseEl) {
    courseEl.addEventListener('input', () => {
      localStorage.setItem('cd_course_code', courseEl.value);
    });
  }
  if (dateEl) {
    dateEl.addEventListener('input', () => {
      localStorage.setItem('cd_exam_date', dateEl.value);
    });
  }
  if (qPerPaperEl) {
    qPerPaperEl.addEventListener('input', () => {
      localStorage.setItem('cd_questions_per_paper', qPerPaperEl.value);
      if (maxMarksEl && isAutoMaxMarks(maxMarksEl.value)) {
        maxMarksEl.value = computeDefaultMaxMarks(currentPaperType, qPerPaperEl.value, marksPerQEl?.value);
      }
    });
  }
  if (marksPerQEl) {
    marksPerQEl.addEventListener('input', () => {
      localStorage.setItem('cd_marks_per_q', marksPerQEl.value);
      if (maxMarksEl && isAutoMaxMarks(maxMarksEl.value)) {
        maxMarksEl.value = computeDefaultMaxMarks(currentPaperType, qPerPaperEl?.value || 5, marksPerQEl.value);
      }
    });
  }
  if (durationEl) {
    durationEl.addEventListener('input', () => {
      localStorage.setItem('cd_duration', durationEl.value);
    });
  }
  instrEl.addEventListener('input', () => {
    if (!defaultInstrCheck.checked) {
      localStorage.setItem('cd_custom_instr', instrEl.value);
    }
  });
}

function renderGenPoolSelector() {
  const wrap = document.getElementById('gen-pool-selector');
  if (!wrap) return;
  const poolsList = window.getPools?.() || [];
  const customMode = document.getElementById('gen-custom-per-pool')?.checked ?? false;
  const anyNonEmpty = poolsList.some(p => (p.count || 0) > 0);

  if (!poolsList.length) {
    wrap.innerHTML = '<div style="font-size:0.8rem;color:var(--text-muted)">No pools in this bank yet.</div>';
    return;
  }

  const prevChecked = new Set(
    Array.from(wrap.querySelectorAll('.gen-pool-chk:checked')).map(el => parseInt(el.value))
  );
  const prevCounts = {};
  wrap.querySelectorAll('.gen-pool-count-input').forEach(el => {
    prevCounts[el.dataset.poolNo] = el.value;
  });

  wrap.innerHTML = poolsList.map(p => {
    const isChecked = prevChecked.size > 0
      ? prevChecked.has(p.pool_no)
      : (anyNonEmpty ? (p.count || 0) > 0 : true);
    const label = window.poolName ? window.poolName(p.pool_no) : `Pool ${p.pool_no}`;
    const defCount = prevCounts[p.pool_no] !== undefined ? prevCounts[p.pool_no] : 1;
    return `
      <div class="gen-pool-card">
        <label class="checkbox-label" style="font-size:0.82rem;cursor:pointer;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(label)} (${p.count ?? 0} questions)">
          <input type="checkbox" class="gen-pool-chk" value="${p.pool_no}" ${isChecked ? 'checked' : ''} />
          <span>${esc(label)} <span style="color:var(--text-muted);font-size:0.75rem">(${p.count ?? 0})</span></span>
        </label>
        <input
          type="number"
          class="input-field gen-pool-count-input ${customMode ? '' : 'hidden'}"
          data-pool-no="${p.pool_no}"
          min="0"
          max="${Math.max(p.count || 100, 1)}"
          value="${defCount}"
          style="width:58px;padding:0.2rem 0.35rem;font-size:0.8rem;text-align:center"
          title="Questions to pick from ${esc(label)}"
        />
      </div>
    `;
  }).join('');

  wrap.querySelectorAll('.gen-pool-chk, .gen-pool-count-input').forEach(el => {
    el.addEventListener('change', syncCustomPerPoolTotal);
    el.addEventListener('input', syncCustomPerPoolTotal);
  });
}

function syncCustomPerPoolTotal() {
  const customMode = document.getElementById('gen-custom-per-pool')?.checked ?? false;
  if (!customMode) return;
  let total = 0;
  document.querySelectorAll('.gen-pool-chk:checked').forEach(chk => {
    const pno = chk.value;
    const inp = document.querySelector(`.gen-pool-count-input[data-pool-no="${pno}"]`);
    total += Math.max(0, parseInt(inp?.value) || 0);
  });
  const qPerPaperEl = document.getElementById('gen-questions-per-paper');
  const maxMarksEl = document.getElementById('gen-max-marks');
  const marksPerQEl = document.getElementById('gen-marks-per-q');
  if (qPerPaperEl && total > 0) {
    qPerPaperEl.value = total;
    if (maxMarksEl && isAutoMaxMarks(maxMarksEl.value)) {
      maxMarksEl.value = computeDefaultMaxMarks(currentPaperType, total, marksPerQEl?.value);
    }
  }
}

async function runGenerate(debugMode) {
  const bank_id = window.getBankId ? window.getBankId() : 1;
  const count = parseInt(document.getElementById('gen-count').value) || 1;
  let questions_per_paper = parseInt(document.getElementById('gen-questions-per-paper')?.value) || 5;
  const subject_name = (document.getElementById('gen-subject')?.value || '').trim();
  const course_code = (document.getElementById('gen-course-code')?.value || '').trim();
  const paper_type = currentPaperType;
  const exam_title = (document.getElementById('gen-exam-title')?.value || '').trim();
  const exam_date = (document.getElementById('gen-date')?.value || '').trim() || getFormattedToday();
  const max_marks = (document.getElementById('gen-max-marks')?.value || '').trim();
  const marks_per_question = (document.getElementById('gen-marks-per-q')?.value || '').trim();
  const duration = (document.getElementById('gen-duration')?.value || '').trim();
  const randomize = document.getElementById('gen-randomize')?.checked ?? true;
  const use_default_instructions = document.getElementById('gen-default-instructions')?.checked ?? true;
  const instructions = (document.getElementById('gen-instructions')?.value || '').trim();

  const pool_ids = Array.from(document.querySelectorAll('.gen-pool-chk:checked')).map(el => parseInt(el.value));
  if (!pool_ids.length) {
    toast('Please select at least one pool to draw questions from.', 'error');
    return;
  }

  let per_pool = null;
  const customPerPool = document.getElementById('gen-custom-per-pool')?.checked ?? false;
  if (customPerPool) {
    per_pool = {};
    let sum = 0;
    for (const pno of pool_ids) {
      const inp = document.querySelector(`.gen-pool-count-input[data-pool-no="${pno}"]`);
      const c = Math.max(0, parseInt(inp?.value) || 0);
      per_pool[pno] = c;
      sum += c;
    }
    if (sum <= 0) {
      toast('Total questions across selected pools must be at least 1.', 'error');
      return;
    }
    questions_per_paper = sum;
  }

  const btn = document.getElementById('btn-generate');
  const resultEl = document.getElementById('gen-result');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  resultEl.className = 'gen-result';
  resultEl.innerHTML = '<div style="display:flex;align-items:center;gap:0.75rem"><span>⏳</span><span>Selecting questions and preparing exam paper layout…</span></div>';
  resultEl.classList.remove('hidden');

  const url = debugMode
    ? '/api/papers/generate?debug=true'
    : '/api/papers/generate';

  try {
    const res = await apiFetch(url, {
      method: 'POST',
      body: JSON.stringify({
        bank_id,
        pool_ids,
        per_pool,
        count,
        questions_per_paper,
        subject_name,
        course_code,
        paper_type,
        exam_title,
        max_marks,
        marks_per_question,
        exam_date,
        duration,
        use_default_instructions,
        instructions,
        randomize,
      })
    });
    resultEl.className = 'gen-result';
    let papersHtml = res.papers.map(uid => `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:0.5rem;padding:0.35rem 0;border-bottom:1px solid var(--glass-border);">
        <span class="mono" style="font-weight:600;">${esc(uid)}</span>
        <div style="display:flex;gap:0.4rem;">
          <button class="btn btn-primary btn-sm" onclick="viewPaper('${uid}')">👁 View Paper</button>
          <a class="btn btn-ghost btn-sm" href="/api/papers/${uid}/pdf" target="_blank">↗ PDF</a>
        </div>
      </div>
    `).join('');

    const bulkPdfHref = window.withBank ? window.withBank('/api/papers/bulk/pdf') : '/api/papers/bulk/pdf';
    const bulkPdfDlHref = window.withBank ? window.withBank('/api/papers/bulk/pdf?download=true') : '/api/papers/bulk/pdf?download=true';

    resultEl.innerHTML = `
      <div style="margin-bottom:0.5rem;font-weight:600;">✓ Successfully generated ${res.generated} paper(s):</div>
      <div style="max-height:180px;overflow-y:auto;margin-bottom:0.8rem;">${papersHtml}</div>
      <div style="display:flex;gap:0.5rem;flex-wrap:wrap;padding-top:0.4rem;border-top:1px solid var(--glass-border);">
        <a class="btn btn-primary btn-sm" href="${bulkPdfHref}" target="_blank">🖨 Bulk Print All (${res.generated} Papers in 1 PDF)</a>
        <a class="btn btn-ghost btn-sm" href="${bulkPdfDlHref}" download="all_papers_bundle.pdf">⬇ Download Merged PDF</a>
      </div>
      ${debugMode ? '<div style="color:var(--accent-amber);font-size:0.8rem;margin-top:0.4rem;">⚠ Debug mode — some pools were empty and skipped.</div>' : ''}
    `;
    resultEl.classList.remove('hidden');
    toast(`${res.generated} paper(s) generated!`, 'success');
    await window.loadPools?.();
    window.loadPapers?.();
  } catch (e) {
    const isEmptyPool = e.message && e.message.toLowerCase().includes('pool') &&
                        e.message.toLowerCase().includes('empty');

    if (!debugMode && isEmptyPool) {
      const retry = confirm(
        `⚠ Debug prompt:\n\n${e.message}\n\n` +
        `Generate anyway using only the pools that have questions?\n` +
        `(This is for testing only — remove before production use.)`
      );
      if (retry) {
        btn.disabled = false;
        btn.innerHTML = '⚡ Generate Papers';
        await runGenerate(true);
        return;
      }
    }

    resultEl.className = 'gen-result error';
    resultEl.textContent = `✕ ${e.message}`;
    resultEl.classList.remove('hidden');
    toast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '⚡ Generate Papers';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initPaperGeneratorControls();

  document.getElementById('btn-generate')?.addEventListener('click', async () => {
    await runGenerate(false);
  });

  document.getElementById('gen-custom-per-pool')?.addEventListener('change', function () {
    const customMode = this.checked;
    document.querySelectorAll('.gen-pool-count-input').forEach(el => {
      el.classList.toggle('hidden', !customMode);
    });
    const hint = document.getElementById('gen-pool-hint');
    if (hint) {
      hint.textContent = customMode
        ? 'Specify the exact number of questions to draw from each checked pool.'
        : 'Questions per paper are spread evenly across checked pools (least-used first).';
    }
    if (customMode) syncCustomPerPoolTotal();
  });

  document.getElementById('btn-select-all-pools')?.addEventListener('click', () => {
    document.querySelectorAll('.gen-pool-chk').forEach(chk => { chk.checked = true; });
    syncCustomPerPoolTotal();
  });

  document.getElementById('btn-select-nonempty-pools')?.addEventListener('click', () => {
    const poolsList = window.getPools?.() || [];
    const nonEmpty = new Set(poolsList.filter(p => (p.count || 0) > 0).map(p => String(p.pool_no)));
    document.querySelectorAll('.gen-pool-chk').forEach(chk => {
      chk.checked = nonEmpty.has(String(chk.value));
    });
    syncCustomPerPoolTotal();
  });

  // How It Works Modal Toggle
  const howBtn = document.getElementById('btn-how-it-works');
  const howModal = document.getElementById('modal-how-it-works-backdrop');
  const howClose = document.getElementById('modal-how-it-works-close');
  const howCloseBtn = document.getElementById('btn-close-how-it-works');

  function openHowModal() {
    howModal?.classList.remove('hidden');
  }
  function closeHowModal() {
    howModal?.classList.add('hidden');
  }

  if (howBtn) howBtn.addEventListener('click', openHowModal);
  if (howClose) howClose.addEventListener('click', closeHowModal);
  if (howCloseBtn) howCloseBtn.addEventListener('click', closeHowModal);
  if (howModal) {
    howModal.addEventListener('click', (e) => {
      if (e.target.id === 'modal-how-it-works-backdrop') closeHowModal();
    });
  }
});

window.renderGenPoolSelector = renderGenPoolSelector;
window.initPaperGeneratorControls = initPaperGeneratorControls;

