import { Actor, log } from "apify";
import { collectEmails, emailKey, lookupDomain, parseEmail, verdict } from "./verify.js";

// DNS-over-HTTPS JSON API: Google first, Cloudflare as fallback. No SMTP connection is ever opened.
const DOH = [
  (name, type) => [`https://dns.google/resolve?name=${encodeURIComponent(name)}&type=${type}`, {}],
  (name, type) => [`https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(name)}&type=${type}`, { accept: "application/dns-json" }],
];

async function dohQuery(name, type) {
  let lastError;
  for (const build of DOH) {
    const [url, headers] = build(name, type);
    try {
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(10_000) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      // 0 = NOERROR, 3 = NXDOMAIN. Anything else (e.g. SERVFAIL) is not an answer; try the other resolver.
      if (json?.Status === 0 || json?.Status === 3) return json;
      throw new Error(`DNS status ${json?.Status}`);
    } catch (err) {
      lastError = err;
    }
  }
  throw new Error(`DNS lookup failed for ${name} (${type}): ${lastError?.message}`);
}

const domainCache = new Map(); // domain -> Promise of the lookup result
function lookupCached(domain) {
  if (!domainCache.has(domain)) domainCache.set(domain, lookupDomain(domain, dohQuery));
  return domainCache.get(domain);
}

async function verify(raw) {
  const parsed = parseEmail(raw);
  const dns = parsed.syntaxValid ? await lookupCached(parsed.domain) : null;
  if (dns?.error) log.warning(dns.error);
  return verdict(parsed, dns);
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const concurrency = Math.min(Math.max(Math.trunc(Number(input.concurrency ?? 10)) || 10, 1), 50);
const emailField = String(input.emailField ?? "").trim() || "emails";

// One item per distinct email (case-insensitive), in first-seen order.
const queue = new Map();
const add = (value) => {
  for (const e of collectEmails(value)) if (!queue.has(emailKey(e))) queue.set(emailKey(e), e);
};
add(input.emails);
if (input.datasetId) {
  try {
    const dataset = await Actor.openDataset(input.datasetId, { forceCloud: true });
    let items = 0;
    await dataset.forEach((item) => {
      items++;
      add(item?.[emailField]);
    });
    log.info(`Dataset ${input.datasetId}: read ${items} items, field "${emailField}"`);
  } catch (err) {
    log.warning(`Could not read dataset ${input.datasetId}: ${err.message}`);
  }
}

const emails = [...queue.values()];
if (!emails.length) log.warning("No emails to check: fill in Emails or pick a dataset.");

const counts = { valid: 0, risky: 0, invalid: 0 };
const BATCH = 200;
for (let start = 0; start < emails.length; start += BATCH) {
  const batch = emails.slice(start, start + BATCH);
  const results = new Array(batch.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(concurrency, batch.length) }, async () => {
    while (next < batch.length) {
      const i = next++;
      results[i] = await verify(batch[i]);
    }
  }));
  // Pay-per-event: one "email" event per checked email.
  const charge = await Actor.charge({ eventName: "email", count: results.length }).catch(() => null);
  await Actor.pushData(results);
  for (const r of results) counts[r.status]++;
  if (charge?.eventChargeLimitReached) {
    log.info("Spending limit reached; stopping.");
    await Actor.exit();
  }
}
log.info(`Done: ${emails.length} emails (${counts.valid} valid, ${counts.risky} risky, ${counts.invalid} invalid), ${domainCache.size} domains looked up`);
await Actor.exit();
