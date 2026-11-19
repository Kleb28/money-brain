// Pure helpers: no network, so they can be unit-tested.

/** Accepts a numeric ID, an App Store URL (…/id284882215) or a free-text name. */
export function parseAppRef(raw) {
  const s = String(raw ?? "").trim();
  if (!s) return null;
  if (/^\d{5,}$/.test(s)) return { id: s };
  const m = /\/id(\d{5,})/.exec(s);
  if (m) {
    const c = /apps\.apple\.com\/([a-z]{2})\//i.exec(s);
    return { id: m[1], country: c ? c[1].toLowerCase() : undefined };
  }
  return { name: s };
}

const label = (o) => (o && typeof o === "object" ? o.label : undefined);

/** Turns one page of Apple's customer-reviews JSON feed into flat review objects. */
export function parseFeedPage(json, { appId, appName, country }) {
  let entries = json?.feed?.entry ?? [];
  if (!Array.isArray(entries)) entries = [entries];
  const out = [];
  for (const e of entries) {
    const rating = Number(label(e["im:rating"]));
    if (!rating) continue; // older feeds put the app itself first, without a rating
    const votes = Number(label(e["im:voteCount"]) ?? 0);
    out.push({
      appId,
      appName: appName ?? null,
      country,
      reviewId: label(e.id) ?? null,
      rating,
      title: label(e.title) ?? "",
      text: label(e.content) ?? "",
      version: label(e["im:version"]) ?? null,
      author: label(e.author?.name) ?? null,
      date: label(e.updated) ? new Date(label(e.updated)).toISOString() : null,
      helpfulVotes: Number(label(e["im:voteSum"]) ?? 0),
      totalVotes: votes,
      url: `https://apps.apple.com/${country}/app/id${appId}?see-all=reviews`,
    });
  }
  return out;
}

export function keep(review, { since, minRating, maxRating }) {
  if (minRating && review.rating < minRating) return false;
  if (maxRating && review.rating > maxRating) return false;
  if (since && review.date && review.date < since) return false;
  return true;
}

export const feedUrl = (country, appId, page, sortBy) =>
  `https://itunes.apple.com/${country}/rss/customerreviews/page=${page}/id=${appId}/sortby=${sortBy}/json`;
