// abstract: Routed Settings page for editing the authenticated Logto account profile name.
// out_of_scope: Password, email, avatar, and application-preference settings.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";

import { cn } from "../../../shared/utils";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import {
  type AccountProfile,
  updateAccountProfile,
  type WebSessionResponse,
} from "../../../shared/web-api/session";
import {
  accountProfileQueryKeys,
  sessionQueryKeys,
  useAccountProfileQuery,
} from "../../../shared/web-api/sessionQueries";

const signInButtonClasses =
  "inline-flex h-10 items-center justify-center rounded-lg bg-[#006bff] px-4 text-[13px] leading-[18px] font-medium text-white transition-colors hover:bg-[#005fe0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]";

function normalizeName(value: string): string {
  return value.trim();
}

function profileName(profile: AccountProfile | undefined): string {
  return profile?.name ?? "";
}

function isAuthenticationError(error: unknown): boolean {
  return error instanceof WebApiRequestError && error.status === 401;
}

function errorMessage(error: unknown): string {
  if (error instanceof WebApiRequestError) {
    return error.message;
  }

  return "Account profile is unavailable.";
}

function SignInPrompt() {
  return (
    <div className="flex w-full flex-col items-start gap-4 rounded-lg border border-[#e0e4eb] bg-white px-4 py-4">
      <p className="m-0 text-[14px] leading-5 font-normal text-[#606e87]">
        Sign in to manage your account.
      </p>
      <form action="/web-api/auth/sign-in" method="post">
        <button className={signInButtonClasses} type="submit">
          Sign in
        </button>
      </form>
    </div>
  );
}

function ErrorNotification({
  message,
  onDismiss,
}: {
  readonly message: string;
  readonly onDismiss: () => void;
}) {
  return (
    <div
      className="flex w-full items-start gap-3 rounded-lg border border-[#fecaca] bg-[#fef2f2] px-3 py-2.5 text-[#991b1b] shadow-[0_12px_24px_rgba(153,27,27,0.08)] lg:absolute lg:top-0 lg:right-0 lg:w-[320px]"
      role="alert"
    >
      <span className="min-w-0 flex-1 text-[13px] leading-[18px] font-medium">
        {message}
      </span>
      <button
        aria-label="Dismiss error"
        className="flex size-5 shrink-0 items-center justify-center rounded-md text-[#991b1b] hover:bg-[#fee2e2] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#dc2626]"
        onClick={onDismiss}
        type="button"
      >
        <X aria-hidden="true" className="size-3.5" strokeWidth={2} />
      </button>
    </div>
  );
}

export function SettingsPage() {
  const queryClient = useQueryClient();
  const profileQuery = useAccountProfileQuery();
  const [draftName, setDraftName] = useState("");
  const [savedName, setSavedName] = useState("");
  const [isFieldInvalid, setIsFieldInvalid] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState<string | null>(
    null,
  );
  const pendingNormalizedNameRef = useRef<string | null>(null);
  const updateProfileMutation = useMutation({
    mutationFn: updateAccountProfile,
  });

  useEffect(() => {
    if (profileQuery.data === undefined) {
      return;
    }

    const nextName = profileName(profileQuery.data);
    setDraftName(nextName);
    setSavedName(nextName);
  }, [profileQuery.data]);

  async function commitDraftName(): Promise<void> {
    const normalizedName = normalizeName(draftName);

    if (
      normalizedName === normalizeName(savedName) ||
      pendingNormalizedNameRef.current === normalizedName
    ) {
      return;
    }

    pendingNormalizedNameRef.current = normalizedName;

    try {
      const updatedProfile = await updateProfileMutation.mutateAsync({
        name: normalizedName === "" ? null : normalizedName,
      });
      const nextName = profileName(updatedProfile);
      const nextSession: WebSessionResponse = {
        status: "authenticated",
        user: {
          email: updatedProfile.email,
          id: updatedProfile.id,
          name: updatedProfile.name,
        },
      };

      queryClient.setQueryData(accountProfileQueryKeys.profile, updatedProfile);
      queryClient.setQueryData(sessionQueryKeys.session, nextSession);
      setDraftName(nextName);
      setSavedName(nextName);
      setIsFieldInvalid(false);
      setNotificationMessage(null);
    } catch (error) {
      setIsFieldInvalid(true);
      setNotificationMessage(errorMessage(error));
    } finally {
      pendingNormalizedNameRef.current = null;
    }
  }

  function handleNameKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.key === "Enter") {
      event.preventDefault();
      void commitDraftName();
      return;
    }

    if (event.key === "Escape") {
      setDraftName(savedName);
      setIsFieldInvalid(false);
    }
  }

  const isAnonymous = isAuthenticationError(profileQuery.error);
  const isProfileReady = profileQuery.data !== undefined;

  return (
    <main
      className="relative h-full min-h-0 overflow-auto bg-[#f8fafc] px-4 pt-5 pb-8 lg:px-8 lg:pt-8"
      data-testid="settings-route-page"
    >
      <section
        className="relative flex w-full max-w-[720px] flex-col gap-4 lg:gap-6"
        data-testid="settings-column"
      >
        <h1 className="m-0 h-8 text-[24px] leading-8 font-black text-[#131c2d]">
          Settings
        </h1>
        {notificationMessage ? (
          <ErrorNotification
            message={notificationMessage}
            onDismiss={() => {
              setNotificationMessage(null);
            }}
          />
        ) : null}
        {isAnonymous ? (
          <SignInPrompt />
        ) : (
          <div
            className="w-full rounded-lg border border-[#e0e4eb] bg-white"
            data-testid="settings-panel"
          >
            <div
              className="grid w-full grid-cols-1 gap-2 px-4 py-4 lg:h-[72px] lg:grid-cols-[240px_360px] lg:items-center lg:gap-[72px] lg:px-6 lg:py-[18px]"
              data-testid="settings-name-row"
            >
              <label
                className="text-[14px] leading-5 font-medium text-[#131c2d]"
                htmlFor="settings-name"
              >
                Name
              </label>
              <input
                aria-invalid={isFieldInvalid}
                autoComplete="name"
                className={cn(
                  "h-9 w-full rounded-md border bg-white px-3 text-[14px] leading-5 font-normal text-[#131c2d] outline-none transition-colors placeholder:text-[#9aa6b2] focus:border-[#006bff] focus:ring-2 focus:ring-[#bfdbfe] lg:w-[360px]",
                  isFieldInvalid
                    ? "border-[#dc2626]"
                    : "border-[#d9e0ea] hover:border-[#b7c2d0]",
                )}
                disabled={!isProfileReady}
                id="settings-name"
                onBlur={() => {
                  void commitDraftName();
                }}
                onChange={(event) => {
                  setDraftName(event.target.value);
                  setIsFieldInvalid(false);
                }}
                onKeyDown={handleNameKeyDown}
                type="text"
                value={draftName}
              />
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
