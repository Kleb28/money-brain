import test from "node:test";
import assert from "node:assert/strict";
import {
  DISPOSABLE_DOMAINS, DOMAIN_TYPOS, FREE_PROVIDERS, ROLE_PREFIXES,
  clean, collectEmails, didYouMean, emailKey, isDisposable, isFreeProvider, isRoleBased, lookupDomain, parseEmail, parseMx, verdict,
} from "../src/verify.js";

const mxAnswer = (...data) => ({ Status: 0, Answer: data.map((d) => ({ name: "x.", type: 15, TTL: 300, data: d })) });
const NODATA = { Status: 0 };
// Fake DNS-over-HTTPS: table of "domain TYPE" -> JSON; records every call. No network.
const fakeQuery = (table) => {
  const calls = [];
  const query = async (name, type) => {
    calls.push(`${name} ${type}`);
    const hit = table[`${name} ${type}`];
    if (hit instanceof Error) throw hit;
    return hit ?? NODATA;
  };
  return { query, calls };
};

test("clean, emailKey, collectEmails", () => {
  assert.equal(clean("  mailto:Jane@Example.com?subject=Hi "), "Jane@Example.com");
  assert.equal(clean("<jane@example.com>"), "jane@example.com");
  assert.equal(emailKey(" Jane@Example.COM "), "jane@example.com");
  assert.deepEqual(collectEmails(["a@b.co", " ", null, 5, " c@d.co "]), ["a@b.co", "c@d.co"]);
  assert.deepEqual(collectEmails("a@b.co"), ["a@b.co"]);
  assert.deepEqual(collectEmails(undefined), []);
  assert.deepEqual(collectEmails({ email: "a@b.co" }), []);
});

test("parseEmail accepts ordinary addresses and normalizes", () => {
  assert.deepEqual(parseEmail(" Hello@Apify.COM "), { email: "Hello@Apify.COM", syntaxValid: true, normalized: "hello@apify.com", local: "hello", domain: "apify.com" });
  for (const ok of ["a@b.co", "first.last+tag@sub.example.co.uk", "o'brien@example.com", "x_y-z@ex-ample.io", "1@2.dev"]) {
    assert.equal(parseEmail(ok).syntaxValid, true, ok);
  }
  assert.equal(parseEmail("user@bücher.de").domain, "xn--bcher-kva.de");
  assert.equal(parseEmail("mailto:info@example.com").normalized, "info@example.com");
});

test("parseEmail rejects bad syntax", () => {
  const bad = [
    "not-an-email", "", "@example.com", "user@", "user@localhost", "user@@example.com", "a b@example.com", "user@exa mple.com",
    ".user@example.com", "user.@example.com", "us..er@example.com", "user@-example.com", "user@example-.com", "user@example..com",
    "user@example.c", "user@example.123", "user@[192.168.0.1]", '"quoted"@example.com', "user@exam_ple.com", "üser@example.com",
    `${"a".repeat(65)}@example.com`, `a@${"b".repeat(64)}.com`, "user@example.com/path",
  ];
  for (const b of bad) assert.equal(parseEmail(b).syntaxValid, false, b);
  assert.deepEqual(parseEmail(null), { email: "", syntaxValid: false, normalized: null, local: null, domain: null });
});

test("built-in lists", () => {
  assert.ok(DISPOSABLE_DOMAINS.size >= 300);
  assert.ok(ROLE_PREFIXES.size >= 50);
  for (const d of DISPOSABLE_DOMAINS) {
    assert.match(d, /^[a-z0-9-]+(\.[a-z0-9-]+)+$/);
    assert.equal(FREE_PROVIDERS.has(d), false, `${d} is listed as both disposable and free provider`);
  }
  for (const [typo, fix] of Object.entries(DOMAIN_TYPOS)) {
    assert.equal(FREE_PROVIDERS.has(typo), false, `${typo} is a real provider`);
    assert.equal(FREE_PROVIDERS.has(fix), true, `${fix} is not a known provider`);
  }
});

test("disposable, role, free provider, typo", () => {
  assert.equal(isDisposable("mailinator.com"), true);
  assert.equal(isDisposable("inbox.mailinator.com"), true);
  assert.equal(isDisposable("notmailinator.example.com"), false);
  assert.equal(isDisposable("apify.com"), false);
  assert.equal(isDisposable("com"), false);
  for (const r of ["info", "sales", "support", "admin", "noreply", "SUPPORT", "info+news"]) assert.equal(isRoleBased(r), true, r);
  for (const r of ["jane", "informant", "john.sales", "sales.team"]) assert.equal(isRoleBased(r), false, r);
  assert.equal(isFreeProvider("gmail.com"), true);
  assert.equal(isFreeProvider("outlook.com"), true);
  assert.equal(isFreeProvider("apify.com"), false);
  assert.equal(didYouMean("jane", "gmial.com"), "jane@gmail.com");
  assert.equal(didYouMean("jane", "hotmail.con"), "jane@hotmail.com");
  assert.equal(didYouMean("jane", "gmail.com"), null);
  assert.equal(didYouMean("jane", "ymail.com"), null);
  assert.equal(didYouMean("jane", "constructor"), null);
});

test("parseMx sorts by priority and handles null MX", () => {
  const json = {
    Status: 0,
    Answer: [
      { name: "x.", type: 5, TTL: 300, data: "alias.example.com." },
      { name: "x.", type: 15, TTL: 300, data: "20 ALT2.mx.example.com." },
      { name: "x.", type: 15, TTL: 300, data: "5 mx1.example.com." },
      { name: "x.", type: 15, TTL: 300, data: "10 b.example.com." },
      { name: "x.", type: 15, TTL: 300, data: "10 a.example.com." },
      { name: "x.", type: 15, TTL: 300, data: "garbage" },
    ],
  };
  assert.deepEqual(parseMx(json), { mxHosts: ["mx1.example.com", "a.example.com", "b.example.com", "alt2.mx.example.com"], nullMx: false });
  assert.deepEqual(parseMx(mxAnswer("0 .")), { mxHosts: [], nullMx: true });
  assert.deepEqual(parseMx(mxAnswer("0 .", "10 mx.example.com.")), { mxHosts: ["mx.example.com"], nullMx: false });
  assert.deepEqual(parseMx(NODATA), { mxHosts: [], nullMx: false });
  assert.deepEqual(parseMx(undefined), { mxHosts: [], nullMx: false });
});

test("lookupDomain: MX found, no extra queries", async () => {
  const { query, calls } = fakeQuery({ "example.com MX": mxAnswer("10 mx.example.com.") });
  assert.deepEqual(await lookupDomain("example.com", query), { exists: true, mxHosts: ["mx.example.com"], nullMx: false, hasAddress: false, error: null });
  assert.deepEqual(calls, ["example.com MX"]);
});

test("lookupDomain: NXDOMAIN, null MX, A and AAAA fallback, nothing, error", async () => {
  const nx = fakeQuery({ "gone.example MX": { Status: 3 } });
  assert.equal((await lookupDomain("gone.example", nx.query)).exists, false);
  assert.deepEqual(nx.calls, ["gone.example MX"]);

  const nul = fakeQuery({ "nomail.example MX": mxAnswer("0 ."), "nomail.example A": { Status: 0, Answer: [{ type: 1, data: "192.0.2.1" }] } });
  const n = await lookupDomain("nomail.example", nul.query);
  assert.equal(n.nullMx, true);
  assert.equal(n.hasAddress, false);
  assert.deepEqual(nul.calls, ["nomail.example MX"]);

  const a = fakeQuery({ "a.example A": { Status: 0, Answer: [{ type: 1, data: "192.0.2.1" }] } });
  assert.equal((await lookupDomain("a.example", a.query)).hasAddress, true);
  assert.deepEqual(a.calls, ["a.example MX", "a.example A"]);

  const v6 = fakeQuery({ "v6.example AAAA": { Status: 0, Answer: [{ type: 28, data: "2001:db8::1" }] } });
  assert.equal((await lookupDomain("v6.example", v6.query)).hasAddress, true);
  assert.deepEqual(v6.calls, ["v6.example MX", "v6.example A", "v6.example AAAA"]);

  const none = await lookupDomain("empty.example", fakeQuery({}).query);
  assert.deepEqual(none, { exists: true, mxHosts: [], nullMx: false, hasAddress: false, error: null });

  const err = await lookupDomain("down.example", fakeQuery({ "down.example MX": new Error("boom") }).query);
  assert.equal(err.error, "boom");
});

test("verdict: status rule", () => {
  const mx = { exists: true, mxHosts: ["mx.example.com"], nullMx: false, hasAddress: false, error: null };
  const v = (email, dns = mx) => verdict(parseEmail(email), dns);

  assert.deepEqual(v("Hello@Apify.com"), {
    email: "Hello@Apify.com", normalized: "hello@apify.com", status: "risky", reason: "role_based", syntaxValid: true, domain: "apify.com",
    hasMx: true, mxHosts: ["mx.example.com"], acceptsMail: true, disposable: false, roleBased: true, freeProvider: false, didYouMean: null,
  });
  assert.deepEqual(verdict(parseEmail("not-an-email"), null), {
    email: "not-an-email", normalized: null, status: "invalid", reason: "invalid_syntax", syntaxValid: false, domain: null,
    hasMx: null, mxHosts: [], acceptsMail: null, disposable: false, roleBased: false, freeProvider: false, didYouMean: null,
  });

  const ok = v("jane.doe@gmail.com");
  assert.deepEqual([ok.status, ok.reason, ok.freeProvider], ["valid", "ok", true]);
  const disp = v("info@mailinator.com");
  assert.deepEqual([disp.status, disp.reason, disp.disposable, disp.roleBased], ["risky", "disposable", true, true]);

  const fallback = v("jane@a.example", { ...mx, mxHosts: [], hasAddress: true });
  assert.deepEqual([fallback.status, fallback.reason, fallback.hasMx, fallback.acceptsMail], ["valid", "ok_address_record_fallback", false, true]);

  const nx = v("jane@gone.example", { ...mx, exists: false, mxHosts: [] });
  assert.deepEqual([nx.status, nx.reason, nx.hasMx, nx.acceptsMail], ["invalid", "domain_not_found", false, false]);
  const nul = v("jane@nomail.example", { ...mx, mxHosts: [], nullMx: true, hasAddress: true });
  assert.deepEqual([nul.status, nul.reason, nul.acceptsMail], ["invalid", "null_mx", false]);
  const none = v("jane@empty.example", { ...mx, mxHosts: [] });
  assert.deepEqual([none.status, none.reason], ["invalid", "no_mx_or_address_record"]);
  // An invalid domain stays invalid even when the address is also role-based or disposable.
  assert.equal(v("info@mailinator.com", { ...mx, exists: false, mxHosts: [] }).status, "invalid");

  const typo = v("jane@gmial.com", { ...mx, exists: false, mxHosts: [] });
  assert.deepEqual([typo.status, typo.didYouMean], ["invalid", "jane@gmail.com"]);

  const failed = v("jane@down.example", { ...mx, mxHosts: [], error: "boom" });
  assert.deepEqual([failed.status, failed.reason, failed.hasMx, failed.acceptsMail], ["risky", "dns_lookup_failed", null, null]);
});
