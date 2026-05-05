// abstract: Browser form and iframe transports for BFF-owned auth routes.
// out_of_scope: Auth state coordination, Logto callbacks, and token handling.

export type SilentSignInStatus = "failed" | "success";

export interface SilentSignInOptions {
  readonly returnTo: string;
  readonly timeoutMs?: number;
}

const silentAuthMessageType = "knowledge.auth.silent";
const defaultSilentTimeoutMs = 10_000;

function normalizeReturnTo(returnTo: string): string {
  try {
    const parsed = new URL(returnTo, window.location.origin);
    if (parsed.origin !== window.location.origin) {
      return "/";
    }

    const normalized = `${parsed.pathname}${parsed.search}${parsed.hash}`;
    return normalized.startsWith("/web-api/") ? "/" : normalized;
  } catch {
    return "/";
  }
}

function createPostForm(options: {
  readonly action: string;
  readonly returnTo?: string;
  readonly target?: string;
}): HTMLFormElement {
  const form = document.createElement("form");

  form.action = options.action;
  form.method = "post";
  form.style.display = "none";

  if (options.target !== undefined) {
    form.target = options.target;
  }

  if (options.returnTo !== undefined) {
    const input = document.createElement("input");
    input.name = "return_to";
    input.type = "hidden";
    input.value = normalizeReturnTo(options.returnTo);
    form.append(input);
  }

  return form;
}

function nextTransportName(): string {
  if (globalThis.crypto?.randomUUID !== undefined) {
    return `knowledge-auth-${globalThis.crypto.randomUUID()}`;
  }

  return `knowledge-auth-${String(Date.now())}-${String(Math.random())}`;
}

export function submitInteractiveSignIn(returnTo: string): void {
  const form = createPostForm({
    action: "/web-api/auth/sign-in",
    returnTo,
  });

  document.body.append(form);
  form.submit();
}

export function submitSignOut(): void {
  const form = createPostForm({
    action: "/web-api/auth/sign-out",
  });

  document.body.append(form);
  form.submit();
}

export async function startSilentSignIn(
  options: SilentSignInOptions,
): Promise<SilentSignInStatus> {
  return await new Promise<SilentSignInStatus>((resolve) => {
    const targetName = nextTransportName();
    const iframe = document.createElement("iframe");
    const form = createPostForm({
      action: "/web-api/auth/silent-sign-in",
      returnTo: options.returnTo,
      target: targetName,
    });
    let isSettled = false;

    iframe.hidden = true;
    iframe.name = targetName;
    document.body.append(iframe, form);

    function cleanup(status: SilentSignInStatus) {
      if (isSettled) {
        return;
      }

      isSettled = true;
      window.removeEventListener("message", handleMessage);
      clearTimeout(timer);
      form.remove();
      iframe.remove();
      resolve(status);
    }

    function handleMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) {
        return;
      }

      const data = event.data;
      if (
        typeof data !== "object" ||
        data === null ||
        !("type" in data) ||
        data.type !== silentAuthMessageType ||
        !("status" in data)
      ) {
        return;
      }

      if (data.status === "success" || data.status === "failed") {
        cleanup(data.status);
      }
    }

    const timer = window.setTimeout(
      () => cleanup("failed"),
      options.timeoutMs ?? defaultSilentTimeoutMs,
    );

    window.addEventListener("message", handleMessage);
    form.submit();
  });
}
