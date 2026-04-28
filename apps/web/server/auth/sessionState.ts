// abstract: Browser-safe web session response types for the BFF auth surface.
// out_of_scope: Token persistence, Logto SDK wiring, and Express route handling.

export interface AuthenticatedWebUser {
  readonly email?: string;
  readonly id: string;
  readonly name?: string;
}

export interface WebAccountProfile {
  readonly email?: string;
  readonly id: string;
  readonly name?: string;
}

export interface UpdateWebAccountProfileRequest {
  readonly name: string | null;
}

export type WebSessionResponse =
  | { readonly status: "anonymous" }
  | {
      readonly status: "authenticated";
      readonly user: AuthenticatedWebUser;
    };
