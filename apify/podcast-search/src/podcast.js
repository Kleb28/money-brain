// Pure logic: Apple iTunes Search API shapes, a small RSS reader for podcast feeds, filters and dedupe keys.
// No network here; src/main.js does the I/O.

export const USER_AGENT = "PodcastFeedReader/0.1 (+https://apify.com)";

const NAMED = { lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", amp: "&" };
/** One pass, so "&amp;lt;" becomes "&lt;" and not "<". */
export const decode = (s) =>
  String(s ?? "").replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] !== "#") return NAMED[e.toLowerCase()] ?? m;
    const n = /^#x/i.test(e) ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
    try {
      return String.fromCodePoint(n);
    } catch {
      return m;
    }
  });
export const htmlToText = (html) =>
  decode(String(html ?? "").replace(/<(br|\/p|\/div|\/li|\/h\d)\s*\/?>/gi, "\n").replace(/<li[^>]*>/gi, "- ").replace(/<[^>]+>/g, ""))
    .replace(/[ \t\r]+/g, " ").replace(/ ?\n ?/g, "\n").replace(/\n{2,}/g, "\n\n").trim();
const iso = (v) => {
  if (v === undefined || v === null || v === "") return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
};

// --- XML helpers (enough for RSS 2.0 + the itunes: namespace; not a general XML parser) ---

/** Inner XML of the first <name>...</name>, or null. Self-closing tags do not match. */
const inner = (xml, name) => {
  if (!xml) return null;
  const m = new RegExp(`<${name}(?:\\s[^>]*?)?(?<!/)>([\\s\\S]*?)</${name}\\s*>`, "i").exec(xml);
  return m ? m[1] : null;
};
/** CDATA content is taken as is; anything else gets its XML entities decoded. */
const unwrap = (s) => {
  if (s === null || s === undefined) return null;
  return /<!\[CDATA\[/.test(s) ? s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, (_, c) => c) : decode(s);
};
const text = (xml, name) => {
  const v = unwrap(inner(xml, name));
  return v === null ? null : v.replace(/\s+/g, " ").trim() || null;
};
const attr = (xml, name, attribute) => {
  if (!xml) return null;
  const m = new RegExp(`<${name}\\s[^>]*?\\b${attribute}\\s*=\\s*(?:"([^"]*)"|'([^']*)')`, "i").exec(xml);
  return m ? decode(m[1] ?? m[2]).trim() || null : null;
};

/** "3723" | "1:02:03" | "62:03" -> seconds, else null. */
export function parseDuration(v) {
  const s = String(v ?? "").trim();
  if (/^\d+(\.\d+)?$/.test(s)) return Math.round(Number(s));
  if (/^\d+(:\d{1,2}){1,2}$/.test(s)) return s.split(":").reduce((sum, p) => sum * 60 + Number(p), 0);
  return null;
}
const parseExplicit = (v) => {
  const s = String(v ?? "").trim().toLowerCase();
  if (["yes", "true", "explicit"].includes(s)) return true;
  if (["no", "false", "clean", "cleaned", "notexplicit"].includes(s)) return false;
  return null;
};
export const cleanEmail = (v) => {
  const s = String(v ?? "").trim().replace(/^mailto:/i, "");
  return /^[^\s@<>,;]+@[^\s@<>,;]+\.[^\s@<>,;]+$/.test(s) ? s : null;
};
const httpUrl = (v) => (/^https?:\/\//i.test(String(v ?? "").trim()) ? String(v).trim() : null);

const ITEM = /<item[\s>][\s\S]*?<\/item\s*>/gi;

/**
 * Podcast RSS XML -> channel fields + latest episodes. Returns null when the text is not an RSS feed.
 * Works on a feed cut off mid-way (size cap): a trailing incomplete <item> is ignored.
 */
export function parseFeed(xml, maxEpisodes = 5) {
  const src = String(xml ?? "");
  const start = src.search(/<channel[\s>]/i);
  if (start < 0) return null;
  const body = src.slice(start);
  const items = body.match(ITEM) ?? [];
  // Channel-level tags only: drop the items, then the RSS <image> block (it has its own <title> and <link>).
  const head = body.replace(ITEM, "").replace(/<item[\s>][\s\S]*$/i, "");
  const plain = head.replace(/<image[\s>][\s\S]*?<\/image\s*>/gi, "");

  const owner = inner(head, "itunes:owner");
  const categories = [...head.matchAll(/<itunes:category\s[^>]*?\btext\s*=\s*(?:"([^"]*)"|'([^']*)')/gi)].map((m) => decode(m[1] ?? m[2]).trim());
  if (!categories.length) for (const m of plain.matchAll(/<category(?:\s[^>]*?)?(?<!\/)>([\s\S]*?)<\/category\s*>/gi)) categories.push((unwrap(m[1]) ?? "").trim());
  const description = unwrap(inner(plain, "description") ?? inner(plain, "itunes:summary") ?? inner(plain, "itunes:subtitle"));

  const episodes = items.map((it) => ({
    title: text(it, "title") ?? text(it, "itunes:title"),
    publishedAt: iso(text(it, "pubDate")),
    duration: parseDuration(text(it, "itunes:duration")),
    audioUrl: httpUrl(attr(it, "enclosure", "url")),
    url: httpUrl(text(it, "link")),
  }));
  // Newest first; feeds are almost always in that order already, undated episodes go last.
  const sorted = episodes
    .map((e, i) => [e, i])
    .sort(([a, i], [b, j]) => (b.publishedAt ?? "").localeCompare(a.publishedAt ?? "") || i - j)
    .map(([e]) => e);

  return {
    title: text(plain, "title"),
    author: text(plain, "itunes:author"),
    ownerName: text(owner, "itunes:name"),
    ownerEmail: cleanEmail(text(owner, "itunes:email")),
    website: httpUrl(text(plain, "link")),
    language: text(plain, "language"),
    genres: [...new Set(categories.filter(Boolean))],
    description: description ? htmlToText(description) || null : null,
    explicit: parseExplicit(text(plain, "itunes:explicit")),
    image: httpUrl(attr(head, "itunes:image", "href")) ?? httpUrl(text(inner(head, "image"), "url")),
    episodeCount: items.length,
    latestEpisodeAt: sorted[0]?.publishedAt ?? null,
    episodes: sorted.slice(0, Math.max(Number(maxEpisodes) || 0, 0)),
  };
}

// --- Apple ---

const cc = (country) => (/^[a-z]{2}$/i.test(String(country ?? "").trim()) ? String(country).trim().toLowerCase() : "us");
export const searchUrl = (term, country, limit) =>
  `https://itunes.apple.com/search?media=podcast&entity=podcast&term=${encodeURIComponent(term)}&country=${cc(country)}&limit=${Math.min(Math.max(Math.trunc(Number(limit)) || 50, 1), 200)}`;
export const lookupUrl = (ids, country) => `https://itunes.apple.com/lookup?id=${[].concat(ids).join(",")}&country=${cc(country)}`;

/** "https://podcasts.apple.com/us/podcast/x/id123" | "123" | "https://example.com/feed.xml" -> {type, id|url}, or null. */
export function parseTarget(raw) {
  const s = String(raw ?? "").trim();
  const bare = /^(?:id)?(\d{4,})$/i.exec(s);
  if (bare) return { type: "id", id: bare[1] };
  let u;
  try {
    u = new URL(s);
  } catch {
    return null;
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") return null;
  if (/(^|\.)apple\.com$/i.test(u.hostname)) {
    const m = /\/id(\d+)/.exec(u.pathname) ?? /^(\d+)$/.exec(u.searchParams.get("id") ?? "");
    return m ? { type: "id", id: m[1] } : null;
  }
  return { type: "feed", url: u.href };
}

const blank = () => ({
  searchTerm: null, podcastId: null, title: null, author: null, ownerName: null, ownerEmail: null, website: null,
  feedUrl: null, applePodcastsUrl: null, genres: [], language: null, episodeCount: null, latestEpisodeAt: null,
  description: null, image: null, explicit: null, episodes: [], error: null,
});

/** One iTunes Search / Lookup result -> output item with the fields Apple knows. */
export function fromApple(r, searchTerm = null) {
  const id = r?.collectionId ?? r?.trackId;
  return {
    ...blank(),
    searchTerm,
    podcastId: id === undefined || id === null ? null : String(id),
    title: r?.collectionName ?? r?.trackName ?? null,
    author: r?.artistName ?? null,
    feedUrl: httpUrl(r?.feedUrl),
    applePodcastsUrl: r?.collectionViewUrl ? String(r.collectionViewUrl).split("?")[0] : null,
    genres: (r?.genres ?? (r?.primaryGenreName ? [r.primaryGenreName] : [])).filter((g) => g && g !== "Podcasts"),
    episodeCount: Number.isFinite(r?.trackCount) ? r.trackCount : null,
    latestEpisodeAt: iso(r?.releaseDate),
    image: r?.artworkUrl600 ?? r?.artworkUrl100 ?? null,
    explicit: parseExplicit(r?.collectionExplicitness ?? r?.trackExplicitness),
  };
}
export const fromFeedUrl = (url) => ({ ...blank(), feedUrl: url });
/** Podcast results of a Search / Lookup response (lookup can also return non-podcast rows). */
export const appleResults = (json) => (json?.results ?? []).filter((r) => r && (r.kind === "podcast" || r.wrapperType === "track" || r.feedUrl));

/** Feed fields win where the feed has them; Apple's stay as fallback. */
export function merge(base, feed) {
  if (!feed) return base;
  return {
    ...base,
    title: base.title ?? feed.title,
    author: feed.author ?? base.author,
    ownerName: feed.ownerName,
    ownerEmail: feed.ownerEmail,
    website: feed.website,
    genres: feed.genres.length ? feed.genres : base.genres,
    language: feed.language,
    episodeCount: feed.episodeCount,
    latestEpisodeAt: feed.latestEpisodeAt ?? base.latestEpisodeAt,
    description: feed.description,
    image: feed.image ?? base.image,
    explicit: feed.explicit ?? base.explicit,
    episodes: feed.episodes,
  };
}

/** Keys used to drop the same show found by several terms. */
export function dedupeKeys(item) {
  const keys = [];
  if (item.podcastId) keys.push(`id:${item.podcastId}`);
  if (item.feedUrl) keys.push(`feed:${item.feedUrl.replace(/^https?:\/\/(www\.)?/i, "").replace(/\/+$/, "").toLowerCase()}`);
  return keys;
}

/** f.activeAfter is an ISO timestamp; a show with no known episode date does not pass it. */
export function keep(item, f = {}) {
  if (f.onlyWithEmail && !item.ownerEmail) return false;
  if (f.activeAfter && !(item.latestEpisodeAt && item.latestEpisodeAt >= f.activeAfter)) return false;
  return true;
}
