import { lookup } from "node:dns/promises";
import { Actor, log } from "apify";
import { chromium } from "playwright";
import { capturePage } from "./capture.js";
import { isPrivateHost, normalizeUrl, resolveOptions, screenshotKey, shortError } from "./helpers.js";

async function launchBrowser() {
  // Apify's Playwright images announce their browser through these variables; elsewhere Playwright's own Chromium is used.
  const executablePath = process.env.APIFY_DEFAULT_BROWSER_PATH || process.env.APIFY_CHROME_EXECUTABLE_PATH || undefined;
  try {
    return await chromium.launch({ headless: true, executablePath });
  } catch (err) {
    log.warning(`Default browser did not start (${shortError(err)}); trying installed Chrome.`);
    return chromium.launch({ headless: true, channel: "chrome" });
  }
}

// A public-looking name can still resolve to a private address.
async function resolvesToPrivate(url) {
  const addresses = await lookup(new URL(url).hostname, { all: true }).catch(() => []);
  return addresses.some((a) => isPrivateHost(a.address));
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const opts = resolveOptions(input);
const urls = (Array.isArray(input.urls) ? input.urls : []).map((u) => String(u ?? "").trim()).filter(Boolean);
if (!urls.length) log.warning("Nothing to do: give at least one URL in 'urls'.");

const store = await Actor.openKeyValueStore();
let done = 0;
let failed = 0;
let next = 0;
let stop = false;

async function handle(raw, index, browser) {
  const item = {
    url: raw, finalUrl: null, status: null, title: null, format: opts.format, screenshotKey: null, screenshotUrl: null,
    width: null, height: null, bytes: null, loadTimeMs: null, capturedAt: new Date().toISOString(), error: null,
  };
  try {
    const target = normalizeUrl(raw);
    if (target.error) throw new Error(target.error);
    item.url = target.url;
    if (await resolvesToPrivate(target.url)) throw new Error("Host resolves to a private address; refused");
    const shot = await capturePage(browser, target.url, opts);
    const key = screenshotKey(index + 1, shot.finalUrl, opts.ext);
    await Actor.setValue(key, shot.buffer, { contentType: opts.contentType });
    Object.assign(item, {
      finalUrl: shot.finalUrl, status: shot.status, title: shot.title, screenshotKey: key,
      // getPublicUrl is sync or async depending on the SDK version.
      screenshotUrl: await Promise.resolve().then(() => store.getPublicUrl(key)).catch(() => null),
      width: shot.width, height: shot.height, bytes: shot.buffer.length, loadTimeMs: shot.loadTimeMs, capturedAt: new Date().toISOString(),
    });
  } catch (err) {
    item.error = shortError(err);
  }
  if (item.error) {
    failed += 1;
    log.warning(`${raw}: ${item.error}`);
    await Actor.pushData(item); // failed URLs are returned but not charged
    return;
  }
  // Pay-per-event: one "screenshot" event per captured page.
  const charge = await Actor.charge({ eventName: "screenshot", count: 1 }).catch(() => null);
  await Actor.pushData(item);
  done += 1;
  log.info(`${item.url} -> ${item.screenshotKey} (${item.bytes} bytes, HTTP ${item.status ?? "?"})`);
  if (charge?.eventChargeLimitReached && !stop) {
    stop = true;
    log.info("Spending limit reached; stopping.");
  }
}

if (urls.length) {
  const browser = await launchBrowser();
  try {
    const worker = async () => {
      while (!stop && next < urls.length) {
        const index = next++;
        await handle(urls[index], index, browser);
      }
    };
    await Promise.all(Array.from({ length: Math.min(opts.concurrency, urls.length) }, worker));
  } finally {
    await browser.close().catch(() => null);
  }
}
log.info(`Done: ${done} captured, ${failed} failed`);
await Actor.exit();
