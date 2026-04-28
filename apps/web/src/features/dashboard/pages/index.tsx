// abstract: Routed dashboard page for personal access token lifecycle management.
// out_of_scope: AppShell navigation chrome and server-side token adapters.

import { useState } from "react";
import { DeleteTokenDialog, TokenDialog } from "../components/TokenDialog";
import { TokenDirectory } from "../components/TokenDirectory";
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

export function DashboardPage() {
  const tokenQuery = useDashboardTokensQuery();
  const createTokenMutation = useCreateDashboardTokenMutation();
  const renameTokenMutation = useRenameDashboardTokenMutation();
  const deleteTokenMutation = useDeleteDashboardTokenMutation();
  const [dialogState, setDialogState] = useState<DialogState>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const tokens = tokenQuery.data?.tokens ?? [];
  const usageAvailable = tokenQuery.data?.usageAvailable ?? true;

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
      setDialogError(errorMessage(error));
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
      setDialogError(errorMessage(error));
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
      setDialogError(errorMessage(error));
    }
  }

  function handleCopy(token: DashboardTokenRow) {
    void navigator.clipboard.writeText(token.tokenValue);
  }

  return (
    <main
      className="flex h-full min-h-0 flex-col gap-4 overflow-hidden px-4 py-4 lg:gap-5 lg:px-8 lg:pt-6 lg:pb-8"
      data-testid="dashboard-route-page"
    >
      <header
        className="flex h-[52px] shrink-0 items-center lg:h-16"
        data-testid="dashboard-page-header"
      >
        <h1 className="m-0 text-[16px] leading-6 font-semibold text-[#131c2d] lg:text-[18px] lg:leading-[48px]">
          Dashboard
        </h1>
      </header>

      <TokenDirectory
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
