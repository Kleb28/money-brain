# Google News Scraper: Search, Topics & Publisher Feeds (RSS)

News articles from Google News as clean JSON. It reads Google News' public RSS feeds only (keyword search, top headlines and topic sections), so runs take seconds: no browser, no proxy, no HTML scraping.

## What you can do with it
- Monitor a brand, a product or competitors: one query per name, scheduled hourly or daily
- Build a daily news digest for a topic, a country or a single publisher (`site:reuters.com biotech`)
- Give an AI agent a reliable "what is in the news about X" tool
- Follow the Business, Technology, Science or Health sections in any language and country edition

## Input
| Field | Meaning |
|---|---|
| `queries` | Search queries, one feed each. Operators work: `site:`, `intitle:`, `"exact phrase"`, `OR`, `-word`, `when:7d` |
| `topics` | Any of `WORLD`, `NATION`, `BUSINESS`, `TECHNOLOGY`, `ENTERTAINMENT`, `SPORTS`, `SCIENCE`, `HEALTH` |
| `topHeadlines` | Also read the top-headlines feed (default off) |
| `language`, `country` | Edition, e.g. `en` + `US`, `de` + `DE`, `ja` + `JP` (defaults `en`, `US`) |
| `timeRange` | `any`, `1h`, `1d`, `7d`, `30d`, `1y`; appended to each query as `when:1d` etc. |
| `after`, `before` | Dates; appended to each query as `after:YYYY-MM-DD` / `before:YYYY-MM-DD` |
| `maxItemsPerQuery` | Limit per feed (default 100) |
| `dedupe` | Return each article link once per run (default on) |

No field is required. With no queries and no topics, the top-headlines feed is read.

## Output (one item per article)
```json
{
  "query": "site:reuters.com biotech",
  "title": "Biotech funding rebounds in third quarter",
  "source": "Reuters",
  "sourceUrl": "https://www.reuters.com",
  "publishedAt": "2026-11-19T14:05:00.000Z",
  "link": "https://news.google.com/rss/articles/CBMiaEFVX3lxTE5f...?oc=5",
  "guid": "CBMiaEFVX3lxTE5f...",
  "snippet": "Biotech funding rebounds in third quarter Reuters",
  "relatedCount": 2,
  "language": "en",
  "country": "US"
}
```

## Notes
- `link` is the Google News article link exactly as the feed gives it. It redirects to the publisher's page in a browser. The actor does not decode or resolve it; `sourceUrl` is the publisher's home page.
- A feed returns at most about 100 items. For more coverage, split a query (by `site:`, by keyword, or by date with `after` / `before`) rather than raising the limit.
- `timeRange`, `after` and `before` apply to search queries only. Topic and top-headlines feeds always return the current selection.
- For topic and top-headlines items, `query` holds the topic code (for example `BUSINESS`) or `TOP_HEADLINES`.
- `title` has the trailing " - Publisher" removed. `snippet` is the plain text of the feed's description, which is usually the headline plus the publisher; when Google groups coverage, it lists the related headlines one per line and `relatedCount` is the number of other articles listed.
- `publishedAt` is `null` if the feed gives no valid date.
- Language and country must be a combination Google News offers; some editions use a longer language code (for example `pt-419` with `BR`, `zh-Hant` with `TW`).
- Requests use a plain identifying user-agent. On HTTP 429 or 5xx the feed is retried three times with a pause, then skipped with a warning.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
