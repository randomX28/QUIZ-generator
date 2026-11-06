/* papers.js — Generated papers listing, document/PDF previewer, and deletion */

async function loadPapers() {
  const list = document.getElementById('papers-list');
  if (!list) return;
  list.innerHTML = '<div class="loading-state">Loading…</div>';
  window.updateBankScopedLinks?.();
  try {
    const papers = await apiFetch(window.withBank ? window.withBank('/api/papers') : '/api/papers');
    if (!papers.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">📄</div><div class="empty-text">No papers generated yet.</div></div>';
      return;
    }
    list.innerHTML = papers.map(p => {
      const typeBadge = p.paper_type === 'subjective'
        ? '<span class="badge-subjective" style="margin-left:0.5rem">Subjective</span>'
        : '<span class="badge-objective" style="margin-left:0.5rem">Objective</span>';
      return `
      <div class="paper-row" id="paper-row-${p.uid}">
        <div style="display:flex;align-items:center">
          <span class="paper-uid">${esc(p.uid)}</span>
          ${typeBadge}
        </div>
        <span class="paper-date">${new Date(p.created_at).toLocaleString()}</span>
        <div class="paper-actions">
          <button class="btn btn-primary btn-sm" onclick="viewPaper('${p.uid}')">👁 View</button>
          <button class="btn btn-ghost btn-sm" onclick="viewSolutionSheet('${p.uid}')" title="View Answer Key & Solutions">🔑 Key</button>
          <a class="btn btn-ghost btn-sm" href="/api/papers/${p.uid}/pdf" target="_blank" title="Open PDF in new tab">↗ PDF</a>
          <a class="btn btn-ghost btn-sm" href="/api/papers/${p.uid}/latex" download="${p.uid}.tex" title="Download LaTeX source">LaTeX</a>
          <button class="btn btn-danger btn-sm" onclick="deletePaper('${p.uid}')" title="Delete paper">🗑</button>
        </div>
      </div>
    `;
    }).join('');
  } catch (e) {
    list.innerHTML = `<div class="error-msg">${e.message}</div>`;
  }
}
window.loadPapers = loadPapers;

async function viewPaper(uid) {
  const backdrop = document.getElementById('modal-paper-view-backdrop');
  const contentEl = document.getElementById('paper-preview-content');
  const uidEl = document.getElementById('paper-view-uid');
  const pdfTab = document.getElementById('paper-view-pdf-tab');
  const pdfDl = document.getElementById('paper-view-pdf-dl');
  const texDl = document.getElementById('paper-view-tex-dl');

  if (uidEl) uidEl.textContent = uid;
  if (pdfTab) pdfTab.href = `/api/papers/${uid}/pdf`;
  if (pdfDl) pdfDl.href = `/api/papers/${uid}/pdf?download=true`;
  if (texDl) texDl.href = `/api/papers/${uid}/latex`;

  if (contentEl) contentEl.innerHTML = '<div class="loading-state">Loading paper content…</div>';
  if (backdrop) backdrop.classList.remove('hidden');

  const btnToggleHtml = document.getElementById('btn-paper-toggle-html');
  const btnTogglePdf = document.getElementById('btn-paper-toggle-pdf');
  const pdfWrap = document.getElementById('paper-preview-pdf-wrap');
  const pdfIframe = document.getElementById('paper-preview-iframe');

  function setViewMode(mode) {
    if (mode === 'pdf') {
      if (contentEl) contentEl.classList.add('hidden');
      if (pdfWrap) pdfWrap.classList.remove('hidden');
      if (btnTogglePdf) btnTogglePdf.className = 'btn btn-sm btn-primary';
      if (btnToggleHtml) btnToggleHtml.className = 'btn btn-sm btn-ghost';
      if (pdfIframe && (!pdfIframe.src || !pdfIframe.src.includes(`/api/papers/${uid}/pdf`))) {
        pdfIframe.src = `/api/papers/${uid}/pdf`;
      }
    } else {
      if (pdfWrap) pdfWrap.classList.add('hidden');
      if (contentEl) contentEl.classList.remove('hidden');
      if (btnToggleHtml) btnToggleHtml.className = 'btn btn-sm btn-primary';
      if (btnTogglePdf) btnTogglePdf.className = 'btn btn-sm btn-ghost';
    }
  }

  if (btnToggleHtml) btnToggleHtml.onclick = () => setViewMode('html');
  if (btnTogglePdf) btnTogglePdf.onclick = () => setViewMode('pdf');
  setViewMode('html');

  try {
    const paper = await apiFetch(`/api/papers/${uid}`);
    const questions = paper.questions || [];
    const isSubj = (paper.paper_type === 'subjective');

    if (contentEl) {
      contentEl.innerHTML = `
        <div class="paper-sheet-preview">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;margin-bottom:0.6rem;">
            <div style="width:70px;flex-shrink:0;">
              <img src="/static/img/iit_logo.png" style="height:62px;width:auto;object-fit:contain;" alt="IIT Logo" onerror="this.style.display='none'" />
            </div>
            <div style="flex:1;text-align:center;">
              <div style="font-size:1.05rem;font-weight:700;color:var(--text-primary);letter-spacing:0.2px;">Indian Institute of Technology (ISM), Dhanbad</div>
              <div style="font-size:0.86rem;color:var(--text-secondary);margin-top:2px;">Department of Computer Science and Engineering</div>
              <div style="font-size:0.92rem;font-weight:700;color:var(--text-primary);margin-top:3px;">${esc(paper.subject_name || 'Compiler Design')} (${esc(paper.course_code || 'NCSC302-CSC302')})</div>
              <div style="font-size:0.9rem;font-weight:700;color:var(--accent-blue);margin-top:2px;">${esc(paper.exam_title || (isSubj ? 'End Semester Examination' : 'Quiz 1'))}</div>
            </div>
            <div style="width:115px;flex-shrink:0;text-align:right;">
              <div style="border:1.5px solid var(--glass-border);padding:4px 6px;border-radius:var(--radius-xs);text-align:center;background:var(--bg-surface-high);">
                <div style="font-size:0.68rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;">Paper Code</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:0.82rem;font-weight:700;color:var(--text-primary);margin-top:2px;">${esc(paper.uid)}</div>
              </div>
            </div>
          </div>

          <div style="border-top:1.5px solid #cbd5e1;border-bottom:1.5px solid #cbd5e1;padding:4px 0;margin:0.5rem 0;display:flex;justify-content:space-between;font-size:0.82rem;color:var(--text-primary);">
            <span><strong>Date:</strong> ${esc(paper.exam_date || '05-Sept-2026')}</span>
            <span><strong>Duration:</strong> ${esc(paper.duration || (isSubj ? '3 Hours' : '30 Minutes'))}</span>
            <span><strong>Max. Marks:</strong> ${esc(paper.max_marks || (isSubj ? '50 Marks' : '10 (2 marks per question)'))}</span>
          </div>

          <div style="display:flex;justify-content:space-between;gap:2rem;margin:0.75rem 0 0.5rem 0;font-size:0.82rem;">
            <div style="flex:1;display:flex;align-items:center;">
              <strong style="white-space:nowrap;margin-right:6px;">Name:</strong>
              <div style="flex:1;border-bottom:1px solid #cbd5e1;height:12px;"></div>
            </div>
            <div style="flex:1;display:flex;align-items:center;">
              <strong style="white-space:nowrap;margin-right:6px;">Admission No.:</strong>
              <div style="flex:1;border-bottom:1px solid #cbd5e1;height:12px;"></div>
            </div>
          </div>

          <div style="border-bottom:1px solid #cbd5e1;padding-bottom:5px;margin-bottom:0.75rem;font-size:0.78rem;color:var(--text-secondary);">
            <strong>Instructions:</strong> ${esc(paper.instructions || (isSubj ? '(i) Answer all questions (ii) Neat diagrams must be drawn wherever necessary' : '(i) Tick the correct option for each question (ii) All questions carry 2 marks each'))}
          </div>

          <div class="paper-sheet-questions">
            ${questions.map((q, idx) => {
              const opts = q.shuffled_options || {};
              const hasOpts = opts && (opts.a || opts.b || opts.c || opts.d);
              const qMarks = (q.marks !== undefined && q.marks !== null && q.marks !== '') ? q.marks : (paper.marks_per_question || (isSubj ? 10 : 2));
              const mStr = String(qMarks);
              const mDisplay = mStr.toLowerCase().includes('mark') ? mStr : `${mStr} Mark${mStr === '1' ? '' : 's'}`;
              return `
                <div class="paper-sheet-q">
                  <div class="sheet-q-text" style="${isSubj ? 'margin-bottom:1rem' : ''}">
                    <strong>${idx + 1}.</strong> ${formatRichText(q.text)}
                    <span style="float:right;font-weight:600;color:var(--text-muted)">[${esc(mDisplay)}]</span>
                  </div>
                  ${(!isSubj && hasOpts) ? `
                  <div class="sheet-q-options">
                    <div><strong>(a)</strong> ${formatRichText(opts.a || '')}</div>
                    <div><strong>(b)</strong> ${formatRichText(opts.b || '')}</div>
                    <div><strong>(c)</strong> ${formatRichText(opts.c || '')}</div>
                    <div><strong>(d)</strong> ${formatRichText(opts.d || '')}</div>
                  </div>` : ''}
                </div>
              `;
            }).join('')}
          </div>

          <div class="paper-sheet-footer">
            <em>--- End of Paper ---</em> &nbsp;&nbsp; <code style="font-family:'JetBrains Mono',monospace">${esc(paper.uid)}</code>
          </div>
        </div>
      `;
      window.renderMathInPage?.(contentEl);
    }
  } catch (err) {
    if (contentEl) {
      contentEl.innerHTML = `<div class="error-msg">✕ Failed to load paper: ${esc(err.message)}</div>`;
    }
  }
}
window.viewPaper = viewPaper;

function closePaperView() {
  document.getElementById('modal-paper-view-backdrop')?.classList.add('hidden');
}
window.closePaperView = closePaperView;

async function deletePaper(uid) {
  if (!confirm(`Delete paper ${uid}?\nThis will remove it from the database and delete its PDF.`)) return;
  try {
    await apiFetch(`/api/papers/${uid}`, { method: 'DELETE' });
    const row = document.getElementById(`paper-row-${uid}`);
    if (row) {
      row.style.transition = 'opacity 0.3s';
      row.style.opacity = '0';
      setTimeout(() => row.remove(), 300);
    }
    toast(`Paper ${uid} deleted.`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}
window.deletePaper = deletePaper;

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modal-paper-view-close')?.addEventListener('click', closePaperView);
  document.getElementById('btn-close-paper-view')?.addEventListener('click', closePaperView);
  document.getElementById('modal-paper-view-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'modal-paper-view-backdrop') closePaperView();
  });

  document.getElementById('btn-refresh-papers')?.addEventListener('click', loadPapers);

  document.getElementById('btn-delete-all-papers')?.addEventListener('click', async () => {
    const list = document.getElementById('papers-list');
    const count = list?.querySelectorAll('.paper-row').length || 0;
    if (!count) { toast('No papers to delete.', 'info'); return; }
    if (!confirm(`Delete all ${count} paper(s) in this bank?\nThis will remove them from the database and delete all PDFs.`)) return;
    try {
      const url = window.withBank ? window.withBank('/api/papers/all') : '/api/papers/all';
      await apiFetch(url, { method: 'DELETE' });
      toast('All papers deleted from this bank.', 'success');
      loadPapers();
      await window.loadPools?.();
    } catch (e) {
      toast(e.message, 'error');
    }
  });
});

