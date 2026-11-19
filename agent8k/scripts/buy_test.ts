// Pays for one summary to prove the x402 flow end to end.
// Testnet (default): BUYER_KEY=0x... AGENT8K_URL=https://agent8k.<you>.workers.dev npx tsx scripts/buy_test.ts AAPL
//   The buyer wallet needs Base Sepolia test USDC (free from Circle's faucet).
// Mainnet self-purchase: add BUYER_NETWORK=eip155:8453. Spends real USDC (the route price, $0.03).
//   Use a throwaway wallet holding about $1, never a main wallet. Record it in repo variable AGENT8K_SELF_CALLS.
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// Key from BUYER_KEY, else from the file written by scripts/new_wallet.ts.
const keyFile = join(homedir(), ".agent8k-buyer-key");
const key = (process.env.BUYER_KEY ?? (existsSync(keyFile) ? readFileSync(keyFile, "utf8").trim() : undefined)) as `0x${string}` | undefined;
const base = process.env.AGENT8K_URL;
if (!key || !base) throw new Error("set AGENT8K_URL, and BUYER_KEY or run scripts/new_wallet.ts first");
const ticker = process.argv[2] ?? "AAPL";
const network = (process.env.BUYER_NETWORK ?? "eip155:84532") as `${string}:${string}`;
if (network !== "eip155:84532" && network !== "eip155:8453") throw new Error("BUYER_NETWORK must be eip155:84532 or eip155:8453");
console.log(`network ${network}${network === "eip155:8453" ? " (real USDC)" : " (test USDC)"}`);

const pay = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network, client: new ExactEvmScheme(privateKeyToAccount(key)) }],
});
// BUY_PATH picks another paid route, e.g. /v1/p/insider-form4 on agent8k-auto.
const path = process.env.BUY_PATH ?? "/v1/8k/summary";
const res = await pay(`${base.replace(/\/$/, "")}${path}?ticker=${ticker}`);
console.log(res.status, res.headers.get("payment-response") ?? res.headers.get("x-payment-response") ?? "");
const ext = res.headers.get("extension-responses");
if (ext) console.log("extension-responses:", Buffer.from(ext, "base64").toString("utf8"));
else console.log("extension-responses: (none; Bazaar discovery was not reported by the facilitator)");
console.log(JSON.stringify(await res.json(), null, 2));
