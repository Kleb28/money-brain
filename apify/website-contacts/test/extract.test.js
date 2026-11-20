import test from "node:test";
import assert from "node:assert/strict";
import { allowed, extractEmails, extractPhones, extractSocial, normalizeSite, pickLinks, robotsDisallows, SOCIAL_HOST, sourceFields } from "../src/extract.js";

test("normalizeSite", () => {
  assert.deepEqual(normalizeSite("Example.com/pricing"), { start: "https://example.com/", domain: "example.com" });
  assert.deepEqual(normalizeSite("http://www.acme.io"), { start: "http://www.acme.io/", domain: "acme.io" });
  assert.equal(normalizeSite("not a site"), null);
});

test("extractEmails: mailto, obfuscated, junk and assets dropped", () => {
  const html = `<a href="mailto:Sales@Acme.io">x</a> info [at] acme [dot] io <img src="logo@2x.png"> noreply@acme.io a@sentry.io hi&#64;acme.io`;
  assert.deepEqual(extractEmails(html).sort(), ["hi@acme.io", "info@acme.io", "sales@acme.io"]);
});

test("extractPhones", () => {
  assert.deepEqual(extractPhones(`<a href="tel:+1 (415) 555-0100">call</a><a href="tel:12">x</a>`), ["+14155550100"]);
});

test("extractSocial", () => {
  const s = extractSocial(`<a href="https://www.linkedin.com/company/acme-inc/">in</a><a href="https://x.com/acme">x</a><a href="https://twitter.com/share?u=1">s</a><a href="https://www.facebook.com/sharer.php">f</a>`);
  assert.equal(s.linkedin, "https://www.linkedin.com/company/acme-inc");
  assert.equal(s.twitter, "https://x.com/acme");
  assert.equal(s.facebook, null);
});

test("pickLinks prefers contact-like internal pages", () => {
  const html = `<a href="/blog/post-1">Post</a><a href="/contact-us">Contact</a><a href="https://other.com/contact">x</a><a href="/about">About us</a><a href="/files/contact.pdf">pdf</a>`;
  assert.deepEqual(pickLinks(html, "https://acme.io/", 5), ["https://acme.io/contact-us", "https://acme.io/about"]);
});

test("robots", () => {
  const d = robotsDisallows("User-agent: bot\nDisallow: /\n\nUser-agent: *\nDisallow: /private\nDisallow:\n");
  assert.deepEqual(d, ["/private"]);
  assert.equal(allowed("https://a.io/private/x", d), false);
  assert.equal(allowed("https://a.io/contact", d), true);
  // wildcard rules must not block the whole site (apify.com: "Disallow: /*?_rsc")
  const w = ["/*?_rsc", "/*.pdf$"];
  assert.equal(allowed("https://a.io/", w), true);
  assert.equal(allowed("https://a.io/p?_rsc=1", w), false);
  assert.equal(allowed("https://a.io/f.pdf", w), false);
  assert.equal(allowed("https://a.io/f.pdfx", w), true);
});

test("dataset rows", () => {
  assert.ok(SOCIAL_HOST.test("facebook.com"));
  assert.ok(SOCIAL_HOST.test("m.facebook.com"));
  assert.ok(!SOCIAL_HOST.test("notfacebook.company"));
  assert.deepEqual(sourceFields({ title: "Cafe A", phone: "+1 555", location: { lat: 1 }, website: "a.com", placeId: "p1", extra: 1 }), { title: "Cafe A", phone: "+1 555", placeId: "p1" });
  assert.equal(sourceFields({ foo: 1 }), null);
});
