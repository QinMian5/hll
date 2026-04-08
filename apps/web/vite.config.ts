// abstract: Vite and Vitest configuration for the taxonomy-view web client.
// out_of_scope: Runtime feature behavior and deployment infrastructure.

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

function normalizeUrl(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const configuredApiBaseUrl = env.VITE_API_BASE_URL?.trim();
  const configuredApiProxyTarget = env.API_PROXY_TARGET?.trim();

  if (
    command === "serve" &&
    mode !== "test" &&
    !configuredApiBaseUrl &&
    !configuredApiProxyTarget
  ) {
    throw new Error(
      "Vite dev requires API_PROXY_TARGET for proxy-based local development or VITE_API_BASE_URL for an explicit API origin.",
    );
  }

  return {
    plugins: [react(), tailwindcss()],
    server:
      configuredApiProxyTarget === undefined || configuredApiProxyTarget === ""
        ? undefined
        : {
            proxy: {
              "/cards": {
                changeOrigin: true,
                target: normalizeUrl(configuredApiProxyTarget),
              },
              "/search": {
                changeOrigin: true,
                target: normalizeUrl(configuredApiProxyTarget),
              },
              "/taxonomy": {
                changeOrigin: true,
                target: normalizeUrl(configuredApiProxyTarget),
              },
            },
          },
    test: {
      environment: "jsdom",
    },
  };
});
