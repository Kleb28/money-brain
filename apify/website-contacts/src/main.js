import { Actor, log } from "apify";
import { allowed, extractEmails, extractPhones, extractSocial, normalizeSite, pickLinks, robotsDisallows, SOCIAL_HOST, sourceFields } from "./extract.js";

const UA = "Mozilla/5.0 (compatible; WebsiteContactFinder/0.1; +https://apify.com)";

async function getText(url, ms = 15000) {
  const res = await fetch(url, { headers: { "user-agent": UA, accept: "text/html,*/*;q=0.8" }, redirect: "follow", signal: AbortSignal.timeout(ms) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  if (!/text|html|xml/i.test(res.headers.get("content-type") ?? "text/html")) return "";
  return (await res.text()).slice(0, 2_000_000);
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const maxPages = Math.min(Math.max(Number(input.maxPagesPerSite ?? 5), 1), 15);

const concurrency = Math.min(Math.max(Number(input.concurrency ?? 5), 1), 20);
let stop = false;

// Targets come from the typed list and, optionally, from another Actor's dataset (for example Google Maps Scraper results).
const targets = [];
const seen = new Set();
const add = (raw, source) => {
  const site = normalizeSite(raw);
  if (!site) return log.warning(`Not a website: "${raw}"`);
  if (SOCIAL_HOST.test(site.domain)) return log.info(`Skipped ${site.domain}: a social profile, not the company's own site`);
  if (seen.has(site.domain)) return;
  seen.add(site.domain);
  targets.push({ site, source });
};
for (const raw of input.websites ?? []) add(raw, null);
if (input.datasetId) {
  const field = String(input.websiteField ?? "website");
  const dataset = await Actor.openDataset(String(input.datasetId), { forceCloud: true });
  let rows = 0;
  await dataset.forEach((row) => {
    rows++;
    const raw = row?.[field] ?? row?.website;
    if (raw) add(raw, sourceFields(row));
  });
  log.info(`Dataset ${input.datasetId}: ${rows} rows, ${targets.length} distinct websites to read`);
}
if (!targets.length) log.warning("Nothing to do: give websites or a datasetId whose rows have a website field.");

async function crawl({ site, source }) {
  const item = { domain: site.domain, website: site.start, emails: [], phones: [], linkedin: null, twitter: null, facebook: null, instagram: null, youtube: null, pagesCrawled: 0, sources: [], error: null };
  try {
    const disallows = input.respectRobotsTxt === false ? [] : robotsDisallows(await getText(`${site.start}robots.txt`, 8000).catch(() => ""));
    const home = await getText(site.start);
    const queue = [site.start, ...pickLinks(home, site.start, maxPages - 1)].filter((u) => allowed(u, disallows));
    const emails = new Set();
    const phones = new Set();
    for (const url of queue.slice(0, maxPages)) {
      let html;
      try {
        html = url === site.start ? home : await getText(url);
      } catch {
        continue;
      }
      item.pagesCrawled++;
      const found = extractEmails(html);
      if (found.length) item.sources.push(url);
      found.forEach((e) => emails.add(e));
      extractPhones(html).forEach((p) => phones.add(p));
      for (const [k, v] of Object.entries(extractSocial(html))) item[k] ??= v;
    }
    item.emails = [...emails].filter((e) => !input.sameDomainEmailsOnly || e.endsWith(`@${site.domain}`) || e.endsWith(`.${site.domain}`));
    item.phones = [...phones];
    if (!item.pagesCrawled) item.error = queue.length ? "no page could be read" : "blocked by robots.txt";
  } catch (err) {
    item.error = String(err.message ?? err).slice(0, 200);
  }
  // Pay-per-event: charged only when the site was reached; unreachable sites are returned free.
  const charge = item.error ? null : await Actor.charge({ eventName: "website", count: 1 }).catch(() => null);
  if (source) item.source = source;
  await Actor.pushData(item);
  log.info(`${site.domain}: ${item.emails.length} emails, ${item.phones.length} phones${item.error ? `, error: ${item.error}` : ""}`);
  if (charge?.eventChargeLimitReached && !stop) {
    stop = true;
    log.info("Spending limit reached; stopping.");
  }
}

// A few sites at a time: each site is its own host, so this stays polite while a long list finishes quickly.
const workers = Array.from({ length: Math.min(concurrency, targets.length) }, async () => {
  while (targets.length && !stop) await crawl(targets.shift());
});
await Promise.all(workers);
await Actor.exit();
