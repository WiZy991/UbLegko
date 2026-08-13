(function () {
  'use strict';

  function escapeHtml(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function ensureSearchGroup(input) {
    var form = input.closest('#changelist-search') || input.form;
    if (!form) return;

    var group = input.closest('.admin-search-group');
    var button =
      (group && group.querySelector('button[type="submit"], .btn[type="submit"]')) ||
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

  function initAdminProductSuggest() {
    var suggestUrl =
      (window.UBLEGKO_PRODUCT_SEARCH_SUGGEST || '').trim() ||
      (document.body && document.body.getAttribute('data-product-search-suggest')) ||
      '';
    if (!suggestUrl) return;

    var input =
      document.getElementById('searchbar') ||
      document.querySelector('#changelist-search input[name="q"]') ||
      document.querySelector('input[name="q"][type="text"]');
    if (!input || input.dataset.suggestBound === '1') return;
    input.dataset.suggestBound = '1';

    ensureSearchGroup(input);

    var wrap = document.createElement('div');
    wrap.className = 'admin-search-suggest-wrap';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var box = document.createElement('div');
    box.className = 'admin-search-suggest';
    box.hidden = true;
    box.setAttribute('role', 'listbox');
    wrap.appendChild(box);

    var timer = null;
    var activeIndex = -1;
    var items = [];
    var lastQuery = '';

    function hide() {
      box.hidden = true;
      box.innerHTML = '';
      items = [];
      activeIndex = -1;
    }

    function setActive(index) {
      activeIndex = index;
      items.forEach(function (el, i) {
        el.classList.toggle('is-active', i === activeIndex);
      });
    }

    function render(results, query) {
      lastQuery = query;
      if (!results.length) {
        box.innerHTML = '<div class="admin-search-suggest__empty">Ничего не найдено</div>';
        box.hidden = false;
        items = [];
        activeIndex = -1;
        return;
      }
      box.innerHTML = results
        .map(function (r, i) {
          var meta = [r.sku, r.category].filter(Boolean).join(' · ');
          return (
            '<a class="admin-search-suggest__item" role="option" href="' +
            escapeHtml(r.url) +
            '" data-index="' +
            i +
            '">' +
            '<span class="admin-search-suggest__name">' +
            escapeHtml(r.name) +
            '</span>' +
            (meta
              ? '<span class="admin-search-suggest__meta">' + escapeHtml(meta) + '</span>'
              : '') +
            '</a>'
          );
        })
        .join('');
      box.hidden = false;
      items = Array.prototype.slice.call(box.querySelectorAll('.admin-search-suggest__item'));
      activeIndex = -1;
    }

    function fetchSuggest(query) {
      if (!query) {
        hide();
        return;
      }
      fetch(suggestUrl + '?q=' + encodeURIComponent(query), {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (input.value.trim() !== query) return;
          render((data && data.results) || [], query);
        })
        .catch(function () {
          hide();
        });
    }

    input.setAttribute('autocomplete', 'off');
    input.setAttribute('aria-autocomplete', 'list');

    input.addEventListener('input', function () {
      var query = input.value.trim();
      window.clearTimeout(timer);
      if (!query) {
        hide();
        return;
      }
      timer = window.setTimeout(function () {
        fetchSuggest(query);
      }, 180);
    });

    input.addEventListener('keydown', function (event) {
      if (box.hidden || !items.length) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActive(activeIndex < items.length - 1 ? activeIndex + 1 : 0);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActive(activeIndex > 0 ? activeIndex - 1 : items.length - 1);
      } else if (event.key === 'Enter' && activeIndex >= 0 && items[activeIndex]) {
        event.preventDefault();
        window.location.href = items[activeIndex].href;
      } else if (event.key === 'Escape') {
        hide();
      }
    });

    input.addEventListener('blur', function () {
      window.setTimeout(hide, 150);
    });

    input.addEventListener('focus', function () {
      var query = input.value.trim();
      if (query && query === lastQuery && box.innerHTML) {
        box.hidden = false;
      } else if (query) {
        fetchSuggest(query);
      }
    });
  }

  // Убрать подсказку Jazzmin/Django у поиска
  function hideSearchHelp() {
    document
      .querySelectorAll(
        '#toolbar .help, #changelist-search .form-text, #changelist-search .help, ' +
          '.search-help, label[for="searchbar"] + .help, #content-main .form-text'
      )
      .forEach(function (el) {
        var text = (el.textContent || '').trim().toLowerCase();
        if (
          !text ||
          text.indexOf('как на сайте') !== -1 ||
          text.indexOf('search') !== -1 ||
          text.indexOf('поиск') !== -1 ||
          text.indexOf('назван') !== -1
        ) {
          el.style.display = 'none';
        }
      });
  }

  function boot() {
    hideSearchHelp();
    initAdminProductSuggest();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
