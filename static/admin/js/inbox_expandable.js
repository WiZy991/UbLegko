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

  function paintStatusGroup(group, status) {
    if (!group) return;
    group.setAttribute('data-inbox-status', status);
    group.querySelectorAll('.inbox-status-btn').forEach(function (btn) {
      btn.classList.toggle('is-active', btn.getAttribute('data-status') === status);
    });
    var row = group.closest('tr.inbox-row');
    if (row) {
      row.setAttribute('data-inbox-status', status);
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

    var kindEl = document.querySelector('.inbox-status-btns[data-inbox-kind]');
    if (kindEl) {
      var base =
        kindEl.getAttribute('data-inbox-kind') === 'order' ? 'Заявки' : 'Запросы';
      var count =
        kindEl.getAttribute('data-inbox-kind') === 'order' ? orders : requests;
      document.title = base + (count > 0 ? ' (' + count + ')' : '') + ' | Убираемся Легко';
    }
  }

  function saveStatus(group, status) {
    var url = group.getAttribute('data-inbox-quick-url');
    if (!url) return;

    var previous = group.getAttribute('data-inbox-status') || 'new';
    if (previous === status) return;

    group.classList.add('is-saving');
    group.querySelectorAll('.inbox-status-btn').forEach(function (btn) {
      btn.disabled = true;
    });
    paintStatusGroup(group, status);

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        Accept: 'application/json',
      },
      body: JSON.stringify({ status: status }),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok && data && data.ok, data: data || {} };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          paintStatusGroup(group, previous);
          window.alert((result.data && result.data.error) || 'Не удалось сохранить статус');
          return;
        }
        var saved = result.data.status || status;
        paintStatusGroup(group, saved);
        applyCounts(result.data);
      })
      .catch(function () {
        paintStatusGroup(group, previous);
        window.alert('Не удалось сохранить статус');
      })
      .finally(function () {
        group.classList.remove('is-saving');
        group.querySelectorAll('.inbox-status-btn').forEach(function (btn) {
          btn.disabled = false;
        });
      });
  }

  document.addEventListener('click', function (event) {
    var expandBtn = event.target.closest('.inbox-row-expand');
    if (expandBtn) {
      event.preventDefault();
      var id = expandBtn.getAttribute('data-inbox-id');
      if (!id) return;
      var detail = document.getElementById('inbox-detail-' + id);
      if (!detail) return;
      var open = detail.hasAttribute('hidden');
      detail.hidden = !open;
      setExpanded(expandBtn, open);
      return;
    }

    var statusBtn = event.target.closest('.inbox-status-btn');
    if (!statusBtn) return;
    event.preventDefault();
    var group = statusBtn.closest('.inbox-status-btns');
    if (!group || group.classList.contains('is-saving')) return;
    var status = statusBtn.getAttribute('data-status');
    if (!status) return;
    saveStatus(group, status);
  });
})();
