import { Actor, log } from "apify";
import { USER_AGENT, appleResults, dedupeKeys, fromApple, fromFeedUrl, keep, lookupUrl, merge, parseFeed, parseTarget, searchUrl } from "./podcast.js";

const FEED_TIMEOUT_MS = 15_000;
const FEED_MAX_BYTES = 3_000_000;
const APPLE_GAP_MS = 3_000; // Apple allows about 20 calls per minute
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const int = (v, def, min, max) => Math.min(Math.max(Number.isFinite(Number(v)) && v !== null && v !== "" ? Math.trunc(Number(v)) : def, min), max);

let lastAppleCall = 0;
async function appleJson(url) {
  for (let i = 0; i < 4; i++) {
    const wait = lastAppleCall + APPLE_GAP_MS - Date.now();
    if (wait > 0) await sleep(wait);
    lastAppleCall = Date.now();
    let res = null;
    try {
      res = await fetch(url, { headers: { accept: "application/json", "user-agent": USER_AGENT }, signal: AbortSignal.timeout(20_000) });
    } catch {
      // network error or timeout: retry below
    }
    if (res?.ok) return res.json();
    // Retry on rate limit (429; Apple also answers 403 when throttling) and server errors; other 4xx are final.
    if (res && res.status !== 429 && res.status !== 403 && res.status < 500) {
      log.warning(`Apple answered HTTP ${res.status} for ${url}`);
      return null;
    }
    const retryAfter = Number(res?.headers.get("retry-after"));
    await sleep(retryAfter > 0 ? Math.min(retryAfter, 60) * 1000 : 5000 * 2 ** i);
  }
  throw new Error(`Apple request failed after retries: ${url}`);
}

/** Feed text (at most FEED_MAX_BYTES of it), or throws an Error whose message is the short reason. */
async function fetchFeed(url) {
  let res;
  try {
    res = await fetch(url, {
      headers: { accept: "application/rss+xml, application/xml, text/xml, */*", "user-agent": USER_AGENT },
      signal: AbortSignal.timeout(FEED_TIMEOUT_MS),
    });
    if (!res.ok) {
      await res.body?.cancel().catch(() => null);
      throw new Error(`feed HTTP ${res.status}`);
    }
    const chunks = [];
    let size = 0;
    const reader = res.body.getReader();
    while (size < FEED_MAX_BYTES) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
      size += value.length;
    }
    if (size >= FEED_MAX_BYTES) await reader.cancel().catch(() => null);
    const buf = Buffer.concat(chunks).subarray(0, FEED_MAX_BYTES);
    const charset = /encoding=["']([\w-]+)["']/i.exec(buf.subarray(0, 200).toString("latin1"))?.[1] ?? "utf-8";
    let decoder;
    try {
      decoder = new TextDecoder(charset);
    } catch {
      decoder = new TextDecoder();
    }
    return decoder.decode(buf);
  } catch (err) {
    if (/^feed HTTP/.test(err.message)) throw err;
    throw new Error(err.name === "TimeoutError" || err.name === "AbortError" ? "feed timeout" : "feed not reachable");
  }
}

async function readShow(base, maxEpisodes) {
  if (!base.feedUrl) return { ...base, error: "no feed URL from Apple" };
  try {
    const feed = parseFeed(await fetchFeed(base.feedUrl), maxEpisodes);
    return feed ? merge(base, feed) : { ...base, error: "not an RSS feed" };
  } catch (err) {
    return { ...base, error: err.message };
  }
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const country = input.country || "us";
const perTerm = int(input.maxPodcastsPerTerm, 50, 1, 200);
const maxEpisodes = int(input.maxEpisodes, 5, 0, 1000);
const concurrency = int(input.concurrency, 5, 1, 20);
const days = int(input.activeWithinDays, 0, 0, 100_000);
const filter = {
  onlyWithEmail: input.onlyWithEmail === true,
  activeAfter: days > 0 ? new Date(Date.now() - days * 86_400_000).toISOString() : undefined,
};

const seen = new Set();
const fresh = (items) =>
  items.filter((it) => {
    const keys = dedupeKeys(it);
    if (!keys.length || keys.some((k) => seen.has(k))) return false;
    for (const k of keys) seen.add(k);
    return true;
  });

let total = 0;
let stopped = false;
/** Fetch feeds `concurrency` at a time, push the shows that pass the filter, charge for those whose feed was read. */
async function readAndPush(label, candidates) {
  let found = 0;
  for (let i = 0; i < candidates.length && !stopped; i += concurrency) {
    const shows = (await Promise.all(candidates.slice(i, i + concurrency).map((c) => readShow(c, maxEpisodes)))).filter((s) => keep(s, filter));
    if (!shows.length) continue;
    // Pay-per-event: one "podcast" event per show whose feed was read; shows with an error are returned free.
    const billable = shows.filter((s) => !s.error).length;
    const charge = billable ? await Actor.charge({ eventName: "podcast", count: billable }).catch(() => null) : null;
    await Actor.pushData(shows);
    found += shows.length;
    if (charge?.eventChargeLimitReached) {
      log.info("Spending limit reached; stopping.");
      stopped = true;
    }
  }
  log.info(`${label}: ${found} podcasts (${candidates.length} new candidates)`);
  total += found;
}

// 1. Specific podcasts: Apple URLs / IDs are looked up in one batch call, feed URLs are read directly.
const ids = [];
const direct = [];
for (const raw of input.podcasts ?? []) {
  const t = parseTarget(raw);
  if (!t) log.warning(`Could not read "${raw}" as an Apple Podcasts URL, numeric ID or RSS feed URL`);
  else if (t.type === "id") ids.push(t.id);
  else direct.push(fromFeedUrl(t.url));
}
for (let i = 0; i < ids.length && !stopped; i += 100) {
  const batch = [...new Set(ids.slice(i, i + 100))];
  try {
    const found = appleResults(await appleJson(lookupUrl(batch, country))).map((r) => fromApple(r));
    const missing = batch.filter((id) => !found.some((f) => f.podcastId === id));
    if (missing.length) log.warning(`Not found on Apple Podcasts (${country}): ${missing.join(", ")}`);
    await readAndPush("Apple lookup", fresh(found));
  } catch (err) {
    log.warning(err.message);
  }
}
if (direct.length && !stopped) await readAndPush("RSS feeds", fresh(direct));

// 2. Keyword search.
for (const raw of input.searchTerms ?? []) {
  if (stopped) break;
  const term = String(raw ?? "").trim();
  if (!term) continue;
  try {
    const found = appleResults(await appleJson(searchUrl(term, country, perTerm))).slice(0, perTerm).map((r) => fromApple(r, term));
    await readAndPush(`"${term}"`, fresh(found));
  } catch (err) {
    log.warning(err.message);
  }
}
log.info(`Done: ${total} podcasts`);
await Actor.exit();
