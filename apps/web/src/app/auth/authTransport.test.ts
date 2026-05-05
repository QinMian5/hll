// abstract: Unit tests for browser auth navigation and silent SSO transports.
// out_of_scope: BFF Logto route behavior and auth coordinator state.

import "@testing-library/jest-dom/vitest";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  startSilentSignIn,
  submitInteractiveSignIn,
  submitSignOut,
} from "./authTransport";

function latestForm(): HTMLFormElement {
  const forms = document.querySelectorAll("form");
  const form = forms.item(forms.length - 1);

  if (!(form instanceof HTMLFormElement)) {
    throw new Error("Expected a form to be created.");
  }

  return form;
}

describe("authTransport", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("submits interactive sign-in through a same-origin POST form", () => {
    submitInteractiveSignIn("https://evil.example/steal");

    const form = latestForm();

    expect(form.action).toBe("http://localhost:3000/web-api/auth/sign-in");
    expect(form.method).toBe("post");
    expect(form.target).toBe("");
    expect(form).toHaveFormValues({ return_to: "/" });
    expect(HTMLFormElement.prototype.submit).toHaveBeenCalledOnce();
  });

  it("submits sign-out through a same-origin POST form", () => {
    submitSignOut();

    const form = latestForm();

    expect(form.action).toBe("http://localhost:3000/web-api/auth/sign-out");
    expect(form.method).toBe("post");
    expect(form.querySelector('[name="return_to"]')).toBeNull();
    expect(HTMLFormElement.prototype.submit).toHaveBeenCalledOnce();
  });

  it("resolves silent sign-in only from same-origin completion messages", async () => {
    const resultPromise = startSilentSignIn({
      returnTo: "/overview",
      timeoutMs: 100,
    });

    const iframe = document.querySelector("iframe");
    const form = latestForm();

    expect(iframe).toBeInstanceOf(HTMLIFrameElement);
    expect(iframe?.hidden).toBe(true);
    expect(form.action).toBe(
      "http://localhost:3000/web-api/auth/silent-sign-in",
    );
    expect(form.method).toBe("post");
    expect(form.target).toBe(iframe?.name);
    expect(form).toHaveFormValues({ return_to: "/overview" });

    window.dispatchEvent(
      new MessageEvent("message", {
        data: { status: "success", type: "knowledge.auth.silent" },
        origin: "https://evil.example",
      }),
    );
    window.dispatchEvent(
      new MessageEvent("message", {
        data: { status: "success", type: "not-auth" },
        origin: window.location.origin,
      }),
    );
    window.dispatchEvent(
      new MessageEvent("message", {
        data: { status: "success", type: "knowledge.auth.silent" },
        origin: window.location.origin,
      }),
    );

    await expect(resultPromise).resolves.toBe("success");
    expect(document.querySelector("iframe")).toBeNull();
    expect(document.querySelector("form")).toBeNull();
  });

  it("returns failed when silent sign-in times out", async () => {
    await expect(
      startSilentSignIn({ returnTo: "/search?q=science", timeoutMs: 1 }),
    ).resolves.toBe("failed");
  });
});
