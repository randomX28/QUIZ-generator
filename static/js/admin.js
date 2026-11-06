/* admin.js — Main UI Orchestrator & Global Event Coordinator */

// ── Global Escape Helper ───────────────────────────────────────────────────
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
window.esc = esc;

// ── Global Bank & Pool Lifecycle Hooks ─────────────────────────────────────
window.onBankChanged = function () {
  window.currentPool = 'all';
  window.updateBankScopedLinks?.();
  window.updateBankHeaderAndDefaults?.();

  const b = window.currentBank?.();
  if (b) {
    const subjEl = document.getElementById('gen-subject');
    const courseEl = document.getElementById('gen-course-code');
    if (subjEl && b.subject_name) subjEl.value = b.subject_name;
    if (courseEl && b.course_code) courseEl.value = b.course_code;
  }

  window.renderPoolTabs?.();
  window.renderPoolSelects?.();
  window.renderGenPoolSelector?.();
};

window.onPoolsChanged = function () {
  window.updateBankHeaderAndDefaults?.();
  window.renderPoolTabs?.();
  window.renderPoolSelects?.();
  window.renderGenPoolSelector?.();
};

// ── Dropdown Menus ─────────────────────────────────────────────────────────
let dropdownsInitialized = false;

function setupDropdowns() {
  if (dropdownsInitialized) return;
  dropdownsInitialized = true;

  const ddImport = document.getElementById('dropdown-import');
  const ddMaster = document.getElementById('dropdown-master');
  const btnImport = document.getElementById('btn-toggle-import');
  const btnMaster = document.getElementById('btn-toggle-master');

  function closeAll() {
    ddImport?.classList.remove('open');
    ddMaster?.classList.remove('open');
  }

  btnImport?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const wasOpen = ddImport?.classList.contains('open');
    closeAll();
    if (!wasOpen) ddImport?.classList.add('open');
  });

  btnMaster?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const wasOpen = ddMaster?.classList.contains('open');
    closeAll();
    if (!wasOpen) ddMaster?.classList.add('open');
  });

  document.getElementById('btn-menu-import-latex')?.addEventListener('click', (e) => {
    e.stopPropagation();
    closeAll();
    document.getElementById('import-latex-input')?.click();
  });

  document.getElementById('btn-menu-import-excel')?.addEventListener('click', (e) => {
    e.stopPropagation();
    closeAll();
    document.getElementById('import-file-input')?.click();
  });

  document.getElementById('link-master-paper-pdf')?.addEventListener('click', closeAll);
  document.getElementById('link-master-paper-latex')?.addEventListener('click', closeAll);

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.dropdown')) {
      closeAll();
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', setupDropdowns);
} else {
  setupDropdowns();
}

// ── Initialization ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupDropdowns();
  if (window.renderMathInPage) {
    window.renderMathInPage(document.body);
  }
});
