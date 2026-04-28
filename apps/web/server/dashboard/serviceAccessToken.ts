// abstract: OAuth client-credentials token requester for BFF-owned service calls.
// out_of_scope: Browser session auth and access token caching.

import { z } from "zod";

import { DashboardDependencyError } from "./errors.js";

export { DashboardDependencyError } from "./errors.js";

export interface ServiceAccessTokenConfig {
  readonly clientId: string;
  readonly clientSecret: string;
  readonly resource: string;
  readonly scopes: string;
  readonly tokenUrl: string;
}

type FetchLike = typeof fetch;

const ServiceAccessTokenResponseSchema = z
  .object({
    access_token: z.string().min(1),
  })
  .passthrough();

export async function requestServiceAccessToken(
  config: ServiceAccessTokenConfig,
  fetchToken: FetchLike = fetch,
): Promise<string> {
  const body = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    grant_type: "client_credentials",
    resource: config.resource,
    scope: config.scopes,
  });

  const response = await fetchToken(config.tokenUrl, {
    body,
    headers: {
      "content-type": "application/x-www-form-urlencoded",
    },
    method: "POST",
  });

  if (!response.ok) {
    throw new DashboardDependencyError("Service token request failed.", {
      upstreamStatus: response.status,
    });
  }

  const parsed = ServiceAccessTokenResponseSchema.safeParse(
    await response.json(),
  );

  if (!parsed.success) {
    throw new DashboardDependencyError(
      "Service token response did not include an access token.",
    );
  }

  return parsed.data.access_token;
}
