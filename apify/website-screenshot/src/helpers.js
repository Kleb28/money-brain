// Pure logic: no network, no browser. Unit-tested in test/helpers.test.js.

export const FORMATS = {
  png: { ext: "png", contentType: "image/png" },
  jpeg: { ext: "jpg", contentType: "image/jpeg" },
  pdf: { ext: "pdf", contentType: "application/pdf" },
};
export const MOBILE_PRESET = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true };
const WAIT_UNTIL = ["load", "domcontentloaded", "networkidle"];

function privateV4(a, b) {
  return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127);
}

/** True for hostnames or IP literals that point at loopback, private or link-local networks. */
export function isPrivateHost(hostname) {
  let h = String(hostname ?? "").trim().toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
  if (!h) return true;
  if (h === "localhost" || /\.(localhost|local|internal|lan|home\.arpa)$/.test(h)) return true;
  const v4 = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (v4) return privateV4(Number(v4[1]), Number(v4[2]));
  if (h.includes(":")) {
    if (h === "::" || h === "::1") return true;
    // IPv4-mapped (::ffff:127.0.0.1, which URL prints as ::ffff:7f00:1)
    const mapped = h.match(/^::ffff:(?:(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}|([0-9a-f]{1,4}):[0-9a-f]{1,4})$/);
    if (mapped) return mapped[3] ? privateV4(parseInt(mapped[3], 16) >> 8, parseInt(mapped[3], 16) & 255) : privateV4(Number(mapped[1]), Number(mapped[2]));
    return /^f[cd]/.test(h) || /^fe[89ab]/.test(h); // fc00::/7 unique local, fe80::/10 link-local
  }
  return false;
}

/** Returns { url } for a public http(s) address, otherwise { error }. */
export function normalizeUrl(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return { error: "Empty URL" };
  // "example.com:8080/x" has no scheme, although URL would read "example.com:" as one.
  const hasScheme = /^[a-z][a-z0-9+.-]*:/i.test(s) && !/^[^/?#]+:\d+(?:[/?#]|$)/.test(s);
  let u;
  try {
    u = new URL(hasScheme ? s : `https://${s}`);
  } catch {
    return { error: "Not a valid URL" };
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") return { error: "Only http and https URLs are supported" };
  if (u.username || u.password) return { error: "URLs with credentials are not supported" };
  if (isPrivateHost(u.hostname)) return { error: "Private, loopback and link-local addresses are refused" };
  if (!u.hostname.includes(".") && !u.hostname.includes(":")) return { error: "Not a valid public hostname" };
  return { url: u.href };
}

/** Key-value store key: "<index>-<host-path>.<ext>", at most 200 chars from [a-zA-Z0-9!-_.'()]. */
export function screenshotKey(index, url, ext) {
  let name = "page";
  try {
    const u = new URL(url);
    name = `${u.hostname.replace(/^www\./, "")}${u.pathname}${u.search}`;
  } catch { /* keep the fallback name */ }
  name = name.replace(/[^a-zA-Z0-9!\-_.'()]+/g, "-").replace(/-{2,}/g, "-").replace(/^[-.]+|[-.]+$/g, "") || "page";
  const prefix = `${String(index).padStart(3, "0")}-`;
  const suffix = `.${ext}`;
  return prefix + name.slice(0, 200 - prefix.length - suffix.length).replace(/[-.]+$/, "") + suffix;
}

export function clampInt(value, def, min, max) {
  const n = Math.round(Number(value));
  if (value === null || value === undefined || value === "" || !Number.isFinite(n)) return def;
  return Math.min(Math.max(n, min), max);
}

/** Turns raw actor input into clamped options plus the Playwright context options. */
export function resolveOptions(input = {}) {
  const format = FORMATS[String(input.format ?? "").toLowerCase()] ? String(input.format).toLowerCase() : String(input.format ?? "").toLowerCase() === "jpg" ? "jpeg" : "png";
  const mobile = input.mobile === true;
  const device = mobile
    ? { ...MOBILE_PRESET, viewport: { ...MOBILE_PRESET.viewport } }
    : {
        viewport: { width: clampInt(input.viewportWidth, 1280, 320, 3840), height: clampInt(input.viewportHeight, 800, 240, 2160) },
        deviceScaleFactor: clampInt(input.deviceScaleFactor, 1, 1, 3),
      };
  const selector = typeof input.selector === "string" && input.selector.trim() ? input.selector.trim() : null;
  const hideSelectors = (Array.isArray(input.hideSelectors) ? input.hideSelectors : [])
    .map((s) => String(s ?? "").trim())
    .filter((s) => s && !/[{}]/.test(s)); // braces would break out of the injected CSS rule
  return {
    format,
    ...FORMATS[format],
    fullPage: input.fullPage !== false,
    mobile,
    waitUntil: WAIT_UNTIL.includes(input.waitUntil) ? input.waitUntil : "load",
    delayMs: clampInt(input.delayMs, 1000, 0, 15000),
    selector,
    hideSelectors,
    jpegQuality: clampInt(input.jpegQuality, 80, 1, 100),
    maxPageHeight: clampInt(input.maxPageHeight, 20000, 100, 50000),
    timeoutMs: clampInt(input.timeoutSecs, 45, 5, 180) * 1000,
    concurrency: clampInt(input.concurrency, 3, 1, 8),
    contextOptions: { ...device, colorScheme: input.darkMode === true ? "dark" : "light" },
  };
}

/** CSS that hides the given selectors; one rule each, so one bad selector does not void the rest. */
export function hideCss(selectors) {
  return selectors.map((s) => `${s} { display: none !important; visibility: hidden !important; }`).join("\n");
}

export function shortError(err) {
  const msg = String(err?.message ?? err ?? "Unknown error").split("\n")[0].replace(/\s+/g, " ").trim();
  return msg.length > 200 ? `${msg.slice(0, 197)}...` : msg;
}
