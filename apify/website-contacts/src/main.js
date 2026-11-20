import { Actor, log } from "apify";
import { allowed, extractEmails, extractPhones, extractSocial, normalizeSite, pickLinks, robotsDisallows } from "./extract.js";

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

for (const raw of input.websites ?? []) {
  const site = normalizeSite(raw);
  if (!site) {
    log.warning(`Not a website: "${raw}"`);
    continue;
  }
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
  await Actor.pushData(item);
  log.info(`${site.domain}: ${item.emails.length} emails, ${item.phones.length} phones${item.error ? `, error: ${item.error}` : ""}`);
  if (charge?.eventChargeLimitReached) {
    log.info("Spending limit reached; stopping.");
    break;
  }
}
await Actor.exit();
