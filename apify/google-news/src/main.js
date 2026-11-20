import { Actor, log } from "apify";
import { TOP_HEADLINES, buildFeeds, itemsFromFeed, locale } from "./news.js";

const USER_AGENT = "GoogleNewsRssReader/0.1 (+https://apify.com)";
const RETRIES = 3;

// One plain request with an honest user-agent; 429 and 5xx are retried with a growing pause.
async function getText(url) {
  let last = "";
  for (let i = 0; i <= RETRIES; i++) {
    if (i) await new Promise((r) => setTimeout(r, 2000 * 2 ** (i - 1)));
    try {
      const res = await fetch(url, {
        headers: { "user-agent": USER_AGENT, accept: "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8" },
        signal: AbortSignal.timeout(30_000),
      });
      if (res.ok) return res.text();
      last = `HTTP ${res.status}`;
      if (res.status !== 429 && res.status < 500) break; // other 4xx will not change on retry
    } catch (err) {
      last = err.message;
    }
  }
  throw new Error(`request failed (${last})`);
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const { language, country } = locale(input);
const max = Math.max(Number(input.maxItemsPerQuery ?? 100) || 100, 1);
const seen = input.dedupe === false ? null : new Set();

let feeds = buildFeeds(input);
if (!feeds.length) {
  log.warning("No queries or topics given; reading top headlines instead.");
  feeds = buildFeeds({ ...input, topHeadlines: true });
}

let total = 0;
for (const { label, url } of feeds) {
  const name = label === TOP_HEADLINES ? "top headlines" : label;
  let xml;
  try {
    xml = await getText(url);
  } catch (err) {
    log.warning(`${name}: ${err.message}; skipping`);
    continue;
  }
  const items = itemsFromFeed(xml, { label, language, country, max, seen });
  if (!items.length) {
    log.info(`${name}: no articles${seen ? " (or all already returned)" : ""}`);
    continue;
  }
  // Pay-per-event: one "article" event per returned article.
  const charge = await Actor.charge({ eventName: "article", count: items.length }).catch(() => null);
  await Actor.pushData(items);
  total += items.length;
  log.info(`${name}: ${items.length} articles`);
  if (charge?.eventChargeLimitReached) {
    log.info("Spending limit reached; stopping.");
    await Actor.exit();
  }
}
log.info(`Done: ${total} articles`);
await Actor.exit();
