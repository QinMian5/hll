// abstract: Routed dashboard page for account quota and token lifecycle management.
// out_of_scope: AppShell navigation chrome and server-side token adapters.

import { useEffect, useRef, useState } from "react";
import { PageHeader } from "../../../shared/ui";
import { WebApiRequestError } from "../../../shared/web-api/errors";
import { QuotaSummary } from "../components/QuotaSummary";
import { DeleteTokenDialog, TokenDialog } from "../components/TokenDialog";
import { TokenDirectory } from "../components/TokenDirectory";
import { useDashboardQuotaQuery } from "../data/dashboardQuota";
import {
  useCreateDashboardTokenMutation,
  useDashboardTokensQuery,
  useDeleteDashboardTokenMutation,
  useRenameDashboardTokenMutation,
} from "../data/dashboardTokens";
import type { DashboardTokenRow } from "../types";

type DialogState =
  | { readonly type: "create" }
  | { readonly token: DashboardTokenRow; readonly type: "delete" }
  | { readonly token: DashboardTokenRow; readonly type: "rename" }
  | null;

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Request failed.";
}

function dashboardTokenErrorMessage(
  error: unknown,
  tokenName?: string,
): string {
  if (!(error instanceof WebApiRequestError)) {
    return errorMessage(error);
  }

  switch (error.code) {
    case "authentication_required":
      return "Authentication required.";
    case "session_expired":
      return "Session expired.";
    case "dashboard_invalid_token_name":
      return "Enter a token name.";
    case "dashboard_token_dependency_unavailable":
      return "Token service is unavailable. Try again later.";
    case "dashboard_token_name_conflict": {
      const trimmedTokenName = tokenName?.trim();
      return trimmedTokenName
        ? `A token named "${trimmedTokenName}" already exists. Use a different name.`
        : "A token with this name already exists. Use a different name.";
    }
    case "dashboard_token_not_found":
      return "This token no longer exists. Refresh and try again.";
    default:
      return error.message;
  }
}

export function DashboardPage() {
  const tokenQuery = useDashboardTokensQuery();
  const quotaQuery = useDashboardQuotaQuery();
  const createTokenMutation = useCreateDashboardTokenMutation();
  const renameTokenMutation = useRenameDashboardTokenMutation();
  const deleteTokenMutation = useDeleteDashboardTokenMutation();
  const copiedTokenResetTimer = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const [dialogState, setDialogState] = useState<DialogState>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [copiedTokenName, setCopiedTokenName] = useState<string | null>(null);

  const tokens = tokenQuery.data?.tokens ?? [];
  const usageAvailable = tokenQuery.data?.usageAvailable ?? true;
  const quota = quotaQuery.data?.quota ?? null;
  const quotaAvailable = quotaQuery.data?.quotaAvailable ?? true;

  useEffect(() => {
    return () => {
      if (copiedTokenResetTimer.current !== null) {
        clearTimeout(copiedTokenResetTimer.current);
      }
    };
  }, []);

  function openDialog(nextDialogState: DialogState) {
    setDialogError(null);
    setDialogState(nextDialogState);
  }

  function closeDialog() {
    setDialogError(null);
    setDialogState(null);
  }

  async function handleCreate(name: string) {
    try {
      setDialogError(null);
      await createTokenMutation.mutateAsync({ name });
      closeDialog();
    } catch (error) {
      setDialogError(dashboardTokenErrorMessage(error, name));
    }
  }

  async function handleRename(name: string) {
    if (dialogState?.type !== "rename") {
      return;
    }

    try {
      setDialogError(null);
      await renameTokenMutation.mutateAsync({
        currentName: dialogState.token.name,
        name,
      });
      closeDialog();
    } catch (error) {
      setDialogError(dashboardTokenErrorMessage(error, name));
    }
  }

  async function handleDelete() {
    if (dialogState?.type !== "delete") {
      return;
    }

    try {
      setDialogError(null);
      await deleteTokenMutation.mutateAsync({ name: dialogState.token.name });
      closeDialog();
    } catch (error) {
      setDialogError(dashboardTokenErrorMessage(error, dialogState.token.name));
    }
  }

  function markTokenCopied(tokenName: string) {
    if (copiedTokenResetTimer.current !== null) {
      clearTimeout(copiedTokenResetTimer.current);
    }

    setCopiedTokenName(tokenName);
    copiedTokenResetTimer.current = setTimeout(() => {
      setCopiedTokenName((currentTokenName) =>
        currentTokenName === tokenName ? null : currentTokenName,
      );
      copiedTokenResetTimer.current = null;
    }, 3000);
  }

  function handleCopy(token: DashboardTokenRow) {
    void navigator.clipboard
      .writeText(token.tokenValue)
      .then(() => markTokenCopied(token.name))
      .catch(() => undefined);
  }

  return (
    <main
      className="flex h-full min-h-0 flex-col gap-knowledge-dashboard-page-gap overflow-hidden px-knowledge-dashboard-page-padding-x pt-knowledge-dashboard-page-padding-top pb-knowledge-dashboard-page-padding-bottom lg:gap-knowledge-dashboard-page-gap-desktop lg:px-knowledge-dashboard-page-padding-x-desktop lg:pt-knowledge-dashboard-page-padding-top-desktop lg:pb-knowledge-dashboard-page-padding-bottom-desktop"
      data-testid="dashboard-route-page"
    >
      <PageHeader data-testid="dashboard-page-header" title="Dashboard" />

      <QuotaSummary
        errorMessage={
          quotaQuery.isError ? errorMessage(quotaQuery.error) : null
        }
        isLoading={quotaQuery.isPending}
        quota={quota}
        quotaAvailable={quotaAvailable}
      />

      <TokenDirectory
        copiedTokenName={copiedTokenName}
        errorMessage={
          tokenQuery.isError ? errorMessage(tokenQuery.error) : null
        }
        isLoading={tokenQuery.isPending}
        onCopy={handleCopy}
        onCreate={() => openDialog({ type: "create" })}
        onDelete={(token) => openDialog({ token, type: "delete" })}
        onRename={(token) => openDialog({ token, type: "rename" })}
        tokens={tokens}
        usageAvailable={usageAvailable}
      />

      {dialogState?.type === "create" ? (
        <TokenDialog
          errorMessage={dialogError}
          isSubmitting={createTokenMutation.isPending}
          mode="create"
          onClose={closeDialog}
          onSubmit={handleCreate}
        />
      ) : null}
      {dialogState?.type === "rename" ? (
        <TokenDialog
          errorMessage={dialogError}
          initialName={dialogState.token.name}
          isSubmitting={renameTokenMutation.isPending}
          mode="rename"
          onClose={closeDialog}
          onSubmit={handleRename}
        />
      ) : null}
      {dialogState?.type === "delete" ? (
        <DeleteTokenDialog
          errorMessage={dialogError}
          isSubmitting={deleteTokenMutation.isPending}
          onClose={closeDialog}
          onConfirm={handleDelete}
          tokenName={dialogState.token.name}
        />
      ) : null}
    </main>
  );
}
