(function () {
  const table = document.getElementById("result_list");
  if (!table) return;
  const tbody = table.tBodies[0];
  if (!tbody) return;

  const url = window.CATEGORY_REORDER_URL;
  if (!url) return;

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function showToast(message) {
    let toast = document.querySelector(".category-sortable-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "category-sortable-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("is-visible");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => toast.classList.remove("is-visible"), 1800);
  }

  function rowId(row) {
    const input = row.querySelector('input.action-select[type="checkbox"]');
    if (input && input.value) return input.value;
    const match = (row.id || "").match(/result_(\d+)/);
    return match ? match[1] : null;
  }

  let dragRow = null;
  let saveTimer = null;

  async function saveOrder() {
    const order = Array.from(tbody.rows).map(rowId).filter(Boolean);
    if (!order.length) return;
    try {
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ order }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        showToast("Не удалось сохранить порядок");
        window.location.reload();
        return;
      }
      showToast("Порядок категорий сохранён");
    } catch (_err) {
      showToast("Ошибка сохранения порядка");
      window.location.reload();
    }
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveOrder, 150);
  }

  Array.from(tbody.rows).forEach((row) => {
    row.classList.add("category-row");
    const handle = row.querySelector(".category-drag-handle");
    if (!handle) return;

    handle.addEventListener("mousedown", () => {
      row.draggable = true;
    });
    document.addEventListener("mouseup", () => {
      row.draggable = false;
    });

    row.addEventListener("dragstart", (event) => {
      if (!row.draggable) {
        event.preventDefault();
        return;
      }
      dragRow = row;
      row.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      try {
        event.dataTransfer.setData("text/plain", rowId(row) || "");
      } catch (_err) {
        /* ignore */
      }
    });

    row.addEventListener("dragend", () => {
      row.classList.remove("is-dragging");
      row.draggable = false;
      Array.from(tbody.rows).forEach((r) => r.classList.remove("drag-over"));
      if (dragRow) {
        dragRow = null;
        scheduleSave();
      }
    });

    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      if (!dragRow || dragRow === row) return;
      const rect = row.getBoundingClientRect();
      const before = event.clientY < rect.top + rect.height / 2;
      tbody.insertBefore(dragRow, before ? row : row.nextSibling);
    });

    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
    });
  });
})();
