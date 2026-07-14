#!/usr/bin/env node

import { readdir } from "node:fs/promises";
import { resolve } from "node:path";

const [endpoint = "http://127.0.0.1:9223", siteRoot = "http://127.0.0.1:8765"] = process.argv.slice(2);
const repoRoot = resolve(import.meta.dirname, "..");
const articleSets = [
  ["en", "blog/articles"],
  ["ko", "blog/ko/articles"],
];

const version = await fetch(`${endpoint}/json/version`).then((response) => response.json());
const socket = new WebSocket(version.webSocketDebuggerUrl);
const pending = new Map();
const listeners = new Map();
let nextId = 1;

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve: done, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else done(message.result);
    return;
  }
  const key = `${message.sessionId || "browser"}:${message.method}`;
  const queue = listeners.get(key);
  if (queue?.length) queue.shift()(message.params);
});

await new Promise((done, reject) => {
  socket.addEventListener("open", done, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

function send(method, params = {}, sessionId) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  return new Promise((done, reject) => pending.set(id, { resolve: done, reject }));
}

function once(method, sessionId) {
  const key = `${sessionId || "browser"}:${method}`;
  return new Promise((done) => {
    const queue = listeners.get(key) || [];
    queue.push(done);
    listeners.set(key, queue);
  });
}

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send("Network.enable", {}, sessionId);
await send("Network.setCacheDisabled", { cacheDisabled: true }, sessionId);

async function inspect(urlPath, width, height) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width < 700 }, sessionId);
  const loaded = once("Page.loadEventFired", sessionId);
  await send("Page.navigate", { url: `${siteRoot}/${urlPath}` }, sessionId);
  await loaded;
  const result = await send("Runtime.evaluate", {
    expression: `(() => {
      const body = document.querySelector('.article-body');
      if (!body) return { missingBody: true };
      const bodyRect = body.getBoundingClientRect();
      const aligned = Array.from(body.querySelectorAll(':scope > p, :scope > h2, :scope > h3, :scope > ul, :scope > ol, :scope > blockquote, :scope > pre, :scope > figure, :scope > .tbl-wrap, :scope > .field-note, :scope > .beginner-example, :scope > .fab-voice, :scope > .field-story, :scope > .reader-shortcut, :scope > .deck-link, :scope > .author-card, :scope > .share, :scope > .related, :scope > .prose-block'));
      const mismatches = aligned
        .filter((item) => {
          const style = getComputedStyle(item);
          return style.display !== 'none' && item.getBoundingClientRect().height > 0;
        })
        .map((item) => ({
          tag: item.tagName.toLowerCase(),
          cls: item.className || '',
          width: Math.round(item.getBoundingClientRect().width * 10) / 10,
          delta: Math.round(Math.abs(item.getBoundingClientRect().width - bodyRect.width) * 10) / 10,
        }))
        .filter((item) => item.delta > 2);
      return {
        missingBody: false,
        bodyWidth: Math.round(bodyRect.width * 10) / 10,
        viewportWidth: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        mismatches,
      };
    })()`,
    returnByValue: true,
  }, sessionId);
  return result.result.value;
}

const failures = [];
let checked = 0;
for (const [language, relativeDir] of articleSets) {
  const files = (await readdir(resolve(repoRoot, relativeDir)))
    .filter((name) => name.endsWith(".html") && !name.toLowerCase().includes("backup"))
    .sort();
  for (const file of files) {
    const urlPath = `${relativeDir}/${file}`.replaceAll("\\", "/");
    const desktop = await inspect(urlPath, 1440, 900);
    const mobile = await inspect(urlPath, 390, 844);
    checked += 1;
    if (desktop.missingBody || desktop.mismatches.length || desktop.scrollWidth > desktop.viewportWidth) {
      failures.push({ language, file, viewport: "desktop", ...desktop });
    }
    if (mobile.missingBody || mobile.scrollWidth > mobile.viewportWidth) {
      failures.push({ language, file, viewport: "mobile", ...mobile });
    }
  }
}

await send("Target.closeTarget", { targetId });
socket.close();

if (failures.length) {
  console.error(JSON.stringify({ checked, failures }, null, 2));
  process.exit(1);
}

console.log(`article width audit passed: ${checked} EN/KO pages at 1440px and 390px`);
