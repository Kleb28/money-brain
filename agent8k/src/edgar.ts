// SEC EDGAR access. EDGAR asks for a descriptive User-Agent with contact info
// and at most 10 requests/second; this Worker makes a handful per paid call.

export interface Filing8K {
  cik: string;
  company: string;
  accession: string; // 0000320193-24-000123
  filed: string; // YYYY-MM-DD
  items: string[]; // ["2.02", "9.01"]
  primaryDocument: string;
  url: string;
}

const TICKERS_URL = "https://www.sec.gov/files/company_tickers.json";

export const ITEM_TITLES: Record<string, string> = {
  "1.01": "Entry into a Material Definitive Agreement",
  "1.02": "Termination of a Material Definitive Agreement",
  "1.03": "Bankruptcy or Receivership",
  "1.05": "Material Cybersecurity Incidents",
  "2.01": "Completion of Acquisition or Disposition of Assets",
  "2.02": "Results of Operations and Financial Condition",
  "2.03": "Creation of a Direct Financial Obligation",
  "2.04": "Triggering Events That Accelerate a Financial Obligation",
  "2.05": "Costs Associated with Exit or Disposal Activities",
  "2.06": "Material Impairments",
  "3.01": "Notice of Delisting or Failure to Satisfy a Listing Rule",
  "3.02": "Unregistered Sales of Equity Securities",
  "3.03": "Material Modification to Rights of Security Holders",
  "4.01": "Changes in Registrant's Certifying Accountant",
  "4.02": "Non-Reliance on Previously Issued Financial Statements",
  "5.01": "Changes in Control of Registrant",
  "5.02": "Departure/Election of Directors or Officers; Compensation",
  "5.03": "Amendments to Articles of Incorporation or Bylaws",
  "5.07": "Submission of Matters to a Vote of Security Holders",
  "7.01": "Regulation FD Disclosure",
  "8.01": "Other Events",
  "9.01": "Financial Statements and Exhibits",
};

async function secFetch(url: string, ua: string): Promise<Response> {
  const res = await fetch(url, { headers: { "User-Agent": ua, Accept: "application/json, text/html" } });
  if (!res.ok) throw new HttpError(res.status === 404 ? 404 : 502, `EDGAR ${res.status} for ${url}`);
  return res;
}

export class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function normalizeTicker(raw: string | undefined | null): string {
  const t = (raw ?? "").trim().toUpperCase();
  if (!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(t)) throw new HttpError(400, "ticker must be a US ticker like AAPL or BRK-B");
  return t.replace(".", "-");
}

export async function tickerToCik(ticker: string, ua: string, kv: KVNamespace): Promise<{ cik: string; name: string }> {
  let map = await kv.get<Record<string, { cik: string; name: string }>>("tickers:v1", "json");
  if (!map) {
    const raw = (await (await secFetch(TICKERS_URL, ua)).json()) as Record<string, { cik_str: number; ticker: string; title: string }>;
    map = {};
    for (const r of Object.values(raw)) map[r.ticker.toUpperCase()] = { cik: String(r.cik_str).padStart(10, "0"), name: r.title };
    await kv.put("tickers:v1", JSON.stringify(map), { expirationTtl: 86400 });
  }
  const hit = map[ticker];
  if (!hit) throw new HttpError(404, `unknown ticker ${ticker}`);
  return hit;
}

export async function recent8Ks(ticker: string, ua: string, kv: KVNamespace, limit = 5): Promise<Filing8K[]> {
  const { cik, name } = await tickerToCik(ticker, ua, kv);
  const cacheKey = `subs:${cik}`;
  let subs = await kv.get<any>(cacheKey, "json");
  if (!subs) {
    subs = await (await secFetch(`https://data.sec.gov/submissions/CIK${cik}.json`, ua)).json();
    const r = subs.filings.recent;
    subs = { form: r.form, accessionNumber: r.accessionNumber, filingDate: r.filingDate, items: r.items, primaryDocument: r.primaryDocument };
    await kv.put(cacheKey, JSON.stringify(subs), { expirationTtl: 3600 });
  }
  const out: Filing8K[] = [];
  for (let i = 0; i < subs.form.length && out.length < limit; i++) {
    if (subs.form[i] !== "8-K") continue;
    const acc: string = subs.accessionNumber[i];
    out.push({
      cik,
      company: name,
      accession: acc,
      filed: subs.filingDate[i],
      items: String(subs.items[i] ?? "").split(",").map((s: string) => s.trim()).filter(Boolean),
      primaryDocument: subs.primaryDocument[i],
      url: `https://www.sec.gov/Archives/edgar/data/${Number(cik)}/${acc.replace(/-/g, "")}/${subs.primaryDocument[i]}`,
    });
  }
  return out;
}

export function htmlToText(html: string): string {
  return html
    .replace(/<(script|style)[\s\S]*?<\/\1>/gi, " ")
    .replace(/<br\s*\/?>|<\/(p|div|tr|li|h\d)>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;|&#160;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#8217;|&rsquo;/gi, "'")
    .replace(/&#8220;|&#8221;|&ldquo;|&rdquo;/gi, '"')
    .replace(/&#\d+;/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s*\n+/g, "\n")
    .trim();
}

// Primary 8-K document plus the first EX-99 exhibit (usually the press release,
// where the substance of an earnings or deal 8-K lives).
export async function filingText(f: Filing8K, ua: string, maxChars = 60000): Promise<string> {
  const base = f.url.slice(0, f.url.lastIndexOf("/") + 1);
  const primary = htmlToText(await (await secFetch(f.url, ua)).text());
  let exhibit = "";
  try {
    const idx = (await (await secFetch(`${base}index.json`, ua)).json()) as { directory: { item: { name: string }[] } };
    const ex = idx.directory.item.map((x) => x.name).find((n) => /ex-?99/i.test(n) && /\.html?$/i.test(n));
    if (ex) exhibit = htmlToText(await (await secFetch(base + ex, ua)).text());
  } catch {
    // exhibit is optional
  }
  const text = `=== 8-K ===\n${primary}\n\n=== EX-99 ===\n${exhibit}`;
  return text.length > maxChars ? text.slice(0, maxChars) + "\n[truncated]" : text;
}
