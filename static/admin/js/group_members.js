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

  function postForm(url, data) {
    var body = new URLSearchParams(data || {});
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: body.toString(),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok || !data.ok) {
          throw new Error((data && data.error) || 'Ошибка');
        }
        return data;
      });
    });
  }

  function initMembers() {
    var root = document.getElementById('group-members');
    if (!root) return;

    var searchInput = document.getElementById('group-member-search');
    var userIdInput = document.getElementById('group-member-user-id');
    var addBtn = document.getElementById('group-member-add-btn');
    var suggest = document.getElementById('group-member-suggest');
    var addForm = document.getElementById('group-member-add-form');
    var searchUrl = root.getAttribute('data-search-url');
    var addUrl = root.getAttribute('data-add-url');
    var timer = null;

    function clearSuggest() {
      suggest.innerHTML = '';
      suggest.hidden = true;
    }

    function renderSuggest(items) {
      suggest.innerHTML = '';
      if (!items || !items.length) {
        suggest.hidden = true;
        return;
      }
      items.forEach(function (item) {
        var li = document.createElement('li');
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = item.text;
        btn.addEventListener('click', function () {
          userIdInput.value = String(item.id);
          searchInput.value = item.text;
          addBtn.disabled = false;
          clearSuggest();
        });
        li.appendChild(btn);
        suggest.appendChild(li);
      });
      suggest.hidden = false;
    }

    if (searchInput) {
      searchInput.addEventListener('input', function () {
        userIdInput.value = '';
        addBtn.disabled = true;
        var q = searchInput.value.trim();
        clearTimeout(timer);
        timer = setTimeout(function () {
          fetch(searchUrl + '?q=' + encodeURIComponent(q), {
            credentials: 'same-origin',
          })
            .then(function (r) { return r.json(); })
            .then(function (data) {
              if (data && data.ok) renderSuggest(data.results || []);
            })
            .catch(function () { clearSuggest(); });
        }, 220);
      });
    }

    if (addForm) {
      addForm.addEventListener('submit', function (event) {
        event.preventDefault();
        if (!userIdInput.value) return;
        addBtn.disabled = true;
        postForm(addUrl, { user_id: userIdInput.value })
          .then(function (data) {
            window.location.href = data.redirect || window.location.href;
          })
          .catch(function (err) {
            addBtn.disabled = false;
            window.alert(err.message || 'Не удалось добавить');
          });
      });
    }

    root.querySelectorAll('.group-members__move').forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        var select = form.querySelector('select[name="target_group_id"]');
        if (!select || !select.value) {
          window.alert('Выберите группу');
          return;
        }
        postForm(form.getAttribute('data-url'), { target_group_id: select.value })
          .then(function (data) {
            window.location.href = data.redirect || window.location.href;
          })
          .catch(function (err) {
            window.alert(err.message || 'Не удалось перенести');
          });
      });
    });

    root.querySelectorAll('.group-members__btn--danger, .group-members__remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!window.confirm('Убрать пользователя из группы?')) return;
        postForm(btn.getAttribute('data-url'), {})
          .then(function () {
            var row = btn.closest('tr');
            if (row) row.remove();
          })
          .catch(function (err) {
            window.alert(err.message || 'Не удалось убрать');
          });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMembers);
  } else {
    initMembers();
  }
})();
