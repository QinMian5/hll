// abstract: Browser dashboard token lifecycle and quota data contracts.
// out_of_scope: Server-side Logto adapters and visual rendering.

export interface DashboardQuotaWindow {
  readonly limit: number;
  readonly remaining: number;
  readonly resetAt: string | null;
  readonly startedAt: string | null;
  readonly used: number;
  readonly windowSeconds: number;
}

export interface DashboardQuotaSummary {
  readonly daily: DashboardQuotaWindow;
  readonly weekly: DashboardQuotaWindow;
}

export interface DashboardQuotaResponse {
  readonly quota: DashboardQuotaSummary | null;
  readonly quotaAvailable: boolean;
}

export interface DashboardTokenRow {
  readonly createdAt: string;
  readonly expiresAt: string | null;
  readonly lastUsedAt: string | null;
  readonly maskedToken: string;
  readonly name: string;
  readonly tokenValue: string;
  readonly usageCount: number | null;
}

export interface DashboardTokensResponse {
  readonly tokens: readonly DashboardTokenRow[];
  readonly usageAvailable: boolean;
}

export interface DashboardTokenMutationResponse {
  readonly token: DashboardTokenRow;
  readonly usageAvailable: boolean;
}

export interface CreateDashboardTokenInput {
  readonly name: string;
}

export interface RenameDashboardTokenInput {
  readonly currentName: string;
  readonly name: string;
}

export interface DeleteDashboardTokenInput {
  readonly name: string;
}
