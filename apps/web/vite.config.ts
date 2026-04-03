// abstract: Vite and Vitest configuration for the semantic-map web client.
// out_of_scope: Runtime feature behavior and deployment infrastructure.

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
  },
});
