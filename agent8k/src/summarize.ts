import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { HttpError, ITEM_TITLES, type Filing8K } from "./edgar";

export interface Summary {
  ticker: string;
  company: string;
  accession: string;
  filed: string;
  source_url: string;
  items: { code: string; title: string }[];
  headline: string;
  key_points: string[];
  figures: { label: string; value: string }[];
  model: string;
  generated_at: string;
  disclaimer: string;
}

export interface Usage {
  input_tokens: number;
  output_tokens: number;
}

const BriefSchema = z.object({
  headline: z.string(),
  key_points: z.array(z.string()),
  figures: z.array(z.object({ label: z.string(), value: z.string() })),
});

const SYSTEM = `You summarize SEC Form 8-K filings for software agents.
headline: one factual sentence (at most 30 words) saying what the company disclosed.
key_points: 2 to 5 short factual statements.
figures: up to 8 amounts, dates, percentages or guidance values copied from the filing, with units.
Use only facts stated in the filing text. No opinions, predictions or investment advice. If the filing is only an exhibit list or cover page, say so in the headline.`;

export async function summarize(
  f: Filing8K,
  ticker: string,
  text: string,
  apiKey: string,
  model: string,
): Promise<{ summary: Summary; usage: Usage }> {
  const client = new Anthropic({ apiKey, maxRetries: 1 });
  let response;
  try {
    response = await client.messages.parse({
      model,
      max_tokens: 4000,
      system: SYSTEM,
      output_config: { effort: "low", format: zodOutputFormat(BriefSchema) },
      messages: [{ role: "user", content: `Company: ${f.company} (${ticker})\nFiled: ${f.filed}\nItems: ${f.items.join(", ")}\n\n${text}` }],
    });
  } catch (err) {
    if (err instanceof Anthropic.RateLimitError) throw new HttpError(503, "model rate limited; retry shortly");
    if (err instanceof Anthropic.APIError) throw new HttpError(502, `model error ${err.status}`);
    throw err;
  }
  if (response.stop_reason === "refusal") throw new HttpError(502, "model declined this filing");
  const out = response.parsed_output;
  if (!out) throw new HttpError(502, "model returned no structured output");
  return {
    usage: { input_tokens: response.usage.input_tokens, output_tokens: response.usage.output_tokens },
    summary: {
      ticker,
      company: f.company,
      accession: f.accession,
      filed: f.filed,
      source_url: f.url,
      items: f.items.map((code) => ({ code, title: ITEM_TITLES[code] ?? "Other" })),
      headline: out.headline.slice(0, 400),
      key_points: out.key_points.slice(0, 5).map((s) => s.slice(0, 400)),
      figures: out.figures.slice(0, 8).map((x) => ({ label: x.label.slice(0, 120), value: x.value.slice(0, 120) })),
      model,
      generated_at: new Date().toISOString(),
      disclaimer: "Machine-generated summary of a public SEC filing. Verify against source_url. Not investment advice.",
    },
  };
}
