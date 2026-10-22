// Where the mock windows put their buttons: every [data-t] element of hf/index.html, in desktop px → hf/targets.json.
// build.py runs this between its two passes, so the cursor lands on the real layout.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");
const HERE = path.dirname(fileURLToPath(import.meta.url));
const CHROME = `${process.env.HOME}/.cache/hyperframes/chrome/chrome-headless-shell/mac_arm-152.0.7977.30/chrome-headless-shell-mac-arm64/chrome-headless-shell`;

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--hide-scrollbars", "--allow-file-access-from-files"] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080 });
await page.goto("file://" + path.join(HERE, "hf", "index.html"), { waitUntil: "networkidle0", timeout: 60000 });
await page.evaluate(() => document.fonts.ready);
const out = await page.evaluate(() => {
  const d = document.getElementById("desk").getBoundingClientRect(), o = {};
  for (const el of document.querySelectorAll("[data-t]")) {
    const r = el.getBoundingClientRect();
    o[el.dataset.t] = [r.x - d.x, r.y - d.y, r.width, r.height].map((v) => Math.round(v * 10) / 10);
  }
  return o;
});
fs.writeFileSync(path.join(HERE, "hf", "targets.json"), JSON.stringify(out, null, 1));
await browser.close();
