// Pure helpers for Google News' public RSS feeds: feed URLs, a small RSS parser and the item normalizer.
// No network here; src/main.js does the I/O.

export const TOPICS = ["WORLD", "NATION", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH"];
export const TIME_RANGES = ["1h", "1d", "7d", "30d", "1y"];
export const TOP_HEADLINES = "TOP_HEADLINES";
const BASE = "https://news.google.com/rss";

const NAMED = { lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", amp: "&" };
const codePoint = (n) => (Number.isInteger(n) && n > 0 && n <= 0x10ffff ? String.fromCodePoint(n) : "");
/** Decodes one level of entities (the five XML ones, &nbsp; and numeric references). */
export const decode = (s) =>
  String(s ?? "").replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] !== "#") return NAMED[e.toLowerCase()] ?? m;
    return codePoint(/^#x/i.test(e) ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10));
  });

/** HTML (already XML-decoded) -> plain text. */
export const htmlToText = (html) =>
  decode(String(html ?? "").replace(/<(br|\/p|\/div|\/li|\/h\d)\s*\/?>/gi, "\n").replace(/<[^>]+>/g, ""))
    .replace(/[ \t ]+/g, " ").replace(/ ?\n\s*/g, "\n").trim();

const iso = (v) => {
  if (v === undefined || v === null || v === "") return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
};

// Text content of an element: CDATA is taken literally, anything else is entity-decoded once.
const content = (raw) => {
  const s = String(raw ?? "").trim();
  const cdata = /^<!\[CDATA\[([\s\S]*)\]\]>$/.exec(s);
  return cdata ? cdata[1] : decode(s);
};
const element = (xml, name) => {
  const m = new RegExp(`<${name}(\\s[^>]*)?>([\\s\\S]*?)</${name}>`, "i").exec(xml);
  return m ? { attrs: m[1] ?? "", text: content(m[2]) } : null;
};
const attr = (attrs, name) => {
  const m = new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)')`, "i").exec(attrs ?? "");
  return m ? decode(m[2] ?? m[3]) : null;
};

/** RSS 2.0 text -> raw items. `description` is HTML (entities decoded once). Returns [] when there is no <item>. */
export function parseRss(xml) {
  const items = [];
  for (const m of String(xml ?? "").matchAll(/<item(?:\s[^>]*)?>([\s\S]*?)<\/item>/gi)) {
    const body = m[1];
    const source = element(body, "source");
    items.push({
      title: element(body, "title")?.text ?? "",
      link: element(body, "link")?.text || null,
      guid: element(body, "guid")?.text || null,
      pubDate: element(body, "pubDate")?.text || null,
      description: element(body, "description")?.text ?? "",
      source: source?.text || null,
      sourceUrl: attr(source?.attrs, "url"),
    });
  }
  return items;
}

/** Google News titles end with " - Publisher"; drop it only when it matches the <source> name. */
export function stripSource(title, source) {
  const t = String(title ?? "").trim();
  const tail = source ? ` - ${source}` : "";
  return tail && t.length > tail.length && t.endsWith(tail) ? t.slice(0, -tail.length).trim() : t;
}

/** A clustered description is an <ol> of articles; returns the number of articles listed besides the item itself. */
export function relatedCount(descriptionHtml) {
  const n = (String(descriptionHtml ?? "").match(/<li[\s>]/gi) ?? []).length;
  return n > 1 ? n - 1 : null;
}

const day = (v) => {
  if (!v) return null;
  const s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  return iso(s)?.slice(0, 10) ?? null;
};

/** Appends the time operators to a search query: "openai" -> "openai when:1d after:2026-11-01". */
export function buildQuery(query, { timeRange, after, before } = {}) {
  const parts = [String(query ?? "").trim()];
  if (TIME_RANGES.includes(timeRange)) parts.push(`when:${timeRange}`);
  if (day(after)) parts.push(`after:${day(after)}`);
  if (day(before)) parts.push(`before:${day(before)}`);
  return parts.filter(Boolean).join(" ");
}

export function locale({ language, country } = {}) {
  const lang = String(language ?? "").trim() || "en";
  const gl = (String(country ?? "").trim() || "US").toUpperCase();
  return { language: lang, country: gl, params: `hl=${encodeURIComponent(lang)}&gl=${encodeURIComponent(gl)}&ceid=${encodeURIComponent(gl)}:${encodeURIComponent(lang)}` };
}

/** Actor input -> the list of feeds to read: [{ label, url }]. `label` becomes the item's `query` field. */
export function buildFeeds(input = {}) {
  const { params } = locale(input);
  const feeds = [];
  const seen = new Set();
  const add = (label, url) => {
    if (seen.has(url)) return;
    seen.add(url);
    feeds.push({ label, url });
  };
  for (const raw of input.queries ?? []) {
    const q = String(raw ?? "").trim();
    if (q) add(q, `${BASE}/search?q=${encodeURIComponent(buildQuery(q, input))}&${params}`);
  }
  for (const raw of input.topics ?? []) {
    const t = String(raw ?? "").trim().toUpperCase();
    if (TOPICS.includes(t)) add(t, `${BASE}/headlines/section/topic/${t}?${params}`);
  }
  if (input.topHeadlines === true) add(TOP_HEADLINES, `${BASE}?${params}`);
  return feeds;
}

/** Raw RSS item -> output item. The Google News redirect link is returned as given. */
export function normalize(item, { label, language, country }) {
  const out = {
    query: label,
    title: stripSource(item.title, item.source),
    source: item.source ?? null,
    sourceUrl: item.sourceUrl ?? null,
    publishedAt: iso(item.pubDate),
    link: item.link ?? null,
    guid: item.guid ?? null,
    snippet: htmlToText(item.description) || null,
  };
  const related = relatedCount(item.description);
  if (related !== null) out.relatedCount = related;
  out.language = language;
  out.country = country;
  return out;
}

/** Feed text -> output items, deduplicated by link against `seen` (a Set shared across feeds) and cut to `max`. */
export function itemsFromFeed(xml, { label, language, country, max = 100, seen = null }) {
  const out = [];
  for (const raw of parseRss(xml)) {
    if (out.length >= max) break;
    const item = normalize(raw, { label, language, country });
    const key = item.link ?? item.guid;
    if (seen && key) {
      if (seen.has(key)) continue;
      seen.add(key);
    }
    out.push(item);
  }
  return out;
}
