// abstract: Quota principal derivation for anonymous and authenticated web users.
// out_of_scope: Cookie generation, Redis persistence, and HTTP response handling.

import { createHash } from "node:crypto";

import type { WebSessionResponse } from "../auth/sessionState.js";

export type QuotaPrincipalKind = "anonymous" | "authenticated";

export interface QuotaPrincipal {
  readonly ipKey: string;
  readonly kind: QuotaPrincipalKind;
  readonly principalKey: string;
}

export interface ResolveQuotaPrincipalInput {
  readonly anonymousId?: string;
  readonly ipAddress: string;
  readonly session: WebSessionResponse;
}

function hashKey(value: string): string {
  return createHash("sha256").update(value).digest("base64url");
}

export function resolveQuotaPrincipal(
  input: ResolveQuotaPrincipalInput,
): QuotaPrincipal {
  const ipKey = `ip:${hashKey(input.ipAddress)}`;

  if (input.session.status === "authenticated") {
    return {
      ipKey,
      kind: "authenticated",
      principalKey: `user:${hashKey(input.session.user.id)}`,
    };
  }

  if (input.anonymousId === undefined || input.anonymousId === "") {
    throw new Error(
      "Anonymous quota principal requires an anonymous identity.",
    );
  }

  return {
    ipKey,
    kind: "anonymous",
    principalKey: `anonymous:${hashKey(input.anonymousId)}`,
  };
}
