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

  function normalizeStainHelpQuery(q) {
    return String(q || "")
      .trim()
      .toLowerCase()
      .replace(/ё/g, "е")
      .replace(/\s+/g, " ");
  }

  function matchesStainHelpQuery(q) {
    const normalized = normalizeStainHelpQuery(q);
    if (!normalized) return false;
    const prefixes = window.ublegkoStainHelpPrefixes || [];
    for (let i = 0; i < prefixes.length; i++) {
      const prefix = normalizeStainHelpQuery(prefixes[i]);
      if (prefix && normalized.startsWith(prefix)) return true;
    }
    return false;
  }

  function requestStainHelpModal(query, source) {
    const q = String(query || "").trim();
    if (!q || !matchesStainHelpQuery(q)) return;
    document.dispatchEvent(
      new CustomEvent("ublegko:stain-help-open", {
        detail: { query: q, source: source || "unknown" },
      })
    );
  }

  // Клик/тап по полоске не открывает шторку — только жест «потянуть»
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-menu-toggle], #menu-toggle");
    if (!toggle) return;
    event.preventDefault();
    suppressMenuToggleClick = false;
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
  // Гистерезис: на Android bounce иначе открывает/закрывает дважды
  const SHEET_OPEN_TOP_PX = 48;
  const SHEET_CLOSE_TOP_PX = 130;
  let sheetSyncQuietUntil = 0;
  let sheetQuietTimer = 0;
  let pendingSheetTopOpen = false;

  let sheetNavLockUntil = 0;
  let sheetLastOpenAt = 0;
  let sheetLastCloseAt = 0;

  function quietSheetSync(ms = 900) {
    sheetSyncQuietUntil = Math.max(sheetSyncQuietUntil, Date.now() + ms);
    if (sheetQuietTimer) clearTimeout(sheetQuietTimer);
    // После тишины догоняем открытие у верха (иначе нужен «второй» скролл)
    sheetQuietTimer = setTimeout(() => {
      sheetQuietTimer = 0;
      flushPendingSheetTopOpen();
    }, ms + 40);
  }
  function isSheetSyncQuiet() {
    return Date.now() < sheetSyncQuietUntil;
  }
  function lockSheetAfterNav(ms = 2000) {
    // Только глушит scroll-toggle. НЕ закрывает шторку сама по себе.
    sheetNavLockUntil = Math.max(sheetNavLockUntil, Date.now() + ms);
    if (!isNearCatalogTop()) pendingSheetTopOpen = false;
    quietSheetSync(ms);
  }
  function isSheetNavLocked() {
    return Date.now() < sheetNavLockUntil;
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

  function isNearCatalogTop() {
    return (window.scrollY || 0) <= SHEET_OPEN_TOP_PX;
  }

  function flushPendingSheetTopOpen() {
    if (!window.matchMedia("(max-width: 900px)").matches) return;
    if (!pendingSheetTopOpen) return;
    // После фильтра/категории не автооткрываем — только ручной скролл к y≈0
    if (isSheetNavLocked()) return;
    if (!isNearCatalogTop()) {
      pendingSheetTopOpen = false;
      return;
    }
    const panel =
      document.querySelector("[data-catalog-sheet]") ||
      document.querySelector("[data-sidebar], #sidebar");
    if (!panel || panel._ublegkoBusy) return;
    pendingSheetTopOpen = false;
    if (panel.classList.contains("is-open") && currentSheetHeight(panel) > 8) return;
    if (Date.now() - sheetLastOpenAt < 800) return;
    setCatalogNavOpen(true, { animate: true });
  }

  function syncCatalogSheetToScroll({ animate = false } = {}) {
    const panel =
      document.querySelector("[data-catalog-sheet]") ||
      document.querySelector("[data-sidebar], #sidebar");
    if (!panel || !window.matchMedia("(max-width: 900px)").matches) {
      if (panel) setCatalogNavOpen(true, { animate: false });
      return;
    }
    // Lock = без анимации от скролла; состояние всё равно по позиции (верх = открыта)
    setCatalogNavOpen(isNearCatalogTop(), {
      animate: Boolean(animate) && !isSheetNavLocked(),
    });
  }

  function settleSheetAfterScroll(ms = 1200) {
    quietSheetSync(ms);
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      pendingSheetTopOpen = false;
      // Как есть по скроллу: наверху открыта, ниже — закрыта
      setCatalogNavOpen(isNearCatalogTop(), { animate: false });
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
    const force = options.force === true;
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

    // Анти-двойная шторка (Android): не перезапускаем ту же сторону
    // (жест/тап — force, противоположное направление всегда можно)
    if (useAnimate && !force) {
      const sameOpen = open && (wasOpen || panel._ublegkoBusy) && Date.now() - sheetLastOpenAt < 1000;
      const sameClose = !open && (!wasOpen || panel._ublegkoBusy) && Date.now() - sheetLastCloseAt < 1000;
      if (sameOpen || sameClose) {
        syncStickyHeaderHeight();
        return;
      }
    }

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
      if (open) sheetLastOpenAt = Date.now();
      else sheetLastCloseAt = Date.now();
      skipStickySync = false;
      syncStickyHeaderHeight();
      return;
    }

    const fullH = measureSheetHeight(panel);
    const to = open ? fullH : 0;

    // Метка сразу — иначе повторный scroll/resize перезапустит анимацию
    if (open) sheetLastOpenAt = Date.now();
    else sheetLastCloseAt = Date.now();

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
    // Антидребезг: не открывать/закрывать шторку пачкой при инерции скролла
    let sheetGateUntil = 0;
    let sheetGateTimer = 0;

    const bumpIgnore = (ms = 450) => {
      ignoreScrollUntil = Date.now() + ms;
    };
    const bumpSheetGate = (ms = IOS_SHEET_MS + 180) => {
      sheetGateUntil = Date.now() + ms;
      if (sheetGateTimer) clearTimeout(sheetGateTimer);
      sheetGateTimer = setTimeout(() => {
        sheetGateTimer = 0;
        flushPendingSheetTopOpen();
      }, ms + 40);
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
      if (window.__ublegkoCatalogReturning) {
        const returnY = Number(window.__ublegkoCatalogReturnY || 0);
        if (isMobile() && returnY > SHEET_OPEN_TOP_PX) {
          setCatalogNavOpen(false, { animate: false, force: true });
          return;
        }
      }
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
        // Тап без протяжки — не тогглим, возвращаем как было
        clearDragStyles();
        suppressMenuToggleClick = true;
        bumpIgnore(120);
        setCatalogNavOpen(startOpen, { animate: false, force: true });
        userHoldOpen = startOpen && isStuckUnderHeader();
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
      setCatalogNavOpen(shouldOpen, { force: true });
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
      // Только тишина от scroll-toggle; наверху шторка должна остаться открытой
      quietSheetSync(900);
    };

    let scrollTicking = false;
    const onWindowScroll = () => {
      if (scrollTicking) return;
      scrollTicking = true;
      requestAnimationFrame(() => {
        scrollTicking = false;

        if (window.__ublegkoCatalogReturning && !window.__ublegkoCatalogScrollRestored) {
          lastY = window.scrollY || 0;
          return;
        }

        if (!isMobile()) {
          userHoldOpen = false;
          setCatalogNavOpen(true, { animate: false });
          lastY = window.scrollY || 0;
          return;
        }

        const y = window.scrollY || 0;
        const nearTop = y <= SHEET_OPEN_TOP_PX;
        const navLocked = isSheetNavLocked();

        if (
          drag ||
          panel._ublegkoBusy ||
          Date.now() < ignoreScrollUntil ||
          Date.now() < sheetGateUntil ||
          isSheetSyncQuiet() ||
          navLocked
        ) {
          // Во время lock после фильтра/категории не копим pending-open
          if (nearTop && !navLocked) pendingSheetTopOpen = true;
          lastY = y;
          return;
        }

        if (pendingSheetTopOpen && nearTop) {
          pendingSheetTopOpen = false;
          userHoldOpen = false;
          if (!panel.classList.contains("is-open") && Date.now() - sheetLastOpenAt >= 900) {
            bumpIgnore(IOS_SHEET_MS);
            bumpSheetGate(IOS_SHEET_MS + 400);
            setCatalogNavOpen(true, { animate: true });
          }
          lastY = y;
          return;
        }

        const dy = y - lastY;
        const isOpen = panel.classList.contains("is-open");

        // Открыть только у самого верха; закрыть только заметно ниже —
        // иначе Android overscroll дважды дёргает разворот.
        if (y <= SHEET_OPEN_TOP_PX) {
          userHoldOpen = false;
          pendingSheetTopOpen = false;
          if (!isOpen && Date.now() - sheetLastOpenAt >= 900) {
            bumpIgnore(IOS_SHEET_MS + 160);
            bumpSheetGate(IOS_SHEET_MS + 400);
            setCatalogNavOpen(true, { animate: true });
          }
        } else if (
          isOpen &&
          !userHoldOpen &&
          y >= SHEET_CLOSE_TOP_PX &&
          dy > 3
        ) {
          bumpIgnore(IOS_SHEET_MS + 160);
          bumpSheetGate(IOS_SHEET_MS + 400);
          setCatalogNavOpen(false, { animate: true });
        } else if (userHoldOpen && isOpen && y >= SHEET_CLOSE_TOP_PX && dy > 10) {
          userHoldOpen = false;
          bumpIgnore(IOS_SHEET_MS + 160);
          bumpSheetGate(IOS_SHEET_MS + 400);
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
    const onViewportResize = () => {
      // Только высота sticky. НЕ трогаем шторку — на Android адресная строка
      // шлёт resize при каждом скролле и открывала шторку повторно.
      syncStickyHeaderHeight();
    };

    window.addEventListener("scroll", onWindowScroll, { passive: true });
    window.addEventListener("resize", onViewportResize);
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
      window.removeEventListener("resize", onViewportResize);
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

  const CATALOG_RETURN_URL_KEY = "ublegko_catalog_return_url";
  const CATALOG_RETURN_SCROLL_KEY = "ublegko_catalog_scroll_y";
  const CATALOG_RETURN_PENDING_KEY = "ublegko_catalog_return_pending";
  const CATALOG_LEFT_FOR_PRODUCT_KEY = "ublegko_catalog_left_for_product";

  function catalogPagePath(pathname) {
    if (!pathname) return false;
    if (pathname === "/") return true;
    if (pathname.startsWith("/category/")) return true;
    if (pathname.startsWith("/search")) return true;
    return false;
  }

  function currentCatalogUrl() {
    return `${window.location.pathname}${window.location.search}`;
  }

  function saveCatalogReturnState() {
    if (!document.querySelector("[data-catalog-root]")) return;
    if (!catalogPagePath(window.location.pathname)) return;
    try {
      sessionStorage.setItem(CATALOG_RETURN_URL_KEY, currentCatalogUrl());
      sessionStorage.setItem(CATALOG_RETURN_SCROLL_KEY, String(Math.round(window.scrollY)));
    } catch (_err) {
      /* private mode / quota */
    }
  }

  function getCatalogReturnUrl() {
    try {
      const saved = sessionStorage.getItem(CATALOG_RETURN_URL_KEY);
      if (!saved) return null;
      const parsed = new URL(saved, window.location.origin);
      if (!catalogPagePath(parsed.pathname)) return null;
      return `${parsed.pathname}${parsed.search}`;
    } catch (_err) {
      return null;
    }
  }

  function getSavedCatalogScrollY() {
    try {
      const scrollY = parseInt(sessionStorage.getItem(CATALOG_RETURN_SCROLL_KEY) || "0", 10);
      return Number.isFinite(scrollY) && scrollY > 0 ? scrollY : 0;
    } catch (_err) {
      return 0;
    }
  }

  function scrollCatalogInstant(scrollY) {
    if (!Number.isFinite(scrollY) || scrollY <= 0) return;
    const root = document.documentElement;
    const prev = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, scrollY);
    root.style.scrollBehavior = prev;
  }

  function markCatalogReturnPending() {
    try {
      sessionStorage.setItem(CATALOG_RETURN_PENDING_KEY, "1");
      sessionStorage.setItem(CATALOG_LEFT_FOR_PRODUCT_KEY, "1");
    } catch (_err) {
      /* ignore */
    }
  }

  function markCatalogLeftForProduct() {
    try {
      sessionStorage.setItem(CATALOG_LEFT_FOR_PRODUCT_KEY, "1");
    } catch (_err) {
      /* ignore */
    }
  }

  function initCatalogReturnLink() {
    const back = document.querySelector("[data-catalog-return]");
    if (!back) return;
    const saved = getCatalogReturnUrl();
    if (saved) back.setAttribute("href", saved);

    back.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      markCatalogReturnPending();
      window.location.assign(saved || back.getAttribute("href") || "/");
    });
  }

  function isCatalogReturnLanding() {
    if (!document.querySelector("[data-catalog-root]")) return false;
    if (window.__ublegkoCatalogScrollRestored) return true;
    try {
      if (sessionStorage.getItem(CATALOG_LEFT_FOR_PRODUCT_KEY) === "1") return true;
      if (sessionStorage.getItem(CATALOG_RETURN_PENDING_KEY) === "1") return true;
      const ref = document.referrer || "";
      return Boolean(ref && new URL(ref, window.location.origin).pathname.includes("/product/"));
    } catch (_err) {
      return false;
    }
  }

  function finalizeCatalogReturnLanding() {
    if (!isCatalogReturnLanding()) return false;

    if (location.hash) {
      history.replaceState(null, "", `${location.pathname}${location.search}`);
    }

    const scrollY = Number(window.__ublegkoCatalogReturnY || getSavedCatalogScrollY() || 0);
    if (scrollY > SHEET_OPEN_TOP_PX) {
      lockSheetAfterNav(1600);
      setCatalogNavOpen(false, { animate: false, force: true });
    } else if (typeof syncCatalogSheetToScroll === "function") {
      syncCatalogSheetToScroll({ animate: false });
    }

    return true;
  }

  window.addEventListener("pageshow", (event) => {
    if (!document.querySelector("[data-catalog-root]")) return;
    if (!event.persisted && !window.__ublegkoCatalogReturning) return;
    if (window.__ublegkoCatalogScrollRestored) return;

    const scrollY = Number(window.__ublegkoCatalogReturnY || getSavedCatalogScrollY() || 0);
    if (scrollY > 0) scrollCatalogInstant(scrollY);
    if (scrollY > SHEET_OPEN_TOP_PX) {
      lockSheetAfterNav(1600);
      setCatalogNavOpen(false, { animate: false, force: true });
    }
  });

  let catalogScrollSaveTimer = 0;
  window.addEventListener(
    "scroll",
    () => {
      if (!document.querySelector("[data-catalog-root]")) return;
      window.clearTimeout(catalogScrollSaveTimer);
      catalogScrollSaveTimer = window.setTimeout(saveCatalogReturnState, 150);
    },
    { passive: true }
  );

  document.addEventListener(
    "click",
    (event) => {
      const link = event.target.closest("a[href]");
      if (!link || event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (!document.querySelector("[data-catalog-root]")) return;
      const href = link.getAttribute("href") || "";
      if (!href.includes("/product/")) return;
      saveCatalogReturnState();
      markCatalogLeftForProduct();
    },
    true
  );

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
    const wasAtTop = Number.isFinite(prevScrollY) && prevScrollY <= SHEET_OPEN_TOP_PX;
    const run = () => {
      // Были наверху — остаёмся наверху, шторка открыта (не прыгаем к секции)
      if (wasAtTop) {
        window.scrollTo({ top: 0, behavior: "auto" });
        if (location.hash) {
          const url = new URL(window.location.href);
          url.hash = "";
          history.replaceState({ catalogAjax: true }, "", `${url.pathname}${url.search}`);
        }
        return;
      }

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

      const doScroll = () => {
        syncStickyHeaderHeight();
        scrollToCategorySection(target, { behavior });
        history.replaceState(null, "", `#${id}`);
      };

      if (isMobile) {
        // stickyStackBottomPx уже считает offset как у свёрнутой шторки —
        // закрываем заранее только если уйдём с верха страницы
        const mark = target.querySelector(".category-block__title") || target;
        const approxTop = Math.max(
          0,
          mark.getBoundingClientRect().top + window.scrollY - (stickyStackBottomPx() + 12)
        );
        quietSheetSync(1200);
        if (approxTop > SHEET_CLOSE_TOP_PX) {
          setCatalogNavOpen(false, { animate: false });
        }
        // На Android smooth даёт пачку scroll/resize → двойная шторка
        const android = /Android/i.test(navigator.userAgent || "");
        const scrollBehavior = android ? "auto" : behavior;
        requestAnimationFrame(() =>
          requestAnimationFrame(() => {
            syncStickyHeaderHeight();
            scrollToCategorySection(target, { behavior: scrollBehavior });
            history.replaceState(null, "", `#${id}`);
            settleSheetAfterScroll(1000);
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
        const wantOpen = enteredCategoryPage ? true : prevScrollY <= SHEET_OPEN_TOP_PX;
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
        setCatalogNavOpen(true, { animate: false });
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
      saveCatalogReturnState();
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
    let stainModalTimer = null;
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
          if (matchesStainHelpQuery(q)) {
            requestStainHelpModal(q, "history");
          } else {
            form.requestSubmit();
          }
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

    form.addEventListener("submit", (event) => {
      const q = input.value.trim();
      if (matchesStainHelpQuery(q)) {
        event.preventDefault();
        pushHistory(q);
        hide();
        requestStainHelpModal(q, "submit");
        return;
      }
      pushHistory(q);
    });

    input.addEventListener("search", () => {
      if (!input.value.trim()) goToCatalog();
    });

    input.addEventListener("input", () => {
      const q = input.value.trim();
      clearTimeout(timer);
      clearTimeout(stainModalTimer);
      if (!q) {
        renderHistory();
        return;
      }
      timer = setTimeout(() => fetchSuggest(q), 180);
      if (matchesStainHelpQuery(q)) {
        stainModalTimer = setTimeout(() => {
          const current = input.value.trim();
          if (current !== q || !matchesStainHelpQuery(current)) return;
          hide();
          requestStainHelpModal(current, "typing");
        }, 650);
      }
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

  function bindPrivacyConsent(root) {
    if (!root) return;
    const checkbox = root.querySelector("[data-privacy-consent]");
    const submitBtn = root.querySelector("[data-privacy-submit], button[type='submit']");
    if (!checkbox || !submitBtn) return;

    function sync() {
      submitBtn.disabled = !checkbox.checked;
    }

    checkbox.addEventListener("change", sync);
    root.querySelectorAll("[data-privacy-policy-link]").forEach((link) => {
      link.addEventListener("click", (event) => {
        event.stopPropagation();
      });
    });
    sync();
  }

  document.querySelectorAll("[data-checkout-form], [data-stain-help-form]").forEach(bindPrivacyConsent);

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

  const catalogReturnLanding = finalizeCatalogReturnLanding();
  initCategoryScrollSpy({ skipHashScroll: catalogReturnLanding });
  initCatalogReturnLink();
  if (!catalogReturnLanding) saveCatalogReturnState();
  initProductGallery();

  function initProductGallery() {
    const root = document.querySelector("[data-product-gallery]");
    const lightbox = document.querySelector("[data-gallery-lightbox]");
    const dataEl = document.getElementById("product-gallery-data");
    if (!root || !lightbox || !dataEl) return;

    let raw = [];
    try {
      raw = JSON.parse(dataEl.textContent || "[]");
    } catch (_err) {
      return;
    }
    if (!raw.length) return;

    // Поддержка старого формата ["url", ...] и нового [{preview, full}, ...]
    const images = raw.map((item) => {
      if (item && typeof item === "object") {
        const full = item.full || item.preview || "";
        const preview = item.preview || full;
        return { preview, full };
      }
      const url = String(item || "");
      return { preview: url, full: url };
    }).filter((item) => item.full);

    if (!images.length) return;

    let index = 0;
    const mainImg = root.querySelector("[data-gallery-main-img]");
    const thumbs = Array.from(root.querySelectorAll(".product-gallery__thumb"));
    const lightboxImg = lightbox.querySelector("[data-gallery-lightbox-img]");
    const currentEl = lightbox.querySelector("[data-gallery-current]");
    const fullReady = images.map((item) => item.preview === item.full);
    const fullLoading = images.map(() => false);

    function setImgSrc(img, url) {
      if (!img || !url) return;
      if (img.getAttribute("src") !== url) {
        img.src = url;
      }
    }

    function setActiveThumb(i) {
      thumbs.forEach((thumb, idx) => {
        const active = idx === i;
        thumb.classList.toggle("is-active", active);
        thumb.setAttribute("aria-current", active ? "true" : "false");
      });
    }

    function preloadFull(i) {
      if (i < 0 || i >= images.length) return;
      if (fullReady[i] || fullLoading[i]) return;
      const { preview, full } = images[i];
      if (!full || full === preview) {
        fullReady[i] = true;
        return;
      }
      fullLoading[i] = true;
      const probe = new Image();
      probe.decoding = "async";
      probe.onload = () => {
        fullReady[i] = true;
        fullLoading[i] = false;
        // В галерее на странице превью не трогаем — только lightbox
        if (!lightbox.hidden && index === i) {
          setLightboxSrc(i);
        }
      };
      probe.onerror = () => {
        fullLoading[i] = false;
      };
      probe.src = full;
    }

    function setLightboxSrc(i) {
      if (!lightboxImg) return;
      const { preview, full } = images[i];
      const url = fullReady[i] ? full : preview;
      setImgSrc(lightboxImg, url);
    }

    function show(i) {
      index = (i + images.length) % images.length;
      // На странице товара всегда только превью — без подмены = без моргания
      setImgSrc(mainImg, images[index].preview);
      if (!lightbox.hidden) {
        setLightboxSrc(index);
        preloadFull(index);
      }
      if (currentEl) currentEl.textContent = String(index + 1);
      setActiveThumb(index);
    }

    function open(i) {
      index = (i + images.length) % images.length;
      setActiveThumb(index);
      if (currentEl) currentEl.textContent = String(index + 1);
      setLightboxSrc(index);
      lightbox.hidden = false;
      document.body.style.overflow = "hidden";
      preloadFull(index);
      window.setTimeout(() => {
        preloadFull(index + 1);
        preloadFull(index - 1);
      }, 80);
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

    // Фоновая подгрузка полных только в кэш браузера — DOM галереи не меняем
    const warmCache = () => {
      preloadFull(0);
      images.forEach((_item, i) => {
        if (i === 0) return;
        window.setTimeout(() => preloadFull(i), 400 + i * 250);
      });
    };
    if (typeof window.requestIdleCallback === "function") {
      window.requestIdleCallback(warmCache, { timeout: 1500 });
    } else {
      window.setTimeout(warmCache, 400);
    }
  }

  // Модалка «Что-то не отмывается»
  (function initStainHelpModal() {
    const modal = document.querySelector("[data-stain-help-modal]");
    const form = document.querySelector("[data-stain-help-form]");
    if (!modal || !form) return;

    const statusEl = form.querySelector("[data-stain-help-status]");
    const submitBtn = form.querySelector(".stain-help-form__submit");
    const consentCheckbox = form.querySelector("[data-privacy-consent]");
    const nameInput = form.querySelector("[name='full_name']");
    const phoneInput = form.querySelector("[name='phone']");
    let lastFocus = null;

    function syncConsentSubmit() {
      if (!submitBtn) return;
      submitBtn.disabled = !(consentCheckbox && consentCheckbox.checked);
    }

    function applyPrefill() {
      const name = (form.getAttribute("data-prefill-name") || "").trim();
      const phone = (form.getAttribute("data-prefill-phone") || "").trim();
      if (nameInput && name && !nameInput.value.trim()) {
        nameInput.value = name;
      }
      if (phoneInput && phone) {
        const formatted =
          typeof formatPhoneMask === "function" ? formatPhoneMask(phone) : phone;
        if (!phoneInput.value.trim()) phoneInput.value = formatted;
        else phoneInput.value = formatPhoneMask(phoneInput.value);
      }
    }

    function clearErrors() {
      form.querySelectorAll("[data-error-for]").forEach((el) => {
        el.textContent = "";
        el.hidden = true;
      });
      form.querySelectorAll(".form-input").forEach((input) => {
        input.classList.remove("is-invalid");
      });
      if (statusEl) {
        statusEl.hidden = true;
        statusEl.textContent = "";
        statusEl.classList.remove("is-error", "is-success");
      }
    }

    function showFieldError(name, message) {
      const box = form.querySelector(`[data-error-for="${name}"]`);
      const input = form.querySelector(`[name="${name}"]`);
      if (box) {
        box.textContent = message || "";
        box.hidden = !message;
      }
      if (input) input.classList.toggle("is-invalid", Boolean(message));
    }

    function openModal(options) {
      const opts = options || {};
      lastFocus = document.activeElement;
      clearErrors();
      applyPrefill();
      if (opts.prefillProblem) {
        const problemInput = form.querySelector("[name='problem']");
        if (problemInput) problemInput.value = opts.prefillProblem;
      }
      modal.hidden = false;
      document.body.style.overflow = "hidden";
      const first = form.querySelector("[name='problem']");
      if (first) first.focus();
      if (!opts.fromSearch) markAutoShown();
    }

    function closeModal() {
      modal.hidden = true;
      document.body.style.overflow = "";
      if (lastFocus && typeof lastFocus.focus === "function") lastFocus.focus();
    }

    const AUTO_SHOWN_KEY = "ublegko_stain_help_auto_shown";
    const SEARCH_SHOWN_KEY = "ublegko_stain_help_search_shown";
    const TYPING_BLOCK_KEY = "ublegko_stain_help_typing_block";

    function isTypingModalBlocked() {
      try {
        return sessionStorage.getItem(TYPING_BLOCK_KEY) === "1";
      } catch (err) {
        return false;
      }
    }

    function blockTypingModal() {
      try {
        sessionStorage.setItem(TYPING_BLOCK_KEY, "1");
      } catch (err) {
        /* ignore */
      }
    }

    function markAutoShown() {
      try {
        sessionStorage.setItem(AUTO_SHOWN_KEY, "1");
      } catch (err) {
        /* ignore quota / private mode */
      }
      document.cookie = AUTO_SHOWN_KEY + "=; path=/; max-age=0; SameSite=Lax";
    }

    function wasAutoShown() {
      try {
        return sessionStorage.getItem(AUTO_SHOWN_KEY) === "1";
      } catch (err) {
        return false;
      }
    }

    function wasSearchModalShown(query) {
      try {
        const seen = JSON.parse(sessionStorage.getItem(SEARCH_SHOWN_KEY) || "[]");
        if (!Array.isArray(seen)) return false;
        const key = String(query || "").trim().toLowerCase();
        return seen.includes(key);
      } catch (err) {
        return false;
      }
    }

    function markSearchModalShown(query) {
      const key = String(query || "").trim().toLowerCase();
      if (!key) return;
      try {
        const seen = JSON.parse(sessionStorage.getItem(SEARCH_SHOWN_KEY) || "[]");
        const list = Array.isArray(seen) ? seen : [];
        if (!list.includes(key)) list.push(key);
        sessionStorage.setItem(SEARCH_SHOWN_KEY, JSON.stringify(list.slice(-20)));
      } catch (err) {
        /* ignore */
      }
    }

    function shouldAutoOpen() {
      if (modal.getAttribute("data-stain-help-auto") !== "1") return false;
      if (wasAutoShown()) return false;
      const ua = navigator.userAgent || "";
      if (/bot|crawl|spider|slurp|yandex|google/i.test(ua)) return false;
      return true;
    }

    applyPrefill();

    const searchQuery = (document.body.getAttribute("data-stain-help-search-query") || "").trim();

    document.addEventListener("ublegko:stain-help-open", (event) => {
      const query = String((event.detail && event.detail.query) || "").trim();
      const source = (event.detail && event.detail.source) || "";
      if (!query) return;
      if (source === "typing" && isTypingModalBlocked()) return;
      if (wasSearchModalShown(query)) return;
      if (modal.hidden) {
        openModal({ prefillProblem: query, fromSearch: true });
        markSearchModalShown(query);
        if (source === "typing") blockTypingModal();
      }
    });

    if (searchQuery && !wasSearchModalShown(searchQuery)) {
      window.setTimeout(() => {
        if (modal.hidden) {
          openModal({ prefillProblem: searchQuery, fromSearch: true });
          markSearchModalShown(searchQuery);
        }
      }, 900);
    } else if (shouldAutoOpen()) {
      window.setTimeout(() => {
        if (modal.hidden && shouldAutoOpen()) openModal();
      }, 800);
    }

    document.querySelectorAll("[data-stain-help-open]").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        openModal();
      });
    });

    modal.addEventListener("click", (event) => {
      if (event.target.closest("[data-stain-help-close]")) {
        closeModal();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (modal.hidden) return;
      if (event.key === "Escape") closeModal();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearErrors();

      const problem = (form.querySelector("[name='problem']")?.value || "").trim();
      const fullName = (nameInput?.value || "").trim();
      const phone = phoneInput?.value || "";
      const contactMethod = (form.querySelector("[name='contact_method']")?.value || "").trim();
      let hasError = false;
      if (problem.length < 3) {
        showFieldError("problem", "Опишите, что не отмывается");
        hasError = true;
      }
      if (fullName.length < 2) {
        showFieldError("full_name", "Укажите имя");
        hasError = true;
      }
      if (!isValidRuPhone(phone)) {
        showFieldError("phone", "Укажите телефон в формате +7 (999) 000-00-00");
        hasError = true;
      }
      if (contactMethod.length < 2) {
        showFieldError("contact_method", "Укажите удобный способ связи");
        hasError = true;
      }
      if (!consentCheckbox || !consentCheckbox.checked) {
        hasError = true;
        if (statusEl) {
          statusEl.textContent = "Нужно согласие с политикой конфиденциальности";
          statusEl.classList.add("is-error");
          statusEl.hidden = false;
        }
      }
      if (hasError) {
        if (statusEl && (!statusEl.textContent || statusEl.hidden)) {
          statusEl.textContent = "Проверьте поля и попробуйте ещё раз.";
          statusEl.classList.add("is-error");
          statusEl.hidden = false;
        }
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Отправляем…";
      }

      const csrf =
        form.querySelector("[name=csrfmiddlewaretoken]")?.value ||
        (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] ||
        "";

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            ...(csrf ? { "X-CSRFToken": decodeURIComponent(csrf) } : {}),
          },
          body: new FormData(form),
          credentials: "same-origin",
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.ok) {
          if (data.errors) {
            Object.entries(data.errors).forEach(([field, messages]) => {
              showFieldError(field, Array.isArray(messages) ? messages[0] : String(messages));
            });
          }
          if (statusEl) {
            statusEl.textContent =
              data.error ||
              (response.status === 403
                ? "Сессия устарела — обновите страницу и отправьте снова."
                : "Проверьте поля и попробуйте ещё раз.");
            statusEl.classList.add("is-error");
            statusEl.hidden = false;
          }
          return;
        }

        const savedName = nameInput ? nameInput.value : "";
        const savedPhone = phoneInput ? phoneInput.value : "";
        form.reset();
        applyPrefill();
        syncConsentSubmit();
        if (nameInput && !nameInput.value && savedName) nameInput.value = savedName;
        if (phoneInput && !phoneInput.value && savedPhone) {
          phoneInput.value = formatPhoneMask(savedPhone);
        }
        if (statusEl) {
          statusEl.textContent = data.message || "Спасибо! Мы получили обращение.";
          statusEl.classList.add("is-success");
          statusEl.hidden = false;
        }
        if (typeof showToast === "function") {
          showToast(data.message || "Обращение отправлено");
        }
        window.setTimeout(closeModal, 1600);
      } catch (_err) {
        if (statusEl) {
          statusEl.textContent = "Сеть недоступна. Попробуйте позже или позвоните.";
          statusEl.classList.add("is-error");
          statusEl.hidden = false;
        }
      } finally {
        if (submitBtn) {
          submitBtn.textContent = "Отправить";
          syncConsentSubmit();
        }
      }
    });
  })();

  // Скачивание Excel-каталога: кольцо на кнопке
  (function () {
    const links = document.querySelectorAll("[data-catalog-xlsx-download]");
    if (!links.length) return;

    let busy = false;

    function isMobileUa() {
      return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent || "");
    }

    function filenameFromDisposition(header, fallback) {
      if (!header) return fallback;
      const utf = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header);
      if (utf && utf[1]) {
        try {
          return decodeURIComponent(utf[1].trim().replace(/["']/g, ""));
        } catch (_err) {
          /* ignore */
        }
      }
      const plain = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;]+)/i.exec(header);
      if (plain) {
        return (plain[1] || plain[2] || "").trim().replace(/^["']|["']$/g, "") || fallback;
      }
      return fallback;
    }

    function saveBlob(blob, filename) {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 4000);
    }

    // Android/iOS: blob + <a download> не попадает в системные «Загрузки».
    // iframe: Content-Disposition: attachment + UI/JS не зависают на время генерации.
    function startNativeDownload(url) {
      const iframe = document.createElement("iframe");
      iframe.setAttribute("hidden", "");
      iframe.setAttribute("aria-hidden", "true");
      iframe.style.cssText = "position:fixed;width:0;height:0;border:0;visibility:hidden";
      iframe.src = url;
      document.body.appendChild(iframe);
      window.setTimeout(() => iframe.remove(), 120000);
    }

    function bindProgress(link) {
      const panel = link.querySelector("[data-catalog-xlsx-progress]");
      const ring = link.querySelector("[data-catalog-xlsx-ring]");
      const pctEl = link.querySelector("[data-catalog-xlsx-pct]");
      let rafId = 0;
      let value = 0;
      let downloadStarted = false;
      let fakeActive = false;
      const ringLen = 2 * Math.PI * 15;

      if (ring) {
        ring.style.strokeDasharray = String(ringLen);
        ring.style.strokeDashoffset = String(ringLen);
      }

      function setPercent(percent) {
        value = Math.max(0, Math.min(100, percent));
        const shown = Math.round(value);
        if (pctEl) pctEl.textContent = shown + "%";
        if (ring) {
          ring.style.strokeDasharray = String(ringLen);
          ring.style.strokeDashoffset = String(ringLen * (1 - value / 100));
        }
      }

      function stopFake() {
        fakeActive = false;
        if (rafId) {
          window.cancelAnimationFrame(rafId);
          rafId = 0;
        }
      }

      function startFake() {
        stopFake();
        downloadStarted = false;
        fakeActive = true;
        value = 0;
        setPercent(0);
        let last = performance.now();

        function tick(now) {
          if (!fakeActive || downloadStarted) return;
          const dt = Math.min(100, now - last);
          last = now;
          const step =
            value < 50 ? 0.045 * dt : value < 80 ? 0.022 * dt : 0.006 * dt;
          setPercent(Math.min(92, value + step));
          rafId = window.requestAnimationFrame(tick);
        }
        rafId = window.requestAnimationFrame(tick);
      }

      function show() {
        link.classList.add("is-busy");
        if (panel) {
          panel.hidden = false;
          panel.setAttribute("aria-hidden", "false");
        }
        startFake();
      }

      function hide() {
        stopFake();
        downloadStarted = false;
        setPercent(0);
        link.classList.remove("is-busy");
        if (panel) {
          panel.hidden = true;
          panel.setAttribute("aria-hidden", "true");
        }
      }

      return {
        show,
        hide,
        setPercent,
        markDownload(pct) {
          downloadStarted = true;
          stopFake();
          setPercent(Math.max(value, pct));
        },
      };
    }

    links.forEach((link) => {
      const progress = bindProgress(link);

      link.addEventListener("click", (event) => {
        event.preventDefault();
        if (busy) return;

        const url = link.getAttribute("href");
        if (!url) return;

        busy = true;
        progress.show();

        // Телефон: сначала кольцо (отрисовать кадр), потом системная загрузка в iframe —
        // иначе генерация Excel блокирует UI и проценты стартуют уже после файла.
        if (isMobileUa()) {
          const panel = link.querySelector("[data-catalog-xlsx-progress]");
          if (panel) void panel.offsetWidth;
          window.requestAnimationFrame(() => {
            startNativeDownload(url);
          });
          window.setTimeout(() => {
            progress.markDownload(100);
            progress.setPercent(100);
          }, 8500);
          window.setTimeout(() => {
            progress.hide();
            busy = false;
          }, 9000);
          return;
        }

        const fallbackName = "Прайс магазина Убираемся легко.xlsx";
        const xhr = new XMLHttpRequest();
        xhr.open("GET", url);
        xhr.responseType = "blob";
        xhr.onprogress = (e) => {
          if (!e.lengthComputable || e.total <= 0) return;
          const pct = Math.round((e.loaded / e.total) * 100);
          progress.markDownload(pct);
        };
        xhr.onload = () => {
          if (xhr.status < 200 || xhr.status >= 300) {
            progress.hide();
            busy = false;
            showToast("Не удалось сформировать каталог. Попробуйте ещё раз.");
            return;
          }
          progress.markDownload(100);
          progress.setPercent(100);
          const name = filenameFromDisposition(
            xhr.getResponseHeader("Content-Disposition"),
            fallbackName
          );
          saveBlob(xhr.response, name);
          window.setTimeout(() => {
            progress.hide();
            busy = false;
          }, 420);
        };
        xhr.onerror = () => {
          progress.hide();
          busy = false;
          showToast("Ошибка сети при скачивании каталога");
        };
        xhr.send();
      });
    });
  })();
})();
