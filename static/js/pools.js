/* pools.js — Dynamic pool tabs, pool select options, and pool CRUD */

function renderPoolTabs() {
  const container = document.getElementById('pool-tabs');
  if (!container) return;
  const poolsList = window.getPools?.() || [];
  const totalQ = (window.allQuestions || []).length || poolsList.reduce((acc, p) => acc + (p.count || 0), 0);
  const curPool = window.currentPool || 'all';

  let html = `<button class="pool-tab ${curPool === 'all' ? 'active' : ''}" data-pool="all">All (${totalQ})</button>`;
  for (const p of poolsList) {
    const isAct = String(curPool) === String(p.pool_no);
    const label = window.poolName ? window.poolName(p.pool_no) : `Pool ${p.pool_no}`;
    html += `<button class="pool-tab ${isAct ? 'active' : ''}" data-pool="${p.pool_no}">${esc(label)} (${p.count ?? 0})</button>`;
  }
  html += `<button type="button" class="pool-tab-add" id="btn-add-pool" title="Add a new topic pool to this bank"><span>+</span> Add Pool</button>`;
  container.innerHTML = html;

  container.querySelectorAll('.pool-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      window.currentPool = tab.dataset.pool;
      renderPoolTabs();
      window.renderQuestions?.();
    });
  });

  document.getElementById('btn-add-pool')?.addEventListener('click', handleAddPoolPrompt);

  const manageBar = document.getElementById('pool-manage-bar');
  if (manageBar) {
    manageBar.classList.toggle('hidden', window.currentPool === 'all');
  }
}

async function handleAddPoolPrompt() {
  const poolsList = window.getPools?.() || [];
  const nextNo = poolsList.length ? Math.max(...poolsList.map(p => p.pool_no)) + 1 : 1;
  const name = prompt(`Enter a name for the new pool (leave blank for "Pool ${nextNo}"):`, `Pool ${nextNo}`);
  if (name === null) return;
  try {
    const res = await apiFetch(`/api/banks/${window.getBankId()}/pools`, {
      method: 'POST',
      body: JSON.stringify({ name: name.trim() || null })
    });
    toast(`Added ${res.name}`, 'success');
    await window.loadPools?.();
  } catch (e) {
    toast(e.message, 'error');
  }
}

function renderPoolSelects() {
  const poolsList = window.getPools?.() || [];
  const fPool = document.getElementById('f-pool');
  if (fPool) {
    const prev = fPool.value;
    fPool.innerHTML = poolsList.map(p =>
      `<option value="${p.pool_no}">${esc(window.poolName ? window.poolName(p.pool_no) : `Pool ${p.pool_no}`)}</option>`
    ).join('') || '<option value="1">Pool 1</option>';
    if (prev && poolsList.some(p => String(p.pool_no) === String(prev))) {
      fPool.value = prev;
    } else if (window.currentPool !== 'all') {
      fPool.value = String(window.currentPool);
    }
  }

  const clearSel = document.getElementById('clear-scope-select');
  if (clearSel) {
    clearSel.innerHTML = `<option value="all">Entire Question Bank (All Pools)</option>` +
      poolsList.map(p =>
        `<option value="${p.pool_no}">${esc(window.poolName ? window.poolName(p.pool_no) : `Pool ${p.pool_no}`)} only (${p.count ?? 0} Q)</option>`
      ).join('');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-rename-pool')?.addEventListener('click', async () => {
    if (window.currentPool === 'all') return;
    const curName = window.poolName ? window.poolName(parseInt(window.currentPool)) : `Pool ${window.currentPool}`;
    const name = prompt(`Rename ${curName}:`, curName);
    if (!name || !name.trim()) return;
    try {
      await apiFetch(`/api/banks/${window.getBankId()}/pools/${window.currentPool}`, {
        method: 'PUT',
        body: JSON.stringify({ name: name.trim() })
      });
      toast('Pool renamed', 'success');
      await window.loadPools?.();
    } catch (e) {
      toast(e.message, 'error');
    }
  });

  document.getElementById('btn-delete-pool')?.addEventListener('click', async () => {
    if (window.currentPool === 'all') return;
    const curName = window.poolName ? window.poolName(parseInt(window.currentPool)) : `Pool ${window.currentPool}`;
    if (!confirm(`Delete "${curName}" and all questions inside it?`)) return;
    try {
      const res = await apiFetch(`/api/banks/${window.getBankId()}/pools/${window.currentPool}`, {
        method: 'DELETE'
      });
      toast(`Deleted ${curName} (${res.deleted_questions} question(s) removed)`, 'info');
      window.currentPool = 'all';
      await window.loadPools?.();
      await window.loadQuestions?.();
    } catch (e) {
      toast(e.message, 'error');
    }
  });
});

window.renderPoolTabs = renderPoolTabs;
window.renderPoolSelects = renderPoolSelects;
window.handleAddPoolPrompt = handleAddPoolPrompt;

