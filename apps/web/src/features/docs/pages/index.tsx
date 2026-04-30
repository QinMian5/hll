// abstract: Routed unified documentation hub for project overview and MCP client setup guidance.
// out_of_scope: Docs search indexing, markdown content loading, live token generation, and external client execution.

const startHereItems = [
  {
    body: "What the Knowledge Graph is, where Search and Graph View fit, and how the project exposes public web and MCP surfaces.",
    title: "Project overview",
  },
  {
    body: "How model clients connect to the public MCP endpoint with a user-created personal access token.",
    title: "MCP access",
  },
  {
    body: "How token scope, account quota, and usage attribution work before a client starts calling search.",
    title: "Security and quota",
  },
] as const;

const clientItems = [
  {
    body: "Add the Knowledge MCP endpoint to Codex, then use a Dashboard token as the bearer credential for search.",
    command: "codex mcp add knowledge --url https://<your-host>/mcp",
    title: "Codex",
  },
  {
    body: "Register the same MCP endpoint in Claude Code project settings and keep personal token values out of shared files.",
    command: ".claude/settings.local.json",
    title: "Claude Code",
  },
] as const;

function SectionCard({
  body,
  title,
}: {
  readonly body: string;
  readonly title: string;
}) {
  return (
    <article className="rounded-lg border border-[#e0e4eb] bg-white p-5">
      <h3 className="m-0 text-[15px] leading-5 font-medium text-[#131c2d]">
        {title}
      </h3>
      <p className="mt-2 mb-0 text-[13px] leading-5 text-[#606e87]">{body}</p>
    </article>
  );
}

function ClientCard({
  body,
  command,
  title,
}: {
  readonly body: string;
  readonly command: string;
  readonly title: string;
}) {
  return (
    <article className="rounded-lg border border-[#e0e4eb] bg-white p-5">
      <h3 className="m-0 text-[15px] leading-5 font-medium text-[#131c2d]">
        {title}
      </h3>
      <p className="mt-2 mb-0 text-[13px] leading-5 text-[#606e87]">{body}</p>
      <code className="mt-4 block overflow-x-auto rounded-md border border-[#e0e4eb] bg-[#f8fafc] px-3 py-2 text-[12px] leading-5 text-[#131c2d]">
        {command}
      </code>
    </article>
  );
}

export function DocsPage() {
  return (
    <main
      className="h-full overflow-auto px-4 py-5 sm:px-6 md:px-8 md:py-8"
      data-testid="docs-route-page"
    >
      <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-8">
        <header className="flex flex-col gap-3">
          <p className="m-0 text-[12px] leading-4 font-medium tracking-[0.08em] text-[#2563eb] uppercase">
            Knowledge Graph
          </p>
          <div className="flex flex-col gap-2">
            <h1 className="m-0 text-[28px] leading-9 font-medium text-[#131c2d]">
              Docs
            </h1>
            <p className="m-0 max-w-[680px] text-[14px] leading-6 text-[#606e87]">
              Guides for understanding Knowledge Graph and connecting model
              clients.
            </p>
          </div>
        </header>

        <section
          aria-labelledby="docs-start-here"
          className="flex flex-col gap-4"
        >
          <h2
            className="m-0 text-[18px] leading-7 font-medium text-[#131c2d]"
            id="docs-start-here"
          >
            Start here
          </h2>
          <div className="grid gap-3 lg:grid-cols-3">
            {startHereItems.map((item) => (
              <SectionCard
                body={item.body}
                key={item.title}
                title={item.title}
              />
            ))}
          </div>
        </section>

        <section
          aria-labelledby="docs-client-configuration"
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1">
            <h2
              className="m-0 text-[18px] leading-7 font-medium text-[#131c2d]"
              id="docs-client-configuration"
            >
              Client configuration
            </h2>
            <p className="m-0 text-[13px] leading-5 text-[#606e87]">
              Use Dashboard to create personal tokens; keep full client setup
              guidance here.
            </p>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {clientItems.map((item) => (
              <ClientCard
                body={item.body}
                command={item.command}
                key={item.title}
                title={item.title}
              />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
