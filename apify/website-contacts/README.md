# Website Contact Finder

Give it a list of company websites and get back the public contact details published on them: emails, phone numbers and social profiles. It reads the home page and the most contact-like internal pages (contact, about, team, impressum) over plain HTTP, so a site takes a second or two and costs a fraction of a browser-based crawl.

## What you can do with it
- Enrich a lead list that has domains but no contact channel
- Add a "find the contact page details" step to an outreach or CRM workflow
- Give an AI agent a cheap way to answer "how do I reach this company?"

## Input
| Field | Meaning |
|---|---|
| `websites` | Domains or URLs, one per line |
| `maxPagesPerSite` | Home page plus up to this many contact-like pages (default 5) |
| `sameDomainEmailsOnly` | Keep only addresses on the site's own domain |
| `respectRobotsTxt` | Skip pages the site disallows for all crawlers (default on) |

## Output (one item per website)
```json
{
  "domain": "acme.io",
  "website": "https://acme.io/",
  "emails": ["sales@acme.io", "support@acme.io"],
  "phones": ["+14155550100"],
  "linkedin": "https://www.linkedin.com/company/acme-inc",
  "twitter": "https://x.com/acme",
  "facebook": null,
  "instagram": null,
  "youtube": null,
  "pagesCrawled": 4,
  "sources": ["https://acme.io/contact"],
  "error": null
}
```

## Notes
- Only what the site itself publishes is returned; nothing is guessed or looked up elsewhere.
- Sites that render contact details only with JavaScript, or block non-browser clients, return fewer results.
- You are responsible for using contact data in line with the laws that apply to you (for example GDPR and anti-spam rules).

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
