// abstract: Shared browser runtime configuration helpers for the web client.
// out_of_scope: Feature-specific API orchestration and React rendering logic.

export interface BrowserRuntimeConfig {
  readonly mcpPublicBaseUrl: string;
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

  return { mcpPublicBaseUrl };
}
