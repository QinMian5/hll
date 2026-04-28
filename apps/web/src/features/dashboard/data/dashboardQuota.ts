// abstract: TanStack Query adapter for dashboard MCP account quota.
// out_of_scope: Dashboard quota rendering and server-side MCP adapters.

import { queryOptions, useQuery } from "@tanstack/react-query";

import { fetchWebApiJson } from "../../../shared/web-api/client";
import type { DashboardQuotaResponse } from "../types";

const dashboardQuotaQueryKeys = {
  quota: ["dashboard", "quota"] as const,
};

export async function fetchDashboardQuota(): Promise<DashboardQuotaResponse> {
  return await fetchWebApiJson<DashboardQuotaResponse>(
    "/web-api/dashboard/quota",
  );
}

export function dashboardQuotaQueryOptions() {
  return queryOptions({
    queryFn: fetchDashboardQuota,
    queryKey: dashboardQuotaQueryKeys.quota,
  });
}

export function useDashboardQuotaQuery() {
  return useQuery(dashboardQuotaQueryOptions());
}
