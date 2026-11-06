/* app.js — Shared state, navigation, toast system, bank & pool state */

const API = '';  // same origin

// ── Bank / Pool state ──────────────────────────────────────────────────────
let currentBankId = parseInt(localStorage.getItem('cd_bank_id')) || 1;
let banks = [];
let pools = [];   // pools of the current bank: [{pool_no, name, count, total_uses}]
let activeTab = 'admin';

function currentBank() {
  return banks.find(b => b.id === currentBankId) || null;
}
function poolName(poolNo) {
  const p = pools.find(x => x.pool_no === poolNo);
  return p && p.name ? p.name : `Pool ${poolNo}`;
}
/** Append bank_id to a URL (handles existing query strings). */
function withBank(url) {
  return url + (url.includes('?') ? '&' : '?') + `bank_id=${currentBankId}`;
}

// ── Navigation ─────────────────────────────────────────────────────────────
const tabs = ['admin', 'papers', 'answers', 'grading', 'results'];

function switchTab(tab) {
  activeTab = tab;
  tabs.forEach(t => {
    document.getElementById(`tab-${t}`)?.classList.toggle('active', t === tab);
    document.querySelectorAll(`.nav-item[data-tab="${t}"]`).forEach(btn => btn.classList.toggle('active', t === tab));
  });
  // Trigger load on tab activation
  if (tab === 'admin')   window.loadQuestions?.();
  if (tab === 'papers')  window.loadPapers?.();
  if (tab === 'answers') window.loadAnswerKeys?.();
  if (tab === 'results') window.loadResults?.();
}

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── API helpers ────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

// ── Banks & Pools ──────────────────────────────────────────────────────────
async function loadBanks() {
  banks = await apiFetch('/api/banks');
  if (!banks.find(b => b.id === currentBankId)) {
    currentBankId = banks.length ? banks[0].id : 1;
    localStorage.setItem('cd_bank_id', currentBankId);
  }
  renderBankSelect();
}

function renderBankSelect() {
  const sel = document.getElementById('bank-select');
  if (!sel) return;
  sel.innerHTML = banks.map(b =>
    `<option value="${b.id}">${escHtml(b.name)} (${escHtml(b.code)}) · ${b.question_count} Q</option>`
  ).join('');
  sel.value = String(currentBankId);
}

async function loadPools() {
  pools = await apiFetch(`/api/banks/${currentBankId}/pools`);
  renderPoolStatus();
  window.onPoolsChanged?.();
}

function renderPoolStatus() {
  const container = document.getElementById('pool-bars');
  if (!container) return;
  const maxCount = Math.max(...pools.map(p => p.count), 1);
  container.innerHTML = pools.map(p => {
    const pct = Math.round((p.count / maxCount) * 100);
    return `
      <div class="pool-bar-row">
        <span class="pool-bar-label" title="${escHtml(poolName(p.pool_no))}">${escHtml(poolName(p.pool_no))}</span>
        <div class="pool-bar-track">
          <div class="pool-bar-fill" style="width:${pct}%"></div>
        </div>
        <span class="pool-bar-count">${p.count}</span>
      </div>`;
  }).join('') || '<div style="font-size:0.78rem;color:var(--text-muted)">No pools</div>';
  const title = document.querySelector('.pool-status-title');
  const b = currentBank();
  if (title) title.textContent = b ? `Pool Coverage — ${b.name}` : 'Pool Coverage';
}

async function refreshPoolStatus() {
  try {
    await Promise.all([loadBanks(), loadPools()]);
  } catch (_) {}
}

async function switchBank(id) {
  currentBankId = parseInt(id);
  localStorage.setItem('cd_bank_id', currentBankId);
  try {
    await loadPools();
    await loadBanks();
  } catch (e) { toast(e.message, 'error'); }
  window.onBankChanged?.();
  switchTab(activeTab);
}

function escHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

document.getElementById('bank-select')?.addEventListener('change', e => switchBank(e.target.value));

// ── TA-Lock Evaluator Mode & Share Modal ───────────────────────────
const ADMIN_PIN = '1234';

function isTaMode() {
  const urlParams = new URLSearchParams(window.location.search);
  const role = urlParams.get('role') || urlParams.get('mode') || urlParams.get('ta');
  if (role === 'ta' || role === 'grader' || role === '1') {
    sessionStorage.setItem('cd_app_role', 'ta');
    return true;
  }
  return sessionStorage.getItem('cd_app_role') === 'ta';
}

function applyTaMode(active) {
  document.body.classList.toggle('ta-mode-active', active);
  if (active) {
    sessionStorage.setItem('cd_app_role', 'ta');
    switchTab('grading');
  } else {
    sessionStorage.removeItem('cd_app_role');
  }
}

function promptUnlockAdmin() {
  const entered = prompt('Enter Admin PIN to unlock full dashboard:', '');
  if (entered === null) return;
  if (entered.trim() === ADMIN_PIN) {
    applyTaMode(false);
    toast('Admin dashboard unlocked', 'success');
  } else {
    toast('Incorrect Admin PIN', 'error');
  }
}

document.getElementById('btn-unlock-admin')?.addEventListener('click', promptUnlockAdmin);

// Share TA Portal Modal
const shareModal = document.getElementById('modal-ta-share-backdrop');
const shareBtn = document.getElementById('btn-share-ta-portal');
const closeShareBtn = document.getElementById('btn-close-ta-share');
const doneShareBtn = document.getElementById('btn-done-ta-share');
const copyUrlBtn = document.getElementById('btn-copy-ta-url');
const urlInput = document.getElementById('ta-share-url');

function openShareModal() {
  if (!shareModal) return;
  const taUrl = `${window.location.origin}/?role=ta`;
  if (urlInput) urlInput.value = taUrl;
  shareModal.classList.remove('hidden');

  const canvas = document.getElementById('ta-portal-qr');
  if (canvas && window.renderQRCodeToCanvas) {
    window.renderQRCodeToCanvas(canvas, taUrl, 180);
  }
}

function closeShareModal() {
  if (shareModal) shareModal.classList.add('hidden');
}

shareBtn?.addEventListener('click', openShareModal);
closeShareBtn?.addEventListener('click', closeShareModal);
doneShareBtn?.addEventListener('click', closeShareModal);
shareModal?.addEventListener('click', (e) => {
  if (e.target === shareModal) closeShareModal();
});

copyUrlBtn?.addEventListener('click', async () => {
  if (!urlInput) return;
  try {
    await navigator.clipboard.writeText(urlInput.value);
    toast('TA Portal link copied to clipboard!', 'success');
  } catch (_) {
    urlInput.select();
    document.execCommand('copy');
    toast('TA Portal link copied!', 'success');
  }
});

// ── Global exports ─────────────────────────────────────────────────────────
window.API          = API;
window.toast        = toast;
window.apiFetch     = apiFetch;
window.switchTab    = switchTab;
window.switchBank   = switchBank;
window.loadBanks    = loadBanks;
window.loadPools    = loadPools;
window.refreshPoolStatus = refreshPoolStatus;
window.withBank     = withBank;
window.poolName     = poolName;
window.currentBank  = currentBank;
window.getBankId    = () => currentBankId;
window.getPools     = () => pools;
window.escHtml      = escHtml;

// Initial load (scripts below are loaded by the time these requests resolve)
(async function init() {
  try {
    await loadBanks();
    await loadPools();
  } catch (e) {
    console.error('Initial load failed', e);
  }
  window.onBankChanged?.();
  if (isTaMode()) {
    applyTaMode(true);
  } else {
    switchTab('admin');
  }
})();
