/* banks.js — Bank switcher, creation, update, and deletion */

function updateBankScopedLinks() {
  const setHref = (id, path) => {
    const el = document.getElementById(id);
    if (el && window.withBank) el.href = window.withBank(path);
  };
  setHref('link-master-paper-pdf', '/api/papers/master-paper/pdf');
  setHref('link-master-paper-latex', '/api/papers/master-paper/latex');
  setHref('link-bulk-pdf', '/api/papers/bulk/pdf');
  setHref('link-bulk-pdf-dl', '/api/papers/bulk/pdf?download=true');
  setHref('link-bulk-latex', '/api/papers/bulk/latex');
  setHref('link-ak-pdf', '/api/papers/answer-keys/pdf');
  setHref('link-ak-excel', '/api/papers/answer-keys/export/excel');
  setHref('link-ak-csv', '/api/papers/answer-keys/export/csv');
  setHref('link-export-questions-archive', '/api/questions/export/archive');
}

function updateBankHeaderAndDefaults() {
  const b = window.currentBank?.();
  const poolsList = window.getPools?.() || [];
  const titleEl = document.getElementById('admin-page-title');
  const subEl = document.getElementById('admin-page-sub');
  if (titleEl) {
    titleEl.textContent = b ? `Question Bank — ${b.name}` : 'Question Bank';
  }
  if (subEl) {
    subEl.textContent = b
      ? `Manage questions across ${poolsList.length} pool(s) · Paper code prefix: ${b.code}`
      : `Manage questions across ${poolsList.length} topic pool(s)`;
  }
  const delBankBtn = document.getElementById('btn-delete-bank');
  if (delBankBtn) {
    delBankBtn.style.display = (b && b.id !== 1) ? 'inline-flex' : 'none';
  }
}

function openNewBankModal() {
  document.getElementById('new-bank-name').value = '';
  document.getElementById('new-bank-code').value = '';
  document.getElementById('new-bank-subject').value = 'Compiler Design';
  document.getElementById('new-bank-course').value = 'NCSC302';
  document.getElementById('new-bank-pools').value = '5';
  document.getElementById('new-bank-error')?.classList.add('hidden');
  document.getElementById('modal-bank-backdrop')?.classList.remove('hidden');
  document.getElementById('new-bank-name')?.focus();
}

function closeNewBankModal() {
  document.getElementById('modal-bank-backdrop')?.classList.add('hidden');
}

// Wire up events
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-new-bank')?.addEventListener('click', openNewBankModal);
  document.getElementById('modal-bank-close')?.addEventListener('click', closeNewBankModal);
  document.getElementById('btn-cancel-bank')?.addEventListener('click', closeNewBankModal);
  document.getElementById('modal-bank-backdrop')?.addEventListener('click', e => {
    if (e.target.id === 'modal-bank-backdrop') closeNewBankModal();
  });

  document.getElementById('btn-save-bank')?.addEventListener('click', async () => {
    const errEl = document.getElementById('new-bank-error');
    errEl?.classList.add('hidden');
    const name = (document.getElementById('new-bank-name')?.value || '').trim();
    const code = (document.getElementById('new-bank-code')?.value || '').trim().toUpperCase();
    const subject_name = (document.getElementById('new-bank-subject')?.value || '').trim() || name;
    const course_code = (document.getElementById('new-bank-course')?.value || '').trim() || code;
    const num_pools = parseInt(document.getElementById('new-bank-pools')?.value) || 5;

    if (!name || !code) {
      if (errEl) {
        errEl.textContent = 'Please provide both a Bank Name and a Paper Code Prefix.';
        errEl.classList.remove('hidden');
      }
      return;
    }

    try {
      const created = await apiFetch('/api/banks', {
        method: 'POST',
        body: JSON.stringify({ name, code, subject_name, course_code, num_pools })
      });
      closeNewBankModal();
      toast(`Created bank "${created.name}" with ${num_pools} pool(s)`, 'success');
      await window.loadBanks?.();
      await window.switchBank?.(created.id);
    } catch (e) {
      if (errEl) {
        errEl.textContent = e.message;
        errEl.classList.remove('hidden');
      }
    }
  });

  document.getElementById('btn-delete-bank')?.addEventListener('click', async () => {
    const b = window.currentBank?.();
    if (!b) return;
    if (b.id === 1) {
      toast('Default bank cannot be deleted. Use Clear Bank to empty its questions.', 'info');
      return;
    }
    if (!confirm(`Delete bank "${b.name}" (${b.code})?\nAll pools, questions, generated papers, and results inside this bank will be permanently deleted.`)) {
      return;
    }
    try {
      await apiFetch(`/api/banks/${b.id}`, { method: 'DELETE' });
      toast(`Bank "${b.name}" deleted.`, 'info');
      await window.loadBanks?.();
      await window.switchBank?.(1);
    } catch (e) {
      toast(e.message, 'error');
    }
  });
});

window.updateBankScopedLinks = updateBankScopedLinks;
window.updateBankHeaderAndDefaults = updateBankHeaderAndDefaults;
window.openNewBankModal = openNewBankModal;
window.closeNewBankModal = closeNewBankModal;

