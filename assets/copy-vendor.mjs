import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync("static/vendor", { recursive: true });
copyFileSync("node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js");
copyFileSync("node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js");
console.log("vendor: htmx, alpine disalin ke static/vendor");
