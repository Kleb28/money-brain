// Pure helpers for reading a Shopify storefront's public /products.json feed:
// input parsing, robots.txt check, normalizer to the output schema, filters. No I/O here.

export const USER_AGENT = "ShopifyProductsReader/0.1 (+https://apify.com)";
export const PAGE_SIZE = 250; // the feed's maximum page size

const decode = (s) =>
  String(s ?? "")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&");
export const htmlToText = (html) =>
  decode(String(html ?? "").replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, "").replace(/\s+/g, " ")
    .replace(/<\/(p|h\d)\s*>/gi, "\n\n").replace(/<(br|\/div|\/li|\/tr)\s*\/?>/gi, "\n").replace(/<li[^>]*>/gi, "- ").replace(/<[^>]+>/g, ""))
    .replace(/[ \t]+/g, " ").replace(/ ?\n ?/g, "\n").replace(/\n{2,}/g, "\n\n").trim();
export const iso = (v) => {
  if (v === undefined || v === null || v === "") return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
};
const num = (v) => {
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/** "allbirds.com" | "https://www.gymshark.com/collections/all?page=2" -> { store, origin, collection } or null. */
export function parseStore(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return null;
  let u;
  try {
    u = new URL(/^https?:\/\//i.test(s) ? s : `https://${s}`);
  } catch {
    return null;
  }
  const store = u.hostname.toLowerCase();
  if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(store)) return null;
  const m = /\/collections\/([^/?#]+)/.exec(u.pathname);
  const collection = m && m[1] !== "products.json" ? m[1] : null; // kept URL-encoded, as it appears in the path
  return { store, origin: `https://${store}`, collection };
}

export const feedPath = (t, page = 1) =>
  `${t.collection ? `/collections/${t.collection}` : ""}/products.json?limit=${PAGE_SIZE}&page=${page}`;
export const feedUrl = (t, page = 1) => `${t.origin}${feedPath(t, page)}`;

// ---- robots.txt (RFC 9309: group for our own token if present, else "*"; longest match wins, Allow wins ties)

function robotsRules(txt, agentToken) {
  const groups = [];
  let cur = null;
  let lastWasAgent = false;
  for (const line of String(txt ?? "").split(/\r?\n/)) {
    const m = /^\s*([A-Za-z-]+)\s*:\s*(.*?)\s*$/.exec(line.replace(/#.*$/, ""));
    if (!m) continue;
    const key = m[1].toLowerCase();
    if (key === "user-agent") {
      if (!lastWasAgent) groups.push((cur = { agents: [], rules: [] }));
      cur.agents.push(m[2].toLowerCase());
      lastWasAgent = true;
    } else if (key === "allow" || key === "disallow") {
      lastWasAgent = false;
      if (cur && m[2]) cur.rules.push({ allow: key === "allow", pattern: m[2] }); // empty Disallow = no restriction
    } // other lines (Sitemap, Crawl-delay) are ignored
  }
  const token = agentToken.toLowerCase();
  const own = groups.filter((g) => g.agents.includes(token));
  return (own.length ? own : groups.filter((g) => g.agents.includes("*"))).flatMap((g) => g.rules);
}
function patternToRegExp(pattern) {
  const anchored = pattern.endsWith("$");
  const body = (anchored ? pattern.slice(0, -1) : pattern).split("*").map((p) => p.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*");
  return new RegExp(`^${body}${anchored ? "$" : ""}`);
}
/** True if robots.txt lets us fetch `path` (path + query). An empty or missing robots.txt allows everything. */
export function robotsAllows(txt, path, agentToken = "ShopifyProductsReader") {
  let best = null;
  for (const r of robotsRules(txt, agentToken)) {
    if (!patternToRegExp(r.pattern).test(path)) continue;
    if (!best || r.pattern.length > best.pattern.length || (r.pattern.length === best.pattern.length && r.allow)) best = r;
  }
  return best ? best.allow : true;
}
/** The feed counts as allowed only if both the bare path and the path with the paging query are allowed. */
export function feedAllowedByRobots(txt, target) {
  const full = feedPath(target, 1);
  return robotsAllows(txt, full) && robotsAllows(txt, full.split("?")[0]);
}

// ---- feed parsing and normalizing

/** Response body text -> products array, or null if it is not the products.json shape. */
export function parseFeed(text) {
  try {
    const j = JSON.parse(text);
    return Array.isArray(j?.products) ? j.products : null;
  } catch {
    return null;
  }
}
/** meta.json body text -> { shopName, currency } (nulls when unreadable). */
export function parseMeta(text) {
  try {
    const j = JSON.parse(text);
    return { shopName: typeof j?.name === "string" ? j.name : null, currency: typeof j?.currency === "string" ? j.currency : null };
  } catch {
    return { shopName: null, currency: null };
  }
}
export const normTags = (t) =>
  (Array.isArray(t) ? t : String(t ?? "").split(",")).map((x) => String(x).trim()).filter(Boolean);

export function normVariant(v) {
  return {
    variantId: v.id ?? null, title: v.title ?? null, sku: v.sku || null,
    price: num(v.price), compareAtPrice: num(v.compare_at_price), available: v.available === true,
    option1: v.option1 ?? null, option2: v.option2 ?? null, option3: v.option3 ?? null,
    grams: num(v.grams), requiresShipping: v.requires_shipping ?? null,
  };
}
/** One feed product -> one output item. ctx = { store, shopName, currency }. */
export function normProduct(p, ctx) {
  const variants = (p.variants ?? []).map(normVariant);
  const prices = variants.map((v) => v.price).filter((n) => n !== null);
  const compares = variants.map((v) => v.compareAtPrice).filter((n) => n !== null);
  const images = (p.images ?? []).map((i) => i?.src).filter(Boolean);
  return {
    store: ctx.store, shopName: ctx.shopName ?? null, currency: ctx.currency ?? null,
    productId: p.id ?? null, title: p.title ?? "", handle: p.handle ?? null,
    url: p.handle ? `https://${ctx.store}/products/${p.handle}` : null,
    vendor: p.vendor || null, productType: p.product_type || null, tags: normTags(p.tags),
    publishedAt: iso(p.published_at), createdAt: iso(p.created_at), updatedAt: iso(p.updated_at),
    priceMin: prices.length ? Math.min(...prices) : null, priceMax: prices.length ? Math.max(...prices) : null,
    compareAtPriceMax: compares.length ? Math.max(...compares) : null,
    onSale: variants.some((v) => v.compareAtPrice !== null && v.price !== null && v.compareAtPrice > v.price),
    available: variants.some((v) => v.available),
    variantCount: variants.length,
    options: (p.options ?? []).map((o) => ({ name: o.name ?? null, values: o.values ?? [] })),
    images, image: images[0] ?? null,
    description: p.body_html ? htmlToText(p.body_html) : null,
    variants,
    error: null,
  };
}
/** Product item -> one row per variant: product fields + the variant's fields (variant title as `variantTitle`) + variantUrl. */
export function toVariantRows(item, { inStockOnly = false } = {}) {
  const { variants, error, ...product } = item;
  return variants.filter((v) => !inStockOnly || v.available).map(({ title, ...v }) => ({
    ...product, ...v, variantTitle: title,
    variantUrl: product.url && v.variantId != null ? `${product.url}?variant=${v.variantId}` : null,
    error: null,
  }));
}
/** The single item returned for a store that could not be read. Never charged. */
export const errorItem = (target, message) => ({
  store: target.store, title: null, url: target.collection ? `${target.origin}/collections/${target.collection}` : target.origin, error: message,
});

// ---- filters

const lower = (x) => String(x ?? "").trim().toLowerCase();
const contains = (text, words) => !words?.length || words.some((w) => lower(text).includes(lower(w)));
const equalsAny = (values, words) => !words?.length || words.some((w) => values.some((v) => lower(v) === lower(w)));
/** f = { titleKeywords, productTypes, vendors, tags, inStockOnly, updatedAfter (ISO string) } */
export function keep(item, f) {
  if (!contains(item.title, f.titleKeywords)) return false;
  if (!equalsAny([item.productType], f.productTypes)) return false;
  if (!equalsAny([item.vendor], f.vendors)) return false;
  if (!equalsAny(item.tags, f.tags)) return false;
  if (f.inStockOnly && !item.available) return false;
  if (f.updatedAfter && (!item.updatedAt || item.updatedAt < f.updatedAfter)) return false;
  return true;
}

// ---- retry timing

/** Wait before the next try: the server's Retry-After (seconds or HTTP date) if given, else 2 s, 4 s, 8 s ... */
export function retryDelayMs(retryAfter, attempt, now = Date.now()) {
  const h = String(retryAfter ?? "").trim();
  if (/^\d+(\.\d+)?$/.test(h)) return Math.ceil(Number(h) * 1000);
  const at = h ? Date.parse(h) : NaN;
  if (!Number.isNaN(at)) return Math.max(at - now, 0);
  return 2000 * 2 ** attempt;
}
