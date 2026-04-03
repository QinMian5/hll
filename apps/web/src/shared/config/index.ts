// abstract: Shared runtime configuration helpers for the web client.
// out_of_scope: Feature-specific API orchestration and React rendering logic.

function normalizeApiBaseUrl(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function getApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!configuredBaseUrl) {
    return normalizeApiBaseUrl(globalThis.location.origin);
  }

  return normalizeApiBaseUrl(configuredBaseUrl);
}
