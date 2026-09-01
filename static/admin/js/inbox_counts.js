(function () {
  'use strict';

  var ORDERS_PATH = '/admin/cart/order/';
  var REQUESTS_PATH = '/admin/cart/stainhelprequest/';
  var API_URL = '/admin/cart/order/inbox-counts/';
  var POLL_MS = 45000;
  var pollTimer = null;

  function isListLink(href, modelPath) {
    if (!href || href.indexOf(modelPath) === -1) return false;
    if (href.indexOf('inbox-counts') !== -1) return false;
    if (href.indexOf('quick-status') !== -1) return false;
    var re = new RegExp(modelPath.replace(/\//g, '\\/') + '(?:\\?.*)?$');
    return re.test(href.split('#')[0]);
  }

  function setNavLabel(anchor, baseLabel, count) {
    if (!anchor) return;
    var text = baseLabel + (count > 0 ? ' (' + count + ')' : '');
    var p = anchor.querySelector('p');
    if (p) {
      var rightIcon = p.querySelector('i.right, .right, i.nav-arrow');
      p.textContent = text;
      if (rightIcon) p.appendChild(rightIcon);
      return;
    }
    var icon = anchor.querySelector(':scope > i.fas, :scope > i.far, :scope > i.nav-icon');
    anchor.textContent = '';
    if (icon) {
      anchor.appendChild(icon);
      anchor.appendChild(document.createTextNode(' ' + text));
    } else {
      anchor.textContent = text;
    }
  }

  function updatePageTitles(orders, requests) {
    var titleEl =
      document.querySelector('.app-main .content-header h3.mb-0') ||
      document.querySelector('.content-header h3.mb-0') ||
      document.querySelector('h3.mb-0');
    if (titleEl) {
      var raw = (titleEl.textContent || '').trim();
      if (raw.indexOf('Заявк') === 0) {
        titleEl.textContent = 'Заявки' + (orders > 0 ? ' (' + orders + ')' : '');
      } else if (raw.indexOf('Запрос') === 0) {
        titleEl.textContent = 'Запросы' + (requests > 0 ? ' (' + requests + ')' : '');
      }
    }

    var kindEl = document.querySelector('.inbox-status-btns[data-inbox-kind]');
    if (kindEl) {
      var base =
        kindEl.getAttribute('data-inbox-kind') === 'order' ? 'Заявки' : 'Запросы';
      var count =
        kindEl.getAttribute('data-inbox-kind') === 'order' ? orders : requests;
      document.title = base + (count > 0 ? ' (' + count + ')' : '') + ' | Убираемся Легко';
    }
  }

  function applyCounts(data) {
    var orders = Number(data.orders_new || 0);
    var requests = Number(data.requests_new || 0);

    document.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (isListLink(href, ORDERS_PATH)) {
        setNavLabel(a, 'Заявки', orders);
      } else if (isListLink(href, REQUESTS_PATH)) {
        setNavLabel(a, 'Запросы', requests);
      }
    });

    updatePageTitles(orders, requests);

    if (window.__UBLEGKO_INBOX_COUNTS__) {
      window.__UBLEGKO_INBOX_COUNTS__.orders_new = orders;
      window.__UBLEGKO_INBOX_COUNTS__.requests_new = requests;
    }
  }

  function fetchCounts() {
    return fetch(API_URL, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    }).then(function (response) {
      if (!response.ok) throw new Error('inbox counts');
      return response.json();
    });
  }

  function refresh() {
    return fetchCounts()
      .then(applyCounts)
      .catch(function () {
        /* нет прав или офлайн */
      });
  }

  function init() {
    if (window.__UBLEGKO_INBOX_COUNTS__) {
      applyCounts(window.__UBLEGKO_INBOX_COUNTS__);
    }
    refresh();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(refresh, POLL_MS);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) refresh();
    });
  }

  window.UblegkoInboxCounts = {
    apply: applyCounts,
    refresh: refresh,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
