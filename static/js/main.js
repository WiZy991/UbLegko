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

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-menu-toggle], #menu-toggle");
    if (!toggle) return;
    const sidebar = document.querySelector("[data-sidebar], #sidebar");
    if (!sidebar) return;
    const open = sidebar.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });

  function syncStickyHeaderHeight() {
    const sticky = document.querySelector(".header-sticky");
    if (!sticky) return;
    const height = Math.ceil(sticky.getBoundingClientRect().height);
    document.documentElement.style.setProperty("--header-sticky-height", `${height}px`);
  }
  syncStickyHeaderHeight();
  window.addEventListener("resize", syncStickyHeaderHeight);
  window.addEventListener("load", syncStickyHeaderHeight);
  if (typeof ResizeObserver !== "undefined") {
    const sticky = document.querySelector(".header-sticky");
    if (sticky) new ResizeObserver(syncStickyHeaderHeight).observe(sticky);
  }

  document.addEventListener("click", (event) => {
    const minus = event.target.closest("[data-qty-minus]");
    const plus = event.target.closest("[data-qty-plus]");
    if (!minus && !plus) return;
    const group = event.target.closest("[data-qty-group]");
    if (!group) return;
    const input = group.querySelector("input");
    if (!input) return;
    const current = parseInt(input.value || "1", 10) || 1;
    input.value = String(minus ? Math.max(1, current - 1) : Math.max(1, current + 1));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });

  const cartQtyState = new WeakMap();

  async function submitCartQty(form, input) {
    const state = cartQtyState.get(input) || { lastSent: input.defaultValue || input.value, inflight: null };
    cartQtyState.set(input, state);
    const value = Math.max(1, parseInt(input.value || "1", 10) || 1);
    input.value = String(value);
    if (String(value) === String(state.lastSent)) return;
    state.lastSent = String(value);

    const formData = new FormData(form);
    try {
      if (state.inflight) state.inflight.abort();
      state.inflight = new AbortController();
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        signal: state.inflight.signal,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });
      const data = await response.json();
      if (!data.ok) {
        form.submit();
        return;
      }
      const row = form.closest("tr");
      const lineTotal = row ? row.querySelector("[data-cart-line-total]") : null;
      if (lineTotal && data.line_total !== undefined) {
        lineTotal.textContent = `${data.line_total} руб`;
      }
      const pageTotal = document.querySelector("[data-cart-page-total]");
      if (pageTotal && data.cart_total !== undefined) {
        pageTotal.textContent = `Итого: ${data.cart_total} руб`;
      }
      const headerTotal = document.querySelector("[data-cart-total]");
      if (headerTotal && data.cart_total !== undefined) {
        headerTotal.textContent = `${data.cart_total} руб`;
      }
      if (data.removed && row) {
        row.remove();
      }
    } catch (err) {
      if (err && err.name === "AbortError") return;
      form.submit();
    }
  }

  document.addEventListener("change", (event) => {
    const input = event.target.closest('[data-cart-qty-form] input[name="quantity"]');
    if (!input) return;
    const form = input.closest("[data-cart-qty-form]");
    if (form) submitCartQty(form, input);
  });

  document.addEventListener("input", (event) => {
    const input = event.target.closest('[data-cart-qty-form] input[name="quantity"]');
    if (!input) return;
    const form = input.closest("[data-cart-qty-form]");
    if (!form) return;
    const state = cartQtyState.get(input) || { lastSent: input.value, timer: null };
    cartQtyState.set(input, state);
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
        const totalEl = document.querySelector("[data-cart-total]");
        if (totalEl && data.cart_total !== undefined) {
          totalEl.textContent = `${data.cart_total} руб`;
        }
        showToast(data.message || "Добавлено в корзину");
      }
    } catch (err) {
      form.submit();
    }
  });

  let catalogAbort = null;
  async function loadCatalog(url, push) {
    const root = document.querySelector("[data-catalog-root]");
    if (!root) {
      window.location.href = url;
      return;
    }
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
      if (push) history.pushState({ catalogAjax: true }, "", url);
      syncStickyHeaderHeight();
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
      const q = (query || "").trim().toLowerCase();
      let visible = 0;
      list.querySelectorAll("[data-city-filter]").forEach((btn) => {
        const match = !q || btn.dataset.cityFilter.includes(q);
        btn.parentElement.hidden = !match;
        if (match) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
    }

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      if (citySelector.classList.contains("is-open")) closeCity();
      else openCity();
    });

    search.addEventListener("input", () => filterCities(search.value));

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
          label.textContent = data.city;
          list.querySelectorAll(".city-selector__item").forEach((item) => {
            item.classList.toggle("is-active", item.dataset.cityId === String(data.id));
          });
          closeCity();
          showToast(`Выбран город: ${data.city}`);
        }
      } catch (err) {
        form.submit();
      }
    });

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
        const btn = form.querySelector(".btn-fav, .btn-heart");
        if (btn) {
          btn.classList.toggle("is-active", data.active);
          const onLabel = btn.dataset.favLabelOn || "Убрать из избранного";
          const offLabel = btn.dataset.favLabelOff || "В избранное";
          btn.textContent = data.active ? onLabel : offLabel;
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

  // Автоподсказки поиска по началу названия (RU/EN)
  document.querySelectorAll("[data-search-form]").forEach((form) => {
    const input = form.querySelector("[data-search-input]");
    const box = form.querySelector("[data-search-suggest]");
    const url = form.getAttribute("data-suggest-url");
    if (!input || !box || !url) return;

    let timer = null;
    let activeIndex = -1;
    let items = [];
    let lastQuery = "";

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

    function escapeHtml(text) {
      return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
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

    input.addEventListener("input", () => {
      const q = input.value.trim();
      clearTimeout(timer);
      if (!q) {
        hide();
        return;
      }
      timer = setTimeout(() => fetchSuggest(q), 180);
    });

    input.addEventListener("keydown", (event) => {
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
      } else if (event.key === "Escape") {
        hide();
      }
    });

    input.addEventListener("blur", () => {
      setTimeout(hide, 150);
    });

    document.addEventListener("click", (event) => {
      if (!form.contains(event.target)) hide();
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
})();
