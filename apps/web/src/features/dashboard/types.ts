// abstract: Browser dashboard token lifecycle data contracts.
// out_of_scope: Server-side Logto adapters and visual rendering.

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
