import test from "node:test";
import assert from "node:assert/strict";
import { MOBILE_PRESET, clampInt, hideCss, isPrivateHost, normalizeUrl, resolveOptions, screenshotKey, shortError } from "../src/helpers.js";

test("normalizeUrl adds https and keeps valid URLs", () => {
  assert.equal(normalizeUrl("apify.com").url, "https://apify.com/");
  assert.equal(normalizeUrl("  http://example.com/a?b=1 ").url, "http://example.com/a?b=1");
  assert.equal(normalizeUrl("example.com:8080/x").url, "https://example.com:8080/x");
  assert.equal(normalizeUrl("HTTPS://Example.com").url, "https://example.com/");
});

test("normalizeUrl rejects non-http schemes and junk", () => {
  for (const bad of ["", "   ", null, "ftp://example.com", "file:///etc/passwd", "javascript:alert(1)", "data:text/html,hi", "about:blank", "chrome://version", "not a url", "intranet", "https://user:pw@example.com"]) {
    assert.ok(normalizeUrl(bad).error, `should reject ${bad}`);
    assert.equal(normalizeUrl(bad).url, undefined);
  }
});

test("normalizeUrl rejects private, loopback and link-local hosts", () => {
  for (const bad of [
    "localhost", "http://localhost:3000", "http://app.localhost", "http://printer.local", "http://127.0.0.1", "http://127.8.9.1:8080/x",
    "http://10.0.0.5", "http://172.16.0.1", "http://172.31.255.255", "http://192.168.1.1", "http://169.254.169.254/latest/meta-data/",
    "http://0.0.0.0", "http://[::1]/", "http://[fe80::1]", "http://[fd00::1]", "http://[::ffff:127.0.0.1]", "http://[::ffff:10.1.2.3]",
    "http://2130706433", "http://0x7f.0.0.1", "http://127.1", "http://localhost.",
  ]) {
    assert.match(normalizeUrl(bad).error ?? "", /refused/, `should refuse ${bad}`);
  }
});

test("isPrivateHost leaves public hosts alone", () => {
  for (const ok of ["example.com", "172.15.0.1", "172.32.0.1", "192.169.0.1", "169.253.1.1", "11.0.0.1", "8.8.8.8", "2606:4700:4700::1111", "[2606:4700:4700::1111]", "::ffff:8.8.8.8", "fdexample.com", "local.example.com"]) {
    assert.equal(isPrivateHost(ok), false, ok);
  }
  for (const bad of ["", "LOCALHOST", "::1", "[::1]", "fe80::1%eth0", "fc00::1", "100.64.0.1", "10.255.255.255"]) {
    assert.equal(isPrivateHost(bad), true, bad);
  }
});

test("screenshotKey", () => {
  assert.equal(screenshotKey(1, "https://www.apify.com/", "png"), "001-apify.com.png");
  assert.equal(screenshotKey(12, "https://news.ycombinator.com/item?id=1&p=2", "jpg"), "012-news.ycombinator.com-item-id-1-p-2.jpg");
  assert.equal(screenshotKey(3, "https://example.com/a b/한글/#frag", "pdf"), "003-example.com-a-20b-ED-95-9C-EA-B8-80.pdf");
  assert.equal(screenshotKey(4, "not a url", "png"), "004-page.png");
  const long = screenshotKey(1234, `https://example.com/${"a/".repeat(300)}`, "png");
  assert.equal(long.length, 200);
  assert.match(long, /^1234-example\.com-a-.*a\.png$/);
  for (const k of [long, screenshotKey(1, "https://example.com/~x/@y,z;w=%20+$*", "png")]) assert.match(k, /^[a-zA-Z0-9!\-_.'()]{1,200}$/);
});

test("clampInt", () => {
  assert.equal(clampInt(undefined, 3, 1, 8), 3);
  assert.equal(clampInt(null, 3, 1, 8), 3);
  assert.equal(clampInt("abc", 3, 1, 8), 3);
  assert.equal(clampInt(99, 3, 1, 8), 8);
  assert.equal(clampInt(-5, 3, 1, 8), 1);
  assert.equal(clampInt("5", 3, 1, 8), 5);
  assert.equal(clampInt(0, 1000, 0, 15000), 0);
  assert.equal(clampInt(2.6, 1, 1, 3), 3);
});

test("resolveOptions defaults", () => {
  const o = resolveOptions({});
  assert.deepEqual(
    { format: o.format, ext: o.ext, contentType: o.contentType, fullPage: o.fullPage, waitUntil: o.waitUntil, delayMs: o.delayMs, selector: o.selector, hideSelectors: o.hideSelectors, jpegQuality: o.jpegQuality, maxPageHeight: o.maxPageHeight, timeoutMs: o.timeoutMs, concurrency: o.concurrency },
    { format: "png", ext: "png", contentType: "image/png", fullPage: true, waitUntil: "load", delayMs: 1000, selector: null, hideSelectors: [], jpegQuality: 80, maxPageHeight: 20000, timeoutMs: 45000, concurrency: 3 },
  );
  assert.deepEqual(o.contextOptions, { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1, colorScheme: "light" });
  assert.equal("userAgent" in o.contextOptions, false);
  assert.deepEqual(resolveOptions().contextOptions, o.contextOptions);
});

test("resolveOptions clamps and validates", () => {
  const o = resolveOptions({
    format: "JPG", fullPage: false, viewportWidth: 99999, viewportHeight: 1, deviceScaleFactor: 10, darkMode: true, waitUntil: "commit",
    delayMs: 999999, selector: "  #main ", hideSelectors: [" .cookie ", "", null, "a{}body{display:none}"], jpegQuality: 500, maxPageHeight: 1, timeoutSecs: 0, concurrency: 50,
  });
  assert.equal(o.format, "jpeg");
  assert.equal(o.ext, "jpg");
  assert.equal(o.contentType, "image/jpeg");
  assert.equal(o.fullPage, false);
  assert.deepEqual(o.contextOptions, { viewport: { width: 3840, height: 240 }, deviceScaleFactor: 3, colorScheme: "dark" });
  assert.equal(o.waitUntil, "load");
  assert.equal(o.delayMs, 15000);
  assert.equal(o.selector, "#main");
  assert.deepEqual(o.hideSelectors, [".cookie"]);
  assert.equal(o.jpegQuality, 100);
  assert.equal(o.maxPageHeight, 100);
  assert.equal(o.timeoutMs, 5000);
  assert.equal(o.concurrency, 8);
  assert.equal(resolveOptions({ format: "gif" }).format, "png");
  assert.equal(resolveOptions({ format: "pdf" }).contentType, "application/pdf");
  assert.equal(resolveOptions({ waitUntil: "networkidle" }).waitUntil, "networkidle");
});

test("mobile preset overrides viewport and sets no user agent", () => {
  const o = resolveOptions({ mobile: true, viewportWidth: 1920, viewportHeight: 1080, deviceScaleFactor: 1 });
  assert.deepEqual(o.contextOptions, { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, colorScheme: "light" });
  assert.equal("userAgent" in o.contextOptions, false);
  o.contextOptions.viewport.width = 1;
  assert.equal(MOBILE_PRESET.viewport.width, 390);
});

test("hideCss and shortError", () => {
  assert.equal(hideCss(["#a", ".b"]), "#a { display: none !important; visibility: hidden !important; }\n.b { display: none !important; visibility: hidden !important; }");
  assert.equal(shortError(new Error("page.goto: Timeout 45000ms exceeded.\nCall log:\n  - navigating")), "page.goto: Timeout 45000ms exceeded.");
  assert.equal(shortError(new Error("x".repeat(500))).length, 200);
  assert.equal(shortError(undefined), "Unknown error");
});
