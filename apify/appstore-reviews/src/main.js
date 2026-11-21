import { Actor, log } from "apify";
import { feedUrl, keep, parseAppRef, parseFeedPage } from "./reviews.js";

const MAX_PAGES = 10; // Apple serves 10 pages of 50

async function getJson(url, tries = 3) {
  for (let i = 0; ; i++) {
    const res = await fetch(url, { headers: { accept: "application/json" } });
    if (res.ok) return res.json();
    if (res.status === 404 || res.status === 400) return null; // past the last page, or no such app in this country
    if (i >= tries - 1) throw new Error(`Apple feed ${res.status} for ${url}`);
    await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
  }
}

async function resolveApp(ref, country) {
  const url = ref.id
    ? `https://itunes.apple.com/lookup?id=${ref.id}&country=${country}`
    : `https://itunes.apple.com/search?term=${encodeURIComponent(ref.name)}&entity=software&limit=1&country=${country}`;
  const hit = (await getJson(url))?.results?.[0];
  if (!hit) return ref.id ? { id: ref.id, name: null } : null;
  return { id: String(hit.trackId), name: hit.trackName ?? null };
}

const feedPage = async (country, app, page, sort) =>
  parseFeedPage(await getJson(feedUrl(country, app.id, page, sort)), { appId: app.id, appName: app.name, country });

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const countries = (input.countries?.length ? input.countries : ["us"]).map((c) => String(c).trim().toLowerCase()).filter((c) => /^[a-z]{2}$/.test(c));
const max = Math.min(Math.max(Number(input.maxReviewsPerApp ?? 100), 1), 500);
const sortBy = input.sortBy === "mosthelpful" ? "mosthelpful" : "mostrecent";
const filter = {
  since: input.since ? new Date(input.since).toISOString() : undefined,
  minRating: input.minRating,
  maxRating: input.maxRating,
};
if (!countries.length) throw new Error("countries: give at least one two-letter code such as us");

let total = 0;
for (const raw of input.apps ?? []) {
  const ref = parseAppRef(raw);
  if (!ref) continue;
  const app = await resolveApp(ref, ref.country ?? countries[0]);
  if (!app) {
    log.warning(`No App Store app found for "${raw}"`);
    continue;
  }
  for (const country of countries) {
    let got = 0;
    let sort = sortBy;
    for (let page = 1; page <= MAX_PAGES && got < max; page++) {
      let reviews = await feedPage(country, app, page, sort);
      if (!reviews.length && page === 1) {
        // Apple's feed intermittently serves an empty "most recent" list while "most helpful" still works.
        for (const wait of [5000, 15000]) {
          await new Promise((r) => setTimeout(r, wait));
          reviews = await feedPage(country, app, 1, sort);
          if (reviews.length) break;
        }
        if (!reviews.length && sort === "mostrecent") {
          reviews = await feedPage(country, app, 1, "mosthelpful");
          if (reviews.length) {
            sort = "mosthelpful";
            log.warning(`${app.name ?? app.id} [${country}]: Apple's most-recent feed is empty right now; returning most-helpful reviews instead (date filter still applied).`);
          }
        }
      }
      if (!reviews.length) break;
      const batch = reviews.filter((r) => keep(r, filter)).slice(0, max - got);
      if (batch.length) {
        // Pay-per-event: one "review" event per returned review. Stops cleanly when the user's spending limit is reached.
        const charge = await Actor.charge({ eventName: "review", count: batch.length }).catch(() => null);
        await Actor.pushData(batch);
        got += batch.length;
        if (charge?.eventChargeLimitReached) {
          log.info("Spending limit reached; stopping.");
          await Actor.exit();
        }
      }
      // Newest first: once a page holds reviews older than `since`, later pages are older still.
      if (filter.since && sort === "mostrecent" && reviews.some((r) => r.date && r.date < filter.since)) break;
    }
    log.info(`${app.name ?? app.id} [${country}]: ${got} reviews`);
    total += got;
  }
}
log.info(`Done: ${total} reviews`);
await Actor.exit();
