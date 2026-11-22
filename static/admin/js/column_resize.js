(function () {
  'use strict';

  function storageKey() {
    var app = '';
    var model = '';
    document.body.classList.forEach(function (name) {
      if (name.indexOf('app-') === 0) app = name;
      if (name.indexOf('model-') === 0) model = name;
    });
    return 'ublegko-cols:' + app + ':' + model;
  }

  function loadColumns() {
    try {
      var raw = window.localStorage.getItem(storageKey());
      if (raw) {
        var data = JSON.parse(raw);
        if (data && typeof data === 'object') return data;
      }
    } catch (error) {}
    if (document.body.classList.contains('model-product')) {
      try {
        var old = JSON.parse(window.localStorage.getItem('ublegko-product-admin-layout') || '{}');
        if (old && old.columns && typeof old.columns === 'object') return old.columns;
      } catch (error) {}
    }
    return {};
  }

  function saveColumns(columns) {
    try {
      window.localStorage.setItem(storageKey(), JSON.stringify(columns));
    } catch (error) {}
  }

  function columnKey(th) {
    if (!th) return '';
    if (th.classList.contains('action-checkbox-column')) return 'action-checkbox';
    var classes = (th.className || '').split(/\s+/);
    for (var i = 0; i < classes.length; i++) {
      if (classes[i].indexOf('column-') === 0) return classes[i];
    }
    return '';
  }

  function canResize(th) {
    var key = columnKey(th);
    return Boolean(key) && key !== 'action-checkbox' && key !== 'column-expand_toggle';
  }

  function minWidth(th) {
    var key = columnKey(th);
    if (key === 'action-checkbox' || key === 'column-expand_toggle') return 32;
    return 56;
  }

  function ensureCols(table) {
    var group = table.querySelector('colgroup');
    var count = table.querySelectorAll('thead th').length;
    if (!group) {
      group = document.createElement('colgroup');
      table.insertBefore(group, table.firstChild);
    }
    while (group.children.length < count) group.appendChild(document.createElement('col'));
    return group;
  }

  function cellsInColumn(table, index) {
    var list = [];
    Array.prototype.forEach.call(table.rows, function (row) {
      var cell = row.cells[index];
      if (cell && cell.colSpan === 1) list.push(cell);
    });
    return list;
  }

  function syncTableWidth(table) {
    var sum = 0;
    Array.prototype.forEach.call(table.querySelectorAll('colgroup col'), function (col) {
      sum += parseFloat(col.style.width) || 0;
    });
    if (sum > 0) {
      var px = Math.ceil(sum) + 'px';
      table.style.setProperty('width', px, 'important');
      table.style.setProperty('min-width', px, 'important');
      table.style.setProperty('max-width', 'none', 'important');
    }
  }

  function paintColumnWidth(table, th, px) {
    var width = Math.max(minWidth(th), Math.round(px));
    var cols = ensureCols(table);
    var col = cols.children[th.cellIndex];
    if (col) col.style.width = width + 'px';
    var value = width + 'px';
    cellsInColumn(table, th.cellIndex).forEach(function (cell) {
      cell.style.setProperty('width', value, 'important');
      cell.style.setProperty('min-width', value, 'important');
      cell.style.setProperty('max-width', value, 'important');
    });
    table.classList.add('has-user-widths');
    syncTableWidth(table);
  }

  function lockAllColumns(table, overrides) {
    var headers = Array.prototype.slice.call(table.querySelectorAll('thead th'));
    var measured = headers.map(function (th) {
      return Math.round(th.getBoundingClientRect().width);
    });
    headers.forEach(function (th, index) {
      var key = columnKey(th);
      var width = measured[index];
      if (key && overrides && overrides[key]) width = overrides[key];
      paintColumnWidth(table, th, width || minWidth(th));
    });
    table.setAttribute('data-cols-locked', '1');
  }

  function persistColumns(table) {
    var headers = table.querySelectorAll('thead th');
    var cols = table.querySelectorAll('colgroup col');
    var stored = {};
    Array.prototype.forEach.call(headers, function (th, index) {
      var key = columnKey(th);
      if (!key) return;
      var width = cols[index] ? parseFloat(cols[index].style.width) : 0;
      if (!width) width = Math.round(th.getBoundingClientRect().width);
      if (width) stored[key] = Math.round(width);
    });
    saveColumns(stored);
  }

  function init() {
    var table = document.getElementById('result_list');
    if (!table || table.getAttribute('data-col-resize') === '1') return;
    var headers = table.querySelectorAll('thead th');
    if (!headers.length) return;
    table.setAttribute('data-col-resize', '1');

    var saved = loadColumns();
    if (Object.keys(saved).length) lockAllColumns(table, saved);

    Array.prototype.forEach.call(headers, function (th) {
      if (!canResize(th)) return;
      var handle = document.createElement('span');
      handle.className = 'product-col-resize';
      handle.title = 'Потяните, чтобы изменить ширину';
      th.appendChild(handle);

      handle.addEventListener('pointerdown', function (event) {
        if (event.button !== 0) return;
        event.preventDefault();
        event.stopPropagation();
        if (table.getAttribute('data-cols-locked') !== '1') lockAllColumns(table, loadColumns());
        var startX = event.clientX;
        var col = table.querySelectorAll('colgroup col')[th.cellIndex];
        var startW = col && parseFloat(col.style.width) ? parseFloat(col.style.width) : th.getBoundingClientRect().width;
        var latest = startW;
        document.body.classList.add('product-col-dragging');

        function move(ev) {
          latest = Math.max(minWidth(th), startW + (ev.clientX - startX));
          paintColumnWidth(table, th, latest);
          persistColumns(table);
        }

        function up() {
          window.removeEventListener('pointermove', move);
          window.removeEventListener('pointerup', up);
          window.removeEventListener('pointercancel', up);
          document.body.classList.remove('product-col-dragging');
          paintColumnWidth(table, th, latest);
          persistColumns(table);
        }

        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', up);
        window.addEventListener('pointercancel', up);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
