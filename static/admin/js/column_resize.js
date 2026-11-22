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

  function columnSelectors(key) {
    if (key === 'action-checkbox') {
      return [
        '#result_list.has-user-widths th.action-checkbox-column',
        '#result_list.has-user-widths td.action-checkbox',
        '#result_list.has-user-widths .action-checkbox',
      ];
    }
    if (key.indexOf('column-') !== 0) return [];
    var field = 'field-' + key.slice('column-'.length);
    return [
      '#result_list.has-user-widths th.' + key,
      '#result_list.has-user-widths td.' + field,
      '#result_list.has-user-widths .' + field,
    ];
  }

  function writeWidthStyle(table, widths) {
    var sum = 0;
    Object.keys(widths).forEach(function (key) {
      sum += widths[key] || 0;
    });
    var css = 'body.change-list #changelist #result_list.has-user-widths{table-layout:fixed !important;width:' +
      sum + 'px !important;min-width:' + sum + 'px !important;max-width:none !important;}';
    Object.keys(widths).forEach(function (key) {
      var px = widths[key];
      columnSelectors(key).forEach(function (selector) {
        css += selector + '{width:' + px + 'px !important;min-width:' + px + 'px !important;max-width:' + px + 'px !important;}';
      });
    });
    var style = document.getElementById('ublegko-col-widths');
    if (!style) {
      style = document.createElement('style');
      style.id = 'ublegko-col-widths';
      document.head.appendChild(style);
    }
    style.textContent = css;
    table.classList.add('has-user-widths');
  }

  function syncTableWidth(table) {
    var headers = table.querySelectorAll('thead th');
    var cols = table.querySelectorAll('colgroup col');
    var widths = {};
    var sum = 0;
    Array.prototype.forEach.call(headers, function (th, index) {
      var key = columnKey(th);
      var width = cols[index] ? parseFloat(cols[index].style.width) || 0 : 0;
      if (!width) width = Math.round(th.getBoundingClientRect().width);
      if (key && width) widths[key] = Math.round(width);
      sum += width || 0;
    });
    if (sum > 0) {
      var px = Math.ceil(sum) + 'px';
      table.style.setProperty('width', px, 'important');
      table.style.setProperty('min-width', px, 'important');
      table.style.setProperty('max-width', 'none', 'important');
      writeWidthStyle(table, widths);
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

  function applySaved(table) {
    var saved = loadColumns();
    if (!Object.keys(saved).length) return;
    lockAllColumns(table, saved);
  }

  function init() {
    var table = document.getElementById('result_list');
    if (!table) return;
    var headers = table.querySelectorAll('thead th');
    if (!headers.length) return;
    applySaved(table);
    if (table.getAttribute('data-col-resize') === '1') return;
    table.setAttribute('data-col-resize', '1');

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
        var startW = th.getBoundingClientRect().width;
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
  window.addEventListener('load', init);
})();
