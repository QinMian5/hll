// abstract: Non-reversible fingerprinting for plaintext Logto personal access tokens.
// out_of_scope: Token storage, token display masking, and request authorization.

import { createHmac } from "node:crypto";

export function createPatFingerprint(
  tokenValue: string,
  secret: string,
): string {
  const digest = createHmac("sha256", secret).update(tokenValue).digest("hex");

  return `pat_${digest}`;
}

export function maskTokenValue(tokenValue: string): string {
  const lastSeparatorIndex = tokenValue.lastIndexOf("_");
  const prefix =
    lastSeparatorIndex <= 0 ? tokenValue.slice(0, 4) : tokenValue.slice(0, 7);
  const suffix = tokenValue.slice(-4);
  const hiddenLength = Math.max(
    8,
    tokenValue.length - prefix.length - suffix.length,
  );

  return `${prefix}${"*".repeat(hiddenLength)}${suffix}`;
}
