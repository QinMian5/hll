// abstract: Figma-projected MCP client setup page for the Docs route.
// out_of_scope: Markdown content loading, live token generation, and external MCP client execution.

import { Copy } from "lucide-react";
import { useMemo, useState } from "react";

import { resolveBrowserRuntimeConfig } from "../../../shared/config";
import { PageHeader, ScrollArea } from "../../../shared/ui";
import { cn } from "../../../shared/utils";

type DocsClientId = "codex" | "claude-code" | "openclaw";

interface DocsInstructionStep {
  readonly body: string;
  readonly description: string;
  readonly kind: "instruction";
  readonly title: string;
}

interface DocsCommandStep {
  readonly command: string;
  readonly copyLabel: string;
  readonly description: string;
  readonly kind: "command";
  readonly label: string;
  readonly title: string;
}

type DocsSetupStep = DocsCommandStep | DocsInstructionStep;

interface DocsClient {
  readonly configurationTitle: string;
  readonly iconSrc: string;
  readonly id: DocsClientId;
  readonly name: string;
  readonly panelTitle: string;
  readonly steps: readonly DocsSetupStep[];
}

interface BrowserRuntimeConfigWindow extends Window {
  readonly __KNOWLEDGE_RUNTIME_CONFIG__?: Record<string, unknown>;
}

function readBrowserRuntimeConfig(): Record<string, unknown> {
  return (
    (window as BrowserRuntimeConfigWindow).__KNOWLEDGE_RUNTIME_CONFIG__ ?? {}
  );
}

function createDocsClients(mcpPublicBaseUrl: string): readonly DocsClient[] {
  return [
    {
      configurationTitle: "Codex Configuration",
      iconSrc: "/docs-clients/codex-icon.png",
      id: "codex",
      name: "Codex",
      panelTitle: "Connect Knowledge to Codex",
      steps: [
        {
          body: "Dashboard > Tokens > Create Token > Copy token",
          description:
            "Create or copy a personal access token in Dashboard, then paste it into the client configuration below.",
          kind: "instruction",
          title: "Create a Dashboard token",
        },
        {
          command: `codex mcp add knowledge --url ${mcpPublicBaseUrl}`,
          copyLabel: "Copy command",
          description: "Add Knowledge as a Streamable HTTP MCP server.",
          kind: "command",
          label: "Terminal",
          title: "Add the MCP server",
        },
        {
          command: `[mcp_servers.knowledge]\nurl = "${mcpPublicBaseUrl}"\nhttp_headers = { Authorization = "Bearer <Dashboard PAT>" }`,
          copyLabel: "Copy configuration",
          description:
            "Add the Dashboard token to the Codex server entry in ~/.codex/config.toml.",
          kind: "command",
          label: "Config",
          title: "Set bearer authentication",
        },
        {
          command: "codex mcp get knowledge",
          copyLabel: "Copy command",
          description: "Review the saved Knowledge MCP definition.",
          kind: "command",
          label: "Terminal",
          title: "Inspect the server",
        },
        {
          command: "codex mcp list",
          copyLabel: "Copy command",
          description:
            "Confirm Knowledge appears in the configured MCP server list.",
          kind: "command",
          label: "Terminal",
          title: "List configured servers",
        },
      ],
    },
    {
      configurationTitle: "Claude Code Configuration",
      iconSrc: "/docs-clients/claudecode-icon.png",
      id: "claude-code",
      name: "Claude Code",
      panelTitle: "Connect Knowledge to Claude Code",
      steps: [
        {
          body: "Dashboard > Tokens > Create Token > Copy token",
          description:
            "Create or copy a personal access token in Dashboard, then paste it into the client configuration below.",
          kind: "instruction",
          title: "Create a Dashboard token",
        },
        {
          command: `claude mcp add --transport http knowledge ${mcpPublicBaseUrl} --header "Authorization: Bearer <Dashboard PAT>"`,
          copyLabel: "Copy command",
          description:
            "Add Knowledge with HTTP transport and the Dashboard token in the Authorization header.",
          kind: "command",
          label: "Terminal",
          title: "Add the MCP server with bearer authentication",
        },
        {
          command: "claude mcp get knowledge",
          copyLabel: "Copy command",
          description: "Review the saved Knowledge MCP definition.",
          kind: "command",
          label: "Terminal",
          title: "Inspect the server",
        },
        {
          command: "claude mcp list",
          copyLabel: "Copy command",
          description:
            "Confirm Knowledge appears in Claude Code's MCP server list.",
          kind: "command",
          label: "Terminal",
          title: "List configured servers",
        },
      ],
    },
    {
      configurationTitle: "OpenClaw Configuration",
      iconSrc: "/docs-clients/openclaw-icon.png",
      id: "openclaw",
      name: "OpenClaw",
      panelTitle: "Connect Knowledge to OpenClaw",
      steps: [
        {
          body: "Dashboard > Tokens > Create Token > Copy token",
          description:
            "Create or copy a personal access token in Dashboard, then paste it into the client configuration below.",
          kind: "instruction",
          title: "Create a Dashboard token",
        },
        {
          command: `openclaw mcp set knowledge '{"url":"${mcpPublicBaseUrl}","transport":"streamable-http","headers":{"Authorization":"Bearer <Dashboard PAT>"}}'`,
          copyLabel: "Copy command",
          description:
            "Save Knowledge as a Streamable HTTP MCP server with the Dashboard token header.",
          kind: "command",
          label: "Terminal",
          title: "Save the MCP server with bearer authentication",
        },
        {
          command: "openclaw mcp show knowledge --json",
          copyLabel: "Copy command",
          description:
            "Review the registry entry. This does not validate live authentication.",
          kind: "command",
          label: "Terminal",
          title: "Inspect the saved server",
        },
        {
          command: "openclaw mcp list",
          copyLabel: "Copy command",
          description:
            "Confirm Knowledge appears in the OpenClaw MCP registry.",
          kind: "command",
          label: "Terminal",
          title: "List configured servers",
        },
      ],
    },
  ];
}

const scrollAreaTheme =
  "[--scroll-area-padding-right:var(--spacing-docs-scrollbar-width)] [--scroll-area-scrollbar-width:var(--spacing-docs-scrollbar-width)] [--scroll-area-thumb-color:var(--color-docs-scrollbar-thumb)] [--scroll-area-track-color:var(--color-docs-scrollbar-track)]";

function copyCommand(command: string) {
  if (typeof navigator === "undefined" || navigator.clipboard === undefined) {
    return;
  }

  void navigator.clipboard.writeText(command).catch(() => undefined);
}

function ClientRow({
  client,
  isSelected,
  onSelect,
}: {
  readonly client: DocsClient;
  readonly isSelected: boolean;
  readonly onSelect: () => void;
}) {
  return (
    <button
      aria-controls="docs-client-configuration-panel"
      aria-pressed={isSelected}
      className={cn(
        "flex h-docs-client-row-height w-full shrink-0 items-center gap-docs-client-row-gap rounded-knowledge-surface border p-docs-control-padding text-left transition-colors",
        isSelected
          ? "border-docs-border-accent bg-knowledge-surface-accent-soft"
          : "border-knowledge-border-card bg-knowledge-surface-card hover:border-docs-border-accent hover:bg-knowledge-surface-accent-soft",
      )}
      onClick={onSelect}
      type="button"
    >
      <img
        alt=""
        className="size-docs-client-icon-size shrink-0 object-cover"
        src={client.iconSrc}
      />
      <span className="min-w-0 flex-1 text-docs-client-label font-semibold text-knowledge-text-default">
        {client.name}
      </span>
    </button>
  );
}

function TerminalCommand({
  command,
  copyLabel,
  label,
}: {
  readonly command: string;
  readonly copyLabel: string;
  readonly label: string;
}) {
  return (
    <div className="flex w-full shrink-0 flex-col items-start overflow-hidden rounded-knowledge-surface bg-docs-terminal-body">
      <div className="flex h-docs-terminal-header-height w-full shrink-0 items-center gap-docs-control-gap bg-docs-terminal-header px-docs-terminal-padding">
        <span className="min-w-0 flex-1 text-docs-terminal-label font-medium text-knowledge-text-inverse">
          {label}
        </span>
        <button
          aria-label={`${copyLabel}: ${command}`}
          className="flex size-docs-icon-button-size shrink-0 items-center justify-center rounded-docs-icon-button text-docs-terminal-action transition-colors hover:bg-docs-terminal-action-hover-bg hover:text-docs-terminal-action-hover"
          onClick={() => copyCommand(command)}
          title={copyLabel}
          type="button"
        >
          <Copy
            aria-hidden="true"
            className="size-docs-copy-icon-size"
            strokeWidth={2}
          />
        </button>
      </div>
      <div className="flex w-full shrink-0 flex-col items-start bg-docs-terminal-body p-docs-terminal-padding">
        <code className="w-full whitespace-pre-wrap break-words font-mono text-docs-terminal text-knowledge-text-inverse">
          {command}
        </code>
      </div>
    </div>
  );
}

function InstructionBlock({ body }: { readonly body: string }) {
  return (
    <div
      className="w-full rounded-knowledge-surface border border-docs-instruction-border bg-docs-instruction-bg px-docs-instruction-padding-x py-docs-instruction-padding-y"
      data-testid="docs-instruction-block"
    >
      <p className="m-0 w-full text-docs-step-body text-knowledge-text-muted">
        {body}
      </p>
    </div>
  );
}

function SetupStep({
  index,
  step,
}: {
  readonly index: number;
  readonly step: DocsSetupStep;
}) {
  return (
    <article
      className="flex w-full shrink-0 items-start gap-docs-step-row-gap"
      data-testid="docs-setup-step"
    >
      <div className="flex size-docs-step-badge-size shrink-0 items-center justify-center rounded-full border border-docs-border-accent bg-knowledge-surface-accent-soft text-center text-docs-terminal-label font-semibold text-knowledge-text-default">
        {index + 1}
      </div>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-docs-content-gap">
        <h3 className="m-0 w-full text-docs-step-title font-semibold text-knowledge-text-default">
          {step.title}
        </h3>
        <p className="m-0 w-full text-docs-step-body text-knowledge-text-muted">
          {step.description}
        </p>
        {step.kind === "instruction" ? (
          <InstructionBlock body={step.body} />
        ) : (
          <TerminalCommand
            command={step.command}
            copyLabel={step.copyLabel}
            label={step.label}
          />
        )}
      </div>
    </article>
  );
}

export function DocsPage() {
  const [selectedClientId, setSelectedClientId] =
    useState<DocsClientId>("codex");
  const browserRuntimeConfig = useMemo(
    () => resolveBrowserRuntimeConfig(readBrowserRuntimeConfig()),
    [],
  );
  const docsClients = useMemo(
    () => createDocsClients(browserRuntimeConfig.mcpPublicBaseUrl),
    [browserRuntimeConfig.mcpPublicBaseUrl],
  );
  const selectedClient =
    docsClients.find((client) => client.id === selectedClientId) ??
    docsClients[0];

  return (
    <main
      className="flex h-full min-h-0 w-full flex-col gap-docs-page-gap overflow-hidden bg-docs-page-bg p-4 md:px-8 md:pt-6 md:pb-8"
      data-testid="docs-route-page"
    >
      <PageHeader title="MCP Client Setup" />

      <div
        className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_minmax(0,2fr)] gap-4 overflow-hidden lg:grid-cols-[256px_minmax(0,1fr)] lg:grid-rows-none xl:grid-cols-[288px_minmax(0,1fr)] 2xl:grid-cols-[320px_minmax(0,1fr)]"
        data-testid="docs-workspace"
      >
        <section
          aria-labelledby="docs-clients-title"
          className="flex min-h-0 flex-col gap-4 overflow-hidden rounded-knowledge-surface lg:h-full"
        >
          <h2
            className="m-0 w-full shrink-0 text-docs-section-title font-semibold text-knowledge-text-default"
            id="docs-clients-title"
          >
            Clients
          </h2>
          <ScrollArea
            className={cn("min-h-0 w-full flex-1", scrollAreaTheme)}
            data-testid="docs-client-scroll-area"
            viewportClassName="flex min-h-full w-full flex-col gap-4"
          >
            {docsClients.map((client) => (
              <ClientRow
                client={client}
                isSelected={client.id === selectedClient.id}
                key={client.id}
                onSelect={() => setSelectedClientId(client.id)}
              />
            ))}
          </ScrollArea>
        </section>

        <section
          aria-labelledby="docs-client-configuration-title"
          className="flex min-h-0 flex-col gap-4 overflow-hidden"
        >
          <h2
            className="m-0 w-full shrink-0 text-docs-section-title font-semibold text-knowledge-text-default"
            id="docs-client-configuration-title"
          >
            {selectedClient.configurationTitle}
          </h2>
          <div
            className="flex min-h-0 flex-1 flex-col items-start gap-4 overflow-hidden rounded-knowledge-surface border border-knowledge-border-card bg-knowledge-surface-card p-4 md:p-knowledge-surface-padding"
            data-testid="docs-setup-panel"
            id="docs-client-configuration-panel"
          >
            <div
              className="flex w-full shrink-0 flex-col items-start"
              data-testid="docs-setup-panel-header"
            >
              <p className="m-0 w-full text-docs-panel-title font-semibold text-knowledge-text-default">
                {selectedClient.panelTitle}
              </p>
            </div>
            <div className="h-px w-full shrink-0 bg-knowledge-divider-subtle" />
            <ScrollArea
              className={cn("min-h-0 w-full flex-1", scrollAreaTheme)}
              data-testid="docs-steps-scroll-area"
              resetScrollKey={selectedClient.id}
              viewportClassName="flex min-h-full w-full flex-col gap-4"
            >
              {selectedClient.steps.map((step, index) => (
                <SetupStep
                  index={index}
                  key={`${selectedClient.id}-${step.title}`}
                  step={step}
                />
              ))}
            </ScrollArea>
          </div>
        </section>
      </div>
    </main>
  );
}
