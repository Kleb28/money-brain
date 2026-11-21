# Email Verifier & Validator: MX, Disposable & Role Check

Checks a list of email addresses and tells you which ones are worth sending to. For every address it checks the syntax, looks up the domain's mail-server (MX) records, and flags disposable domains, role-based addresses, free mailbox providers and common domain typos.

It does **not** open SMTP connections or probe mailboxes. It checks syntax, the domain and its mail-server records, not whether the specific mailbox exists. `valid` therefore means "well-formed address on a domain that accepts mail", not "this inbox exists".

## What you can do with it
- Clean a lead list before an email campaign: drop `invalid`, review `risky`
- Verify the emails found by a website contact scraper: pass that run's dataset as `datasetId`
- Catch typos such as `gmial.com` at signup or import time (`didYouMean`)
- Separate personal addresses from shared inboxes (`roleBased`) and company domains from free providers (`freeProvider`)

## Input
| Field | Meaning |
|---|---|
| `emails` | Email addresses to check |
| `datasetId` | Optional. Dataset of another Actor run whose items contain emails; checked together with `emails` |
| `emailField` | Field in those dataset items that holds the email (default `emails`). It may be a string or an array of strings |
| `concurrency` | Emails checked in parallel (default 10, max 50) |

Duplicates are checked once (comparison ignores letter case).

## Output (one item per distinct email)
```json
{
  "email": "test@mailinator.com",
  "normalized": "test@mailinator.com",
  "status": "risky",
  "reason": "disposable",
  "syntaxValid": true,
  "domain": "mailinator.com",
  "hasMx": true,
  "mxHosts": ["mail.mailinator.com", "mail2.mailinator.com"],
  "acceptsMail": true,
  "disposable": true,
  "roleBased": true,
  "freeProvider": false,
  "didYouMean": null
}
```

| `status` | When | `reason` |
|---|---|---|
| `invalid` | Bad syntax, or the domain accepts no mail | `invalid_syntax`, `domain_not_found`, `null_mx`, `no_mx_or_address_record` |
| `risky` | Disposable domain or role-based address; also when the DNS lookup itself failed | `disposable`, `role_based`, `dns_lookup_failed` |
| `valid` | Everything else | `ok`, `ok_address_record_fallback` |

## Notes
- `mxHosts` is sorted by MX priority. `acceptsMail` is true when the domain has MX records, or, without any MX record, an A/AAAA record (the standard fallback). A "null MX" record (`0 .`) means the domain declares that it accepts no mail.
- DNS lookups go through the public DNS-over-HTTPS JSON APIs of Google (`dns.google`) and, as a fallback, Cloudflare. Answers are cached per domain within a run.
- For an address with invalid syntax nothing is looked up: `normalized`, `domain`, `hasMx` and `acceptsMail` are `null`. They are also `null` for `hasMx` and `acceptsMail` when the DNS lookup failed.
- The syntax check covers the usual `name@domain.tld` form. Quoted local parts, IP-address domains and non-ASCII local parts are reported as invalid. Internationalized domains are accepted and shown in punycode.
- `normalized` is the lowercased address. Provider-specific rules (Gmail dots, `+tags`) are not applied.
- `disposable`, `roleBased`, `freeProvider` and `didYouMean` come from lists built into the Actor (about 590 disposable domains, about 110 role names such as `info`, `sales`, `support`, `admin`). The lists are not exhaustive, so `disposable: false` does not prove a domain is permanent. A role name is matched on the whole part before `@`.
- `didYouMean` covers a fixed set of misspellings of large providers (Gmail, Yahoo, Hotmail, Outlook, iCloud and a few others); it is `null` otherwise.
- Catch-all domains, full mailboxes and deactivated accounts cannot be detected without contacting the mail server, which this Actor does not do.

## Pricing
Free for now: you pay only Apify platform usage (a typical run costs well under one cent).
