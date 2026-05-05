// abstract: User-facing error copy for suggested edit submission failures.
// out_of_scope: Dialog rendering and mutation transport execution.

import { WebApiRequestError } from "../../shared/web-api/errors";

export function suggestedEditErrorMessage(error: unknown): string {
  if (!(error instanceof WebApiRequestError)) {
    return "Could not submit the suggestion. Try again.";
  }

  switch (error.code) {
    case "authentication_required":
      return "Sign in to suggest edits.";
    case "session_expired":
      return "Session expired. Sign in again.";
    case "APPLICATION_API_INPUT_INVALID":
    case "invalid_request":
      return "Check the suggestion fields and try again.";
    case "DOMAIN_KNOWLEDGE_RESOURCE_NOT_FOUND":
      return "This card version no longer exists. Refresh and try again.";
    case "DOMAIN_KNOWLEDGE_RULE_VIOLATION":
      return "Change the title or content before submitting.";
    default:
      return error.status >= 400 && error.status < 500
        ? error.message
        : "Could not submit the suggestion. Try again.";
  }
}
