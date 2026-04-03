// abstract: Semantic-map transport client built from generated OpenAPI artifacts.
// out_of_scope: Query caching policy and React component rendering behavior.

import { createContractsClient } from "@knowledge/contracts/generated/client";

import { getApiBaseUrl } from "../../../shared/config";

export function createSemanticMapClient() {
  return createContractsClient({
    baseUrl: getApiBaseUrl(),
  });
}
