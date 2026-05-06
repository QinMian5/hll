// abstract: Routed Settings page for editing the authenticated Logto account profile name.
// out_of_scope: Password, email, avatar, and application-preference settings.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";

import { PageHeader } from "../../../shared/ui";
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

function normalizeName(value: string): string {
  return value.trim();
}

function profileName(profile: AccountProfile | undefined): string {
  return profile?.name ?? "";
}

function errorMessage(error: unknown): string {
  if (error instanceof WebApiRequestError) {
    return error.message;
  }

  return "Account profile is unavailable.";
}

function ErrorNotification({
  message,
  onDismiss,
}: {
  readonly message: string;
  readonly onDismiss?: () => void;
}) {
  return (
    <div
      className="flex w-full items-start gap-3 rounded-lg border border-knowledge-danger-border bg-knowledge-danger-surface px-3 py-3 text-knowledge-danger-text-strong shadow-knowledge-danger lg:absolute lg:top-0 lg:right-0 lg:w-knowledge-notification-width"
      role="alert"
    >
      <span className="min-w-0 flex-1 text-knowledge-caption font-medium">
        {message}
      </span>
      {onDismiss ? (
        <button
          aria-label="Dismiss error"
          className="flex size-5 shrink-0 items-center justify-center rounded-md text-knowledge-danger-text-strong hover:bg-knowledge-danger-surface-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-knowledge-danger-focus"
          onClick={onDismiss}
          type="button"
        >
          <X aria-hidden="true" className="size-3.5" strokeWidth={2} />
        </button>
      ) : null}
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

  const profileLoadError =
    profileQuery.error === null ? null : errorMessage(profileQuery.error);
  const visibleNotificationMessage = notificationMessage ?? profileLoadError;
  const isProfileReady = profileQuery.data !== undefined;

  return (
    <main
      className="relative h-full min-h-0 overflow-auto bg-knowledge-page-bg px-4 pt-5 pb-8 lg:px-8 lg:pt-8"
      data-testid="settings-route-page"
    >
      <section
        className="relative flex w-full max-w-knowledge-settings-width flex-col gap-4 lg:gap-6"
        data-testid="settings-column"
      >
        <PageHeader title="Settings" />
        {visibleNotificationMessage ? (
          <ErrorNotification
            message={visibleNotificationMessage}
            onDismiss={
              notificationMessage === null
                ? undefined
                : () => {
                    setNotificationMessage(null);
                  }
            }
          />
        ) : null}
        {profileLoadError ? null : (
          <div
            className="w-full rounded-lg border border-knowledge-border-subtle bg-knowledge-surface-card-solid"
            data-testid="settings-panel"
          >
            <div
              className="grid w-full grid-cols-1 gap-2 px-4 py-4 lg:h-knowledge-settings-row-height lg:grid-cols-[var(--spacing-knowledge-settings-label-width)_var(--spacing-knowledge-settings-field-width)] lg:items-center lg:gap-knowledge-settings-row-gap-desktop lg:px-6 lg:py-knowledge-settings-row-padding-y-desktop"
              data-testid="settings-name-row"
            >
              <label
                className="text-knowledge-button font-medium text-knowledge-text-default"
                htmlFor="settings-name"
              >
                Name
              </label>
              <input
                aria-invalid={isFieldInvalid}
                autoComplete="name"
                className={cn(
                  "h-9 w-full rounded-md border bg-knowledge-surface-card-solid px-3 text-knowledge-search-input font-normal text-knowledge-text-default outline-none transition-colors placeholder:text-knowledge-input-placeholder focus:border-knowledge-brand focus:ring-2 focus:ring-knowledge-border-focus-soft lg:w-knowledge-settings-field-width",
                  isFieldInvalid
                    ? "border-knowledge-danger-focus"
                    : "border-knowledge-border-field hover:border-knowledge-border-field-hover",
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
