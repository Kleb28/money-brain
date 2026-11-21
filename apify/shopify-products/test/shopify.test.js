import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  errorItem, feedAllowedByRobots, feedPath, feedUrl, htmlToText, keep, normProduct, normTags, parseFeed, parseMeta, parseStore, retryDelayMs, robotsAllows, toVariantRows,
} from "../src/shopify.js";

const fixture = readFileSync(new URL("./fixtures/products.json", import.meta.url), "utf8");
const ctx = { store: "www.allbirds.com", shopName: "Allbirds", currency: "USD" };
const items = () => parseFeed(fixture).map((p) => normProduct(p, ctx));

test("parseStore", () => {
  assert.deepEqual(parseStore("https://www.allbirds.com"), { store: "www.allbirds.com", origin: "https://www.allbirds.com", collection: null });
  assert.deepEqual(parseStore("Allbirds.com/"), { store: "allbirds.com", origin: "https://allbirds.com", collection: null });
  assert.equal(parseStore("https://www.gymshark.com/collections/all").collection, "all");
  assert.equal(parseStore("http://shop.example.com/en-us/collections/new-in/products/tee?variant=1").collection, "new-in");
  assert.equal(parseStore("https://shop.example.com/collections/sale/products.json?page=3").collection, "sale");
  assert.equal(parseStore("https://shop.example.com/products/tee").collection, null);
  assert.equal(parseStore("not a store"), null);
  assert.equal(parseStore("localhost"), null);
  assert.equal(parseStore(""), null);
});

test("feedUrl", () => {
  assert.equal(feedUrl(parseStore("allbirds.com")), "https://allbirds.com/products.json?limit=250&page=1");
  assert.equal(feedUrl(parseStore("https://www.gymshark.com/collections/all"), 3), "https://www.gymshark.com/collections/all/products.json?limit=250&page=3");
  assert.equal(feedPath(parseStore("allbirds.com"), 2), "/products.json?limit=250&page=2");
});

test("robots.txt: Shopify's default rules leave the feed open", () => {
  const robots = [
    "# we use Shopify as our ecommerce platform",
    "User-agent: *",
    "Disallow: /admin",
    "Disallow: /cart",
    "Disallow: /checkout",
    "Disallow: /collections/*sort_by*",
    "Disallow: /collections/*+*",
    "Disallow: /search",
    "Disallow: /*?*oseid=*",
    "Sitemap: https://www.allbirds.com/sitemap.xml",
    "",
    "User-agent: Nutch",
    "Disallow: /",
  ].join("\n");
  assert.equal(feedAllowedByRobots(robots, parseStore("www.allbirds.com")), true);
  assert.equal(feedAllowedByRobots(robots, parseStore("www.allbirds.com/collections/mens")), true);
  assert.equal(robotsAllows(robots, "/cart"), false);
  assert.equal(robotsAllows(robots, "/collections/mens?sort_by=price"), false);
  assert.equal(feedAllowedByRobots("", parseStore("a.com")), true);
});

test("robots.txt: disallowed feed or site is detected", () => {
  const t = parseStore("shop.example.com");
  const c = parseStore("shop.example.com/collections/all");
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /", t), false);
  assert.equal(feedAllowedByRobots("User-agent: *\r\nDisallow: /products.json\r\n", t), false);
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /products.json$", t), false);
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /*.json", c), false);
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /products.json", c), true);
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /collections/", c), false);
  // a longer Allow beats a shorter Disallow; an empty Disallow restricts nothing
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /\nAllow: /products.json", t), true);
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow:", t), true);
  // rules for other bots do not apply; several user-agent lines share one group
  assert.equal(feedAllowedByRobots("User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /admin", t), true);
  assert.equal(feedAllowedByRobots("User-agent: GPTBot\nUser-agent: *\nDisallow: /", t), false);
  // a group naming this reader takes precedence over *
  assert.equal(feedAllowedByRobots("User-agent: *\nDisallow: /admin\n\nUser-agent: ShopifyProductsReader\nDisallow: /", t), false);
});

test("parseFeed and parseMeta", () => {
  assert.equal(parseFeed(fixture).length, 3);
  assert.deepEqual(parseFeed('{"products":[]}'), []);
  assert.equal(parseFeed("<!doctype html><html><body>Enter store password</body></html>"), null);
  assert.equal(parseFeed('{"errors":"Not Found"}'), null);
  assert.deepEqual(parseMeta('{"id":1,"name":"Allbirds","country":"US","currency":"USD","money_format":"${{amount}}"}'), { shopName: "Allbirds", currency: "USD" });
  assert.deepEqual(parseMeta("<html>"), { shopName: null, currency: null });
});

test("normProduct on the fixture", () => {
  const [runner, sock, card] = items();
  assert.equal(runner.store, "www.allbirds.com");
  assert.equal(runner.shopName, "Allbirds");
  assert.equal(runner.currency, "USD");
  assert.equal(runner.productId, 7093452013648);
  assert.equal(runner.url, "https://www.allbirds.com/products/mens-wool-runners-natural-black");
  assert.equal(runner.updatedAt, "2026-11-18T14:31:17.000Z");
  assert.equal(runner.priceMin, 98);
  assert.equal(runner.priceMax, 98);
  assert.equal(runner.compareAtPriceMax, null);
  assert.equal(runner.onSale, false);
  assert.equal(runner.available, true);
  assert.equal(runner.variantCount, 2);
  assert.deepEqual(runner.options, [{ name: "Size", values: ["8", "9"] }]);
  assert.equal(runner.images.length, 2);
  assert.equal(runner.image, runner.images[0]);
  assert.equal(runner.description, "Our original sneaker, made with ZQ Merino wool & a sugarcane midsole.\n\n- Machine washable\n- Wear with or without socks");
  assert.deepEqual(runner.variants[1], {
    variantId: 40872615805008, title: "9", sku: "WR3MNBK090", price: 98, compareAtPrice: null, available: false,
    option1: "9", option2: null, option3: null, grams: 700, requiresShipping: true,
  });
  assert.equal(runner.error, null);

  assert.deepEqual(sock.tags, ["gender::unisex", "material::trino", "sale"]); // comma string -> array
  assert.equal(sock.priceMin, 12);
  assert.equal(sock.priceMax, 14.5);
  assert.equal(sock.compareAtPriceMax, 16);
  assert.equal(sock.onSale, true);
  assert.equal(sock.variants[1].sku, null);

  assert.equal(card.available, false);
  assert.equal(card.productType, null);
  assert.deepEqual(card.tags, []);
  assert.deepEqual(card.images, []);
  assert.equal(card.image, null);
  assert.equal(card.description, null);
  assert.equal(card.variants[0].requiresShipping, false);
});

test("normProduct tolerates missing fields; compare_at_price equal to price is not a sale", () => {
  const p = normProduct({ id: 1, title: "X" }, { store: "a.com" });
  assert.equal(p.url, null);
  assert.equal(p.priceMin, null);
  assert.equal(p.variantCount, 0);
  assert.equal(p.available, false);
  assert.equal(p.currency, null);
  const q = normProduct({ id: 2, handle: "y", variants: [{ id: 3, price: "10.00", compare_at_price: "10.00", available: true }] }, { store: "a.com" });
  assert.equal(q.onSale, false);
  assert.deepEqual(normTags(" a , ,b"), ["a", "b"]);
});

test("toVariantRows", () => {
  const [runner] = items();
  const rows = toVariantRows(runner);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].title, "Men's Wool Runner - Natural Black"); // product title is not overwritten
  assert.equal(rows[0].variantTitle, "8");
  assert.equal(rows[0].variantId, 40872615772240);
  assert.equal(rows[0].price, 98);
  assert.equal(rows[0].variantUrl, "https://www.allbirds.com/products/mens-wool-runners-natural-black?variant=40872615772240");
  assert.equal(rows[0].variantCount, 2);
  assert.equal("variants" in rows[0], false);
  assert.equal(rows[0].error, null);
  assert.deepEqual(toVariantRows(runner, { inStockOnly: true }).map((r) => r.variantTitle), ["8"]);
});

test("keep", () => {
  const [runner, sock, card] = items();
  assert.equal(keep(runner, {}), true);
  assert.equal(keep(runner, { titleKeywords: ["wool runner"] }), true);
  assert.equal(keep(runner, { titleKeywords: ["sock", "boot"] }), false);
  assert.equal(keep(sock, { productTypes: ["socks"] }), true);
  assert.equal(keep(runner, { productTypes: ["socks"] }), false);
  assert.equal(keep(card, { productTypes: ["socks"] }), false);
  assert.equal(keep(runner, { vendors: ["ALLBIRDS"] }), true);
  assert.equal(keep(runner, { vendors: ["Nike"] }), false);
  assert.equal(keep(sock, { tags: ["Sale"] }), true);
  assert.equal(keep(runner, { tags: ["sale"] }), false);
  assert.equal(keep(card, { inStockOnly: true }), false);
  assert.equal(keep(runner, { inStockOnly: true }), true);
  assert.equal(keep(runner, { updatedAfter: "2026-11-18T00:00:00.000Z" }), true);
  assert.equal(keep(sock, { updatedAfter: "2026-11-18T00:00:00.000Z" }), false);
  assert.equal(keep(runner, { titleKeywords: [], tags: [], updatedAfter: null }), true);
});

test("htmlToText", () => {
  assert.equal(htmlToText("<p>A&nbsp;B</p><style>p{color:red}</style><div>C<br>D</div>"), "A B\n\nC\nD");
});

test("errorItem", () => {
  assert.deepEqual(errorItem(parseStore("https://a.com/collections/x"), "nope"), { store: "a.com", title: null, url: "https://a.com/collections/x", error: "nope" });
});

test("retryDelayMs honors Retry-After, else backs off", () => {
  assert.equal(retryDelayMs("5", 0), 5000);
  assert.equal(retryDelayMs("2.0", 2), 2000);
  const now = Date.parse("2026-11-20T10:00:00Z");
  assert.equal(retryDelayMs("Fri, 20 Nov 2026 10:00:30 GMT", 0, now), 30000);
  assert.equal(retryDelayMs("Fri, 20 Nov 2026 09:00:00 GMT", 0, now), 0);
  assert.equal(retryDelayMs(null, 0), 2000);
  assert.equal(retryDelayMs("", 1), 4000);
  assert.equal(retryDelayMs("soon", 2), 8000);
});
