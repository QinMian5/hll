// abstract: Shared browser runtime configuration helpers for the web client.
// out_of_scope: Feature-specific API orchestration and React rendering logic.

export interface BrowserRuntimeConfig {
  readonly mcpPublicBaseUrl: string;
  readonly searchMaxConnected: number;
  readonly searchMaxMatched: number;
}

function resolvePositiveIntegerConfig(
  env: Record<string, unknown>,
  key: "searchMaxConnected" | "searchMaxMatched",
): number {
  const value = env[key];

  if (typeof value !== "number") {
    throw new Error(`Missing browser runtime config: ${key}.`);
  }

  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`Invalid browser runtime config: ${key}.`);
  }

  return value;
}

export function resolveBrowserRuntimeConfig(
  env: Record<string, unknown>,
): BrowserRuntimeConfig {
  const mcpPublicBaseUrl = env.mcpPublicBaseUrl;

  if (typeof mcpPublicBaseUrl !== "string") {
    throw new Error("Missing browser runtime config: mcpPublicBaseUrl.");
  }

  if (!URL.canParse(mcpPublicBaseUrl)) {
    throw new Error("Invalid browser runtime config: mcpPublicBaseUrl.");
  }

  return {
    mcpPublicBaseUrl,
    searchMaxConnected: resolvePositiveIntegerConfig(env, "searchMaxConnected"),
    searchMaxMatched: resolvePositiveIntegerConfig(env, "searchMaxMatched"),
  };
}
