/* Perilaku umum aplikasi (progressive enhancement - semua aksi tetap jalan tanpa JS):
   - form / tombol dengan data-confirm="..." meminta konfirmasi lewat dialog sebelum dikirim
   - bilah muat di atas halaman saat permintaan HTMX berjalan; pesan jelas bila server / jaringan gagal
   - sidebar dapat diciutkan (diingat per peramban); Ctrl+K atau "/" membuka pencarian global */
(function () {
  const dialog = () => document.getElementById("confirm-dialog");

  function ask(message) {
    const d = dialog();
    if (!d || typeof d.showModal !== "function") return Promise.resolve(window.confirm(message));
    d.querySelector(".confirm-text").textContent = message;
    d.returnValue = "";
    d.showModal();
    return new Promise((resolve) => d.addEventListener("close", () => resolve(d.returnValue === "ok"), { once: true }));
  }

  document.addEventListener("submit", (e) => {
    const form = e.target;
    const msg = (e.submitter && e.submitter.dataset.confirm) || form.dataset.confirm;
    if (!msg || form.dataset.confirmed === "1") return;
    e.preventDefault();
    ask(msg).then((ok) => {
      if (!ok) return;
      form.dataset.confirmed = "1";
      if (e.submitter && e.submitter.name) {
        const hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = e.submitter.name;
        hidden.value = e.submitter.value;
        form.appendChild(hidden);
      }
      form.requestSubmit ? form.requestSubmit() : form.submit();
    });
  });

  const ICONS = { success: "circle-check", error: "alert-circle", warning: "alert-triangle", info: "info-circle" };

  function toast(text, kind) {
    const box = document.getElementById("toasts");
    if (!box) return;
    kind = ICONS[kind] ? kind : "error";
    const el = document.createElement("div");
    el.className = "toast toast-" + kind;
    el.setAttribute("role", "status");
    const icon = document.createElement("i");
    icon.className = "ti ti-" + ICONS[kind];
    icon.setAttribute("aria-hidden", "true");
    const span = document.createElement("span");
    span.className = "flex-1";
    span.textContent = text;
    el.append(icon, span);
    box.appendChild(el);
    setTimeout(() => el.remove(), 7000);
  }

  function toggleSidebar() {
    const collapsed = document.documentElement.classList.toggle("sb-collapsed");
    try { localStorage.setItem("spi.sidebar", collapsed ? "collapsed" : "expanded"); } catch (e) { /* mode privat: tidak diingat */ }
  }

  window.SPIToast = toast;
  window.SPI = { toast, toggleSidebar };

  /* Pencarian global: Ctrl/Cmd+K atau "/" (di luar kolom isian); panah atas/bawah menelusuri hasil */
  document.addEventListener("keydown", (e) => {
    const input = document.querySelector("[data-global-search]");
    if (!input) return;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if (((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") || (e.key === "/" && !typing)) {
      e.preventDefault();
      if (input.offsetParent === null) {
        const opener = document.querySelector("[aria-label='Cari']");
        if (opener) opener.click();
      }
      input.focus();
      input.select();
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    const hits = Array.from(document.querySelectorAll("#search-results .search-hit"));
    if (!hits.length || !(document.activeElement === input || hits.includes(document.activeElement))) return;
    e.preventDefault();
    const i = hits.indexOf(document.activeElement);
    const next = e.key === "ArrowDown" ? (i + 1) % hits.length : i <= 0 ? -1 : i - 1;
    (next < 0 ? input : hits[next]).focus();
  });

  /* Menu <details data-menu>: tutup bila klik di luar / Esc, dan hanya satu yang terbuka */
  document.addEventListener("click", (e) => {
    document.querySelectorAll("details[data-menu][open]").forEach((d) => { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") document.querySelectorAll("details[data-menu][open]").forEach((d) => d.removeAttribute("open"));
  });

  let pending = 0;
  const bar = () => document.getElementById("loading-bar");
  document.addEventListener("htmx:beforeRequest", () => {
    pending++;
    if (bar()) bar().classList.add("is-active");
  });
  document.addEventListener("htmx:afterRequest", () => {
    pending = Math.max(0, pending - 1);
    if (!pending && bar()) bar().classList.remove("is-active");
  });
  document.addEventListener("htmx:responseError", (e) => {
    const s = e.detail.xhr.status;
    toast(s === 403 ? "Anda tidak punya izin untuk aksi ini." : "Gagal memuat (kode " + s + "). Coba lagi.", "error");
  });
  document.addEventListener("htmx:sendError", () => toast("Tidak tersambung ke server. Periksa jaringan lalu coba lagi.", "error"));
})();
