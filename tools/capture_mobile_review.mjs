#!/usr/bin/env node

import { writeFile } from "node:fs/promises";

const [endpoint = "http://127.0.0.1:9223", url, output, widthArg = "390", heightArg = "844"] = process.argv.slice(2);
const viewportWidth = Number.parseInt(widthArg, 10);
const viewportHeight = Number.parseInt(heightArg, 10);
if (!url || !output) {
  console.error("usage: node tools/capture_mobile_review.mjs <debug-endpoint> <url> <output.png> [width] [height]");
  process.exit(2);
}
if (!Number.isFinite(viewportWidth) || !Number.isFinite(viewportHeight)) {
  console.error("width and height must be integers");
  process.exit(2);
}

const version = await fetch(`${endpoint}/json/version`).then((response) => response.json());
const socket = new WebSocket(version.webSocketDebuggerUrl);
const pending = new Map();
const listeners = new Map();
let nextId = 1;

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
    return;
  }
  const key = `${message.sessionId || "browser"}:${message.method}`;
  const queue = listeners.get(key);
  if (queue?.length) queue.shift()(message.params);
});

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

function send(method, params = {}, sessionId) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

function once(method, sessionId) {
  const key = `${sessionId || "browser"}:${method}`;
  return new Promise((resolve) => {
    const queue = listeners.get(key) || [];
    queue.push(resolve);
    listeners.set(key, queue);
  });
}

const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
await send("Page.enable", {}, sessionId);
await send(
  "Emulation.setDeviceMetricsOverride",
  { width: viewportWidth, height: viewportHeight, deviceScaleFactor: 1, mobile: viewportWidth < 700 },
  sessionId,
);
const loaded = once("Page.loadEventFired", sessionId);
await send("Page.navigate", { url }, sessionId);
await loaded;
await send(
  "Runtime.evaluate",
  { expression: "document.fonts.ready", awaitPromise: true, returnByValue: true },
  sessionId,
);
await send(
  "Runtime.evaluate",
  {
    expression: `Promise.all(Array.from(document.images, (item) => {
      item.loading = "eager";
      if (item.complete) return item.naturalWidth > 0;
      return new Promise((resolve) => {
        item.addEventListener("load", () => resolve(true), { once: true });
        item.addEventListener("error", () => resolve(false), { once: true });
      });
    }))`,
    awaitPromise: true,
    returnByValue: true,
  },
  sessionId,
);
await send(
  "Runtime.evaluate",
  {
    expression: `(() => {
      if (!location.hash) return;
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) {
        document.documentElement.style.scrollBehavior = "auto";
        target.scrollIntoView({ behavior: "auto", block: "start" });
      }
    })()`,
  },
  sessionId,
);
await send(
  "Runtime.evaluate",
  {
    expression: "new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))",
    awaitPromise: true,
  },
  sessionId,
);
const metrics = await send(
  "Runtime.evaluate",
  {
    expression: `({
      width: innerWidth,
      height: innerHeight,
      scrollY,
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
      hash: location.hash,
      anchorFound: !location.hash || Boolean(document.getElementById(decodeURIComponent(location.hash.slice(1)))),
      anchorTop: location.hash
        ? document.getElementById(decodeURIComponent(location.hash.slice(1)))?.getBoundingClientRect().top ?? null
        : null,
      imageCount: document.images.length,
      brokenImages: Array.from(document.images)
        .filter((item) => !item.complete || item.naturalWidth === 0)
        .map((item) => item.getAttribute("src")),
    })`,
    returnByValue: true,
  },
  sessionId,
);
const capture = await send("Page.captureScreenshot", { format: "png", fromSurface: true }, sessionId);
await writeFile(output, Buffer.from(capture.data, "base64"));
await send("Target.closeTarget", { targetId });
socket.close();
console.log(JSON.stringify(metrics.result.value));
