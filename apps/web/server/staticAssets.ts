// abstract: Static asset resolution for the production web BFF runtime.
// out_of_scope: Vite development middleware and browser feature routing.

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { ProductionRuntime } from "./app.js";

export async function loadProductionRuntime(): Promise<ProductionRuntime> {
  const serverRoot = dirname(fileURLToPath(import.meta.url));
  const clientRoot = resolve(serverRoot, "../client");
  const indexHtml = await readFile(resolve(clientRoot, "index.html"), "utf-8");

  return {
    clientRoot,
    indexHtml,
    kind: "production",
  };
}
