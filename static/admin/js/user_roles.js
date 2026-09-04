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

  function bindSelect(select, urlAttr, payloadKey) {
    if (!select || select.dataset.bound === '1') return;
    select.dataset.bound = '1';
    var previous = select.value;

    select.addEventListener('change', function () {
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
          if (payloadKey === 'role') {
            select.classList.remove(
              'user-role-select--admin',
              'user-role-select--staff',
              'user-role-select--user'
            );
            select.classList.add('user-role-select--' + (data.role || select.value));
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
    scope.querySelectorAll('.user-segment-select').forEach(function (el) {
      bindSelect(el, 'data-segment-url', 'segment');
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
