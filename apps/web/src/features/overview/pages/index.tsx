// abstract: Routed placeholder page for the future Overview view.
// out_of_scope: Future Overview feature modules and live data integrations.

export function OverviewPage() {
  return (
    <main
      className="flex min-h-full items-center justify-center p-6"
      data-testid="overview-route-page"
    >
      <section className="rounded-[24px] border border-[rgba(15,23,42,0.08)] bg-white px-8 py-10 shadow-[0_18px_52px_rgba(107,133,189,0.06)]">
        <h1 className="m-0 text-[24px] leading-8 font-medium text-[#0F172A]">
          Overview
        </h1>
        <p className="mt-3 mb-0 text-[14px] leading-6 text-[rgba(71,85,105,0.92)]">
          Overview content is not implemented yet.
        </p>
      </section>
    </main>
  );
}
