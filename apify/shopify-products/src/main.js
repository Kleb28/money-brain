import { Actor, log } from "apify";
import {
  USER_AGENT, errorItem, feedAllowedByRobots, feedUrl, iso, keep, normProduct, parseFeed, parseMeta, parseStore, retryDelayMs, toVariantRows,
} from "./shopify.js";

const PAGE_DELAY_MS = 500; // pause between requests to the same store
const MAX_WAIT_MS = 60_000; // a longer Retry-After stops the store instead of being cut short
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** GET with an honest user-agent. Retries 429/5xx/network errors (honoring Retry-After); other statuses are returned as they are. */
async function get(url, tries = 3) {
  let last = "";
  for (let i = 0; i < tries; i++) {
    let wait;
    try {
      const res = await fetch(url, { headers: { "user-agent": USER_AGENT, accept: "application/json, text/plain;q=0.9, */*;q=0.1" }, signal: AbortSignal.timeout(30_000) });
      if (res.status !== 429 && res.status < 500) return res;
      last = `HTTP ${res.status}`;
      wait = retryDelayMs(res.headers.get("retry-after"), i);
      await res.arrayBuffer().catch(() => null);
    } catch (err) {
      last = err.message;
      wait = retryDelayMs(null, i);
    }
    if (wait > MAX_WAIT_MS) throw new Error(`${last}; the store asked to wait ${Math.round(wait / 1000)} s`);
    if (i < tries - 1) await sleep(wait);
  }
  throw new Error(`${last} after ${tries} tries`);
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const updatedAfter = iso(input.updatedAfter);
if (input.updatedAfter && !updatedAfter) log.warning(`updatedAfter "${input.updatedAfter}" is not a date; ignored`);
const filter = {
  titleKeywords: input.titleKeywords,
  productTypes: input.productTypes,
  vendors: input.vendors,
  tags: input.tags,
  inStockOnly: input.inStockOnly === true,
  updatedAfter,
};
const max = Math.max(Number(input.maxProductsPerStore ?? 1000) || 1000, 1);
const perVariant = input.oneRowPer === "variant";
const withText = input.includeDescription !== false;
const respectRobots = input.respectRobotsTxt !== false;
const concurrency = Math.min(Math.max(Number(input.concurrency ?? 3) || 3, 1), 10);

// Targets on the same host are read one after another, so a host never gets parallel requests.
const byHost = new Map();
const seen = new Set();
for (const raw of input.stores ?? []) {
  const t = parseStore(raw);
  if (!t) {
    log.warning(`Could not read "${raw}" as a store or collection URL`);
    continue;
  }
  const key = `${t.store}/${t.collection ?? ""}`;
  if (seen.has(key)) continue;
  seen.add(key);
  byHost.set(t.store, [...(byHost.get(t.store) ?? []), t]);
}
if (!byHost.size) log.warning("No stores given. Add store or collection URLs to the 'stores' input.");

let stop = false; // set when the user's spending limit is reached
let total = 0;

async function readTarget(t) {
  const label = t.collection ? `${t.store}/collections/${t.collection}` : t.store;
  const fail = async (message) => {
    log.warning(`${label}: ${message}`);
    await Actor.pushData(errorItem(t, message)); // error items are not charged
  };

  if (respectRobots) {
    let robots;
    try {
      const res = await get(`${t.origin}/robots.txt`);
      robots = res.ok ? await res.text() : ""; // 4xx: no robots.txt, nothing is disallowed
    } catch (err) {
      return fail(`robots.txt could not be read (${err.message}); store skipped`);
    }
    if (!feedAllowedByRobots(robots, t)) return fail("robots.txt disallows the products.json feed; store skipped");
    await sleep(PAGE_DELAY_MS);
  }

  let meta = { shopName: null, currency: null };
  try {
    const res = await get(`${t.origin}/meta.json`, 1);
    if (res.ok) meta = parseMeta(await res.text());
  } catch {
    // meta.json is optional
  }
  const ctx = { store: t.store, ...meta };

  let kept = 0;
  let prevFirstId;
  for (let page = 1; kept < max && !stop; page++) {
    await sleep(PAGE_DELAY_MS);
    let res;
    try {
      res = await get(feedUrl(t, page));
    } catch (err) {
      return fail(`stopped at page ${page} (${err.message}); ${kept} products were returned before that`);
    }
    if (!res.ok) {
      const why = [401, 403, 404].includes(res.status)
        ? "the store has turned the public products.json feed off, or it is not a Shopify store"
        : "the feed could not be read";
      return fail(`HTTP ${res.status} at page ${page}: ${why}${kept ? `; ${kept} products were returned before that` : ""}`);
    }
    const products = parseFeed(await res.text());
    if (!products) return fail(`page ${page} is not products.json data: the store is not on Shopify, is password-protected, or has the feed off`);
    if (!products.length) break;
    if (products[0]?.id !== undefined && products[0].id === prevFirstId) break; // the store ignores ?page=
    prevFirstId = products[0]?.id;

    const items = products.map((p) => normProduct(p, ctx)).filter((p) => keep(p, filter)).slice(0, max - kept);
    if (!items.length) continue;
    if (!withText) for (const p of items) delete p.description;
    const rows = perVariant ? items.flatMap((p) => toVariantRows(p, filter)) : items;
    // Pay-per-event: one "product" event per returned product (also in variant mode).
    const charge = await Actor.charge({ eventName: "product", count: items.length }).catch(() => null);
    await Actor.pushData(rows);
    kept += items.length;
    if (charge?.eventChargeLimitReached) {
      log.info("Spending limit reached; stopping.");
      stop = true;
    }
  }
  total += kept;
  log.info(`${label}: ${kept} products${kept ? "" : " (none matched, or the catalog is empty)"}`);
}

const queue = [...byHost.values()];
await Promise.all(
  Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (queue.length && !stop) {
      for (const t of queue.shift()) {
        if (stop) break;
        try {
          await readTarget(t);
        } catch (err) {
          log.warning(`${t.store}: ${err.message}`);
        }
      }
    }
  }),
);
log.info(`Done: ${total} products`);
await Actor.exit();
