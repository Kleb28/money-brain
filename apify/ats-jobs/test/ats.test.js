import test from "node:test";
import assert from "node:assert/strict";
import { ATS, htmlToText, keep, parseCompany, workday, workdayPosted } from "../src/ats.js";

test("parseCompany", () => {
  assert.deepEqual(parseCompany("https://boards.greenhouse.io/stripe"), [{ ats: "greenhouse", slug: "stripe" }]);
  assert.deepEqual(parseCompany("https://job-boards.greenhouse.io/stripe/jobs/123"), [{ ats: "greenhouse", slug: "stripe" }]);
  assert.deepEqual(parseCompany("https://jobs.lever.co/spotify/abc"), [{ ats: "lever", slug: "spotify" }]);
  assert.deepEqual(parseCompany("https://jobs.ashbyhq.com/openai"), [{ ats: "ashby", slug: "openai" }]);
  assert.deepEqual(parseCompany("https://apply.workable.com/acme/"), [{ ats: "workable", slug: "acme" }]);
  assert.deepEqual(parseCompany("Greenhouse:stripe"), [{ ats: "greenhouse", slug: "stripe" }]);
  assert.equal(parseCompany("stripe").length, 5);
  assert.deepEqual(parseCompany("not a company!"), []);
});

test("htmlToText decodes Greenhouse's escaped HTML", () => {
  assert.equal(htmlToText("&lt;p&gt;Build &amp;amp; ship&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Go&lt;/li&gt;&lt;/ul&gt;"), "Build & ship\n- Go");
});

test("normalizers", () => {
  const g = ATS.greenhouse.norm({ id: 1, title: "Engineer", location: { name: "Remote - US" }, updated_at: "2026-11-18T10:00:00-05:00", absolute_url: "u", departments: [{ name: "Eng" }], content: "&lt;p&gt;Hi&lt;/p&gt;" }, "acme");
  assert.equal(g.remote, true);
  assert.equal(g.updatedAt, "2026-11-18T15:00:00.000Z");
  assert.equal(g.description, "Hi");
  const l = ATS.lever.norm({ id: "a", text: "PM", categories: { location: "Berlin", team: "Product", commitment: "Full-time" }, createdAt: 1763400000000, hostedUrl: "h", applyUrl: "a", workplaceType: "remote", descriptionPlain: "d" }, "acme");
  assert.equal(l.remote, true);
  assert.equal(l.employmentType, "Full-time");
  assert.ok(l.postedAt.startsWith("2025-11-17"));
  const a = ATS.ashby.norm({ id: "x", title: "Researcher", location: "SF", isRemote: false, publishedAt: "2026-11-01T00:00:00.000+00:00", jobUrl: "j", compensation: { compensationTierSummary: "$200K" } }, "acme");
  assert.equal(a.compensation, "$200K");
  assert.equal(a.remote, false);
  const w = ATS.workable.norm({ title: "Ops", shortcode: "ABC", city: "Athens", country: "Greece", published_on: "2026-11-10", url: "w" }, "acme", { name: "Acme Inc" });
  assert.equal(w.company, "Acme Inc");
  assert.equal(w.location, "Athens, Greece");
});

test("keep", () => {
  const j = { title: "Senior Data Engineer", location: "London", remote: false, postedAt: "2026-11-10T00:00:00.000Z", updatedAt: null };
  assert.equal(keep(j, {}), true);
  assert.equal(keep(j, { titleKeywords: ["data"] }), true);
  assert.equal(keep(j, { titleKeywords: ["designer"] }), false);
  assert.equal(keep(j, { locationKeywords: ["berlin"] }), false);
  assert.equal(keep(j, { remoteOnly: true }), false);
  assert.equal(keep(j, { postedAfter: "2026-11-15T00:00:00.000Z" }), false);
});

test("workday", () => {
  assert.deepEqual(parseCompany("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"), [{ ats: "workday", slug: "nvidia.wd5/NVIDIAExternalCareerSite" }]);
  assert.deepEqual(parseCompany("https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/x"), [{ ats: "workday", slug: "nvidia.wd5/NVIDIAExternalCareerSite" }]);
  assert.deepEqual(parseCompany("workday:nvidia.wd5/NVIDIAExternalCareerSite"), [{ ats: "workday", slug: "nvidia.wd5/NVIDIAExternalCareerSite" }]);
  assert.equal(workday.listUrl("nvidia.wd5/NVIDIAExternalCareerSite"), "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs");
  const now = Date.parse("2026-11-20T12:00:00Z");
  assert.equal(workdayPosted("Posted Today", now), "2026-11-20T00:00:00.000Z");
  assert.equal(workdayPosted("Posted 3 Days Ago", now), "2026-11-17T00:00:00.000Z");
  assert.equal(workdayPosted("Posted 30+ Days Ago", now), null);
  const j = workday.norm({ title: "Senior Production Engineer", externalPath: "/job/Switzerland-Remote/Senior_JR1", locationsText: "2 Locations", postedOn: "Posted Yesterday", bulletFields: ["JR1"] }, "nvidia.wd5/NVIDIAExternalCareerSite", now);
  assert.equal(j.jobId, "JR1");
  assert.equal(j.remote, true);
  assert.equal(j.url, "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/Switzerland-Remote/Senior_JR1");
  assert.equal(j.postedAt, "2026-11-19T00:00:00.000Z");
});
