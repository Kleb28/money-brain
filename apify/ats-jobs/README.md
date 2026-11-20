# Workday, Greenhouse, Lever & Ashby Jobs Scraper

Live open jobs for any list of companies, in one unified JSON schema. It reads six applicant tracking systems directly (Workday, Greenhouse, Lever, Ashby, Workable, SmartRecruiters), using their public job-board JSON, so results are current to the minute and runs take seconds: no browser, no proxy, no stale index.

## What you can do with it
- Track new openings at target accounts every day (set **Posted or updated on or after**)
- Build a niche job board or a hiring-signal feed for sales and recruiting
- Give an AI agent a reliable "what is this company hiring for" tool
- Filter by title keywords, location or remote so you only get the jobs you need

## Input
| Field | Meaning |
|---|---|
| `companies` | Careers URLs (`https://jobs.ashbyhq.com/openai`), `ats:slug` (`greenhouse:stripe`), or a bare slug (`stripe`), which is tried on every system except Workday. For Workday give the careers URL (`https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`) |
| `titleKeywords`, `locationKeywords` | Keep jobs containing any keyword |
| `remoteOnly` | Only jobs marked remote |
| `postedAfter` | ISO date; older jobs are skipped |
| `includeDescription` | Plain-text description on each item (default on) |
| `maxJobsPerCompany` | Limit per company |

## Output (one item per job)
```json
{
  "company": "Stripe",
  "ats": "greenhouse",
  "jobId": "7123456",
  "title": "Backend Engineer, Payments",
  "location": "Seattle, San Francisco, New York City",
  "remote": false,
  "department": "Engineering",
  "employmentType": null,
  "postedAt": "2026-09-09T14:50:29.000Z",
  "updatedAt": "2026-11-19T17:12:24.000Z",
  "url": "https://stripe.com/jobs/search?gh_jid=7123456",
  "applyUrl": "https://stripe.com/jobs/search?gh_jid=7123456",
  "compensation": null,
  "description": "Who we are ..."
}
```

## Notes
- Fields a system does not publish are `null` (for example, Greenhouse has no employment type; SmartRecruiters' and Workday's lists have no description).
- Workday shows relative dates ("Posted 3 Days Ago"), so `postedAt` is a day-level estimate and is `null` for jobs older than 30 days. Without filters a Workday board is read up to `maxJobsPerCompany`; with filters, up to its first 2,000 postings.
- A company must use one of the six systems with a public board. iCIMS and custom career sites are not covered.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
