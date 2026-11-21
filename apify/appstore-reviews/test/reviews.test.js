import test from "node:test";
import assert from "node:assert/strict";
import { feedUrl, keep, parseAppRef, parseFeedPage } from "../src/reviews.js";

const entry = (over = {}) => ({
  author: { name: { label: "sam" }, uri: { label: "x" } },
  updated: { label: "2026-11-18T07:12:44-07:00" },
  "im:rating": { label: "2" },
  "im:version": { label: "4.1" },
  id: { label: "13000000001" },
  title: { label: "Crashes" },
  content: { label: "Crashes on launch", attributes: { type: "text" } },
  "im:voteSum": { label: "3" },
  "im:voteCount": { label: "5" },
  ...over,
});

test("parseAppRef", () => {
  assert.deepEqual(parseAppRef("284882215"), { id: "284882215" });
  assert.deepEqual(parseAppRef("https://apps.apple.com/gb/app/facebook/id284882215"), { id: "284882215", country: "gb" });
  assert.deepEqual(parseAppRef("Duolingo"), { name: "Duolingo" });
  assert.equal(parseAppRef("  "), null);
});

test("parseFeedPage: array, single object, app entry without rating, empty", () => {
  const ctx = { appId: "1", appName: "A", country: "us" };
  const many = parseFeedPage({ feed: { entry: [{ title: { label: "the app" } }, entry()] } }, ctx);
  assert.equal(many.length, 1);
  assert.equal(many[0].rating, 2);
  assert.equal(many[0].date, "2026-11-18T14:12:44.000Z");
  assert.equal(many[0].helpfulVotes, 3);
  assert.equal(parseFeedPage({ feed: { entry: entry() } }, ctx).length, 1);
  assert.deepEqual(parseFeedPage({ feed: {} }, ctx), []);
  assert.deepEqual(parseFeedPage(null, ctx), []);
});

test("keep", () => {
  const r = { rating: 2, date: "2026-11-18T14:12:44.000Z" };
  assert.equal(keep(r, {}), true);
  assert.equal(keep(r, { minRating: 3 }), false);
  assert.equal(keep(r, { maxRating: 2 }), true);
  assert.equal(keep(r, { since: "2026-11-19T00:00:00.000Z" }), false);
});

test("feedUrl", () => {
  assert.equal(feedUrl("us", "1", 2, "mostrecent"), "https://itunes.apple.com/us/rss/customerreviews/page=2/id=1/sortby=mostrecent/json");
});
