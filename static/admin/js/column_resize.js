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

  var widths = {};

  function columnSelectors(key) {
    if (key === 'action-checkbox') {
      return ['th.action-checkbox-column', 'td.action-checkbox'];
    }
    if (key.indexOf('column-') !== 0) return [];
    return ['th.' + key, 'td.field-' + key.slice('column-'.length)];
  }

  function writeWidthStyle() {
    var sum = 0;
    var css = '';
    Object.keys(widths).forEach(function (key) {
      var px = widths[key];
      if (!px) return;
      sum += px;
      columnSelectors(key).forEach(function (selector) {
        css += 'html body.change-list #changelist #result_list ' + selector +
          '{width:' + px + 'px !important;min-width:' + px + 'px !important;max-width:' + px + 'px !important;}';
      });
    });
    if (!sum) return;
    css = 'html body.change-list #changelist #result_list{table-layout:fixed !important;width:max-content !important;min-width:max-content !important;max-width:none !important;}' + css;
    var style = document.getElementById('ublegko-col-widths');
    if (!style) {
      style = document.createElement('style');
      style.id = 'ublegko-col-widths';
      document.head.appendChild(style);
    }
    if (style.textContent !== css) style.textContent = css;
  }

  function rememberWidths() {
    var saved = loadColumns();
    Object.keys(saved).forEach(function (key) {
      var px = Math.round(Number(saved[key]));
      if (px > 0) widths[key] = px;
    });
  }

  function paintColumnWidth(table, th, px) {
    var key = columnKey(th);
    var width = Math.max(minWidth(th), Math.round(px));
    if (key) widths[key] = width;
    var cols = ensureCols(table);
    var col = cols.children[th.cellIndex];
    if (col) col.style.width = width + 'px';
    writeWidthStyle();
  }

  function seedMissing(table) {
    Array.prototype.forEach.call(table.querySelectorAll('thead th'), function (th) {
      var key = columnKey(th);
      if (!key || widths[key]) return;
      var width = Math.round(th.getBoundingClientRect().width);
      if (width) widths[key] = Math.max(minWidth(th), width);
    });
  }

  function persistColumns() {
    saveColumns(widths);
  }

  function init() {
    var table = document.getElementById('result_list');
    if (!table) return;
    var headers = table.querySelectorAll('thead th');
    if (!headers.length) return;
    rememberWidths();
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
        seedMissing(table);
        var startX = event.clientX;
        var startW = th.getBoundingClientRect().width;
        var latest = startW;
        document.body.classList.add('product-col-dragging');

        function move(ev) {
          latest = Math.max(minWidth(th), startW + (ev.clientX - startX));
          paintColumnWidth(table, th, latest);
          persistColumns();
        }

        function up() {
          window.removeEventListener('pointermove', move);
          window.removeEventListener('pointerup', up);
          window.removeEventListener('pointercancel', up);
          document.body.classList.remove('product-col-dragging');
          paintColumnWidth(table, th, latest);
          persistColumns();
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
