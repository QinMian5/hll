// abstract: Shared runtime configuration helpers for the web client.
// out_of_scope: Feature-specific API orchestration and React rendering logic.

export interface ApiRuntimeEnv {
  readonly VITE_API_BASE_URL?: string;
}

function normalizeApiBaseUrl(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function resolveApiBaseUrl(env: ApiRuntimeEnv): string | undefined {
  const configuredBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (!configuredBaseUrl) {
    return undefined;
  }

  return normalizeApiBaseUrl(configuredBaseUrl);
}

export function getApiBaseUrl(): string | undefined {
  return resolveApiBaseUrl({
    VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  });
}
