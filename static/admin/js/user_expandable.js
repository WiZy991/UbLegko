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

  function setStatus(item, text, kind) {
    var status = item.querySelector('.user-review-item__status');
    if (!status) return;
    status.hidden = !text;
    status.textContent = text || '';
    status.classList.remove('is-ok', 'is-error');
    if (kind) status.classList.add(kind);
  }

  function setBusy(item, busy) {
    item.classList.toggle('is-saving', busy);
    item.querySelectorAll('button, select, textarea').forEach(function (el) {
      el.disabled = busy;
    });
  }

  function updateReviewsCount(fold, count) {
    var counter = fold && fold.querySelector('.user-reviews-count');
    if (counter) counter.textContent = String(count);
  }

  function saveReview(item) {
    var btn = item.querySelector('.user-review-btn--save');
    var url = btn && btn.getAttribute('data-save-url');
    if (!url) return;

    var ratingEl = item.querySelector('.user-review-item__rating');
    var commentEl = item.querySelector('.user-review-item__comment');
    setBusy(item, true);
    setStatus(item, '', '');

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        Accept: 'application/json',
      },
      body: JSON.stringify({
        rating: ratingEl ? Number(ratingEl.value) : 0,
        comment: commentEl ? commentEl.value : '',
      }),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok && data && data.ok, data: data || {} };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setStatus(item, (result.data && result.data.error) || 'Не удалось сохранить', 'is-error');
          return;
        }
        if (ratingEl && result.data.rating) ratingEl.value = String(result.data.rating);
        if (commentEl && typeof result.data.comment === 'string') {
          commentEl.value = result.data.comment;
        }
        setStatus(item, 'Сохранено', 'is-ok');
      })
      .catch(function () {
        setStatus(item, 'Не удалось сохранить', 'is-error');
      })
      .finally(function () {
        setBusy(item, false);
      });
  }

  function deleteReview(item) {
    var btn = item.querySelector('.user-review-btn--delete');
    var url = btn && btn.getAttribute('data-delete-url');
    if (!url) return;
    if (!window.confirm('Удалить этот комментарий и оценку?')) return;

    var fold = item.closest('.user-fold');
    setBusy(item, true);
    setStatus(item, '', '');

    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
        Accept: 'application/json',
      },
      body: '{}',
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok && data && data.ok, data: data || {} };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setStatus(item, (result.data && result.data.error) || 'Не удалось удалить', 'is-error');
          setBusy(item, false);
          return;
        }
        var list = item.parentElement;
        item.remove();
        updateReviewsCount(fold, result.data.reviews_count || 0);
        if (list && !list.querySelector('.user-review-item')) {
          var body = fold && fold.querySelector('.user-fold__body');
          if (body) {
            body.innerHTML = '<p class="user-fold__empty">Оценок и комментариев нет.</p>';
          }
        }
      })
      .catch(function () {
        setStatus(item, 'Не удалось удалить', 'is-error');
        setBusy(item, false);
      });
  }

  document.addEventListener('click', function (event) {
    var saveBtn = event.target.closest('.user-review-btn--save');
    if (saveBtn) {
      event.preventDefault();
      var saveItem = saveBtn.closest('.user-review-item');
      if (saveItem && !saveItem.classList.contains('is-saving')) saveReview(saveItem);
      return;
    }

    var deleteBtn = event.target.closest('.user-review-btn--delete');
    if (deleteBtn) {
      event.preventDefault();
      var deleteItem = deleteBtn.closest('.user-review-item');
      if (deleteItem && !deleteItem.classList.contains('is-saving')) deleteReview(deleteItem);
    }
  });
})();
