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

  function ensureAdminSearchGroup() {
    var form = document.getElementById('changelist-search');
    if (!form) return;
    var input =
      form.querySelector('#searchbar') || form.querySelector('input[name="q"]');
    if (!input) return;

    var group = input.closest('.admin-search-group');
    var button =
      (group && group.querySelector('button[type="submit"], .btn[type="submit"]')) ||
      form.querySelector(':scope > button[type="submit"], :scope > .btn[type="submit"]') ||
      form.querySelector('button[type="submit"], .btn[type="submit"]');

    if (!group) {
      group = document.createElement('div');
      group.className = 'admin-search-group';
      input.parentNode.insertBefore(group, input);
      group.appendChild(input);
    }
    if (button && button.parentNode !== group) {
      group.appendChild(button);
    }
  }

  function setInboxNavLabel(anchor, baseLabel, count) {
    if (!anchor) return;
    var text = baseLabel + (count > 0 ? ' (' + count + ')' : '');
    var p = anchor.querySelector('p');
    if (p) {
      // Jazzmin: иконка справа в <p> как <i class="right ...">
      var rightIcon = p.querySelector('i.right, .right');
      p.textContent = text;
      if (rightIcon) p.appendChild(rightIcon);
      return;
    }
    var icon = anchor.querySelector(':scope > i');
    anchor.textContent = '';
    if (icon) {
      anchor.appendChild(icon);
      anchor.appendChild(document.createTextNode(' ' + text));
    } else {
      anchor.textContent = text;
    }
  }

  function isInboxListLink(href, modelPath) {
    if (!href || href.indexOf(modelPath) === -1) return false;
    if (href.indexOf('inbox-counts') !== -1) return false;
    // changelist: .../order/ или .../order/?... — не .../order/12/change/
    var re = new RegExp(modelPath.replace(/\//g, '\\/') + '(?:\\?.*)?$');
    return re.test(href.split('#')[0]);
  }

  function updateInboxNavCounts() {
    fetch('/admin/cart/order/inbox-counts/', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(function (response) {
        if (!response.ok) throw new Error('inbox counts');
        return response.json();
      })
      .then(function (data) {
        var orders = Number(data.orders_new || 0);
        var requests = Number(data.requests_new || 0);
        document.querySelectorAll('a[href]').forEach(function (a) {
          var href = a.getAttribute('href') || '';
          if (isInboxListLink(href, '/admin/cart/order/')) {
            setInboxNavLabel(a, 'Заявки', orders);
          } else if (isInboxListLink(href, '/admin/cart/stainhelprequest/')) {
            setInboxNavLabel(a, 'Запросы', requests);
          }
        });
      })
      .catch(function () {
        /* ignore: нет прав или офлайн */
      });
  }

  function init() {
    localizeModeSelect();
    addQuickThemeToggle();
    bindModeSelect();
    applyMode(getStoredMode());
    watchHtmlThemeAttr();
    ensureAdminSearchGroup();
    updateInboxNavCounts();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
