# Shopify Products Scraper: Prices, Variants, Stock & Images (products.json)

Products of any Shopify store or collection, read from the storefront's own public JSON feed (`/products.json`). You get prices, variants, availability, images, tags and descriptions in one flat schema, as one row per product or one row per variant. No browser and no proxy: the actor sends plain requests with an honest user-agent, reads `robots.txt` first and pauses between pages.

## What you can do with it
- Monitor competitor prices and discounts (`priceMin`, `priceMax`, `compareAtPriceMax`, `onSale`) on a schedule
- Export a full catalog, or one collection, to CSV, Excel or JSON
- Find new or changed products since your last run (set **Updated on or after**)
- Check which products and variants are in stock (`available`)
- Filter by title keywords, product type, vendor or tag so you only get the products you need

## Input
| Field | Meaning |
|---|---|
| `stores` | Store URLs or domains (`https://www.allbirds.com`, `allbirds.com`) for the whole catalog, or collection URLs (`https://www.gymshark.com/collections/all`) for one collection |
| `maxProductsPerStore` | Limit per store or collection, after filtering (default 1000) |
| `oneRowPer` | `product` (default; variants nested) or `variant` (one item per variant) |
| `titleKeywords` | Keep products whose title contains any keyword |
| `productTypes`, `vendors`, `tags` | Keep products matching any of the given values (case-insensitive, whole value) |
| `inStockOnly` | Only products with at least one available variant; in variant mode, only available variants |
| `updatedAfter` | ISO date; products last updated before it are skipped |
| `includeDescription` | Plain-text description on each item (default on) |
| `respectRobotsTxt` | Skip a store whose `robots.txt` disallows the feed (default on) |
| `concurrency` | Stores read in parallel (default 3, max 10); pages of one store are always read one at a time |

## Output (one item per product)
```json
{
  "store": "www.allbirds.com",
  "shopName": "Allbirds",
  "currency": "USD",
  "productId": 7093452013648,
  "title": "Men's Wool Runner - Natural Black",
  "handle": "mens-wool-runners-natural-black",
  "url": "https://www.allbirds.com/products/mens-wool-runners-natural-black",
  "vendor": "Allbirds",
  "productType": "Shoes",
  "tags": ["gender::mens", "material::wool"],
  "publishedAt": "2024-03-12T16:00:05.000Z",
  "createdAt": "2024-03-01T19:22:41.000Z",
  "updatedAt": "2026-11-18T14:31:17.000Z",
  "priceMin": 98,
  "priceMax": 98,
  "compareAtPriceMax": null,
  "onSale": false,
  "available": true,
  "variantCount": 2,
  "options": [{ "name": "Size", "values": ["8", "9"] }],
  "images": ["https://cdn.shopify.com/s/files/1/1104/4168/files/WR3MNBK_SHOE_LEFT.png?v=1709320964"],
  "image": "https://cdn.shopify.com/s/files/1/1104/4168/files/WR3MNBK_SHOE_LEFT.png?v=1709320964",
  "description": "Our original sneaker, made with ZQ Merino wool ...",
  "variants": [
    {
      "variantId": 40872615772240,
      "title": "8",
      "sku": "WR3MNBK080",
      "price": 98,
      "compareAtPrice": null,
      "available": true,
      "option1": "8",
      "option2": null,
      "option3": null,
      "grams": 680,
      "requiresShipping": true
    }
  ],
  "error": null
}
```

With `oneRowPer: "variant"` each item is one variant: the product fields above (without the `variants` array) plus `variantId`, `variantTitle`, `sku`, `price`, `compareAtPrice`, `available`, `option1`-`option3`, `grams`, `requiresShipping` and `variantUrl` (`https://<store>/products/<handle>?variant=<id>`). In this mode `available` is the variant's own availability, and `title` stays the product title.

A store that cannot be read returns one item with `store`, `url` and an `error` text instead of products.

## Notes
- It works only for Shopify stores that leave the public `products.json` feed on. If a store has turned the feed off, is password-protected, blocks the request or is not on Shopify, you get one `error` item for it and nothing else. The actor does not try to get around that.
- Stock quantity numbers are not in the feed. Only `available` true/false per variant is published.
- The feed returns at most 250 products per page. The actor pages through with a pause of about half a second between pages; on HTTP 429 or 5xx it waits (following `Retry-After`) and tries up to 3 times, then stops that store with an `error` item. Products already returned stay in the dataset.
- `currency` and `shopName` come from the store's `/meta.json`. When that file is not available they are `null`; prices are then in the store's default currency.
- Prices are numbers in the store's currency. `onSale` is true when any variant has a compare-at price above its price.
- Filters run after download, so a narrow filter on a large catalog still reads every page.
- With `respectRobotsTxt` on, a store is skipped when its `robots.txt` disallows the feed path (or the whole site) for all crawlers, or when `robots.txt` answers with a server error.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
