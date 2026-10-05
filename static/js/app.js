/* Perilaku umum aplikasi (progressive enhancement - semua aksi tetap jalan tanpa JS):
   - form / tombol dengan data-confirm="..." meminta konfirmasi lewat dialog sebelum dikirim
   - bilah muat di atas halaman saat permintaan HTMX berjalan; pesan jelas bila server / jaringan gagal */
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

  function toast(text, kind) {
    const box = document.getElementById("toasts");
    if (!box) return;
    const el = document.createElement("div");
    el.className = "toast toast-" + (kind || "error");
    el.setAttribute("role", "status");
    el.textContent = text;
    box.appendChild(el);
    setTimeout(() => el.remove(), 8000);
  }
  window.SPIToast = toast;

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
