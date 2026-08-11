(function () {
  'use strict';

  var baselines = {};

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

  function fieldValue(el) {
    if (!el) return '';
    if (el.type === 'checkbox') return el.checked ? '1' : '0';
    return String(el.value == null ? '' : el.value);
  }

  function readListField(row, fieldName) {
    var cell = row.querySelector('.field-' + fieldName);
    if (!cell) return null;
    var el = cell.querySelector('input, select, textarea');
    return el ? fieldValue(el) : null;
  }

  function collectPayload(productId) {
    var payload = {};
    var row = document.querySelector('tr.product-row[data-product-id="' + productId + '"]');
    var detail = document.getElementById('product-detail-' + productId);

    // Сначала поля раскрытой строки, затем list_editable — они перекрывают status и т.п.
    if (detail) {
      detail.querySelectorAll('[data-quick-field]').forEach(function (field) {
        var key = field.getAttribute('data-quick-field');
        if (!key) return;
        payload[key] = fieldValue(field);
      });
    }

    if (row) {
      ['name', 'category', 'price', 'old_price', 'status', 'recommendation_codes', 'is_visible'].forEach(function (key) {
        var value = readListField(row, key);
        if (value !== null) payload[key] = value;
      });
    }

    return payload;
  }

  function syncSharedFields(source, fieldName) {
    var productId = productIdFromEventTarget(source);
    if (!productId) return;
    var value = fieldValue(source);
    var row = document.querySelector('tr.product-row[data-product-id="' + productId + '"]');
    var detail = document.getElementById('product-detail-' + productId);
    var listEl = row && row.querySelector('.field-' + fieldName + ' input, .field-' + fieldName + ' select');
    var detailEl = detail && detail.querySelector('[data-quick-field="' + fieldName + '"]');
    if (listEl && listEl !== source) listEl.value = value;
    if (detailEl && detailEl !== source) detailEl.value = value;
  }

  function syncStatusFields(source) {
    syncSharedFields(source, 'status');
  }

  function snapshot(productId) {
    baselines[productId] = JSON.stringify(collectPayload(productId));
  }

  function setDirty(productId, dirty) {
    document.querySelectorAll('[data-product-save="' + productId + '"]').forEach(function (btn) {
      btn.classList.toggle('is-dirty', dirty);
      btn.disabled = !dirty;
    });
  }

  function refreshDirty(productId) {
    if (!productId) return;
    if (!baselines[productId]) {
      snapshot(productId);
    }
    var current = JSON.stringify(collectPayload(productId));
    setDirty(productId, current !== baselines[productId]);
  }

  function productIdFromEventTarget(target) {
    var row = target.closest('tr.product-row');
    if (row) return row.getAttribute('data-product-id');
    var detail = target.closest('tr.product-row-detail');
    if (detail && detail.id) return detail.id.replace('product-detail-', '');
    return '';
  }

  function initBaselines() {
    document.querySelectorAll('tr.product-row[data-product-id]').forEach(function (row) {
      var id = row.getAttribute('data-product-id');
      if (id) {
        snapshot(id);
        setDirty(id, false);
      }
    });
  }

  function saveProduct(productId, triggerBtn) {
    var url = (triggerBtn && triggerBtn.getAttribute('data-quick-url')) || '';
    if (!url) {
      var withUrl = document.querySelector(
        '[data-product-save="' + productId + '"][data-quick-url]'
      );
      url = withUrl ? withUrl.getAttribute('data-quick-url') : '';
    }
    if (!url) return;

    var payload = collectPayload(productId);
    var buttons = document.querySelectorAll('[data-product-save="' + productId + '"]');
    var detail = document.getElementById('product-detail-' + productId);

    buttons.forEach(function (btn) {
      btn.disabled = true;
    });
    if (detail) setNotice(detail, 'Сохраняю...', 'is-loading');

    fetch(url, {
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
        snapshot(productId);
        setDirty(productId, false);
        if (detail) {
          setNotice(detail, result.data.message || 'Сохранено — изменения уже на сайте', 'is-success');
        }
      })
      .catch(function (error) {
        refreshDirty(productId);
        if (detail) setNotice(detail, error.message || 'Ошибка сохранения', 'is-error');
        else window.alert(error.message || 'Ошибка сохранения');
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
    if (willOpen) {
      refreshDirty(id);
    }
  });

  document.addEventListener('click', function (event) {
    var saveBtn = event.target.closest('[data-product-save]');
    if (!saveBtn || saveBtn.disabled || !saveBtn.classList.contains('is-dirty')) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    var productId = saveBtn.getAttribute('data-product-save');
    if (!productId) return;
    saveProduct(productId, saveBtn);
  });

  document.addEventListener('change', function (event) {
    if (event.target.closest('[data-photo-upload]')) return;
    var target = event.target;
    if (target.matches && target.matches('[data-quick-field="status"]')) {
      syncSharedFields(target, 'status');
    } else if (target.closest && target.closest('.field-status select')) {
      syncSharedFields(target.closest('.field-status select') || target, 'status');
    }
    if (target.matches && target.matches('[data-quick-field="name"]')) {
      syncSharedFields(target, 'name');
    } else if (target.closest && target.closest('.field-name input')) {
      syncSharedFields(target.closest('.field-name input') || target, 'name');
    }
    if (target.matches && target.matches('[data-quick-field="recommendation_codes"]')) {
      syncSharedFields(target, 'recommendation_codes');
    } else if (target.closest && target.closest('.field-recommendation_codes input')) {
      syncSharedFields(
        target.closest('.field-recommendation_codes input') || target,
        'recommendation_codes'
      );
    }
    var id = productIdFromEventTarget(target);
    if (id) refreshDirty(id);
  });

  document.addEventListener('input', function (event) {
    var target = event.target;
    if (target.matches && target.matches('[data-quick-field="name"]')) {
      syncSharedFields(target, 'name');
    } else if (target.closest && target.closest('.field-name input')) {
      syncSharedFields(target.closest('.field-name input') || target, 'name');
    }
    if (target.matches && target.matches('[data-quick-field="recommendation_codes"]')) {
      syncSharedFields(target, 'recommendation_codes');
    } else if (target.closest && target.closest('.field-recommendation_codes input')) {
      syncSharedFields(
        target.closest('.field-recommendation_codes input') || target,
        'recommendation_codes'
      );
    }
    var id = productIdFromEventTarget(target);
    if (id) refreshDirty(id);
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBaselines);
  } else {
    initBaselines();
  }

  // На всякий случай убрать общую нижнюю «Сохранить» Jazzmin
  function removeBulkSave() {
    document.querySelectorAll('#changelist-form input[name="_save"]').forEach(function (el) {
      el.remove();
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', removeBulkSave);
  } else {
    removeBulkSave();
  }
})();
