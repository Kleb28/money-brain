import { hideCss, isPrivateHost } from "./helpers.js";

function hostOf(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.hostname : null;
  } catch {
    return null;
  }
}

/**
 * Opens `url` in a fresh context of `browser` (a Playwright Browser), captures it and always closes the context.
 * `blocked(hostname)` decides which hosts the page may not reach; the default refuses private networks.
 */
export async function capturePage(browser, url, opts, blocked = isPrivateHost) {
  const context = await browser.newContext(opts.contextOptions);
  try {
    context.setDefaultTimeout(opts.timeoutMs);
    // Requests the page itself makes to private addresses (frames, scripts, images) are dropped.
    await context.route("**/*", (route) => {
      const host = hostOf(route.request().url());
      return host && blocked(host) ? route.abort("blockedbyclient") : route.continue();
    });
    const page = await context.newPage();
    const started = Date.now();
    const response = await page.goto(url, { waitUntil: opts.waitUntil, timeout: opts.timeoutMs });
    const loadTimeMs = Date.now() - started;
    const finalUrl = page.url();
    // Route handlers do not see redirect hops, so the landing address is checked again.
    const finalHost = hostOf(finalUrl);
    if (!finalHost || blocked(finalHost)) throw new Error("Redirected to a private or non-http address; refused");

    if (opts.hideSelectors.length) await page.addStyleTag({ content: hideCss(opts.hideSelectors) });
    if (opts.delayMs) await page.waitForTimeout(opts.delayMs);

    const title = await page.title();
    const doc = await page.evaluate(() => ({
      width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth ?? 0, window.innerWidth),
      height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight ?? 0, window.innerHeight),
    }));

    let buffer;
    let { width, height } = doc;
    if (opts.format === "pdf") {
      buffer = await page.pdf({ printBackground: true, format: "A4" });
    } else {
      const image = { type: opts.format, ...(opts.format === "jpeg" ? { quality: opts.jpegQuality } : {}) };
      if (opts.selector) {
        const element = page.locator(opts.selector).first();
        await element.waitFor({ state: "visible", timeout: Math.min(opts.timeoutMs, 10000) });
        buffer = await element.screenshot(image);
        const box = await element.boundingBox();
        width = Math.round(box?.width ?? 0);
        height = Math.round(box?.height ?? 0);
      } else if (opts.fullPage) {
        height = Math.min(doc.height, opts.maxPageHeight);
        buffer = await page.screenshot({ ...image, fullPage: true, ...(doc.height > height ? { clip: { x: 0, y: 0, width, height } } : {}) });
      } else {
        ({ width, height } = opts.contextOptions.viewport);
        buffer = await page.screenshot(image);
      }
    }
    return { buffer, finalUrl, status: response?.status() ?? null, title, width, height, loadTimeMs };
  } finally {
    await context.close().catch(() => null);
  }
}
