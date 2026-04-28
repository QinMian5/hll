// abstract: Vite and Vitest configuration for the taxonomy-view web client.
// out_of_scope: Runtime feature behavior and deployment infrastructure.

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              maxSize: 250_000,
              minSize: 20_000,
              name: "leaf-scene-vendor",
              priority: 10,
              test: /node_modules[\\/](?:\.pnpm[\\/].*?[\\/]node_modules[\\/])?(?:@deck\.gl|@loaders\.gl|@luma\.gl|@math\.gl|@probe\.gl|mjolnir\.js|wgsl_reflect)[\\/]/,
            },
          ],
          includeDependenciesRecursively: false,
        },
        strictExecutionOrder: true,
      },
    },
  },
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
  },
});
