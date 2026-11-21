import test from "node:test";
import assert from "node:assert/strict";
import { buildFeeds, buildQuery, decode, htmlToText, itemsFromFeed, normalize, parseRss, relatedCount, stripSource } from "../src/news.js";

// Shape of a Google News search feed: escaped HTML in <description>, publisher in <source url="...">.
const FIXTURE = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
<generator>NFE/5.0</generator>
<title>"openai" - Google News</title>
<link>https://news.google.com/search?q=openai&amp;hl=en-US&amp;gl=US&amp;ceid=US:en</link>
<language>en-US</language>
<webMaster>news-webmaster@google.com</webMaster>
<copyright>Copyright © 2026 Google. All rights reserved.</copyright>
<lastBuildDate>Fri, 20 Nov 2026 09:30:00 GMT</lastBuildDate>
<description>Google News</description>
<item>
<title>OpenAI signs chip supply deal with AT&amp;T partner - Reuters</title>
<link>https://news.google.com/rss/articles/CBMiaEFVX3lxTE5fAAA?oc=5</link>
<guid isPermaLink="false">CBMiaEFVX3lxTE5fAAA</guid>
<pubDate>Thu, 19 Nov 2026 14:05:00 GMT</pubDate>
<description>&lt;a href="https://news.google.com/rss/articles/CBMiaEFVX3lxTE5fAAA?oc=5" target="_blank"&gt;OpenAI signs chip supply deal with AT&amp;amp;T partner&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Reuters&lt;/font&gt;</description>
<source url="https://www.reuters.com">Reuters</source>
</item>
<item>
<title>What the new model means for developers - The Verge</title>
<link>https://news.google.com/rss/articles/CBMiBBBB?oc=5</link>
<guid isPermaLink="false">CBMiBBBB</guid>
<pubDate>Wed, 18 Nov 2026 22:40:10 GMT</pubDate>
<description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/rss/articles/CBMiBBBB?oc=5" target="_blank"&gt;What the new model means for developers&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;The Verge&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/rss/articles/CBMiCCCC?oc=5" target="_blank"&gt;Developers react to the launch&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;TechCrunch&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/rss/articles/CBMiDDDD?oc=5" target="_blank"&gt;Pricing explained&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Ars Technica&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description>
<source url="https://www.theverge.com">The Verge</source>
</item>
<item>
<title><![CDATA[Q&A: safety - a short history - MIT Technology Review]]></title>
<link>https://news.google.com/rss/articles/CBMiEEEE?oc=5</link>
<guid isPermaLink="false">CBMiEEEE</guid>
<pubDate>not a date</pubDate>
<description></description>
<source url='https://www.technologyreview.com'>MIT Technology Review</source>
</item>
</channel>
</rss>`;

test("decode handles named and numeric entities, one level at a time", () => {
  assert.equal(decode("&lt;b&gt; &amp;amp; &#39;x&#x27; &quot;y&quot; &#8217; &unknown;"), "<b> &amp; 'x' \"y\" ’ &unknown;");
});

test("htmlToText strips tags and decodes entities", () => {
  assert.equal(htmlToText('<a href="u">Tom &amp; Jerry</a>&nbsp;&nbsp;<font color="#6f6f6f">BBC</font>'), "Tom & Jerry BBC");
  assert.equal(htmlToText("<ol><li>One</li><li>Two</li></ol>"), "One\nTwo");
});

test("parseRss reads items, CDATA and the source url attribute", () => {
  const items = parseRss(FIXTURE);
  assert.equal(items.length, 3);
  assert.equal(items[0].title, "OpenAI signs chip supply deal with AT&T partner - Reuters");
  assert.equal(items[0].link, "https://news.google.com/rss/articles/CBMiaEFVX3lxTE5fAAA?oc=5");
  assert.equal(items[0].guid, "CBMiaEFVX3lxTE5fAAA");
  assert.equal(items[0].source, "Reuters");
  assert.equal(items[0].sourceUrl, "https://www.reuters.com");
  assert.ok(items[0].description.startsWith('<a href="https://news.google.com/'));
  assert.equal(items[2].title, "Q&A: safety - a short history - MIT Technology Review");
  assert.equal(items[2].sourceUrl, "https://www.technologyreview.com");
  assert.deepEqual(parseRss("<html><body>Sorry</body></html>"), []);
  assert.deepEqual(parseRss(""), []);
});

test("stripSource removes only the matching publisher suffix", () => {
  assert.equal(stripSource("A - B - Reuters", "Reuters"), "A - B");
  assert.equal(stripSource("A - B", "Reuters"), "A - B");
  assert.equal(stripSource("A - B", null), "A - B");
  assert.equal(stripSource(" - Reuters", "Reuters"), "- Reuters");
});

test("relatedCount", () => {
  assert.equal(relatedCount('<a href="u">t</a>'), null);
  assert.equal(relatedCount("<ol><li>a</li></ol>"), null);
  assert.equal(relatedCount("<ol><li>a</li><li>b</li><li>c</li></ol>"), 2);
});

test("normalize", () => {
  const [a, b, c] = parseRss(FIXTURE).map((x) => normalize(x, { label: "openai", language: "en", country: "US" }));
  assert.deepEqual(a, {
    query: "openai",
    title: "OpenAI signs chip supply deal with AT&T partner",
    source: "Reuters",
    sourceUrl: "https://www.reuters.com",
    publishedAt: "2026-11-19T14:05:00.000Z",
    link: "https://news.google.com/rss/articles/CBMiaEFVX3lxTE5fAAA?oc=5",
    guid: "CBMiaEFVX3lxTE5fAAA",
    snippet: "OpenAI signs chip supply deal with AT&T partner Reuters",
    language: "en",
    country: "US",
  });
  assert.equal(b.title, "What the new model means for developers");
  assert.equal(b.relatedCount, 2);
  assert.equal(b.snippet, "What the new model means for developers The Verge\nDevelopers react to the launch TechCrunch\nPricing explained Ars Technica");
  assert.equal(c.title, "Q&A: safety - a short history");
  assert.equal(c.publishedAt, null);
  assert.equal(c.snippet, null);
  assert.equal("relatedCount" in c, false);
});

test("buildQuery appends time operators", () => {
  assert.equal(buildQuery(" openai "), "openai");
  assert.equal(buildQuery("openai", { timeRange: "any" }), "openai");
  assert.equal(buildQuery("openai", { timeRange: "1d" }), "openai when:1d");
  assert.equal(buildQuery("openai", { timeRange: "7d", after: "2026-11-01", before: "2026-11-15T00:00:00.000Z" }), "openai when:7d after:2026-11-01 before:2026-11-15");
  assert.equal(buildQuery("openai", { timeRange: "2w", after: "nonsense" }), "openai");
});

test("buildFeeds", () => {
  assert.deepEqual(buildFeeds({}), []);
  const feeds = buildFeeds({ queries: ["site:reuters.com biotech", "", "site:reuters.com biotech"], topics: ["business", "WEATHER"], topHeadlines: true, timeRange: "1d" });
  assert.deepEqual(feeds, [
    { label: "site:reuters.com biotech", url: "https://news.google.com/rss/search?q=site%3Areuters.com%20biotech%20when%3A1d&hl=en&gl=US&ceid=US:en" },
    { label: "BUSINESS", url: "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en&gl=US&ceid=US:en" },
    { label: "TOP_HEADLINES", url: "https://news.google.com/rss?hl=en&gl=US&ceid=US:en" },
  ]);
  assert.equal(buildFeeds({ topHeadlines: true, language: "de", country: "de" })[0].url, "https://news.google.com/rss?hl=de&gl=DE&ceid=DE:de");
});

test("itemsFromFeed applies the limit and dedupes by link across feeds", () => {
  const opts = { label: "openai", language: "en", country: "US" };
  assert.equal(itemsFromFeed(FIXTURE, { ...opts, max: 2 }).length, 2);
  const seen = new Set();
  assert.equal(itemsFromFeed(FIXTURE, { ...opts, seen }).length, 3);
  assert.equal(itemsFromFeed(FIXTURE, { ...opts, label: "other", seen }).length, 0);
  assert.equal(itemsFromFeed(FIXTURE, { ...opts, label: "other" }).length, 3);
});
