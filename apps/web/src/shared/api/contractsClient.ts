// abstract: Shared runtime wiring for the generated OpenAPI contracts client.
// out_of_scope: Feature-specific query orchestration and React rendering logic.

import {
  type ContractsClient,
  createContractsClient,
} from "@knowledge/contracts/generated/client";

import { getApiBaseUrl } from "../config";

export function getContractsClient(): ContractsClient {
  const baseUrl = getApiBaseUrl();

  return baseUrl === undefined
    ? createContractsClient()
    : createContractsClient({ baseUrl });
}
