# agent8k-auto journal

Written by agent8k/auto_agent.py. Do not edit by hand.
- 2026-11-19 12:31Z [44524636264] upsert 8k-events forms=['8-K'] price=$0.02 -> 200 created
- 2026-11-19 12:31Z [44524636264] upsert insider-form4 forms=['4'] price=$0.01 -> 200 created
- 2026-11-19 12:31Z [44524636264] note: Run1: no products existed. Created 8k-events ($0.02) and insider-form4 ($0.01). Next: check get_stats for paid calls after several days before changing anything.
- 2026-11-19 12:31Z [44524636264] run cost $0.0272 (8487 in / 1026 out tokens, claude-sonnet-5-5)
- 2026-11-19 12:31Z [44524636264] final: I created two products, since the catalog was empty and there was no sales data yet:  - **`8k-events`** ($0.02 per call): summarizes a company's latest 8-K filings by ticker. It returns event type, item numbers, key facts, dollar amounts, counterparties, dates and a bullish/bearish/neutral flag. - **`insider-form4`** ($0.01 per call): summarizes recent Form 4 insider transactions by ticker. It returns insider name and role, buy or sell, shares, price, total value, holdings after the trade and a 10b5-1 plan flag.  Neither product has a paid call yet, so neither is listed in the Bazaar. I'll che
