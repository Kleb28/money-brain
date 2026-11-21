# Website Screenshot API: Full Page PNG, JPEG & PDF in Bulk

Give it a list of URLs and get one screenshot per page as PNG, JPEG or PDF. Each page is opened in a real Chromium browser, captured full-page or at viewport size, saved to the run's key-value store and listed in the dataset with a direct link to the file.

## What you can do with it
- Visual monitoring: capture the same pages on a schedule and compare them over time
- Thumbnails and link previews for directories, dashboards and reports
- Archive pages as PDF or full-page images
- Give an AI agent eyes on a page: pass the image URL to a vision model
- Capture desktop, mobile and dark-mode versions, or only one element (**Element selector**)

## Input
| Field | Meaning |
|---|---|
| `urls` | Pages to capture; `https://` is added when the scheme is missing |
| `format` | `png` (default), `jpeg` or `pdf` (A4 pages with backgrounds) |
| `fullPage` | Whole scrollable page (default on) or only the viewport |
| `viewportWidth`, `viewportHeight` | Browser window size, default 1280 x 800 |
| `deviceScaleFactor` | Pixel density 1 to 3 (default 1) |
| `mobile` | Phone emulation: 390 x 844, scale 3, mobile layout and touch; overrides the viewport and scale fields. The browser's own user agent is kept |
| `darkMode` | Request the page's dark color scheme |
| `waitUntil` | `load` (default), `domcontentloaded` or `networkidle` |
| `delayMs` | Extra wait after load, default 1000, max 15000 |
| `selector` | CSS selector; only the first matching element is captured |
| `hideSelectors` | CSS selectors of elements to hide before capture, such as cookie banners |
| `jpegQuality` | 1 to 100, default 80 |
| `maxPageHeight` | Full-page captures are clipped to this height in CSS pixels, default 20000 |
| `timeoutSecs` | Page load timeout, default 45 |
| `concurrency` | Pages captured in parallel, default 3, max 8 |

## Output (one item per URL)
```json
{
  "url": "https://apify.com/",
  "finalUrl": "https://apify.com/",
  "status": 200,
  "title": "Apify: Full-stack web scraping and data extraction platform",
  "format": "png",
  "screenshotKey": "001-apify.com.png",
  "screenshotUrl": "https://api.apify.com/v2/key-value-stores/AbCdEfGhIjKlMnOpQ/records/001-apify.com.png",
  "width": 1280,
  "height": 9412,
  "bytes": 1843201,
  "loadTimeMs": 1630,
  "capturedAt": "2026-11-20T09:15:42.118Z",
  "error": null
}
```

## Notes
- Files are stored in the run's default key-value store under `screenshotKey` and linked per row in `screenshotUrl`. They are kept as long as the run's storage is kept.
- `width` and `height` are the captured area in CSS pixels; the image has `deviceScaleFactor` times as many pixels on each side. For PDF they are the page's document size, and `fullPage` and `selector` do not apply.
- `status` is the HTTP status of the main response. An error page (404, 500) is still captured and returned with its status.
- URLs that fail (timeout, DNS error, selector not found) are returned with a short `error` message and no file.
- Pages that block automated browsers may return an error or show a challenge page. The actor uses a plain browser: no proxy, no CAPTCHA solving, no fingerprint changes.
- Private network addresses (localhost, 127.x, 10.x, 172.16-31.x, 192.168.x, 169.254.x, `::1` and similar) are refused, including when a public page redirects to one.
- 2 GB of memory is recommended. Lower `concurrency` for long pages or scale factors above 1.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent per page).
