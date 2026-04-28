// abstract: Contract tests for dashboard PAT fingerprinting helpers.
// out_of_scope: Token persistence and Logto Management API calls.
// @vitest-environment node

import { describe, expect, it } from "vitest";

import { createPatFingerprint, maskTokenValue } from "./patFingerprint.js";

describe("PAT fingerprinting", () => {
  it("creates a stable non-reversible PAT fingerprint", () => {
    const first = createPatFingerprint("kg_pat_plaintext_value", "secret-a");
    const second = createPatFingerprint("kg_pat_plaintext_value", "secret-a");

    expect(first).toBe(second);
    expect(first).toMatch(/^pat_[0-9a-f]{64}$/);
    expect(first).not.toContain("kg_pat_plaintext_value");
  });

  it("separates fingerprints by deployment secret", () => {
    const first = createPatFingerprint("kg_pat_plaintext_value", "secret-a");
    const second = createPatFingerprint("kg_pat_plaintext_value", "secret-b");

    expect(first).not.toBe(second);
  });

  it("masks token values without mutating the copyable plaintext", () => {
    const value = "kg_pat_plaintext_value";

    expect(maskTokenValue(value)).toBe("kg_pat_***********alue");
    expect(maskTokenValue(value)).not.toBe(value);
  });
});
