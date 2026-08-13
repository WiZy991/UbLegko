(function () {
  'use strict';

  if (typeof gsap === 'undefined') return;

  var EASE = 'power2.easeOut';
  var canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  var pills = [];
  var resizeTimer = null;

  function ensureHoverLabel(pill) {
    var stack = pill.querySelector('.ub-pill__stack');
    var label = pill.querySelector('.ub-pill__label');
    if (!stack || !label) return null;

    var hover = stack.querySelector('.ub-pill__label-hover');
    if (!hover) {
      hover = label.cloneNode(true);
      hover.classList.remove('ub-pill__label');
      hover.classList.add('ub-pill__label-hover');
      hover.setAttribute('aria-hidden', 'true');
      // Remove live-updating ids/attrs that must stay unique
      hover.querySelectorAll('[data-city-label]').forEach(function (el) {
        el.removeAttribute('data-city-label');
      });
      hover.querySelectorAll('[data-cart-total]').forEach(function (el) {
        el.removeAttribute('data-cart-total');
      });
      stack.appendChild(hover);
    }
    return hover;
  }

  function syncHoverLabel(pill) {
    var label = pill.querySelector('.ub-pill__label');
    var hover = pill.querySelector('.ub-pill__label-hover');
    if (!label || !hover) return;
    hover.innerHTML = label.innerHTML;
    hover.querySelectorAll('[data-city-label]').forEach(function (el) {
      el.removeAttribute('data-city-label');
    });
    hover.querySelectorAll('[data-cart-total]').forEach(function (el) {
      el.removeAttribute('data-cart-total');
    });
  }

  function layoutPill(state) {
    var pill = state.el;
    var circle = state.circle;
    if (!circle || !pill) return;

    var label = state.label;
    var hover = state.hover || pill.querySelector('.ub-pill__label-hover');
    state.hover = hover;

    // Жирный hover шире/выше обычного текста — овал должен вмещать оба
    // Корзина — строго круг 36×36, размеры не трогаем
    var isCart = pill.classList.contains('ub-pill--cart-icon');
    if (label && hover && !isCart) {
      gsap.set(label, { clearProps: 'transform' });
      gsap.set(hover, { clearProps: 'transform', opacity: 0, y: 0 });

      var isSlogan = pill.classList.contains('ub-pill--slogan');
      hover.style.maxWidth = 'none';
      hover.style.minHeight = '';

      if (isSlogan) {
        // Ширина как у основного текста; высота — по самому высокому варианту
        var availW = Math.ceil(label.getBoundingClientRect().width);
        hover.style.width = availW + 'px';
        hover.style.minWidth = availW + 'px';
      } else {
        // Одна строка: не сжимать жирный текст (иначе перенос и обрезка)
        hover.style.width = 'auto';
        hover.style.minWidth = 'max-content';
      }

      var cs = window.getComputedStyle(pill);
      var padX =
        (parseFloat(cs.paddingLeft) || 0) + (parseFloat(cs.paddingRight) || 0);
      var padY =
        (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
      var borX =
        (parseFloat(cs.borderLeftWidth) || 0) +
        (parseFloat(cs.borderRightWidth) || 0);
      var borY =
        (parseFloat(cs.borderTopWidth) || 0) +
        (parseFloat(cs.borderBottomWidth) || 0);

      var needW = Math.max(label.scrollWidth, hover.scrollWidth) + padX + borX;
      var needH =
        Math.max(label.scrollHeight, hover.scrollHeight) + padY + borY;

      pill.style.minHeight = Math.ceil(needH) + 'px';
      if (isSlogan) {
        // Ширину слогана не раздуваем — только высота, чтобы телефон не обрезался
        pill.style.height = 'auto';
        pill.style.maxHeight = 'none';
      } else {
        pill.style.minWidth = Math.ceil(needW) + 'px';
        pill.style.height = 'auto';
        pill.style.maxHeight = 'none';
      }
    }

    var rect = pill.getBoundingClientRect();
    var w = rect.width;
    var h = rect.height;
    if (w < 2 || h < 2) return;

    var R = (w * w) / 4 / h + h / 2;
    var D = Math.ceil(2 * R) + 2;
    var delta = Math.ceil(R - Math.sqrt(Math.max(0, R * R - (w * w) / 4))) + 1;
    var originY = D - delta;

    circle.style.width = D + 'px';
    circle.style.height = D + 'px';
    circle.style.bottom = -delta + 'px';

    gsap.set(circle, {
      xPercent: -50,
      scale: 0,
      transformOrigin: '50% ' + originY + 'px',
    });

    if (label) gsap.set(label, { y: 0 });
    if (hover) gsap.set(hover, { y: Math.ceil(h + 12), opacity: 0 });

    if (state.tl) state.tl.kill();
    var tl = gsap.timeline({ paused: true });
    tl.to(
      circle,
      { scale: 1.2, xPercent: -50, duration: 2, ease: EASE, overwrite: 'auto' },
      0
    );
    if (label) {
      tl.to(label, { y: -(h + 8), duration: 2, ease: EASE, overwrite: 'auto' }, 0);
    }
    if (hover) {
      gsap.set(hover, { y: Math.ceil(h + 100), opacity: 0 });
      tl.to(hover, { y: 0, opacity: 1, duration: 2, ease: EASE, overwrite: 'auto' }, 0);
    }
    state.tl = tl;
  }

  function bindPill(pill, hoverRoot) {
    var circle = pill.querySelector('.ub-pill__circle');
    var label = pill.querySelector('.ub-pill__label');
    if (!circle || !label) return;

    var hover = ensureHoverLabel(pill);
    var state = {
      el: pill,
      circle: circle,
      label: label,
      hover: hover,
      tl: null,
      tween: null,
    };

    layoutPill(state);

    var root = hoverRoot || pill;

    if (canHover) {
      root.addEventListener('mouseenter', function () {
        syncHoverLabel(pill);
        state.hover = pill.querySelector('.ub-pill__label-hover');
        layoutPill(state);
        if (!state.tl) return;
        if (state.tween) state.tween.kill();
        state.tween = state.tl.tweenTo(state.tl.duration(), {
          duration: 0.3,
          ease: EASE,
          overwrite: 'auto',
        });
      });
      root.addEventListener('mouseleave', function () {
        if (!state.tl) return;
        if (state.tween) state.tween.kill();
        state.tween = state.tl.tweenTo(0, {
          duration: 0.2,
          ease: EASE,
          overwrite: 'auto',
        });
      });
    }

    var observer = new MutationObserver(function () {
      syncHoverLabel(pill);
      layoutPill(state);
    });
    observer.observe(label, {
      characterData: true,
      childList: true,
      subtree: true,
    });

    pills.push(state);
  }

  function layoutAll() {
    pills.forEach(layoutPill);
  }

  function init() {
    var isMobile = window.matchMedia('(max-width: 900px)').matches;
    if (isMobile || !canHover) {
      // На узких экранах / touch — без GSAP-клонов, чтобы не ломать ряд кнопок
      return;
    }

    document
      .querySelectorAll('.topbar .ub-pill:not(.ub-pill--cart-icon), .account-bar .ub-pill')
      .forEach(function (pill) {
        bindPill(pill);
      });

    document.querySelectorAll('.topbar__cart[data-ub-pill-host]').forEach(function (host) {
      var iconPill = host.querySelector('.ub-pill--cart-icon');
      if (iconPill) bindPill(iconPill, host);
    });

    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(layoutAll, 80);
    });

    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(layoutAll).catch(function () {});
    }

    document.addEventListener('cart:updated', layoutAll);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
