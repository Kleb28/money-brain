# App Store Reviews API

Recent iOS App Store reviews for any app, in any country storefront, as clean JSON. It reads Apple's own public review feed, so there is no login, no proxy and no browser: runs finish in seconds.

## What you can do with it
- Monitor new reviews daily (set **Only reviews on or after** and the run stops as soon as it reaches older reviews)
- Pull complaints only (set **Maximum rating** to 2) for support or product triage
- Compare the same app across countries, or several competitors in one run
- Feed reviews to an LLM for themes, sentiment or release-regression checks

## Input
| Field | Meaning |
|---|---|
| `apps` | App Store IDs (`284882215`), App Store URLs, or app names |
| `countries` | Two-letter storefront codes, e.g. `["us","gb","de"]` |
| `maxReviewsPerApp` | Per app and country, up to 500 (Apple's feed limit) |
| `sortBy` | `mostrecent` or `mosthelpful` |
| `since` | ISO date; older reviews are skipped |
| `minRating`, `maxRating` | Star filters |

## Output (one item per review)
```json
{
  "appId": "284882215",
  "appName": "Facebook",
  "country": "us",
  "reviewId": "14804636513",
  "rating": 2,
  "title": "Crashes",
  "text": "Crashes on launch since the last update",
  "version": "588.0.0",
  "author": "sam",
  "date": "2026-11-18T11:34:45.000Z",
  "helpfulVotes": 3,
  "totalVotes": 5,
  "url": "https://apps.apple.com/us/app/id284882215?see-all=reviews"
}
```

## Limits
- Apple's feed holds the 500 most recent reviews per app and country. For a full history, run it on a schedule and keep the results.
- Reviews only (text reviews), not star-only ratings.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
