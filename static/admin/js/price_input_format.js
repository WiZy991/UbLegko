(function () {
  'use strict';

  var PRICE_SELECTOR =
    'input[name="price"], input[name="old_price"], ' +
    '.field-price input, .field-old_price input, ' +
    '#result_list .field-price input, #result_list .field-old_price input';

  function digitsOnly(value) {
    return String(value || '').replace(/[^\d]/g, '');
  }

  function formatGrouped(digits) {
    if (!digits) return '';
    return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function formatPriceInput(input) {
    if (!input || input.dataset.priceFormatting === '1') return;
    input.dataset.priceFormatting = '1';
    var start = input.selectionStart;
    var before = input.value || '';
    var digitsBeforeCaret = digitsOnly(before.slice(0, start));
    var digits = digitsOnly(before);
    var formatted = formatGrouped(digits);
    if (formatted === before) {
      input.dataset.priceFormatting = '0';
      return;
    }
    input.value = formatted;
    var caret = formatted.length;
    if (digitsBeforeCaret.length) {
      var seen = 0;
      caret = formatted.length;
      for (var i = 0; i < formatted.length; i++) {
        if (/\d/.test(formatted.charAt(i))) {
          seen += 1;
          if (seen >= digitsBeforeCaret.length) {
            caret = i + 1;
            break;
          }
        }
      }
    } else {
      caret = 0;
    }
    try {
      input.setSelectionRange(caret, caret);
    } catch (err) {
      /* ignore */
    }
    input.dataset.priceFormatting = '0';
  }

  function bindInput(input) {
    if (!input || input.dataset.priceGroupedBound === '1') return;
    input.dataset.priceGroupedBound = '1';
    input.setAttribute('inputmode', 'numeric');
    input.setAttribute('autocomplete', 'off');
    formatPriceInput(input);
    input.addEventListener('input', function () {
      formatPriceInput(input);
    });
    input.addEventListener('blur', function () {
      formatPriceInput(input);
    });
  }

  function scan(root) {
    (root || document).querySelectorAll(PRICE_SELECTOR).forEach(bindInput);
  }

  function init() {
    scan(document);
    if (window.MutationObserver) {
      var observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
          mutation.addedNodes.forEach(function (node) {
            if (node.nodeType !== 1) return;
            if (node.matches && node.matches(PRICE_SELECTOR)) bindInput(node);
            else if (node.querySelectorAll) scan(node);
          });
        });
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
