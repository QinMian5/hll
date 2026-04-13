// abstract: Shared utility helpers for class composition and small UI adapters.
// out_of_scope: Feature-specific data formatting or domain logic.

export type ClassValue = false | null | string | undefined;

export function cn(...inputs: readonly ClassValue[]): string {
  return inputs.filter(Boolean).join(" ");
}
