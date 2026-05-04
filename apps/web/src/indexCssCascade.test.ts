// abstract: CSS cascade governance tests for the web client global stylesheet.
// out_of_scope: Component-level rendering behavior and visual regression snapshots.

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const stylesheetPath = join(process.cwd(), "src/index.css");

function readStylesheet(): string {
  return readFileSync(stylesheetPath, "utf8");
}

describe("global stylesheet cascade", () => {
  it("keeps custom global resets in Tailwind base layer", () => {
    const stylesheet = readStylesheet();
    const baseLayerStart = stylesheet.indexOf("@layer base {");

    expect(baseLayerStart).toBeGreaterThanOrEqual(0);
    expect(stylesheet.slice(baseLayerStart)).toContain(
      [
        "  button,",
        "  input,",
        "  textarea,",
        "  select {",
        "    font: inherit;",
        "  }",
      ].join("\n"),
    );
    expect(stylesheet.slice(0, baseLayerStart)).not.toContain("font: inherit;");
  });
});
