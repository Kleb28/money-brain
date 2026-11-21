import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { appleResults, cleanEmail, decode, dedupeKeys, fromApple, fromFeedUrl, htmlToText, keep, lookupUrl, merge, parseDuration, parseFeed, parseTarget, searchUrl } from "../src/podcast.js";

const fixture = (name) => readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8");
const FEED = fixture("feed.xml");
const SEARCH = JSON.parse(fixture("itunes-search.json"));

test("parseTarget", () => {
  assert.deepEqual(parseTarget("https://podcasts.apple.com/us/podcast/the-biotech-bench/id1502871393?uo=4"), { type: "id", id: "1502871393" });
  assert.deepEqual(parseTarget("https://itunes.apple.com/lookup?id=1502871393"), { type: "id", id: "1502871393" });
  assert.deepEqual(parseTarget(" 1502871393 "), { type: "id", id: "1502871393" });
  assert.deepEqual(parseTarget("id1502871393"), { type: "id", id: "1502871393" });
  assert.deepEqual(parseTarget("https://feeds.example.com/biotech-bench"), { type: "feed", url: "https://feeds.example.com/biotech-bench" });
  assert.equal(parseTarget("https://podcasts.apple.com/us/browse"), null);
  assert.equal(parseTarget("biotech"), null);
  assert.equal(parseTarget("ftp://example.com/feed.xml"), null);
  assert.equal(parseTarget(""), null);
});

test("searchUrl and lookupUrl", () => {
  assert.equal(searchUrl("startup founders", "US", 500), "https://itunes.apple.com/search?media=podcast&entity=podcast&term=startup%20founders&country=us&limit=200");
  assert.ok(searchUrl("r&d", "not-a-country", 0).endsWith("term=r%26d&country=us&limit=50"));
  assert.equal(lookupUrl(["1", "2"], "gb"), "https://itunes.apple.com/lookup?id=1,2&country=gb");
});

test("decode, htmlToText, parseDuration, cleanEmail", () => {
  assert.equal(decode("&amp;lt; &#169; &#x1F600; &unknown;"), "&lt; © \u{1F600} &unknown;");
  assert.equal(htmlToText("<p>Build &amp; ship</p><ul><li>Go</li></ul>"), "Build & ship\n- Go");
  assert.equal(parseDuration("00:45:12"), 2712);
  assert.equal(parseDuration("32:00"), 1920);
  assert.equal(parseDuration("3240"), 3240);
  assert.equal(parseDuration("about an hour"), null);
  assert.equal(parseDuration(undefined), null);
  assert.equal(cleanEmail(" mailto:Host@Show.fm "), "Host@Show.fm");
  assert.equal(cleanEmail("no email"), null);
  assert.equal(cleanEmail(null), null);
});

test("parseFeed reads channel fields, not item or <image> fields", () => {
  const f = parseFeed(FEED, 2);
  assert.equal(f.title, "The Biotech Bench");
  assert.equal(f.author, "Priya Nair & Helix Media");
  assert.equal(f.ownerName, "Helix Media LLC");
  assert.equal(f.ownerEmail, "hello@biotechbench.example");
  assert.equal(f.website, "https://www.biotechbench.example/");
  assert.equal(f.language, "en-us");
  assert.deepEqual(f.genres, ["Science", "Life Sciences", "Business"]);
  assert.equal(f.description, "Weekly conversations with the scientists & founders building new medicines.\nHosted by Priya Nair.");
  assert.equal(f.explicit, false);
  assert.equal(f.image, "https://cdn.example.com/shows/biotech-bench/cover-3000.jpg");
  assert.equal(f.episodeCount, 4);
  assert.equal(f.latestEpisodeAt, "2026-11-17T08:00:00.000Z");
});

test("parseFeed episodes", () => {
  const f = parseFeed(FEED, 10);
  assert.equal(f.episodes.length, 4);
  assert.deepEqual(f.episodes[0], {
    title: "Ep. 212: Base editing leaves the lab",
    publishedAt: "2026-11-17T08:00:00.000Z",
    duration: 2712,
    audioUrl: "https://media.example.com/biotech-bench/212.mp3?source=rss&v=2",
    url: "https://www.biotechbench.example/episodes/212",
  });
  assert.equal(f.episodes[1].title, "Ep. 211: GLP-1s & the manufacturing crunch");
  assert.equal(f.episodes[1].publishedAt, "2026-11-10T08:00:00.000Z");
  assert.equal(f.episodes[1].duration, 3240);
  assert.equal(f.episodes[1].audioUrl, "https://media.example.com/biotech-bench/211.mp3");
  assert.equal(f.episodes[2].title, "Ep. 210: A founder's guide to Series A");
  assert.equal(f.episodes[2].url, null);
  assert.deepEqual(f.episodes[3], { title: "Trailer", publishedAt: null, duration: null, audioUrl: null, url: null });
  assert.equal(parseFeed(FEED, 2).episodes.length, 2);
  assert.deepEqual(parseFeed(FEED, 0).episodes, []);
});

test("parseFeed sorts episodes newest first when the feed is oldest first", () => {
  const xml = `<rss><channel><title>T</title>
    <item><title>old</title><pubDate>Mon, 05 Jan 2026 10:00:00 GMT</pubDate></item>
    <item><title>new</title><pubDate>Mon, 12 Jan 2026 10:00:00 GMT</pubDate></item></channel></rss>`;
  const f = parseFeed(xml, 1);
  assert.equal(f.episodes[0].title, "new");
  assert.equal(f.latestEpisodeAt, "2026-01-12T10:00:00.000Z");
});

test("parseFeed handles sparse, truncated and non-feed input", () => {
  const sparse = parseFeed("<rss><channel><title>Bare &amp; simple</title><category>Tech</category><description>Plain &lt;b&gt;text&lt;/b&gt;</description><image><url>https://x.example/i.png</url></image></channel></rss>");
  assert.equal(sparse.title, "Bare & simple");
  assert.equal(sparse.ownerEmail, null);
  assert.equal(sparse.website, null);
  assert.deepEqual(sparse.genres, ["Tech"]);
  assert.equal(sparse.description, "Plain text");
  assert.equal(sparse.image, "https://x.example/i.png");
  assert.equal(sparse.explicit, null);
  assert.equal(sparse.episodeCount, 0);
  assert.equal(sparse.latestEpisodeAt, null);

  // Cut in the middle of the second item (size cap): the first item still counts, the partial one does not leak into channel fields.
  const cut = parseFeed(FEED.slice(0, FEED.indexOf("Ep. 211") + 10), 5);
  assert.equal(cut.episodeCount, 1);
  assert.equal(cut.title, "The Biotech Bench");
  assert.equal(cut.ownerEmail, "hello@biotechbench.example");

  assert.equal(parseFeed("<!doctype html><html><body>Not found</body></html>"), null);
  assert.equal(parseFeed(""), null);
});

test("fromApple and appleResults", () => {
  const rows = appleResults(SEARCH);
  assert.equal(rows.length, 3);
  const a = fromApple(rows[0], "biotech");
  assert.equal(a.searchTerm, "biotech");
  assert.equal(a.podcastId, "1502871393");
  assert.equal(a.title, "The Biotech Bench");
  assert.equal(a.author, "Helix Media");
  assert.equal(a.feedUrl, "https://feeds.example.com/biotech-bench");
  assert.equal(a.applePodcastsUrl, "https://podcasts.apple.com/us/podcast/the-biotech-bench/id1502871393");
  assert.deepEqual(a.genres, ["Life Sciences", "Science", "Business"]);
  assert.equal(a.episodeCount, 212);
  assert.equal(a.latestEpisodeAt, "2026-11-17T08:00:00.000Z");
  assert.equal(a.explicit, false);
  assert.equal(a.error, null);
  assert.equal(fromApple(rows[1]).explicit, true);
  assert.equal(fromApple(rows[1]).searchTerm, null);
  assert.equal(fromApple(rows[2]).feedUrl, null);
  assert.deepEqual(appleResults({ resultCount: 0, results: [] }), []);
  assert.deepEqual(appleResults(null), []);
  assert.deepEqual(appleResults({ results: [{ wrapperType: "artist", artistName: "x" }] }), []);
});

test("merge keeps Apple fields and adds feed fields", () => {
  const item = merge(fromApple(SEARCH.results[0], "biotech"), parseFeed(FEED, 1));
  assert.deepEqual(Object.keys(item), [
    "searchTerm", "podcastId", "title", "author", "ownerName", "ownerEmail", "website", "feedUrl", "applePodcastsUrl",
    "genres", "language", "episodeCount", "latestEpisodeAt", "description", "image", "explicit", "episodes", "error",
  ]);
  assert.equal(item.podcastId, "1502871393");
  assert.equal(item.author, "Priya Nair & Helix Media");
  assert.equal(item.ownerEmail, "hello@biotechbench.example");
  assert.equal(item.episodeCount, 4); // episodes in the feed, not Apple's trackCount
  assert.equal(item.episodes.length, 1);
  assert.equal(item.error, null);

  const direct = merge(fromFeedUrl("https://feeds.example.com/biotech-bench"), parseFeed(FEED, 0));
  assert.equal(direct.title, "The Biotech Bench");
  assert.equal(direct.podcastId, null);
  assert.equal(direct.applePodcastsUrl, null);

  const base = fromApple(SEARCH.results[1]);
  assert.equal(merge(base, null), base);
});

test("dedupeKeys", () => {
  const a = fromApple(SEARCH.results[0]);
  assert.deepEqual(dedupeKeys(a), ["id:1502871393", "feed:feeds.example.com/biotech-bench"]);
  assert.deepEqual(dedupeKeys(fromFeedUrl("http://www.Feeds.Example.com/biotech-bench/")), ["feed:feeds.example.com/biotech-bench"]);
  assert.deepEqual(dedupeKeys(fromApple({})), []);
});

test("keep", () => {
  const show = { ownerEmail: "a@b.co", latestEpisodeAt: "2026-11-10T00:00:00.000Z" };
  assert.equal(keep(show), true);
  assert.equal(keep(show, { onlyWithEmail: true }), true);
  assert.equal(keep({ ...show, ownerEmail: null }, { onlyWithEmail: true }), false);
  assert.equal(keep(show, { activeAfter: "2026-11-01T00:00:00.000Z" }), true);
  assert.equal(keep(show, { activeAfter: "2026-11-15T00:00:00.000Z" }), false);
  assert.equal(keep({ ...show, latestEpisodeAt: null }, { activeAfter: "2026-11-01T00:00:00.000Z" }), false);
});
