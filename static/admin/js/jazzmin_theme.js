(function () {
  'use strict';

  function getResolvedMode() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
  }

  function syncAdminContainers(mode) {
    var sidebar = document.getElementById('jazzy-sidebar');
    if (sidebar) {
      sidebar.setAttribute('data-bs-theme', mode);
      sidebar.classList.toggle('sidebar-dark-info', mode === 'dark');
      sidebar.classList.toggle('sidebar-light-info', mode === 'light');
    }
    var header = document.getElementById('jazzy-navbar');
    if (header) {
      header.classList.toggle('navbar-dark', mode === 'dark');
      header.classList.toggle('navbar-light', mode === 'light');
    }
  }

  function applyMode(mode) {
    var resolved = mode;
    if (mode === 'auto') {
      resolved =
        window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light';
    }
    document.documentElement.setAttribute('data-bs-theme', resolved);
    syncAdminContainers(resolved);
    localStorage.setItem('jazzmin-theme-mode', mode);
  }

  function localizeModeSelect() {
    var modeSelect = document.getElementById('jazzmin-mode-select');
    if (!modeSelect) {
      return;
    }

    var labels = {
      light: 'Светлая',
      dark: 'Тёмная',
      auto: 'Как в системе',
    };

    Array.from(modeSelect.options).forEach(function (option) {
      if (labels[option.value]) {
        option.textContent = labels[option.value];
      }
    });

    var headers = document.querySelectorAll('#jazzy-theme-chooser .dropdown-header');
    headers.forEach(function (header) {
      if (header.textContent.trim() === 'Color Scheme') {
        header.textContent = 'Цветовая схема';
      }
    });
  }

  function updateQuickToggleIcon() {
    var btn = document.getElementById('jazzmin-quick-theme-toggle');
    if (!btn) {
      return;
    }
    var icon = btn.querySelector('i');
    if (!icon) {
      return;
    }
    icon.className = getResolvedMode() === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    btn.title =
      getResolvedMode() === 'dark' ? 'Светлая тема' : 'Тёмная тема';
  }

  function addQuickThemeToggle() {
    var nav = document.querySelector('#jazzy-navbar .navbar-nav.ms-auto');
    if (!nav || document.getElementById('jazzmin-quick-theme-toggle')) {
      return;
    }

    var item = document.createElement('li');
    item.className = 'nav-item';
    item.innerHTML =
      '<button type="button" class="nav-link btn" id="jazzmin-quick-theme-toggle" title="Тёмная тема" aria-label="Переключить тему">' +
      '<i class="fas fa-moon" aria-hidden="true"></i>' +
      '</button>';

    var paletteItem = nav.querySelector('#jazzy-theme-chooser')
      ? nav.querySelector('#jazzy-theme-chooser').closest('.nav-item')
      : null;
    if (paletteItem) {
      nav.insertBefore(item, paletteItem);
    } else {
      nav.insertBefore(item, nav.firstChild);
    }

    var btn = item.querySelector('button');
    var modeSelect = document.getElementById('jazzmin-mode-select');

    btn.addEventListener('click', function () {
      var next = getResolvedMode() === 'dark' ? 'light' : 'dark';
      applyMode(next);
      if (modeSelect) {
        modeSelect.value = next;
      }
      updateQuickToggleIcon();
    });

    updateQuickToggleIcon();
    syncAdminContainers(getResolvedMode());
  }

  function init() {
    localizeModeSelect();
    addQuickThemeToggle();

    var modeSelect = document.getElementById('jazzmin-mode-select');
    if (modeSelect) {
      var savedMode = localStorage.getItem('jazzmin-theme-mode');
      if (savedMode) {
        modeSelect.value = savedMode;
      }
      modeSelect.addEventListener('change', function () {
        applyMode(modeSelect.value);
        updateQuickToggleIcon();
      });
    }

    updateQuickToggleIcon();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
