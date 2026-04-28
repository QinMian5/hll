// abstract: Anonymous Search card edit sign-in prompt dialog.
// out_of_scope: Logto callback handling and authenticated suggestion form behavior.

import { X } from "lucide-react";

interface SignInRequiredDialogProps {
  readonly onClose: () => void;
}

export function SignInRequiredDialog({ onClose }: SignInRequiredDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(15,23,42,0.22)] px-4">
      <button
        aria-label="Close sign-in required dialog scrim"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        type="button"
      />
      <section
        aria-modal="true"
        aria-label="Sign in to suggest edits"
        className="relative flex w-full max-w-[440px] flex-col gap-5 rounded-lg border border-[#e0e4eb] bg-white p-6 shadow-[0_24px_80px_rgba(38,51,82,0.22)]"
        role="dialog"
      >
        <div className="flex items-center gap-3">
          <h2 className="m-0 min-w-0 flex-1 text-[18px] leading-6 font-semibold text-[#131c2d]">
            Sign in to suggest edits
          </h2>
          <button
            aria-label="Close sign-in required dialog"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-[#606e87] hover:bg-[#eff6ff] hover:text-[#131c2d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
        <p className="m-0 text-[14px] leading-5 text-[#606e87]">
          Sign in to suggest changes and help improve this knowledge card.
        </p>
        <form action="/web-api/auth/sign-in" method="post">
          <button
            className="h-10 w-full rounded-lg bg-[#006bff] px-4 text-[14px] leading-5 font-medium text-white hover:bg-[#005fe0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#006bff]"
            type="submit"
          >
            Sign in
          </button>
        </form>
      </section>
    </div>
  );
}
