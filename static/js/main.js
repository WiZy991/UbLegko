(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  const toast = document.getElementById("toast");
  function showToast(message) {
    if (!toast || !message) return;
    toast.textContent = message;
    toast.classList.add("is-visible");
    setTimeout(() => toast.classList.remove("is-visible"), 2200);
  }

  let suppressMenuToggleClick = false;

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-menu-toggle], #menu-toggle");
    if (!toggle) return;
    if (suppressMenuToggleClick) {
      event.preventDefault();
      event.stopPropagation();
      suppressMenuToggleClick = false;
      return;
    }
    const sidebar = document.querySelector("[data-sidebar], #sidebar");
    if (!sidebar) return;
    setCatalogNavOpen(!sidebar.classList.contains("is-open"));
  });

  let skipStickySync = false;

  function syncStickyHeaderHeight() {
    if (skipStickySync) return;
    const sticky = document.querySelector(".header-sticky");
    const catalogNav = document.querySelector("[data-catalog-nav-shell]");
    const toolbar = document.querySelector("[data-catalog-toolbar]");
    const headerH = sticky ? Math.round(sticky.getBoundingClientRect().height) : 0;
    const isMobile = window.matchMedia("(max-width: 900px)").matches;
    const navH = isMobile && catalogNav ? Math.round(catalogNav.getBoundingClientRect().height) : 0;
    // На мобиле фильтры внутри .catalog-nav — не дублируем их высоту
    const toolbarH =
      !isMobile && toolbar ? Math.round(toolbar.getBoundingClientRect().height) : 0;
    const overlap = navH || toolbarH ? 2 : 0;
    document.documentElement.style.setProperty("--header-sticky-height", `${headerH}px`);
    document.documentElement.style.setProperty("--catalog-nav-height", `${navH}px`);
    document.documentElement.style.setProperty("--catalog-toolbar-height", `${toolbarH}px`);
    document.documentElement.style.setProperty(
      "--sticky-offset",
      `${Math.max(headerH + navH + toolbarH - overlap, headerH)}px`
    );
  }
  syncStickyHeaderHeight();
  window.addEventListener("resize", syncStickyHeaderHeight);
  window.addEventListener("load", syncStickyHeaderHeight);

  if (typeof ResizeObserver !== "undefined") {
    const stickyObserver = new ResizeObserver(syncStickyHeaderHeight);
    const sticky = document.querySelector(".header-sticky");
    if (sticky) stickyObserver.observe(sticky);
    const catalogNav = document.querySelector("[data-catalog-nav-shell]");
    if (catalogNav) stickyObserver.observe(catalogNav);
    const toolbar = document.querySelector("[data-catalog-toolbar]");
    if (toolbar) stickyObserver.observe(toolbar);
    // Re-bind toolbar after AJAX catalog swaps
    const observeToolbar = () => {
      const next = document.querySelector("[data-catalog-toolbar]");
      if (next) stickyObserver.observe(next);
      const nextNav = document.querySelector("[data-catalog-nav-shell]");
      if (nextNav) stickyObserver.observe(nextNav);
    };
    window.__ublegkoObserveToolbar = observeToolbar;
  }

  // iOS-like: одна анимация height (WAAPI), без grid 0fr/1fr
  const IOS_SHEET_EASING = "cubic-bezier(0.32, 0.72, 0, 1)";
  const IOS_SHEET_MS = 480;
  // Глушим только программный sync после AJAX — скролл пользователя анимируется
  let sheetSyncQuietUntil = 0;
  function quietSheetSync(ms = 900) {
    sheetSyncQuietUntil = Math.max(sheetSyncQuietUntil, Date.now() + ms);
  }
  function isSheetSyncQuiet() {
    return Date.now() < sheetSyncQuietUntil;
  }

  function isCatalogNavStuck() {
    const shell = document.querySelector("[data-catalog-nav-shell]");
    const anchor = document.querySelector("[data-catalog-nav-anchor]");
    const header = document.querySelector(".header-sticky");
    const stickyLine = header ? header.getBoundingClientRect().bottom - 2 : 0;
    if (anchor) return anchor.getBoundingClientRect().bottom <= stickyLine + 1;
    if (shell) return shell.getBoundingClientRect().top <= stickyLine + 1;
    return (window.scrollY || 0) > 24;
  }

  function syncCatalogSheetToScroll({ animate = false } = {}) {
    const panel =
      document.querySelector("[data-catalog-sheet]") ||
      document.querySelector("[data-sidebar], #sidebar");
    if (!panel || !window.matchMedia("(max-width: 900px)").matches) {
      if (panel) setCatalogNavOpen(true, { animate: false });
      return;
    }
    setCatalogNavOpen(!isCatalogNavStuck(), { animate: Boolean(animate) });
  }

  function settleSheetAfterScroll(ms = 900) {
    quietSheetSync(ms);
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      quietSheetSync(120);
      // После программного скролла — без анимации; дальше пользовательский скролл снова с анимацией
      syncCatalogSheetToScroll({ animate: false });
    };
    if ("onscrollend" in window) {
      window.addEventListener("scrollend", done, { once: true });
    }
    setTimeout(done, ms);
  }

  function measureSheetHeight(panel) {
    const shell = document.querySelector("[data-catalog-nav-shell]");
    const prevHeight = panel.style.height;
    const prevTransition = panel.style.transition;
    const wasOpen = panel.classList.contains("is-open");
    const wasPulling = shell && shell.classList.contains("is-pulling");
    const wasAnimating = shell && shell.classList.contains("is-sheet-animating");

    if (shell) {
      shell.classList.add("is-pulling");
      shell.classList.remove("is-sheet-animating");
    }
    panel.classList.add("is-open");
    panel.style.transition = "none";
    panel.style.padding = "0";
    panel.style.height = "auto";
    // Полная высота панели (как после анимации с height:auto) — без расхождения с фильтрами
    const h = Math.min(
      Math.max(Math.round(panel.getBoundingClientRect().height), 72),
      Math.round(window.innerHeight * 0.7),
      480
    );
    panel.style.height = prevHeight;
    panel.style.transition = prevTransition;
    panel.style.padding = "";
    if (!wasOpen) panel.classList.remove("is-open");
    if (shell) {
      if (!wasPulling) shell.classList.remove("is-pulling");
      if (wasAnimating) shell.classList.add("is-sheet-animating");
    }
    panel._ublegkoFullH = h;
    return h;
  }

  function clearSheetInline(panel) {
    if (!panel) return;
    panel.style.height = "";
    panel.style.transition = "";
    panel.style.overflow = "";
    panel.style.background = "";
    panel.style.willChange = "";
    panel.style.padding = "";
  }

  function cancelSheetAnimation(panel) {
    if (!panel) return;
    if (panel._ublegkoSheetAnim) {
      const anim = panel._ublegkoSheetAnim;
      panel._ublegkoSheetAnim = null;
      anim.onfinish = null;
      anim.oncancel = null;
      try {
        anim.cancel();
      } catch (_) {
        /* ignore */
      }
    }
    if (panel._ublegkoSheetTimer) {
      clearTimeout(panel._ublegkoSheetTimer);
      panel._ublegkoSheetTimer = 0;
    }
    if (panel._ublegkoSheetFinish) {
      panel.removeEventListener("transitionend", panel._ublegkoSheetFinish);
      panel._ublegkoSheetFinish = null;
    }
    panel._ublegkoBusy = false;
  }

  function currentSheetHeight(panel) {
    if (panel.style.height && panel.style.height.endsWith("px")) {
      return Math.max(0, parseFloat(panel.style.height) || 0);
    }
    if (!panel.classList.contains("is-open")) return 0;
    return Math.round(panel.getBoundingClientRect().height);
  }

  function setCatalogNavOpen(open, options = {}) {
    const animate = options.animate !== false;
    const shell = document.querySelector("[data-catalog-nav-shell]");
    const toggle = document.querySelector("[data-menu-toggle], #menu-toggle");
    const panel =
      document.querySelector("[data-catalog-sheet]") ||
      document.querySelector("[data-sidebar], #sidebar");
    if (!toggle || !panel) return;

    const wasOpen = panel.classList.contains("is-open");
    const from = currentSheetHeight(panel);
    const isMobile = window.matchMedia("(max-width: 900px)").matches;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const useAnimate = animate && isMobile && !reduceMotion;

    if (
      wasOpen === open &&
      !panel._ublegkoBusy &&
      !(shell && shell.classList.contains("is-pulling"))
    ) {
      const settledTarget = open ? panel._ublegkoFullH || from : 0;
      // Не выходим рано после жеста — иначе дожим с промежуточной высоты пропускается
      if (!useAnimate || Math.abs(from - settledTarget) < 2) {
        syncStickyHeaderHeight();
        return;
      }
    }

    cancelSheetAnimation(panel);
    clearSheetInline(panel);
    if (shell) shell.classList.remove("is-pulling");

    if (!useAnimate) {
      if (shell) shell.classList.add("is-instant");
      panel.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      void panel.offsetHeight;
      if (shell) shell.classList.remove("is-instant", "is-sheet-animating");
      skipStickySync = false;
      syncStickyHeaderHeight();
      return;
    }

    const fullH = measureSheetHeight(panel);
    const to = open ? fullH : 0;

    skipStickySync = true;
    panel._ublegkoBusy = true;
    if (shell) shell.classList.add("is-sheet-animating");
    panel.classList.add("is-open");
    panel.style.height = `${from}px`;
    panel.style.padding = "0";
    panel.style.overflow = "hidden";
    panel.style.background = "var(--bg)";
    panel.style.willChange = "height";
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    void panel.offsetHeight;

    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      if (panel._ublegkoSheetTimer) {
        clearTimeout(panel._ublegkoSheetTimer);
        panel._ublegkoSheetTimer = 0;
      }
      // Класс до cancel(anim), иначе на закрытии мигает height:auto
      panel.classList.toggle("is-open", open);
      if (open) {
        // Оставляем height в px — переход на auto дёргал фильтры
        panel.style.height = `${to}px`;
      } else {
        panel.style.height = "0px";
      }
      if (panel._ublegkoSheetAnim) {
        const anim = panel._ublegkoSheetAnim;
        panel._ublegkoSheetAnim = null;
        anim.onfinish = null;
        anim.oncancel = null;
        try {
          anim.cancel();
        } catch (_) {
          /* ignore */
        }
      }
      if (shell) shell.classList.remove("is-sheet-animating");
      panel.style.transition = "";
      panel.style.background = "";
      panel.style.willChange = "";
      panel.style.padding = "";
      panel.style.overflow = "hidden";
      if (!open) {
        panel.style.height = "";
        panel.style.overflow = "";
      }
      panel._ublegkoBusy = false;
      skipStickySync = false;
      syncStickyHeaderHeight();
    };

    if (Math.abs(from - to) < 1) {
      finish();
      return;
    }

    if (typeof panel.animate === "function") {
      const anim = panel.animate(
        [{ height: `${from}px` }, { height: `${to}px` }],
        { duration: IOS_SHEET_MS, easing: IOS_SHEET_EASING, fill: "forwards" }
      );
      panel._ublegkoSheetAnim = anim;
      anim.onfinish = finish;
      anim.oncancel = finish;
    } else {
      panel.style.transition = `height ${IOS_SHEET_MS}ms ${IOS_SHEET_EASING}`;
      requestAnimationFrame(() => {
        panel.style.height = `${to}px`;
      });
      const onEnd = (evt) => {
        if (evt && evt.propertyName && evt.propertyName !== "height") return;
        panel.removeEventListener("transitionend", onEnd);
        panel._ublegkoSheetFinish = null;
        finish();
      };
      panel._ublegkoSheetFinish = onEnd;
      panel.addEventListener("transitionend", onEnd);
    }
    panel._ublegkoSheetTimer = setTimeout(finish, IOS_SHEET_MS + 100);
  }

  let catalogNavCollapseCleanup = null;

  function initMobileCatalogNavCollapse() {
    if (typeof catalogNavCollapseCleanup === "function") {
      catalogNavCollapseCleanup();
      catalogNavCollapseCleanup = null;
    }

    const shell = document.querySelector("[data-catalog-nav-shell]");
    const anchor = document.querySelector("[data-catalog-nav-anchor]");
    const toggle = document.querySelector("[data-menu-toggle], #menu-toggle");
    const panel =
      document.querySelector("[data-catalog-sheet]") ||
      document.querySelector("[data-sidebar], #sidebar");
    if (!shell || !toggle || !panel) return;

    let lastY = window.scrollY || 0;
    let ignoreScrollUntil = 0;
    let userHoldOpen = false;
    let drag = null;
    let fullH = 160;
    let rafId = 0;
    let pendingH = null;
    let freezeY = 0;

    const bumpIgnore = (ms = 450) => {
      ignoreScrollUntil = Date.now() + ms;
    };

    const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

    const onFreezeScroll = (event) => {
      if (!drag) return;
      if (event && event.cancelable) event.preventDefault();
      if (window.scrollY !== freezeY) {
        window.scrollTo(0, freezeY);
      }
    };

    const startScrollFreeze = () => {
      freezeY = window.scrollY || 0;
      window.addEventListener("scroll", onFreezeScroll, { passive: false, capture: true });
      window.addEventListener("wheel", onFreezeScroll, { passive: false, capture: true });
    };

    const stopScrollFreeze = () => {
      window.removeEventListener("scroll", onFreezeScroll, { capture: true });
      window.removeEventListener("wheel", onFreezeScroll, { capture: true });
    };

    const isStuckUnderHeader = () => {
      const header = document.querySelector(".header-sticky");
      const stickyLine = header ? header.getBoundingClientRect().bottom - 2 : 0;
      if (anchor) {
        return anchor.getBoundingClientRect().bottom <= stickyLine + 1;
      }
      if (shell.getBoundingClientRect().top <= stickyLine + 1) return true;
      return (window.scrollY || 0) > 24;
    };

    const applyStickyState = (opts = {}) => {
      const animate = opts.animate === true;
      if (!isMobile()) {
        userHoldOpen = false;
        setCatalogNavOpen(true, { animate: false });
        return;
      }
      if (drag || panel._ublegkoBusy || Date.now() < ignoreScrollUntil) return;
      // Во время quiet разрешаем только мгновенный sync (после AJAX), не анимированный
      if (isSheetSyncQuiet() && animate) return;
      const stuck = isStuckUnderHeader();
      if (!stuck) {
        userHoldOpen = false;
        if (!panel.classList.contains("is-open")) {
          if (animate) bumpIgnore(IOS_SHEET_MS);
          setCatalogNavOpen(true, { animate });
        }
        return;
      }
      if (!userHoldOpen && panel.classList.contains("is-open")) {
        if (animate) bumpIgnore(IOS_SHEET_MS);
        setCatalogNavOpen(false, { animate });
      }
    };

    const paintH = (h) => {
      pendingH = h;
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        rafId = 0;
        if (pendingH == null || !drag) return;
        panel.style.height = `${pendingH}px`;
        pendingH = null;
      });
    };

    const clearDragStyles = () => {
      shell.classList.remove("is-pulling");
      stopScrollFreeze();
    };

    const onToggleClick = () => {
      if (drag) return;
      bumpIgnore(500);
      requestAnimationFrame(() => {
        userHoldOpen = panel.classList.contains("is-open") && isStuckUnderHeader();
      });
    };

    const onDocTouchMove = (event) => {
      // Блокируем скролл страницы только пока тянем зацеп
      if (!drag || !drag.locked) return;
      if (event.cancelable) event.preventDefault();
      if (window.scrollY !== freezeY) window.scrollTo(0, freezeY);
    };

    const onTouchStart = (event) => {
      if (!isMobile() || event.touches.length !== 1) return;
      if (drag) return;
      if (event.cancelable) event.preventDefault();

      const t = event.touches[0];
      const fromH = currentSheetHeight(panel);
      const startOpen = panel.classList.contains("is-open") || fromH > 1;
      cancelSheetAnimation(panel);
      shell.classList.remove("is-sheet-animating");

      startScrollFreeze();
      skipStickySync = true;
      fullH = measureSheetHeight(panel);
      shell.classList.add("is-pulling");
      panel.style.transition = "none";
      panel.style.overflow = "hidden";
      panel.style.background = "var(--bg)";
      panel.style.padding = "0";
      panel.style.willChange = "height";
      if (startOpen) panel.classList.add("is-open");

      drag = {
        id: t.identifier,
        x: t.clientX,
        y: t.clientY,
        startOpen,
        locked: false,
        h: startOpen ? fromH || fullH : fromH,
        lastY: t.clientY,
        lastT: performance.now(),
        velocity: 0,
      };
      bumpIgnore(2000);
      paintH(drag.h);
    };

    const onTouchMove = (event) => {
      if (!drag || event.touches.length !== 1) return;
      const t = event.touches[0];
      if (t.identifier !== drag.id) return;

      if (event.cancelable) event.preventDefault();

      const now = performance.now();
      const dy = t.clientY - drag.y;
      const dx = t.clientX - drag.x;
      const dt = Math.max(1, now - drag.lastT);
      drag.velocity = (t.clientY - drag.lastY) / dt;
      drag.lastY = t.clientY;
      drag.lastT = now;

      if (!drag.locked && Math.abs(dy) > 4 && Math.abs(dy) >= Math.abs(dx) * 0.8) {
        const opening = !drag.startOpen && dy > 0;
        const closing = drag.startOpen && dy < 0;
        if (opening || closing) drag.locked = true;
      }
      if (!drag.locked) return;

      let h;
      if (drag.startOpen) {
        h = Math.max(0, Math.min(fullH, fullH + dy));
      } else {
        h = Math.max(0, Math.min(fullH, dy));
      }
      drag.h = h;
      bumpIgnore(2000);
      paintH(h);
    };

    const onTouchEnd = (event) => {
      if (!drag) return;
      const t = event.changedTouches[0];
      if (!t || t.identifier !== drag.id) {
        drag = null;
        clearDragStyles();
        skipStickySync = false;
        syncStickyHeaderHeight();
        return;
      }

      const dy = t.clientY - drag.y;
      const locked = drag.locked;
      const h = drag.h;
      const startOpen = drag.startOpen;
      const velocity = drag.velocity;
      drag = null;

      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
      pendingH = null;

      if (!locked) {
        clearDragStyles();
        suppressMenuToggleClick = true;
        bumpIgnore(IOS_SHEET_MS);
        const next = !startOpen;
        setCatalogNavOpen(next);
        userHoldOpen = next && isStuckUnderHeader();
        return;
      }

      suppressMenuToggleClick = true;
      bumpIgnore(IOS_SHEET_MS);

      let shouldOpen;
      if (velocity > 0.4) shouldOpen = true;
      else if (velocity < -0.4) shouldOpen = false;
      else shouldOpen = startOpen ? h > fullH * 0.4 : h >= fullH * 0.18 || dy > 28;

      userHoldOpen = shouldOpen && isStuckUnderHeader();
      // Дожим тем же height/WAAPI-путём, что и скролл/тап
      clearDragStyles();
      panel.style.height = `${Math.max(0, h)}px`;
      panel.classList.toggle("is-open", startOpen || h > 0);
      setCatalogNavOpen(shouldOpen);
    };

    const onTouchCancel = () => {
      if (!drag) return;
      drag = null;
      clearDragStyles();
      clearSheetInline(panel);
      skipStickySync = false;
      syncStickyHeaderHeight();
    };

    const onNavClick = (event) => {
      if (!isMobile()) return;
      const link = event.target.closest("a[data-scroll-spy-link], a[data-catalog-nav]");
      if (!link) return;
      // Не трогаем шторку тут — loadCatalog синхронизирует без двойной анимации
      if (link.hasAttribute("data-scroll-spy-link")) return;
      userHoldOpen = false;
      quietSheetSync(1200);
    };

    let scrollTicking = false;
    const onWindowScroll = () => {
      if (scrollTicking) return;
      scrollTicking = true;
      requestAnimationFrame(() => {
        scrollTicking = false;

        if (!isMobile()) {
          userHoldOpen = false;
          setCatalogNavOpen(true, { animate: false });
          lastY = window.scrollY || 0;
          return;
        }
        // Скролл пользователя всегда с анимацией. quiet — только для AJAX-sync.
        if (drag || panel._ublegkoBusy || Date.now() < ignoreScrollUntil) {
          lastY = window.scrollY || 0;
          return;
        }

        const y = window.scrollY || 0;
        const stuck = isStuckUnderHeader();
        const isOpen = panel.classList.contains("is-open");

        if (!stuck) {
          userHoldOpen = false;
          if (!isOpen) {
            bumpIgnore(IOS_SHEET_MS);
            setCatalogNavOpen(true, { animate: true });
          }
        } else if (userHoldOpen && y > lastY + 8) {
          userHoldOpen = false;
          if (isOpen) {
            bumpIgnore(IOS_SHEET_MS);
            setCatalogNavOpen(false, { animate: true });
          }
        } else if (!userHoldOpen && isOpen) {
          bumpIgnore(IOS_SHEET_MS);
          setCatalogNavOpen(false, { animate: true });
        }

        lastY = y;
      });
    };

    document.addEventListener("touchmove", onDocTouchMove, { passive: false, capture: true });
    toggle.addEventListener("touchstart", onTouchStart, { passive: false });
    toggle.addEventListener("touchmove", onTouchMove, { passive: false });
    toggle.addEventListener("touchend", onTouchEnd);
    toggle.addEventListener("touchcancel", onTouchCancel);
    toggle.addEventListener("click", onToggleClick);
    shell.addEventListener("click", onNavClick);
    window.addEventListener("scroll", onWindowScroll, { passive: true });
    window.addEventListener("resize", () => applyStickyState({ animate: false }));
    applyStickyState({ animate: false });

    catalogNavCollapseCleanup = () => {
      drag = null;
      clearDragStyles();
      cancelSheetAnimation(panel);
      clearSheetInline(panel);
      document.removeEventListener("touchmove", onDocTouchMove, { capture: true });
      toggle.removeEventListener("touchstart", onTouchStart);
      toggle.removeEventListener("touchmove", onTouchMove);
      toggle.removeEventListener("touchend", onTouchEnd);
      toggle.removeEventListener("touchcancel", onTouchCancel);
      toggle.removeEventListener("click", onToggleClick);
      shell.removeEventListener("click", onNavClick);
      window.removeEventListener("scroll", onWindowScroll);
      window.removeEventListener("resize", applyStickyState);
    };
  }
  initMobileCatalogNavCollapse();
  window.__ublegkoRefreshCatalogNav = initMobileCatalogNavCollapse;

  const cartQtyState = new WeakMap();

  function ensureCartQtyState(input) {
    let state = cartQtyState.get(input);
    if (!state) {
      const initial =
        input.defaultValue !== undefined && input.defaultValue !== ""
          ? input.defaultValue
          : "0";
      state = { lastSent: String(initial), inflight: null, timer: null, requestId: 0 };
      cartQtyState.set(input, state);
    }
    return state;
  }

  function getCsrfToken(form) {
    const field = form && form.querySelector('input[name="csrfmiddlewaretoken"]');
    if (field && field.value) return field.value;
    return getCookie("csrftoken");
  }

  function syncProductQtyInputs(productId, quantity, exceptInput) {
    if (!productId) return;
    document
      .querySelectorAll(`[data-cart-qty-form][data-product-id="${productId}"] input[name="quantity"]`)
      .forEach((el) => {
        if (exceptInput && el === exceptInput) return;
        el.value = String(quantity);
        const state = ensureCartQtyState(el);
        state.lastSent = String(quantity);
      });
  }

  function updateCartTotals(data) {
    const pageTotal = document.querySelector("[data-cart-page-total]");
    if (pageTotal && data.cart_total !== undefined) {
      pageTotal.textContent = `Итого: ${data.cart_total} руб`;
    }
    const headerTotals = document.querySelectorAll("[data-cart-total]");
    if (headerTotals.length && data.cart_total !== undefined) {
      headerTotals.forEach((el) => {
        el.textContent = `${data.cart_total} руб`;
      });
    }
  }

  async function refreshCartTable() {
    const wrap = document.querySelector(".cart-table-wrap");
    if (!wrap) return false;
    try {
      const response = await fetch(window.location.pathname + window.location.search, {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const next = doc.querySelector(".cart-table-wrap");
      if (!next) return false;
      wrap.replaceWith(next);
      return true;
    } catch (err) {
      return false;
    }
  }

  async function submitCartQty(form, input) {
    const state = ensureCartQtyState(input);
    const min = Number.isFinite(parseInt(input.min, 10)) ? parseInt(input.min, 10) : 0;
    let value = parseInt(input.value || String(min), 10);
    if (!Number.isFinite(value)) value = min;
    value = Math.max(min, value);
    input.value = String(value);
    if (String(value) === String(state.lastSent)) return;

    const formData = new FormData(form);
    formData.set("quantity", String(value));
    const requestId = ++state.requestId;

    try {
      if (state.inflight) state.inflight.abort();
      state.inflight = new AbortController();
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        credentials: "same-origin",
        signal: state.inflight.signal,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(form),
        },
      });
      if (requestId !== state.requestId) return;
      const data = await response.json();
      if (requestId !== state.requestId) return;
      if (!response.ok || !data.ok) {
        input.value = String(state.lastSent);
        if (data && data.error) showToast(data.error);
        return;
      }

      const qty = data.removed ? 0 : Number(data.quantity);
      input.value = String(qty);
      state.lastSent = String(qty);
      syncProductQtyInputs(form.getAttribute("data-product-id"), qty, input);
      updateCartTotals(data);

      const row = form.closest(".cart-item");
      const fromRecommendations = !row && Boolean(document.querySelector(".cart-table-wrap"));

      if (fromRecommendations) {
        // Добавление/изменение из блока «обычно берут» — обновляем таблицу корзины
        const ok = await refreshCartTable();
        if (!ok) window.location.reload();
        else if (data.removed || qty === 0) showToast("Удалено из корзины");
        else showToast(`В корзине: ${qty}`);
        return;
      }

      const lineTotals = row ? row.querySelectorAll("[data-cart-line-total]") : [];
      if (lineTotals.length && data.line_total !== undefined) {
        lineTotals.forEach((el) => {
          el.textContent = `${data.line_total} руб`;
        });
      }
      if (data.removed && row) {
        row.remove();
        if (!document.querySelector(".cart-list .cart-item")) {
          window.location.reload();
        }
      } else if (!row) {
        if (data.removed || qty === 0) {
          showToast("Удалено из корзины");
        } else {
          showToast(`В корзине: ${qty}`);
        }
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;
      if (requestId !== state.requestId) return;
      input.value = String(state.lastSent);
    }
  }

  document.addEventListener("click", (event) => {
    const minus = event.target.closest("[data-qty-minus]");
    const plus = event.target.closest("[data-qty-plus]");
    if (!minus && !plus) return;
    if ((minus && minus.disabled) || (plus && plus.disabled)) return;
    const group = event.target.closest("[data-qty-group]");
    if (!group || group.classList.contains("is-disabled")) return;
    const input = group.querySelector('input[name="quantity"], input');
    if (!input || input.disabled) return;
    event.preventDefault();

    const min = Number.isFinite(parseInt(input.min, 10)) ? parseInt(input.min, 10) : 0;
    const current = parseInt(input.value || String(min), 10);
    const safeCurrent = Number.isFinite(current) ? current : min;
    const next = minus ? Math.max(min, safeCurrent - 1) : safeCurrent + 1;
    input.value = String(next);

    const form = input.closest("[data-cart-qty-form]");
    if (form) {
      const state = ensureCartQtyState(input);
      clearTimeout(state.timer);
      submitCartQty(form, input);
      return;
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  document.addEventListener("change", (event) => {
    const input = event.target.closest('[data-cart-qty-form] input[name="quantity"]');
    if (!input) return;
    if (event.isTrusted === false) return;
    const form = input.closest("[data-cart-qty-form]");
    if (form) submitCartQty(form, input);
  });

  document.addEventListener("input", (event) => {
    const input = event.target.closest('[data-cart-qty-form] input[name="quantity"]');
    if (!input) return;
    if (event.isTrusted === false) return;
    const form = input.closest("[data-cart-qty-form]");
    if (!form) return;
    const state = ensureCartQtyState(input);
    clearTimeout(state.timer);
    state.timer = setTimeout(() => submitCartQty(form, input), 450);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const input = event.target.closest('[data-cart-qty-form] input[name="quantity"]');
    if (!input) return;
    event.preventDefault();
    const form = input.closest("[data-cart-qty-form]");
    const state = cartQtyState.get(input);
    if (state) clearTimeout(state.timer);
    if (form) submitCartQty(form, input);
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-ajax-cart]");
    if (!form) return;
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });
      const data = await response.json();
      if (data.ok) {
        const totalEls = document.querySelectorAll("[data-cart-total]");
        if (totalEls.length && data.cart_total !== undefined) {
          totalEls.forEach((el) => {
            el.textContent = `${data.cart_total} руб`;
          });
        }
        showToast(data.message || "Добавлено в корзину");
      }
    } catch (err) {
      form.submit();
    }
  });

  let catalogAbort = null;
  let categorySpyScrollHandler = null;
  let categorySpyLockUntil = 0;

  function getActiveCatalogCategoryId() {
    // Считаем по геометрии: класс .is-active мог остаться от открытой шторки
    // (там линия активации уезжала вниз и подсвечивалась нижняя категория).
    const sections = Array.from(document.querySelectorAll("[data-category-section]"));
    if (sections.length) {
      const line = stickyStackBottomPx() + 8;
      let currentId = null;
      for (const section of sections) {
        const title = section.querySelector(".category-block__title") || section;
        if (title.getBoundingClientRect().top <= line) {
          currentId = section.getAttribute("data-category-section");
        } else {
          break;
        }
      }
      if (currentId) return currentId;
    }
    if (location.hash && location.hash.startsWith("#category-")) {
      return location.hash.slice(1);
    }
    const active = document.querySelector("[data-scroll-spy-link].is-active");
    if (active) {
      return active.getAttribute("data-scroll-spy-link");
    }
    return null;
  }

  function stickyOffsetPx() {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--sticky-offset");
    const parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : 130;
  }

  function stickyStackBottomPx() {
    const sticky = document.querySelector(".header-sticky");
    const nav = document.querySelector("[data-catalog-nav-shell]");
    const toolbar = document.querySelector("[data-catalog-toolbar]");
    const panel = document.querySelector("[data-catalog-sheet]");
    const toggle = document.querySelector("[data-menu-toggle], #menu-toggle");
    const isMobile = window.matchMedia("(max-width: 900px)").matches;
    let bottom = 0;
    if (sticky) {
      bottom = Math.max(bottom, sticky.getBoundingClientRect().bottom);
    }
    if (isMobile && nav) {
      // Открытая шторка перекрывает контент — для spy/скролла считаем
      // свёрнутый бар (зацеп + фильтры), иначе активной становится нижняя категория.
      const sheetOpen = panel && panel.classList.contains("is-open");
      if (sheetOpen) {
        const handleH = toggle ? toggle.offsetHeight || 28 : 28;
        const toolbarH = toolbar ? toolbar.offsetHeight || 0 : 0;
        bottom = Math.max(bottom, nav.getBoundingClientRect().top + handleH + toolbarH);
      } else {
        bottom = Math.max(bottom, nav.getBoundingClientRect().bottom);
      }
    } else if (!isMobile && toolbar) {
      bottom = Math.max(bottom, toolbar.getBoundingClientRect().bottom);
    }
    if (!bottom) {
      return stickyOffsetPx();
    }
    return bottom;
  }

  function scrollToCategorySection(target, { behavior = "smooth" } = {}) {
    if (!target) return;
    syncStickyHeaderHeight();
    const mark = target.querySelector(".category-block__title") || target;
    const offset = stickyStackBottomPx() + 12;
    const top = mark.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: Math.max(0, top), behavior });
  }

  function scrollToCatalogTop({ behavior = "auto" } = {}) {
    const root = document.querySelector("[data-catalog-root]");
    if (!root) {
      window.scrollTo({ top: 0, behavior });
      return;
    }
    syncStickyHeaderHeight();
    const offset = stickyStackBottomPx() + 8;
    const top = root.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: Math.max(0, top), behavior });
  }

  function restoreScrollAfterCatalogFilter(categoryId, prevScrollY) {
    categorySpyLockUntil = Date.now() + 1200;
    const run = () => {
      let target = categoryId ? document.getElementById(categoryId) : null;
      if (!target) {
        target = document.querySelector("[data-category-section]");
      }
      if (target) {
        const id = target.id || target.getAttribute("data-category-section");
        scrollToCategorySection(target, { behavior: "auto" });
        if (id) {
          const url = new URL(window.location.href);
          url.hash = id;
          history.replaceState(
            { catalogAjax: true },
            "",
            `${url.pathname}${url.search}${url.hash}`
          );
        }
        return;
      }

      // Контент укоротился (фильтр) — не клампим старый scrollY в футер
      const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      if (Number.isFinite(prevScrollY) && prevScrollY <= maxY + 24) {
        window.scrollTo({ top: prevScrollY, behavior: "auto" });
      } else {
        scrollToCatalogTop({ behavior: "auto" });
      }
      if (location.hash) {
        const url = new URL(window.location.href);
        url.hash = "";
        history.replaceState({ catalogAjax: true }, "", `${url.pathname}${url.search}`);
      }
    };
    // После replaceWith нужны кадры на layout, иначе координаты секций врёт
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        quietSheetSync(900);
        run();
        syncCatalogSheetToScroll({ animate: false });
        settleSheetAfterScroll(900);
      })
    );
  }

  function initCategoryScrollSpy(options = {}) {
    if (categorySpyScrollHandler) {
      window.removeEventListener("scroll", categorySpyScrollHandler);
      categorySpyScrollHandler = null;
    }
    const sections = Array.from(document.querySelectorAll("[data-category-section]"));
    const links = Array.from(document.querySelectorAll("[data-scroll-spy-link]"));
    const homeLink = document.querySelector("[data-scroll-spy-home]");
    if (!sections.length || !links.length) return;

    function setActive(id) {
      links.forEach((link) => {
        const on = Boolean(id) && link.getAttribute("data-scroll-spy-link") === id;
        link.classList.toggle("is-active", on);
        if (!on && document.activeElement === link) link.blur();
      });
      if (homeLink) {
        homeLink.classList.toggle("is-active", !id);
        if (id && document.activeElement === homeLink) homeLink.blur();
      }
    }

    function updateActiveFromScroll() {
      if (Date.now() < categorySpyLockUntil) return;

      // Линия активации = низ липкого стека (шапка + категории + фильтры).
      const line = stickyStackBottomPx() + 8;

      let currentId = null;
      for (const section of sections) {
        const title = section.querySelector(".category-block__title") || section;
        if (title.getBoundingClientRect().top <= line) {
          currentId = section.getAttribute("data-category-section");
        } else {
          break;
        }
      }
      setActive(currentId);
    }

    let ticking = false;
    categorySpyScrollHandler = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        updateActiveFromScroll();
      });
    };
    window.addEventListener("scroll", categorySpyScrollHandler, { passive: true });
    updateActiveFromScroll();

    function goToCategory(id, target, { behavior = "smooth" } = {}) {
      categorySpyLockUntil = Date.now() + 1400;
      setActive(id);
      const isMobile = window.matchMedia("(max-width: 900px)").matches;
      const panel = document.querySelector("[data-catalog-sheet]");

      const doScroll = () => {
        syncStickyHeaderHeight();
        scrollToCategorySection(target, { behavior });
        history.replaceState(null, "", `#${id}`);
      };

      if (isMobile) {
        quietSheetSync(900);
        // Перед прыжком к секции сворачиваем без анимации — иначе offset врёт
        setCatalogNavOpen(false, { animate: false });
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            doScroll();
            settleSheetAfterScroll(900);
          })
        );
        return;
      }
      requestAnimationFrame(() => requestAnimationFrame(doScroll));
    }

    links.forEach((link) => {
      if (link.dataset.scrollBound === "1") return;
      link.dataset.scrollBound = "1";
      link.addEventListener("click", (event) => {
        const id = link.getAttribute("data-scroll-spy-link");
        const target = id ? document.getElementById(id) : null;
        if (!target) return;
        event.preventDefault();
        link.blur();
        goToCategory(id, target, { behavior: "smooth" });
      });
    });

    if (!options.skipHashScroll && location.hash) {
      const id = location.hash.slice(1);
      const target = document.getElementById(id);
      if (target) {
        setTimeout(() => {
          goToCategory(id, target, { behavior: "smooth" });
        }, 50);
      }
    }
  }

  async function loadCatalog(url, push) {
    const root = document.querySelector("[data-catalog-root]");
    if (!root) {
      window.location.href = url;
      return;
    }
    const preferCategoryId = getActiveCatalogCategoryId();
    const prevScrollY = window.scrollY;
    const prevPath = window.location.pathname;
    try {
      if (catalogAbort) catalogAbort.abort();
      catalogAbort = new AbortController();
      root.classList.add("is-loading");
      const response = await fetch(url, {
        signal: catalogAbort.signal,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const next = doc.querySelector("[data-catalog-root]");
      if (!next) {
        window.location.href = url;
        return;
      }
      const isMobile = window.matchMedia("(max-width: 900px)").matches;
      const nextUrl = new URL(url, window.location.origin);
      const enteredCategoryPage =
        nextUrl.pathname.includes("/category/") && !prevPath.includes("/category/");
      // HTML всегда с is-open — до insert ставим нужный класс, чтобы не мигало
      const nextPanel = next.querySelector("[data-catalog-sheet]");
      const nextToggle = next.querySelector("[data-menu-toggle], #menu-toggle");
      if (isMobile && nextPanel) {
        const wantOpen = enteredCategoryPage ? true : prevScrollY <= 24;
        nextPanel.classList.toggle("is-open", wantOpen);
        if (nextToggle) nextToggle.setAttribute("aria-expanded", wantOpen ? "true" : "false");
        if (!wantOpen) {
          nextPanel.style.height = "0px";
          nextPanel.style.overflow = "hidden";
        }
      }

      quietSheetSync(900);
      root.replaceWith(next);
      const title = doc.querySelector("title");
      if (title) document.title = title.textContent;
      if (push) {
        history.pushState(
          { catalogAjax: true },
          "",
          `${nextUrl.pathname}${nextUrl.search}`
        );
      }
      syncStickyHeaderHeight();
      if (typeof window.__ublegkoObserveToolbar === "function") {
        window.__ublegkoObserveToolbar();
      }
      if (typeof window.__ublegkoRefreshCatalogNav === "function") {
        window.__ublegkoRefreshCatalogNav();
      }

      if (enteredCategoryPage) {
        categorySpyLockUntil = Date.now() + 900;
        window.scrollTo({ top: 0, behavior: "auto" });
        quietSheetSync(900);
        syncCatalogSheetToScroll({ animate: false });
      } else {
        restoreScrollAfterCatalogFilter(preferCategoryId, prevScrollY);
      }

      initCategoryScrollSpy({ skipHashScroll: true });
      if (preferCategoryId && document.getElementById(preferCategoryId)) {
        document.querySelectorAll("[data-scroll-spy-link]").forEach((link) => {
          link.classList.toggle(
            "is-active",
            link.getAttribute("data-scroll-spy-link") === preferCategoryId
          );
        });
        const homeLink = document.querySelector("[data-scroll-spy-home]");
        if (homeLink) homeLink.classList.remove("is-active");
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;
      window.location.href = url;
    }
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-catalog-nav]");
    if (!link || event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (
      link.getAttribute("aria-hidden") === "true" ||
      link.getAttribute("aria-disabled") === "true" ||
      link.classList.contains("is-hidden") ||
      link.classList.contains("is-disabled")
    ) {
      return;
    }
    if (!document.querySelector("[data-catalog-root]")) return;
    event.preventDefault();
    loadCatalog(link.href, true);
  });

  // Клик по категории в сайдбаре при активном фильтре: если секции нет — открыть страницу категории
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-scroll-spy-link]");
    if (!link || event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const id = link.getAttribute("data-scroll-spy-link");
    const target = id ? document.getElementById(id) : null;
    if (target) return; // обычный scroll-spy обработает
    const path = link.getAttribute("data-category-path");
    if (!path) return;
    event.preventDefault();
    const next = new URL(path, window.location.origin);
    next.search = window.location.search;
    loadCatalog(next.href, true);
  });

  window.addEventListener("popstate", () => {
    if (document.querySelector("[data-catalog-root]")) {
      loadCatalog(window.location.href, false);
    }
  });

  const citySelector = document.querySelector("[data-city-selector]");
  if (citySelector) {
    const toggle = citySelector.querySelector("[data-city-toggle]");
    const dropdown = citySelector.querySelector("[data-city-dropdown]");
    const search = citySelector.querySelector("[data-city-search]");
    const list = citySelector.querySelector("[data-city-list]");
    const empty = citySelector.querySelector("[data-city-empty]");
    const label = citySelector.querySelector("[data-city-label]");
    const form = document.getElementById("city-set-form");
    const input = form ? form.querySelector("[data-city-input]") : null;

    function closeCity() {
      citySelector.classList.remove("is-open");
      if (dropdown) dropdown.hidden = true;
      if (toggle) toggle.setAttribute("aria-expanded", "false");
    }

    function openCity() {
      citySelector.classList.add("is-open");
      if (dropdown) dropdown.hidden = false;
      if (toggle) toggle.setAttribute("aria-expanded", "true");
      if (search) {
        search.value = "";
        filterCities("");
        search.focus();
      }
    }

    function filterCities(query) {
      if (!list) return;
      const q = (query || "").trim().toLowerCase();
      let visible = 0;
      list.querySelectorAll("[data-city-filter]").forEach((btn) => {
        const match = !q || (btn.dataset.cityFilter || "").includes(q);
        if (btn.parentElement) btn.parentElement.hidden = !match;
        if (match) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
    }

    if (toggle) {
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        if (citySelector.classList.contains("is-open")) closeCity();
        else openCity();
      });
    }

    if (search) {
      search.addEventListener("input", () => filterCities(search.value));
    }

    if (list) {
      list.addEventListener("click", async (event) => {
        const btn = event.target.closest("[data-city-id]");
        if (!btn || !form || !input) return;
        input.value = btn.dataset.cityId;
        const formData = new FormData(form);
        try {
          const response = await fetch(form.action, {
            method: "POST",
            body: formData,
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              "X-CSRFToken": getCookie("csrftoken"),
            },
          });
          const data = await response.json();
          if (data.ok) {
            if (label) label.textContent = data.city;
            list.querySelectorAll(".city-selector__item").forEach((item) => {
              const active = item.dataset.cityId === String(data.id);
              item.classList.toggle("is-active", active);
              item.setAttribute("aria-selected", active ? "true" : "false");
            });
            closeCity();
            showToast(`Выбран город: ${data.city}`);
          }
        } catch (err) {
          form.submit();
        }
      });
    }

    document.addEventListener("click", (event) => {
      if (!citySelector.contains(event.target)) closeCity();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeCity();
    });
  }

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-ajax-favorite]");
    if (!form) return;
    event.preventDefault();
    const formData = new FormData(form);
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });
      const data = await response.json();
      if (data.ok) {
        const btn = form.querySelector(".btn-fav, .btn-heart, .fav-heart");
        if (btn) {
          btn.classList.toggle("is-active", data.active);
          const onLabel = btn.dataset.favLabelOn || "Убрать из избранного";
          const offLabel = btn.dataset.favLabelOff || "В избранное";
          if (btn.classList.contains("fav-heart")) {
            btn.setAttribute("aria-label", data.active ? onLabel : offLabel);
          } else {
            btn.textContent = data.active ? onLabel : offLabel;
          }
        }
        document.querySelectorAll("[data-favorites-count]").forEach((el) => {
          if (data.favorites_count !== undefined) {
            el.textContent = data.favorites_count;
          }
        });
        showToast(data.message || "Избранное обновлено");
        if (!data.active && window.location.pathname.indexOf("/favorites") === 0) {
          const card = form.closest(".product-card");
          if (card) card.remove();
        }
      }
    } catch (err) {
      form.submit();
    }
  });

  // Автоподсказки поиска + история запросов
  document.querySelectorAll("[data-search-form]").forEach((form) => {
    const input = form.querySelector("[data-search-input]");
    const box = form.querySelector("[data-search-suggest]");
    const url = form.getAttribute("data-suggest-url");
    const homeUrl = form.getAttribute("data-home-url") || "/";
    if (!input || !box || !url) return;

    const HISTORY_KEY = "ublegko_search_history";
    const HISTORY_LIMIT = 5;
    let timer = null;
    let activeIndex = -1;
    let items = [];
    let lastQuery = "";

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function getHistory() {
      try {
        const raw = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
        if (!Array.isArray(raw)) return [];
        return raw
          .filter((item) => typeof item === "string" && item.trim())
          .map((item) => item.trim())
          .slice(0, HISTORY_LIMIT);
      } catch (err) {
        return [];
      }
    }

    function pushHistory(q) {
      const query = String(q || "").trim();
      if (!query) return;
      const next = [
        query,
        ...getHistory().filter((item) => item.toLowerCase() !== query.toLowerCase()),
      ].slice(0, HISTORY_LIMIT);
      try {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
      } catch (err) {
        /* ignore quota */
      }
    }

    function hide() {
      box.hidden = true;
      box.innerHTML = "";
      items = [];
      activeIndex = -1;
      input.setAttribute("aria-expanded", "false");
    }

    function highlight() {
      box.querySelectorAll(".search-suggest__item").forEach((el, i) => {
        el.classList.toggle("is-active", i === activeIndex);
      });
    }

    function bindHistoryClicks() {
      box.querySelectorAll("[data-history-q]").forEach((btn) => {
        btn.addEventListener("mousedown", (event) => event.preventDefault());
        btn.addEventListener("click", () => {
          const q = btn.getAttribute("data-history-q") || "";
          input.value = q;
          hide();
          form.requestSubmit();
        });
      });
    }

    function renderHistory() {
      const history = getHistory();
      if (!history.length) {
        hide();
        return;
      }
      box.innerHTML =
        '<div class="search-suggest__label">Недавние запросы</div>' +
        history
          .map(
            (q, i) =>
              `<button type="button" class="search-suggest__item search-suggest__item--history" role="option" data-history-q="${escapeHtml(q)}" data-index="${i}">` +
              `<span class="search-suggest__name">${escapeHtml(q)}</span>` +
              `<span class="search-suggest__meta">История</span>` +
              `</button>`
          )
          .join("");
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      items = Array.from(box.querySelectorAll(".search-suggest__item"));
      activeIndex = -1;
      bindHistoryClicks();
    }

    function render(results) {
      if (!results.length) {
        box.innerHTML = '<div class="search-suggest__empty">Ничего не найдено</div>';
        box.hidden = false;
        input.setAttribute("aria-expanded", "true");
        items = [];
        activeIndex = -1;
        return;
      }
      box.innerHTML = results
        .map(
          (r, i) =>
            `<a class="search-suggest__item" role="option" href="${r.url}" data-index="${i}">` +
            `<span class="search-suggest__name">${escapeHtml(r.name)}</span>` +
            `<span class="search-suggest__meta">${escapeHtml(r.price)} ₽</span>` +
            `</a>`
        )
        .join("");
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      items = Array.from(box.querySelectorAll(".search-suggest__item"));
      activeIndex = -1;
    }

    async function fetchSuggest(q) {
      lastQuery = q;
      try {
        const response = await fetch(`${url}?q=${encodeURIComponent(q)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        const data = await response.json();
        if (input.value.trim() !== lastQuery) return;
        render(data.results || []);
      } catch (err) {
        hide();
      }
    }

    async function goToCatalog() {
      hide();
      input.value = "";
      const onSearchPage = /\/search\/?$/.test(window.location.pathname);
      const hadQuery = Boolean(new URLSearchParams(window.location.search).get("q"));
      if (onSearchPage || hadQuery) {
        if (document.querySelector("[data-catalog-root]")) {
          await loadCatalog(homeUrl, true);
        } else {
          window.location.href = homeUrl;
          return;
        }
      }
      // После крестика focus не срабатывает повторно — открываем историю сразу.
      if (document.activeElement === input) renderHistory();
    }

    function openHistoryOrSuggest() {
      const q = input.value.trim();
      if (!q) {
        renderHistory();
        return;
      }
      fetchSuggest(q);
    }

    form.addEventListener("submit", () => {
      pushHistory(input.value);
    });

    input.addEventListener("search", () => {
      if (!input.value.trim()) goToCatalog();
    });

    input.addEventListener("input", () => {
      const q = input.value.trim();
      clearTimeout(timer);
      if (!q) {
        renderHistory();
        return;
      }
      timer = setTimeout(() => fetchSuggest(q), 180);
    });

    // click — даже если поле уже в фокусе (после поиска/крестика)
    input.addEventListener("focus", openHistoryOrSuggest);
    input.addEventListener("click", openHistoryOrSuggest);

    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hide();
        return;
      }
      if (box.hidden || !items.length) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        highlight();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        highlight();
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        items[activeIndex].click();
      }
    });

    input.addEventListener("blur", () => {
      setTimeout(hide, 150);
    });

    document.addEventListener("click", (event) => {
      if (!form.contains(event.target)) hide();
    });

    box.addEventListener("click", (event) => {
      const productLink = event.target.closest(".search-suggest__item[href]");
      if (productLink && input.value.trim()) pushHistory(input.value);
    });
  });

  // Маска телефона +7 (999) 000-00-00
  function formatPhoneMask(value) {
    let digits = String(value || "").replace(/\D/g, "");
    if (!digits) return "";
    if (digits[0] === "8") digits = "7" + digits.slice(1);
    if (digits[0] !== "7") digits = "7" + digits;
    digits = digits.slice(0, 11);
    let out = "+7";
    if (digits.length > 1) out += " (" + digits.slice(1, 4);
    if (digits.length >= 4) out += ")";
    if (digits.length > 4) out += " " + digits.slice(4, 7);
    if (digits.length > 7) out += "-" + digits.slice(7, 9);
    if (digits.length > 9) out += "-" + digits.slice(9, 11);
    return out;
  }

  function isValidRuPhone(value) {
    const digits = String(value || "").replace(/\D/g, "");
    return digits.length === 11 && digits[0] === "7";
  }

  function isValidEmail(value) {
    return /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(String(value || "").trim());
  }

  function setFieldError(input, message) {
    let box = input.parentElement && input.parentElement.querySelector("[data-field-error]");
    if (!box) {
      box = document.createElement("div");
      box.className = "field-error";
      box.setAttribute("data-field-error", "1");
      input.insertAdjacentElement("afterend", box);
    }
    box.textContent = message || "";
    box.hidden = !message;
    input.classList.toggle("is-invalid", Boolean(message));
  }

  document.querySelectorAll("[data-phone-mask]").forEach((input) => {
    if (input.value) input.value = formatPhoneMask(input.value);
    input.addEventListener("input", () => {
      const start = input.selectionStart;
      const before = input.value.length;
      input.value = formatPhoneMask(input.value);
      const diff = input.value.length - before;
      if (document.activeElement === input && start != null) {
        const pos = Math.max(0, start + diff);
        input.setSelectionRange(pos, pos);
      }
      setFieldError(input, "");
    });
    input.addEventListener("blur", () => {
      if (!input.value.trim()) {
        setFieldError(input, "Укажите телефон");
        return;
      }
      setFieldError(
        input,
        isValidRuPhone(input.value) ? "" : "Телефон в формате +7 (999) 000-00-00"
      );
    });
  });

  document.querySelectorAll("[data-email-validate]").forEach((input) => {
    input.addEventListener("blur", () => {
      const value = input.value.trim();
      if (!value) {
        setFieldError(input, "Укажите email");
        return;
      }
      setFieldError(input, isValidEmail(value) ? "" : "Укажите корректный email, например name@mail.ru");
    });
    input.addEventListener("input", () => setFieldError(input, ""));
  });

  document.querySelectorAll("form").forEach((form) => {
    const phone = form.querySelector("[data-phone-mask]");
    const email = form.querySelector("[data-email-validate]");
    if (!phone && !email) return;
    form.addEventListener("submit", (event) => {
      let ok = true;
      if (phone) {
        phone.value = formatPhoneMask(phone.value);
        if (!isValidRuPhone(phone.value)) {
          setFieldError(phone, "Телефон в формате +7 (999) 000-00-00");
          ok = false;
        }
      }
      if (email) {
        const value = email.value.trim();
        if (!isValidEmail(value)) {
          setFieldError(email, "Укажите корректный email, например name@mail.ru");
          ok = false;
        }
      }
      if (!ok) event.preventDefault();
    });
  });

  // Глазок для пароля
  const eyeOpen =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 19c-7 0-11-7-11-7a21.8 21.8 0 0 1 5.06-5.94M9.9 4.24A10.94 10.94 0 0 1 12 5c7 0 11 7 11 7a21.9 21.9 0 0 1-2.16 3.19M1 1l22 22"/><path d="M14.12 14.12A3 3 0 0 1 9.88 9.88"/></svg>';

  document.querySelectorAll("input[data-password-toggle], input[type='password']").forEach((input) => {
    if (input.closest(".password-field")) return;
    const wrap = document.createElement("div");
    wrap.className = "password-field";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "password-toggle";
    btn.setAttribute("aria-label", "Показать пароль");
    btn.innerHTML = eyeOpen;
    wrap.appendChild(btn);
    btn.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.setAttribute("aria-label", show ? "Скрыть пароль" : "Показать пароль");
      btn.innerHTML = show ? eyeOff : eyeOpen;
    });
  });

  function syncCheckoutDelivery() {
    const form = document.querySelector("[data-checkout-form]");
    if (!form) return;
    const selected = form.querySelector("[data-delivery-method]:checked");
    const method = selected ? selected.value : "courier";
    const addressGroup = form.querySelector("[data-checkout-address]");
    if (!addressGroup) return;
    const isPickup = method === "pickup";
    addressGroup.hidden = isPickup;
    const addressField = addressGroup.querySelector("input, textarea, select");
    if (addressField) {
      addressField.required = !isPickup;
      if (isPickup && addressField.tagName !== "SELECT") {
        addressField.value = "";
      }
    }
  }

  document.addEventListener("change", (event) => {
    if (event.target.matches("[data-delivery-method]")) {
      syncCheckoutDelivery();
    }
  });
  syncCheckoutDelivery();

  function enhanceSelect(select) {
    if (!select || select.dataset.customSelect === "1") return;
    select.dataset.customSelect = "1";
    select.classList.add("visually-hidden");
    select.setAttribute("tabindex", "-1");
    select.setAttribute("aria-hidden", "true");

    const wrap = document.createElement("div");
    wrap.className = "custom-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);

    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "custom-select__trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");

    const label = document.createElement("span");
    label.className = "custom-select__label";
    const chevron = document.createElement("span");
    chevron.className = "custom-select__chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.innerHTML =
      '<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    trigger.append(label, chevron);

    const menu = document.createElement("ul");
    menu.className = "custom-select__menu";
    menu.hidden = true;
    menu.setAttribute("role", "listbox");

    wrap.append(trigger, menu);

    function syncLabel() {
      const option = select.options[select.selectedIndex];
      label.textContent = option ? option.textContent : "";
    }

    function renderOptions() {
      menu.innerHTML = "";
      Array.from(select.options).forEach((option, index) => {
        const item = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "custom-select__option";
        btn.textContent = option.textContent;
        btn.dataset.value = option.value;
        if (index === select.selectedIndex) btn.classList.add("is-active");
        btn.addEventListener("click", () => {
          select.value = option.value;
          select.dispatchEvent(new Event("change", { bubbles: true }));
          syncLabel();
          close();
        });
        item.appendChild(btn);
        menu.appendChild(item);
      });
    }

    function open() {
      renderOptions();
      wrap.classList.add("is-open");
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
    }

    function close() {
      wrap.classList.remove("is-open");
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", () => {
      if (wrap.classList.contains("is-open")) close();
      else open();
    });

    document.addEventListener("click", (event) => {
      if (!wrap.contains(event.target)) close();
    });

    select.addEventListener("change", syncLabel);
    syncLabel();
  }

  document.querySelectorAll("select.form-input").forEach(enhanceSelect);

  initCategoryScrollSpy();
  initProductGallery();

  function initProductGallery() {
    const root = document.querySelector("[data-product-gallery]");
    const lightbox = document.querySelector("[data-gallery-lightbox]");
    const dataEl = document.getElementById("product-gallery-data");
    if (!root || !lightbox || !dataEl) return;

    let images = [];
    try {
      images = JSON.parse(dataEl.textContent || "[]");
    } catch (_err) {
      return;
    }
    if (!images.length) return;

    let index = 0;
    const mainImg = root.querySelector("[data-gallery-main-img]");
    const thumbs = Array.from(root.querySelectorAll(".product-gallery__thumb"));
    const lightboxImg = lightbox.querySelector("[data-gallery-lightbox-img]");
    const currentEl = lightbox.querySelector("[data-gallery-current]");

    function setActiveThumb(i) {
      thumbs.forEach((thumb, idx) => {
        const active = idx === i;
        thumb.classList.toggle("is-active", active);
        thumb.setAttribute("aria-current", active ? "true" : "false");
      });
    }

    function show(i) {
      index = (i + images.length) % images.length;
      if (mainImg) mainImg.src = images[index];
      if (lightboxImg) lightboxImg.src = images[index];
      if (currentEl) currentEl.textContent = String(index + 1);
      setActiveThumb(index);
    }

    function open(i) {
      show(i);
      lightbox.hidden = false;
      document.body.style.overflow = "hidden";
    }

    function close() {
      lightbox.hidden = true;
      document.body.style.overflow = "";
    }

    root.addEventListener("click", (event) => {
      const thumb = event.target.closest("[data-gallery-thumb]");
      if (thumb && root.contains(thumb)) {
        const i = Number(thumb.dataset.index || 0);
        show(Number.isFinite(i) ? i : 0);
        return;
      }
      const btn = event.target.closest("[data-gallery-open]");
      if (!btn || !root.contains(btn)) return;
      const i = Number(btn.dataset.index || 0);
      open(Number.isFinite(i) ? i : 0);
    });

    lightbox.addEventListener("click", (event) => {
      if (event.target.closest("[data-gallery-close]")) {
        close();
        return;
      }
      if (event.target.closest("[data-gallery-prev]")) {
        show(index - 1);
        return;
      }
      if (event.target.closest("[data-gallery-next]")) {
        show(index + 1);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (lightbox.hidden) return;
      if (event.key === "Escape") close();
      else if (event.key === "ArrowLeft") show(index - 1);
      else if (event.key === "ArrowRight") show(index + 1);
    });
  }
})();
