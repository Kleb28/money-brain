# Podcast Scraper: Apple Podcasts Search, Host Contact Email & Episodes

Find podcasts by keyword and get one clean record per show: who runs it, the contact email the show publishes, website, categories, how many episodes it has, when it last published and its latest episodes. It searches Apple's public iTunes Search API, then reads each show's public RSS feed directly: no browser, no proxy, no login.

## What you can do with it
- Find shows to pitch a guest, a sponsorship or a press story, and keep only the ones that are still publishing (set **Active within (days)**)
- Build a podcast directory or a niche list by topic and country
- Monitor new episodes of a fixed list of shows (pass Apple Podcasts URLs or RSS feed URLs and schedule the run)
- Give an AI agent a reliable "which podcasts cover this topic and how do I reach them" tool

## Input
| Field | Meaning |
|---|---|
| `searchTerms` | Keywords searched on Apple Podcasts, one search per term |
| `podcasts` | Optional. Apple Podcasts URLs (`https://podcasts.apple.com/us/podcast/name/id123456789`), numeric Apple IDs, or RSS feed URLs |
| `country` | Two-letter Apple storefront code (default `us`) |
| `maxPodcastsPerTerm` | Shows per search term (default 50; Apple returns at most 200) |
| `maxEpisodes` | Latest episodes included per show (default 5, `0` = none) |
| `onlyWithEmail` | Keep only shows whose feed publishes an owner email |
| `activeWithinDays` | Keep only shows whose latest episode is newer than this many days |
| `concurrency` | RSS feeds fetched at the same time (default 5, max 20) |

## Output (one item per podcast)
```json
{
  "searchTerm": "biotech",
  "podcastId": "1502871393",
  "title": "The Biotech Bench",
  "author": "Priya Nair & Helix Media",
  "ownerName": "Helix Media LLC",
  "ownerEmail": "hello@biotechbench.example",
  "website": "https://www.biotechbench.example/",
  "feedUrl": "https://feeds.example.com/biotech-bench",
  "applePodcastsUrl": "https://podcasts.apple.com/us/podcast/the-biotech-bench/id1502871393",
  "genres": ["Science", "Life Sciences", "Business"],
  "language": "en-us",
  "episodeCount": 212,
  "latestEpisodeAt": "2026-11-17T08:00:00.000Z",
  "description": "Weekly conversations with the scientists & founders building new medicines.",
  "image": "https://cdn.example.com/shows/biotech-bench/cover-3000.jpg",
  "explicit": false,
  "episodes": [
    {
      "title": "Ep. 212: Base editing leaves the lab",
      "publishedAt": "2026-11-17T08:00:00.000Z",
      "duration": 2712,
      "audioUrl": "https://media.example.com/biotech-bench/212.mp3",
      "url": "https://www.biotechbench.example/episodes/212"
    }
  ],
  "error": null
}
```

## Notes
- `ownerEmail` is the address the show itself publishes in its RSS feed (`itunes:owner`). Nothing is guessed or looked up elsewhere. Many shows do not publish one (several hosting platforms hide it by default), so expect `null` for a share of results; use `onlyWithEmail` to skip those.
- If you contact podcast owners, you are responsible for following the anti-spam and privacy laws that apply to you and to them (for example CAN-SPAM, GDPR, CASL): identify yourself, keep the message relevant to the show, and honour opt-outs.
- A show found by several search terms is returned once, under the first term that found it. `searchTerm`, `podcastId` and `applePodcastsUrl` are `null` for shows given as RSS feed URLs.
- If a feed cannot be read (timeout after 15 s, HTTP error, not an RSS feed), the show is still returned with the fields Apple provides and a short reason in `error`. With `onlyWithEmail` on, such shows are dropped.
- `episodeCount` is the number of episodes in the feed. Some shows keep only their most recent episodes in the feed, and only the first 3 MB of a feed is read, so for very large feeds the count can be lower than the show's full archive. The latest episodes are not affected.
- `duration` is in seconds. Fields a feed does not publish are `null`.
- Apple limits its search API to about 20 calls per minute, so the Actor waits 3 seconds between searches. Apple IDs are looked up in batches, and reading feeds does not count against that limit.
- The Actor identifies itself as `PodcastFeedReader/0.1 (+https://apify.com)` and does not use proxies. Feeds that refuse that request are reported in `error`.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
