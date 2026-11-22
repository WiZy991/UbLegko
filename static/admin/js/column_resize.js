(function () {
  'use strict';

  function columnKey(th) {
    if (window.ublegkoColumnKey) return window.ublegkoColumnKey(th);
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

  function init() {
    var table = document.getElementById('result_list');
    if (!table) return;
    if (window.ublegkoApplySavedColumns) window.ublegkoApplySavedColumns(table);
    var headers = table.querySelectorAll('thead th');
    if (!headers.length || table.getAttribute('data-col-resize') === '1') return;
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
        var startX = event.clientX;
        var startW = th.getBoundingClientRect().width;
        var latest = startW;
        document.body.classList.add('product-col-dragging');

        function move(ev) {
          latest = Math.max(minWidth(th), startW + (ev.clientX - startX));
          if (window.ublegkoSetColumnWidth) window.ublegkoSetColumnWidth(table, th, latest);
        }

        function up() {
          window.removeEventListener('pointermove', move);
          window.removeEventListener('pointerup', up);
          window.removeEventListener('pointercancel', up);
          document.body.classList.remove('product-col-dragging');
          if (window.ublegkoSetColumnWidth) window.ublegkoSetColumnWidth(table, th, latest);
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
