// abstract: Browser-facing runtime configuration serialization for the web BFF.
// out_of_scope: Server-only credentials and feature-specific route behavior.

import type { WebServerConfig } from "./config.js";

export interface BrowserRuntimeConfigPayload {
  readonly mcpPublicBaseUrl: string;
}

export function createBrowserRuntimeConfig(
  config: WebServerConfig,
): BrowserRuntimeConfigPayload {
  return {
    mcpPublicBaseUrl: config.mcpPublicBaseUrl,
  };
}

export function serializeBrowserRuntimeConfig(
  payload: BrowserRuntimeConfigPayload,
): string {
  const json = JSON.stringify(payload).replaceAll("<", "\\u003c");
  return `<script>window.__KNOWLEDGE_RUNTIME_CONFIG__=${json};</script>`;
}

export function injectBrowserRuntimeConfig(
  html: string,
  config: WebServerConfig,
): string {
  const script = serializeBrowserRuntimeConfig(
    createBrowserRuntimeConfig(config),
  );

  if (html.includes("</head>")) {
    return html.replace("</head>", `${script}</head>`);
  }

  return `${html}${script}`;
}
