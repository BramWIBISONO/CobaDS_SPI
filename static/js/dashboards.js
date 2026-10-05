/* Grafik dasbor SPI: membaca spesifikasi JSON dari templat (components/chart_card.html) dan menggambar dengan Chart.js.
   Batang tipis berujung bulat 4px, garis 2px, grid samar, tooltip angka Indonesia; klik batang = tautan saringan di tabel. */
(function () {
  const fmt = new Intl.NumberFormat("id-ID");
  const ink = "#475569", grid = "#e2e8f0";
  const charts = new WeakMap();

  function config(spec) {
    const money = (v) => (spec.money ? "Rp " : "") + fmt.format(v);
    const line = spec.type === "line";
    const datasets = spec.series.map((s) => ({
      label: s.label, data: s.data, borderColor: s.color, backgroundColor: line ? s.color : s.color,
      borderWidth: line ? 2 : 0, borderRadius: line ? 0 : 4, borderSkipped: line ? undefined : "start",
      maxBarThickness: 28, pointRadius: line ? 2 : 0, pointHoverRadius: 5, tension: 0.25,
    }));
    const valueAxis = { beginAtZero: true, stacked: spec.stacked, grid: { color: grid }, border: { display: false },
                        ticks: { color: ink, callback: (v) => (spec.money ? fmt.format(v / 1e6) + " jt" : fmt.format(v)) } };
    const catAxis = { stacked: spec.stacked, grid: { display: false }, ticks: { color: ink, autoSkip: true, maxRotation: 0 } };
    return {
      type: line ? "line" : "bar",
      data: { labels: spec.labels, datasets },
      options: {
        responsive: true, maintainAspectRatio: false, indexAxis: spec.horizontal ? "y" : "x",
        animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 200 },
        interaction: line ? { mode: "index", intersect: false } : { mode: "nearest", intersect: true },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${money(c.parsed[spec.horizontal ? "x" : "y"])}` } },
        },
        scales: spec.horizontal ? { x: valueAxis, y: catAxis } : { x: catAxis, y: valueAxis },
        onHover: (e, els) => { e.native.target.style.cursor = els.length && spec.links && spec.links[els[0].index] ? "pointer" : "default"; },
        onClick: (e, els) => {
          if (!els.length || !spec.links || !spec.links[els[0].index]) return;
          const a = document.querySelector(`[data-chart-link="${spec.id}"][data-i="${els[0].index}"]`);
          if (a) a.click();
        },
      },
    };
  }

  function init(root) {
    if (!window.Chart) return;
    Chart.defaults.font.family = '"Plus Jakarta Sans", ui-sans-serif, system-ui, sans-serif';
    (root || document).querySelectorAll("canvas[data-chart]").forEach((canvas) => {
      const el = document.getElementById(canvas.dataset.chart);
      if (!el) return;
      if (charts.has(canvas)) charts.get(canvas).destroy();
      charts.set(canvas, new Chart(canvas, config(JSON.parse(el.textContent))));
    });
  }

  window.SPICharts = { init };
  document.addEventListener("DOMContentLoaded", () => init(document));
  document.addEventListener("htmx:afterSettle", (e) => init(e.detail.target));
})();
