// Build a single self-contained HTML file (works from file:// and as a shareable artifact).
//   node tools/bundle.mjs  -> dist/model-detector.html
import fs from "node:fs";
const read = (p) => fs.readFileSync(p, "utf8");
const strip = (src) => src.replace(/^\s*import\s[^;]*;\s*$/gm, "").replace(/^\s*export\s+default\s+/gm, "const __default = ").replace(/^\s*export\s+(const|function|let|class)\s+/gm, "$1 ");
let reference = strip(read("docs/reference.js"));
let engine = strip(read("docs/engine.js"));
let model = read("docs/model.js").replace(/^\/\/.*\n/, "").replace(/^export default\s+/, "const MODEL = ");
let app = strip(read("docs/app.js")).replace(/const MODEL = __default;?/, "");
const css = read("docs/styles.css");
let html = read("docs/index.html");
// replacer functions: the code contains "$&" and "${...}", which String.replace would otherwise interpret
html = html.replace(/<link rel="stylesheet" href="styles.css"\s*\/?>/, () => `<style>\n${css}\n</style>`);
html = html.replace(/<script type="module" src="app.js"><\/script>/, () => `<script>\n${reference}\n${engine}\n${model}\n${app}\n</script>`);
fs.mkdirSync("dist", { recursive: true });
fs.writeFileSync("dist/model-detector.html", html);
console.log(`wrote dist/model-detector.html (${(html.length / 1024).toFixed(0)} kB)`);
