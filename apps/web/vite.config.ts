// abstract: Vite and Vitest configuration for the taxonomy-view web client.
// out_of_scope: Runtime feature behavior and deployment infrastructure.

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
  },
});
