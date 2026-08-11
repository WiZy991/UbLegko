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

  function syncStickyHeaderHeight() {
    const sticky = document.querySelector(".header-sticky");
    const catalogNav = document.querySelector("[data-catalog-nav-shell]");
    const toolbar = document.querySelector("[data-catalog-toolbar]");
    const headerH = sticky ? Math.round(sticky.getBoundingClientRect().height) : 0;
    const isMobile = window.matchMedia("(max-width: 900px)").matches;
    const navH = isMobile && catalogNav ? Math.round(catalogNav.getBoundingClientRect().height) : 0;
    const toolbarH = toolbar ? Math.round(toolbar.getBoundingClientRect().height) : 0;
    // -2px: следующий sticky наезжает на предыдущий, закрывая субпиксельный просвет
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

  function setCatalogNavOpen(open) {
    const toggle = document.querySelector("[data-menu-toggle], #menu-toggle");
    const sidebar = document.querySelector("[data-sidebar], #sidebar");
    if (!toggle || !sidebar) return;
    const wasOpen = sidebar.classList.contains("is-open");
    if (wasOpen === open) return;
    sidebar.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    syncStickyHeaderHeight();
  }

  function initMobileCatalogNavCollapse() {
    const shell = document.querySelector("[data-catalog-nav-shell]");
    const anchor = document.querySelector("[data-catalog-nav-anchor]");
    const toggle = document.querySelector("[data-menu-toggle], #menu-toggle");
    const sidebar = document.querySelector("[data-sidebar], #sidebar");
    if (!shell || !toggle || !sidebar) return;

    let lastY = window.scrollY || 0;
    let ignoreScrollUntil = 0;
    let userHoldOpen = false;

    const bumpIgnore = (ms = 400) => {
      ignoreScrollUntil = Date.now() + ms;
    };

    const isMobile = () => window.matchMedia("(max-width: 900px)").matches;

    const isStuckUnderHeader = () => {
      const header = document.querySelector(".header-sticky");
      if (!header) return window.scrollY > 8;
      const stickyLine = header.getBoundingClientRect().bottom - 2;
      if (anchor) {
        return anchor.getBoundingClientRect().bottom <= stickyLine + 1;
      }
      return shell.getBoundingClientRect().top <= stickyLine + 1;
    };

    const applyStickyState = () => {
      if (!isMobile()) {
        userHoldOpen = false;
        setCatalogNavOpen(true);
        return;
      }
      if (Date.now() < ignoreScrollUntil) return;

      const stuck = isStuckUnderHeader();
      if (!stuck) {
        userHoldOpen = false;
        setCatalogNavOpen(true);
        return;
      }
      if (!userHoldOpen) {
        setCatalogNavOpen(false);
      }
    };

    toggle.addEventListener("click", () => {
      bumpIgnore(500);
      requestAnimationFrame(() => {
        userHoldOpen = sidebar.classList.contains("is-open") && isStuckUnderHeader();
      });
    });

    // Простой свайп без follow-finger (без лагов): вниз — открыть, вверх — закрыть
    let drag = null;
    const SWIPE_MIN = 24;

    const onTouchStart = (event) => {
      if (!isMobile() || event.touches.length !== 1) return;
      const t = event.touches[0];
      drag = {
        id: t.identifier,
        x: t.clientX,
        y: t.clientY,
        locked: false,
      };
    };

    const onTouchMove = (event) => {
      if (!drag || event.touches.length !== 1) return;
      const t = event.touches[0];
      if (t.identifier !== drag.id) return;
      const dy = t.clientY - drag.y;
      const dx = t.clientX - drag.x;
      if (!drag.locked && Math.abs(dy) > 8 && Math.abs(dy) > Math.abs(dx)) {
        drag.locked = true;
      }
      if (drag.locked && event.cancelable) {
        event.preventDefault();
      }
    };

    const onTouchEnd = (event) => {
      if (!drag) return;
      const t = event.changedTouches[0];
      if (!t || t.identifier !== drag.id) {
        drag = null;
        return;
      }
      const dy = t.clientY - drag.y;
      const dx = t.clientX - drag.x;
      const locked = drag.locked;
      drag = null;
      if (!locked || Math.abs(dy) < SWIPE_MIN || Math.abs(dy) < Math.abs(dx)) return;

      suppressMenuToggleClick = true;
      bumpIgnore(600);
      if (dy > 0) {
        userHoldOpen = isStuckUnderHeader();
        setCatalogNavOpen(true);
      } else {
        userHoldOpen = false;
        setCatalogNavOpen(false);
      }
    };

    toggle.addEventListener("touchstart", onTouchStart, { passive: true });
    toggle.addEventListener("touchmove", onTouchMove, { passive: false });
    toggle.addEventListener("touchend", onTouchEnd);
    toggle.addEventListener("touchcancel", () => {
      drag = null;
    });

    shell.addEventListener(
      "touchstart",
      (event) => {
        if (!isMobile() || toggle.getAttribute("aria-expanded") !== "false") return;
        if (event.target.closest("a, button, input, select, textarea")) return;
        onTouchStart(event);
      },
      { passive: true }
    );
    shell.addEventListener("touchmove", onTouchMove, { passive: false });
    shell.addEventListener("touchend", onTouchEnd);
    shell.addEventListener("touchcancel", () => {
      drag = null;
    });

    sidebar.addEventListener("click", (event) => {
      if (!isMobile()) return;
      const link = event.target.closest("a");
      if (!link) return;
      if (link.hasAttribute("data-scroll-spy-link")) return;
      userHoldOpen = false;
      setCatalogNavOpen(false);
    });

    window.addEventListener(
      "scroll",
      () => {
        if (!isMobile()) {
          userHoldOpen = false;
          setCatalogNavOpen(true);
          lastY = window.scrollY || 0;
          return;
        }
        if (Date.now() < ignoreScrollUntil) {
          lastY = window.scrollY || 0;
          return;
        }

        const y = window.scrollY || 0;
        const stuck = isStuckUnderHeader();

        if (!stuck) {
          userHoldOpen = false;
          setCatalogNavOpen(true);
        } else if (userHoldOpen && y > lastY + 8) {
          userHoldOpen = false;
          setCatalogNavOpen(false);
        } else if (!userHoldOpen) {
          setCatalogNavOpen(false);
        }

        lastY = y;
      },
      { passive: true }
    );

    window.addEventListener("resize", applyStickyState);
    applyStickyState();
  }
  initMobileCatalogNavCollapse();

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
    const active = document.querySelector("[data-scroll-spy-link].is-active");
    if (active) {
      return active.getAttribute("data-scroll-spy-link");
    }
    if (location.hash && location.hash.startsWith("#category-")) {
      return location.hash.slice(1);
    }
    // Fallback: какая секция сейчас под шапкой
    const sections = Array.from(document.querySelectorAll("[data-category-section]"));
    if (!sections.length) return null;
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
    return currentId;
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
    let bottom = 0;
    if (sticky) {
      bottom = Math.max(bottom, sticky.getBoundingClientRect().bottom);
    }
    if (nav && window.matchMedia("(max-width: 900px)").matches) {
      bottom = Math.max(bottom, nav.getBoundingClientRect().bottom);
    }
    if (toolbar) {
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
    const offset = stickyStackBottomPx() + 12;
    const top = target.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: Math.max(0, top), behavior });
  }

  function restoreScrollAfterCatalogFilter(categoryId, prevScrollY) {
    categorySpyLockUntil = Date.now() + 900;
    const target = categoryId ? document.getElementById(categoryId) : null;
    if (target) {
      scrollToCategorySection(target, { behavior: "auto" });
      const url = new URL(window.location.href);
      url.hash = categoryId;
      history.replaceState({ catalogAjax: true }, "", `${url.pathname}${url.search}${url.hash}`);
      return true;
    }
    // Не прыгаем вверх к шапке — оставляем позицию, только не даём уехать за низ страницы
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    window.scrollTo({ top: Math.min(prevScrollY, maxY), behavior: "auto" });
    if (location.hash) {
      const url = new URL(window.location.href);
      url.hash = "";
      history.replaceState({ catalogAjax: true }, "", `${url.pathname}${url.search}`);
    }
    return false;
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
        link.classList.toggle("is-active", Boolean(id) && link.getAttribute("data-scroll-spy-link") === id);
      });
      if (homeLink) homeLink.classList.toggle("is-active", !id);
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

    links.forEach((link) => {
      if (link.dataset.scrollBound === "1") return;
      link.dataset.scrollBound = "1";
      link.addEventListener("click", (event) => {
        const id = link.getAttribute("data-scroll-spy-link");
        const target = id ? document.getElementById(id) : null;
        if (!target) return;
        event.preventDefault();
        categorySpyLockUntil = Date.now() + 1200;
        setActive(id);
        // Сначала сворачиваем категории, ждём пересчёт sticky-высот, потом скроллим
        if (window.matchMedia("(max-width: 900px)").matches) {
          setCatalogNavOpen(false);
        }
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            scrollToCategorySection(target, { behavior: "smooth" });
            history.replaceState(null, "", `#${id}`);
          });
        });
      });
    });

    if (!options.skipHashScroll && location.hash) {
      const id = location.hash.slice(1);
      const target = document.getElementById(id);
      if (target) {
        categorySpyLockUntil = Date.now() + 1200;
        setTimeout(() => {
          if (window.matchMedia("(max-width: 900px)").matches) {
            setCatalogNavOpen(false);
          }
          requestAnimationFrame(() => {
            scrollToCategorySection(target, { behavior: "smooth" });
            setActive(id);
          });
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
      root.replaceWith(next);
      const title = doc.querySelector("title");
      if (title) document.title = title.textContent;
      const nextUrl = new URL(url, window.location.origin);
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

      const enteredCategoryPage =
        nextUrl.pathname.includes("/category/") && !prevPath.includes("/category/");
      if (enteredCategoryPage) {
        categorySpyLockUntil = Date.now() + 900;
        window.scrollTo({ top: 0, behavior: "auto" });
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
    if (link.getAttribute("aria-hidden") === "true" || link.classList.contains("is-hidden")) return;
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
