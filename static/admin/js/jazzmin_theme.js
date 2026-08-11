(function () {
  'use strict';

  var STORAGE_KEY = 'jazzmin-theme-mode';
  var applying = false;

  function getStoredMode() {
    return localStorage.getItem(STORAGE_KEY) || 'dark';
  }

  function resolveMode(mode) {
    if (mode === 'auto') {
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
    }
    return mode === 'light' ? 'light' : 'dark';
  }

  function getResolvedMode() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }

  function syncChrome(resolved) {
    document.documentElement.style.colorScheme = resolved;
    if (document.body) {
      document.body.setAttribute('data-bs-theme', resolved);
    }

    var sidebar = document.getElementById('jazzy-sidebar');
    if (sidebar) {
      sidebar.setAttribute('data-bs-theme', resolved);
      sidebar.classList.remove(
        'sidebar-dark-primary',
        'sidebar-dark-info',
        'sidebar-dark-success',
        'sidebar-dark-warning',
        'sidebar-dark-danger',
        'sidebar-dark-secondary',
        'sidebar-light-primary',
        'sidebar-light-info',
        'sidebar-light-success',
        'sidebar-light-warning',
        'sidebar-light-danger',
        'sidebar-light-secondary'
      );
      sidebar.classList.add(resolved === 'dark' ? 'sidebar-dark-info' : 'sidebar-light-info');
    }

    var header = document.getElementById('jazzy-navbar');
    if (header) {
      header.setAttribute('data-bs-theme', resolved);
      header.classList.toggle('navbar-dark', resolved === 'dark');
      header.classList.toggle('navbar-light', resolved === 'light');
      header.classList.toggle('bg-dark', resolved === 'dark');
      header.classList.toggle('bg-white', resolved === 'light');
      header.classList.toggle('border-bottom', resolved === 'light');
    }

    var wrapper = document.querySelector('.app-wrapper') || document.querySelector('.wrapper');
    if (wrapper) {
      wrapper.setAttribute('data-bs-theme', resolved);
    }
  }

  function applyMode(mode) {
    var stored = mode === 'auto' || mode === 'light' || mode === 'dark' ? mode : 'dark';
    var resolved = resolveMode(stored);

    applying = true;
    document.documentElement.setAttribute('data-bs-theme', resolved);
    syncChrome(resolved);
    localStorage.setItem(STORAGE_KEY, stored);
    applying = false;

    var modeSelect = document.getElementById('jazzmin-mode-select');
    if (modeSelect && modeSelect.value !== stored) {
      modeSelect.value = stored;
    }
    updateQuickToggleIcon();
  }

  function localizeModeSelect() {
    var modeSelect = document.getElementById('jazzmin-mode-select');
    if (!modeSelect) return;

    var labels = {
      light: 'Светлая',
      dark: 'Тёмная',
      auto: 'Как в системе',
    };
    Array.from(modeSelect.options).forEach(function (option) {
      if (labels[option.value]) option.textContent = labels[option.value];
    });

    document.querySelectorAll('#jazzy-theme-chooser .dropdown-header').forEach(function (header) {
      var text = header.textContent.trim();
      if (text === 'Color Scheme') header.textContent = 'Цветовая схема';
      if (text === 'Theme') header.textContent = 'Тема';
    });
  }

  function updateQuickToggleIcon() {
    var btn = document.getElementById('jazzmin-quick-theme-toggle');
    if (!btn) return;
    var icon = btn.querySelector('i');
    var isDark = getResolvedMode() === 'dark';
    if (icon) icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
    btn.title = isDark ? 'Включить светлую тему' : 'Включить тёмную тему';
    btn.setAttribute('aria-label', btn.title);
  }

  function addQuickThemeToggle() {
    var nav =
      document.querySelector('#jazzy-navbar .navbar-nav.ms-auto') ||
      document.querySelector('#jazzy-navbar .navbar-nav:last-child');
    if (!nav || document.getElementById('jazzmin-quick-theme-toggle')) return;

    var item = document.createElement('li');
    item.className = 'nav-item';
    item.innerHTML =
      '<button type="button" class="nav-link btn" id="jazzmin-quick-theme-toggle" ' +
      'title="Переключить тему" aria-label="Переключить тему">' +
      '<i class="fas fa-moon" aria-hidden="true"></i></button>';

    var palette = document.getElementById('jazzy-theme-chooser');
    var paletteItem = palette ? palette.closest('.nav-item') : null;
    if (paletteItem && paletteItem.parentNode === nav) {
      nav.insertBefore(item, paletteItem);
    } else {
      nav.insertBefore(item, nav.firstChild);
    }

    item.querySelector('button').addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      applyMode(getResolvedMode() === 'dark' ? 'light' : 'dark');
    });
  }

  function bindModeSelect() {
    var modeSelect = document.getElementById('jazzmin-mode-select');
    if (!modeSelect || modeSelect.dataset.ublegkoBound === '1') return;
    modeSelect.dataset.ublegkoBound = '1';
    modeSelect.addEventListener('change', function () {
      applyMode(modeSelect.value);
    });
  }

  function watchHtmlThemeAttr() {
    if (window.__ublegkoThemeObserver) return;
    window.__ublegkoThemeObserver = new MutationObserver(function () {
      if (applying) return;
      applying = true;
      syncChrome(getResolvedMode());
      updateQuickToggleIcon();
      applying = false;
    });
    window.__ublegkoThemeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme'],
    });
  }

  function init() {
    localizeModeSelect();
    addQuickThemeToggle();
    bindModeSelect();
    applyMode(getStoredMode());
    watchHtmlThemeAttr();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
