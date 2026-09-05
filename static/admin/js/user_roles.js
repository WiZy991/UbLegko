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

  function postJson(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok || !data.ok) {
          var err = new Error((data && data.error) || 'Ошибка сохранения');
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  function setRoleLock(roleSelect, locked) {
    if (!roleSelect) return;
    roleSelect.disabled = !!locked;
    roleSelect.classList.toggle('is-locked', !!locked);
    roleSelect.title = locked
      ? 'Права задаёт группа — смените группу или выберите «— без сегмента»'
      : 'Права доступа';
  }

  function syncRowSelects(userId, data) {
    var roleSelect = document.querySelector(
      '.user-role-select[data-user-id="' + userId + '"]'
    );
    var membershipSelect = document.querySelector(
      '.user-membership-select[data-user-id="' + userId + '"]'
    );
    if (roleSelect && data.role != null) {
      roleSelect.value = data.role;
      roleSelect.classList.remove(
        'user-role-select--admin',
        'user-role-select--staff',
        'user-role-select--user'
      );
      roleSelect.classList.add('user-role-select--' + data.role);
    }
    if (membershipSelect && data.membership != null) {
      membershipSelect.value = data.membership;
      setRoleLock(roleSelect, data.role_locked != null ? data.role_locked : data.membership !== '');
    } else if (data.role_locked != null) {
      setRoleLock(roleSelect, data.role_locked);
    }
  }

  function bindSelect(select, urlAttr, payloadKey) {
    if (!select || select.dataset.bound === '1') return;
    select.dataset.bound = '1';
    var previous = select.value;
    var userId = select.getAttribute('data-user-id');

    select.addEventListener('change', function () {
      if (select.disabled) return;
      var url = select.getAttribute(urlAttr);
      if (!url) return;

      var payload = {};
      payload[payloadKey] = select.value;
      select.classList.add('is-saving');
      select.classList.remove('is-error');

      postJson(url, payload)
        .then(function (data) {
          previous = select.value;
          select.classList.remove('is-saving');
          syncRowSelects(userId, data);
          // Если смена группы на странице группы — убрать строку, если больше не в этой группе
          if (payloadKey === 'membership' && select.classList.contains('group-page-membership')) {
            var currentKey = select.getAttribute('data-current-group-key') || '';
            if (String(data.membership || '') !== String(currentKey)) {
              var row = select.closest('tr.inbox-row') || select.closest('tr');
              var detail = userId
                ? document.getElementById('inbox-detail-' + userId)
                : null;
              if (row) row.remove();
              if (detail) detail.remove();
              var counter = document.querySelector('[data-members-count]');
              if (counter) {
                var n = document.querySelectorAll(
                  '.group-page-members tr.inbox-row'
                ).length;
                counter.textContent = String(n);
              }
            }
          }
        })
        .catch(function (err) {
          select.value = previous;
          select.classList.remove('is-saving');
          select.classList.add('is-error');
          window.alert(err.message || 'Не удалось сохранить');
        });
    });
  }

  function init(root) {
    var scope = root || document;
    scope.querySelectorAll('.user-role-select').forEach(function (el) {
      bindSelect(el, 'data-role-url', 'role');
    });
    scope.querySelectorAll('.user-membership-select').forEach(function (el) {
      bindSelect(el, 'data-membership-url', 'membership');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      init();
    });
  } else {
    init();
  }
})();
