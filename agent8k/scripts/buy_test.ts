// Pays for one summary with a TEST wallet on Base Sepolia, to prove the x402 flow end to end.
// Usage: BUYER_KEY=0x... AGENT8K_URL=https://agent8k.<you>.workers.dev npx tsx scripts/buy_test.ts AAPL
// The buyer wallet needs Base Sepolia test USDC (free from Circle's faucet). Never use a real-money key here.
import { wrapFetchWithPaymentFromConfig } from "@x402/fetch";
import { ExactEvmScheme } from "@x402/evm";
import { privateKeyToAccount } from "viem/accounts";

const key = process.env.BUYER_KEY as `0x${string}` | undefined;
const base = process.env.AGENT8K_URL;
if (!key || !base) throw new Error("set BUYER_KEY and AGENT8K_URL");
const ticker = process.argv[2] ?? "AAPL";

const pay = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{ network: "eip155:84532", client: new ExactEvmScheme(privateKeyToAccount(key)) }],
});
const res = await pay(`${base.replace(/\/$/, "")}/v1/8k/summary?ticker=${ticker}`);
console.log(res.status, res.headers.get("payment-response") ?? res.headers.get("x-payment-response") ?? "");
console.log(JSON.stringify(await res.json(), null, 2));
