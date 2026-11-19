// Creates a throwaway buyer wallet for scripts/buy_test.ts.
// The private key is written only to ~/.agent8k-buyer-key (never printed); the address is printed.
// Usage: npx tsx scripts/new_wallet.ts
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";

const file = join(homedir(), ".agent8k-buyer-key");
if (existsSync(file)) {
  const key = readFileSync(file, "utf8").trim() as `0x${string}`;
  console.log(`key file already exists (${file}); its address:`);
  console.log(privateKeyToAccount(key).address);
} else {
  const key = generatePrivateKey();
  writeFileSync(file, key, { mode: 0o600 });
  console.log(`key saved to ${file}; address:`);
  console.log(privateKeyToAccount(key).address);
}
