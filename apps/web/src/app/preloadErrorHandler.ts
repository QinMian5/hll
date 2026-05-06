// abstract: Browser recovery hook for Vite preload failures after asset version changes.
// out_of_scope: Static asset serving policy and route-level error rendering.

const preloadReloadStorageKey = "knowledge.assets.preload-reloaded";

export interface InstallVitePreloadErrorReloadOptions {
  readonly reload?: () => void;
}

export function installVitePreloadErrorReload(
  options: InstallVitePreloadErrorReloadOptions = {},
): () => void {
  const reload = options.reload ?? (() => window.location.reload());

  function handlePreloadError(event: Event) {
    event.preventDefault();

    if (window.sessionStorage.getItem(preloadReloadStorageKey) === "1") {
      return;
    }

    window.sessionStorage.setItem(preloadReloadStorageKey, "1");
    reload();
  }

  window.addEventListener("vite:preloadError", handlePreloadError);

  return () => {
    window.removeEventListener("vite:preloadError", handlePreloadError);
  };
}
