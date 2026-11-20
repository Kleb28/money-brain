import { Actor, log } from "apify";
import { ATS, keep, parseCompany } from "./ats.js";

async function getJson(url) {
  for (let i = 0; i < 3; i++) {
    const res = await fetch(url, { headers: { accept: "application/json" } });
    if (res.ok) return res.json();
    if (res.status === 404 || res.status === 400 || res.status === 422) return null; // no such board on this ATS
    await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
  }
  throw new Error(`request failed after retries: ${url}`);
}

await Actor.init();
const input = (await Actor.getInput()) ?? {};
const filter = {
  titleKeywords: input.titleKeywords,
  locationKeywords: input.locationKeywords,
  remoteOnly: input.remoteOnly === true,
  postedAfter: input.postedAfter ? new Date(input.postedAfter).toISOString() : undefined,
};
const max = Math.max(Number(input.maxJobsPerCompany ?? 1000), 1);
const withText = input.includeDescription !== false;

let total = 0;
for (const raw of input.companies ?? []) {
  const targets = parseCompany(raw);
  if (!targets.length) {
    log.warning(`Could not read "${raw}" as a careers URL, ats:slug or slug`);
    continue;
  }
  let found = 0;
  for (const { ats, slug } of targets) {
    let json;
    try {
      json = await getJson(ATS[ats].url(slug));
      // SmartRecruiters pages by offset (100 per page); the other four return every job in one response.
      for (let offset = 100; ats === "smartrecruiters" && json?.content?.length === offset && offset < 2000; offset += 100) {
        const more = await getJson(`${ATS[ats].url(slug)}&offset=${offset}`);
        if (!more?.content?.length) break;
        json.content.push(...more.content);
      }
    } catch (err) {
      log.warning(`${ats}:${slug} ${err.message}`);
      continue;
    }
    const jobs = ATS[ats].list(json).map((x) => ATS[ats].norm(x, slug, json)).filter((j) => keep(j, filter)).slice(0, max - found);
    if (!jobs.length) continue;
    if (!withText) for (const j of jobs) delete j.description;
    // Pay-per-event: one "job" event per returned job.
    const charge = await Actor.charge({ eventName: "job", count: jobs.length }).catch(() => null);
    await Actor.pushData(jobs);
    found += jobs.length;
    log.info(`${raw} -> ${ats}:${slug}: ${jobs.length} jobs`);
    if (charge?.eventChargeLimitReached) {
      log.info("Spending limit reached; stopping.");
      await Actor.exit();
    }
    if (found >= max) break;
  }
  if (!found) log.info(`${raw}: no open jobs matched (or no public board found)`);
  total += found;
}
log.info(`Done: ${total} jobs`);
await Actor.exit();
