(function () {
  'use strict';

  function getCookie(name) {
    var matches = document.cookie.match(
      new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
    );
    return matches ? decodeURIComponent(matches[1]) : '';
  }

  function setExpanded(btn, expanded) {
    btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    var icon = btn.querySelector('i');
    if (icon) {
      icon.className = expanded ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
    }
    var row = btn.closest('tr.product-row');
    if (row) {
      row.classList.toggle('product-row--expanded', expanded);
    }
  }

  function setNotice(detailRow, text, state) {
    var messageBox = detailRow.querySelector('[data-quick-message]');
    if (!messageBox) return;
    messageBox.textContent = text || '';
    messageBox.className = 'product-row-detail__notice' + (state ? ' ' + state : '');
  }

  function replaceGallery(detailRow, photosHtml, thumbHtml) {
    var gallery = detailRow.querySelector('[data-photo-gallery]');
    if (gallery && photosHtml) {
      var wrap = document.createElement('div');
      wrap.innerHTML = photosHtml;
      var next = wrap.firstElementChild;
      if (next) {
        gallery.replaceWith(next);
      }
    }
    if (typeof thumbHtml === 'string') {
      var productId = detailRow.id && detailRow.id.replace('product-detail-', '');
      var productRow = productId
        ? document.querySelector('tr.product-row[data-product-id="' + productId + '"]')
        : null;
      if (productRow) {
        var thumbCell = productRow.querySelector('.field-thumb');
        if (thumbCell) {
          thumbCell.innerHTML = thumbHtml;
        }
      }
    }
  }

  function postPhotos(url, formData) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: formData,
    }).then(function (response) {
      return response.json().then(function (data) {
        return { ok: response.ok, data: data };
      });
    });
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest('.product-row-expand');
    if (!btn) {
      return;
    }

    event.preventDefault();
    var id = btn.getAttribute('data-product-id');
    if (!id) {
      return;
    }

    var detail = document.getElementById('product-detail-' + id);
    if (!detail) {
      return;
    }

    var willOpen = detail.hidden;
    detail.hidden = !willOpen;
    setExpanded(btn, willOpen);
  });

  document.addEventListener('click', function (event) {
    var saveBtn = event.target.closest('[data-quick-save]');
    if (!saveBtn) {
      return;
    }

    event.preventDefault();
    var detailRow = saveBtn.closest('.product-row-detail');
    if (!detailRow) {
      return;
    }

    var fields = detailRow.querySelectorAll('[data-quick-field]');
    var payload = {};

    fields.forEach(function (field) {
      var key = field.getAttribute('data-quick-field');
      if (!key) return;
      if (field.type === 'checkbox') {
        payload[key] = field.checked;
      } else {
        payload[key] = field.value;
      }
    });

    saveBtn.disabled = true;
    setNotice(detailRow, 'Сохраняю...', 'is-loading');

    fetch(saveBtn.getAttribute('data-quick-url'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error(result.data.error || 'Ошибка сохранения');
        }
        setNotice(detailRow, result.data.message || 'Сохранено', 'is-success');
      })
      .catch(function (error) {
        setNotice(detailRow, error.message || 'Ошибка сохранения', 'is-error');
      })
      .finally(function () {
        saveBtn.disabled = false;
      });
  });

  document.addEventListener('change', function (event) {
    var input = event.target.closest('[data-photo-upload]');
    if (!input || !input.files || !input.files.length) {
      return;
    }

    var detailRow = input.closest('.product-row-detail');
    var gallery = input.closest('[data-photo-gallery]');
    if (!detailRow || !gallery) {
      return;
    }

    var url = gallery.getAttribute('data-photos-url');
    var kind = input.getAttribute('data-photo-upload');
    var formData = new FormData();

    if (kind === 'main') {
      formData.append('action', 'upload_main');
      formData.append('image', input.files[0]);
    } else {
      formData.append('action', 'upload_gallery');
      Array.from(input.files).forEach(function (file) {
        formData.append('images', file);
      });
    }

    setNotice(detailRow, 'Загружаю фото...', 'is-loading');
    postPhotos(url, formData)
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error(result.data.error || 'Ошибка загрузки');
        }
        replaceGallery(detailRow, result.data.photos_html, result.data.thumb_html);
        setNotice(detailRow, result.data.message || 'Фото загружено', 'is-success');
      })
      .catch(function (error) {
        setNotice(detailRow, error.message || 'Ошибка загрузки', 'is-error');
      })
      .finally(function () {
        input.value = '';
      });
  });

  document.addEventListener('click', function (event) {
    var deleteBtn = event.target.closest('[data-photo-delete]');
    var setMainBtn = event.target.closest('[data-photo-set-main]');
    if (!deleteBtn && !setMainBtn) {
      return;
    }

    event.preventDefault();
    var detailRow = event.target.closest('.product-row-detail');
    var gallery = event.target.closest('[data-photo-gallery]');
    if (!detailRow || !gallery) {
      return;
    }

    var url = gallery.getAttribute('data-photos-url');
    var formData = new FormData();

    if (deleteBtn) {
      var kind = deleteBtn.getAttribute('data-photo-delete');
      if (kind === 'main') {
        if (!window.confirm('Удалить главное фото?')) return;
        formData.append('action', 'delete_main');
      } else {
        if (!window.confirm('Удалить это фото из галереи?')) return;
        formData.append('action', 'delete_gallery');
        formData.append('image_id', deleteBtn.getAttribute('data-photo-id') || '');
      }
      setNotice(detailRow, 'Удаляю фото...', 'is-loading');
    } else {
      formData.append('action', 'set_main');
      formData.append('image_id', setMainBtn.getAttribute('data-photo-set-main') || '');
      setNotice(detailRow, 'Меняю главное фото...', 'is-loading');
    }

    postPhotos(url, formData)
      .then(function (result) {
        if (!result.ok || !result.data.ok) {
          throw new Error(result.data.error || 'Ошибка');
        }
        replaceGallery(detailRow, result.data.photos_html, result.data.thumb_html);
        setNotice(detailRow, result.data.message || 'Готово', 'is-success');
      })
      .catch(function (error) {
        setNotice(detailRow, error.message || 'Ошибка', 'is-error');
      });
  });
})();
