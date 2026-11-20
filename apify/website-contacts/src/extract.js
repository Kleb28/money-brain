// Pure extraction helpers (no network).

const decode = (s) => s.replace(/&amp;/g, "&").replace(/&#64;|&#x40;/gi, "@").replace(/&#46;|&#x2e;/gi, ".").replace(/&nbsp;/g, " ");
const ASSET = /\.(png|jpe?g|gif|svg|webp|avif|css|js|ico|woff2?|ttf|mp4|pdf)$/i;
const JUNK_EMAIL = /(example\.|sentry\.|wixpress\.|@sentry|noreply|no-reply|donotreply|your@|you@|name@|email@|user@|@domain\.|@email\.|@test\.|u003e)/i;

export function normalizeSite(raw) {
  let s = String(raw ?? "").trim();
  if (!s) return null;
  if (!/^https?:\/\//i.test(s)) s = `https://${s}`;
  try {
    const u = new URL(s);
    if (!u.hostname.includes(".")) return null;
    return { start: `${u.protocol}//${u.host}/`, domain: u.hostname.replace(/^www\./, "").toLowerCase() };
  } catch {
    return null;
  }
}

export function extractEmails(html) {
  const text = decode(html).replace(/\s*(\[at\]|\(at\))\s*/gi, "@").replace(/\s*(\[dot\]|\(dot\))\s*/gi, ".");
  const out = new Set();
  for (const m of text.matchAll(/[a-z0-9][a-z0-9._%+-]{0,63}@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,24}/gi)) {
    const e = m[0].toLowerCase().replace(/^(mailto:|u003e)/, "").replace(/\.$/, "");
    if (ASSET.test(e) || JUNK_EMAIL.test(e) || /\d+x\d*\./.test(e)) continue;
    out.add(e);
  }
  return [...out];
}

export function extractPhones(html) {
  const out = new Set();
  for (const m of html.matchAll(/href\s*=\s*["']tel:([^"']+)["']/gi)) {
    const p = decodeURIComponent(m[1]).replace(/[^\d+]/g, "");
    if (p.replace(/\D/g, "").length >= 7 && p.replace(/\D/g, "").length <= 15) out.add(p);
  }
  return [...out];
}

const SOCIAL = {
  linkedin: /https?:\/\/(?:[a-z]{2,3}\.)?linkedin\.com\/(?:company|school|in)\/[\w%.-]+/i,
  twitter: /https?:\/\/(?:www\.)?(?:twitter|x)\.com\/(?!share|intent|home|search|hashtag)[\w]{1,15}(?=["'/?\s]|$)/i,
  facebook: /https?:\/\/(?:www\.)?facebook\.com\/(?!sharer|share|tr\b|plugins|dialog)[\w.%-]+/i,
  instagram: /https?:\/\/(?:www\.)?instagram\.com\/(?!p\/|explore|reel)[\w.]+/i,
  youtube: /https?:\/\/(?:www\.)?youtube\.com\/(?:@[\w.-]+|channel\/[\w-]+|c\/[\w%.-]+|user\/[\w-]+)/i,
};
export function extractSocial(html) {
  const out = {};
  for (const [k, re] of Object.entries(SOCIAL)) out[k] = re.exec(html)?.[0] ?? null;
  return out;
}

const WANT = /(contact|kontakt|contacto|contatt|about|ueber-uns|uber-uns|impressum|imprint|team|company|support|legal|a-propos|nous-contacter|sobre|chi-siamo)/i;
/** Internal links, most contact-like first. */
export function pickLinks(html, start, limit) {
  const base = new URL(start);
  const scored = new Map();
  for (const m of html.matchAll(/<a\b[^>]*href\s*=\s*["']([^"'#]+)["'][^>]*>([\s\S]{0,120}?)<\/a>/gi)) {
    let u;
    try {
      u = new URL(m[1], base);
    } catch {
      continue;
    }
    if (!/^https?:$/.test(u.protocol) || u.hostname.replace(/^www\./, "") !== base.hostname.replace(/^www\./, "") || ASSET.test(u.pathname)) continue;
    u.hash = "";
    u.search = "";
    const key = u.href;
    if (key === base.href || scored.has(key)) continue;
    const score = (WANT.test(u.pathname) ? 2 : 0) + (WANT.test(m[2]) ? 1 : 0) - u.pathname.split("/").filter(Boolean).length * 0.1;
    if (score > 0) scored.set(key, score);
  }
  return [...scored.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([k]) => k);
}

/** Minimal robots.txt check for the `*` group: returns disallowed path prefixes. */
export function robotsDisallows(txt) {
  const out = [];
  let applies = false;
  for (const line of String(txt ?? "").split(/\r?\n/)) {
    const [k, ...rest] = line.split(":");
    const v = rest.join(":").split("#")[0].trim();
    const key = k.trim().toLowerCase();
    if (key === "user-agent") applies = v === "*";
    else if (applies && key === "disallow" && v) out.push(v);
  }
  return out;
}
// robots.txt path patterns: "*" matches any run of characters, a trailing "$" anchors the end.
const robotsRe = (p) => new RegExp("^" + p.split("*").map((x) => x.replace(/[.+?^{}()|[\]\\]/g, "\\$&").replace(/\$$/, "$")).join(".*"));
export const allowed = (url, disallows) => {
  const u = new URL(url);
  const target = u.pathname + u.search;
  return !disallows.some((p) => robotsRe(p).test(target));
};
