/**
 * Material 3 Theme Manager
 * Supports Dark / Light Mode with instant localStorage persistence
 * and prefers-color-scheme detection.
 */

(function () {
  function getPreferredTheme() {
    const saved = localStorage.getItem('app-theme');
    if (saved === 'dark' || saved === 'light') {
      return saved;
    }
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const icon = document.getElementById('theme-toggle-icon');
    const text = document.getElementById('theme-toggle-text');
    if (icon && text) {
      if (theme === 'dark') {
        icon.textContent = '☀️';
        text.textContent = 'Light Mode';
      } else {
        icon.textContent = '🌙';
        text.textContent = 'Dark Mode';
      }
    }
  }

  function initTheme() {
    const current = getPreferredTheme();
    applyTheme(current);

    const toggleBtn = document.getElementById('btn-theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        const activeTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem('app-theme', activeTheme);
        applyTheme(activeTheme);
      });
    }

    // Listen for OS preference changes if user hasn't explicitly chosen
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('app-theme')) {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
})();
