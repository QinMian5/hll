// abstract: Routed placeholder page for the Settings account-menu surface.
// out_of_scope: Account preferences workflows and backend data orchestration.

export function SettingsPage() {
  return (
    <main
      className="flex h-full min-h-0 items-center justify-center overflow-hidden text-center"
      data-testid="settings-route-page"
    >
      <div>
        <h1 className="m-0 text-[16px] leading-[22px] font-black text-[#131c2d]">
          Settings
        </h1>
        <p className="m-0 text-[13px] leading-[18px] font-normal text-[#606e87]">
          Route content is projected here
        </p>
      </div>
    </main>
  );
}
