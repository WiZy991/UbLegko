(function () {
  'use strict';

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

  function paintProcessedCheckbox(input) {
    if (!input) return;
    var row = input.closest('tr.inbox-row');
    if (!row) return;
    row.setAttribute('data-inbox-status', input.checked ? 'processed' : 'new');
    var badge = row.querySelector('.field-processed_badge .status-badge');
    if (badge) {
      if (input.checked) {
        badge.className = 'status-badge status-badge--done';
        badge.textContent = 'Обработано';
      } else {
        badge.className = 'status-badge status-badge--new';
        badge.textContent = 'Новая';
      }
    }
  }

  function initStatusControls() {
    document.querySelectorAll('#result_list .field-status select').forEach(function (select) {
      paintStatusSelect(select);
      select.addEventListener('change', function () {
        paintStatusSelect(select);
      });
    });
    document
      .querySelectorAll('#result_list .field-is_processed input[type="checkbox"]')
      .forEach(function (input) {
        paintProcessedCheckbox(input);
        input.addEventListener('change', function () {
          paintProcessedCheckbox(input);
        });
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStatusControls);
  } else {
    initStatusControls();
  }
})();
