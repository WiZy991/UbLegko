(function () {
  'use strict';

  function getCookie(name) {
    var cookies = document.cookie ? document.cookie.split(';') : [];
    for (var i = 0; i < cookies.length; i++) {
      var cookie = cookies[i].trim();
      if (cookie.indexOf(name + '=') === 0) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return '';
  }

  function setExpanded(btn, expanded) {
    btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    var icon = btn.querySelector('i');
    if (icon) {
      icon.className = expanded ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
    }
    var row = btn.closest('tr.inbox-row');
    if (row) {
      row.classList.toggle('inbox-row--expanded', expanded);
    }
  }

  function paintStatusSelect(select) {
    if (!select) return;
    select.classList.remove('status-select--new', 'status-select--processed');
    var value = String(select.value || '');
    if (value === 'new') {
      select.classList.add('status-select--new');
    } else if (value === 'processed') {
      select.classList.add('status-select--processed');
    }
    var row = select.closest('tr.inbox-row');
    if (row) {
      row.setAttribute('data-inbox-status', value);
    }
  }

  function setNavLabel(anchor, baseLabel, count) {
    if (!anchor) return;
    var text = baseLabel + (count > 0 ? ' (' + count + ')' : '');
    var p = anchor.querySelector('p');
    if (p) {
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

  function isListLink(href, modelPath) {
    if (!href || href.indexOf(modelPath) === -1) return false;
    if (href.indexOf('inbox-counts') !== -1) return false;
    if (href.indexOf('quick-status') !== -1) return false;
    var re = new RegExp(modelPath.replace(/\//g, '\\/') + '(?:\\?.*)?$');
    return re.test(href.split('#')[0]);
  }

  function applyCounts(data) {
    var orders = Number(data.orders_new || 0);
    var requests = Number(data.requests_new || 0);

    document.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (isListLink(href, '/admin/cart/order/')) {
        setNavLabel(a, 'Заявки', orders);
      } else if (isListLink(href, '/admin/cart/stainhelprequest/')) {
        setNavLabel(a, 'Запросы', requests);
      }
    });

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

    var kind = document.querySelector('.inbox-status-select[data-inbox-kind]');
    if (kind) {
      var base =
        kind.getAttribute('data-inbox-kind') === 'order' ? 'Заявки' : 'Запросы';
      var count =
        kind.getAttribute('data-inbox-kind') === 'order' ? orders : requests;
      document.title = base + (count > 0 ? ' (' + count + ')' : '') + ' | Убираемся Легко';
    }
  }

  function saveStatus(select) {
    var url = select.getAttribute('data-inbox-quick-url');
    if (!url) return;

    var previous = select.getAttribute('data-inbox-prev') || select.value;
    select.disabled = true;
    select.classList.add('inbox-status-select--saving');

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        Accept: 'application/json',
      },
      body: JSON.stringify({ status: select.value }),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok && data && data.ok, data: data || {} };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          select.value = previous;
          paintStatusSelect(select);
          window.alert((result.data && result.data.error) || 'Не удалось сохранить статус');
          return;
        }
        select.setAttribute('data-inbox-prev', select.value);
        paintStatusSelect(select);
        applyCounts(result.data);
      })
      .catch(function () {
        select.value = previous;
        paintStatusSelect(select);
        window.alert('Не удалось сохранить статус');
      })
      .finally(function () {
        select.disabled = false;
        select.classList.remove('inbox-status-select--saving');
      });
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest('.inbox-row-expand');
    if (!btn) return;
    event.preventDefault();
    var id = btn.getAttribute('data-inbox-id');
    if (!id) return;
    var detail = document.getElementById('inbox-detail-' + id);
    if (!detail) return;
    var open = detail.hasAttribute('hidden');
    detail.hidden = !open;
    setExpanded(btn, open);
  });

  function initStatusControls() {
    document.querySelectorAll('.inbox-status-select').forEach(function (select) {
      select.setAttribute('data-inbox-prev', select.value);
      paintStatusSelect(select);
      select.addEventListener('change', function () {
        paintStatusSelect(select);
        saveStatus(select);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStatusControls);
  } else {
    initStatusControls();
  }
})();
