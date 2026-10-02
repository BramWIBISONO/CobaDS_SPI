import { copyFileSync, existsSync, mkdirSync } from "node:fs";

mkdirSync("static/vendor/fonts", { recursive: true });
mkdirSync("static/vendor/tabler", { recursive: true });
copyFileSync("node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js");
copyFileSync("node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js");
const chart = ["node_modules/chart.js/dist/chart.umd.min.js", "node_modules/chart.js/dist/chart.umd.js"].find(existsSync);
copyFileSync(chart, "static/vendor/chart.umd.min.js");
for (const w of [400, 500, 600, 700, 800]) {
  const f = `plus-jakarta-sans-latin-${w}-normal.woff2`;
  copyFileSync(`node_modules/@fontsource/plus-jakarta-sans/files/${f}`, `static/vendor/fonts/${f}`);
}
copyFileSync("node_modules/@tabler/icons-webfont/dist/tabler-icons.min.css", "static/vendor/tabler/tabler-icons.min.css");
mkdirSync("static/vendor/tabler/fonts", { recursive: true });
for (const f of ["tabler-icons.woff2", "tabler-icons.woff"]) {   // hanya bobot biasa; svg/ttf & varian 200/300/filled tidak dipakai
  copyFileSync(`node_modules/@tabler/icons-webfont/dist/fonts/${f}`, `static/vendor/tabler/fonts/${f}`);
}
console.log("vendor: htmx, alpine, chart.js, Plus Jakarta Sans, Tabler Icons disalin ke static/vendor");
