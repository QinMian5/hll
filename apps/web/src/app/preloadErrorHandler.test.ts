// abstract: Unit tests for browser preload-error recovery after asset version changes.
// out_of_scope: Vite build output and production cache header verification.

import { afterEach, describe, expect, it, vi } from "vitest";

import { installVitePreloadErrorReload } from "./preloadErrorHandler";

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("installVitePreloadErrorReload", () => {
  it("prevents Vite preload errors and reloads the page once per browser session", () => {
    const reload = vi.fn();
    const uninstall = installVitePreloadErrorReload({ reload });

    const firstEvent = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(firstEvent);

    expect(firstEvent.defaultPrevented).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(
      window.sessionStorage.getItem("knowledge.assets.preload-reloaded"),
    ).toBe("1");

    const secondEvent = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(secondEvent);

    expect(secondEvent.defaultPrevented).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);

    uninstall();
  });
});
