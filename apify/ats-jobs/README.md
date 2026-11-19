# Company Jobs API: Greenhouse, Lever, Ashby, Workable, SmartRecruiters

Live open jobs for any list of companies, in one unified JSON schema. It calls the official public job-board APIs of five applicant tracking systems directly, so results are current to the minute and runs take seconds: no browser, no proxy, no stale index.

## What you can do with it
- Track new openings at target accounts every day (set **Posted or updated on or after**)
- Build a niche job board or a hiring-signal feed for sales and recruiting
- Give an AI agent a reliable "what is this company hiring for" tool
- Filter by title keywords, location or remote before you pay for a result

## Input
| Field | Meaning |
|---|---|
| `companies` | Careers URLs (`https://jobs.ashbyhq.com/openai`), `ats:slug` (`greenhouse:stripe`), or a bare slug (`stripe`), which is tried on all five systems |
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
- Fields a system does not publish are `null` (for example, Greenhouse has no employment type; SmartRecruiters' list has no description).
- A company must use one of the five systems with a public board. Workday, iCIMS and custom career sites are not covered.

## Pricing
Pay per job returned. A company with no matching jobs costs nothing beyond platform usage.
