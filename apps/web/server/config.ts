// abstract: Runtime configuration loader for the web BFF process.
// out_of_scope: Feature-specific route policy and browser runtime configuration.

import { z } from "zod";

const BooleanStringSchema = z
  .enum(["true", "false"])
  .default("false")
  .transform((value) => value === "true");

const OptionalTrimmedStringSchema = z
  .string()
  .trim()
  .transform((value) => (value === "" ? undefined : value))
  .optional();

const OptionalUrlStringSchema = OptionalTrimmedStringSchema.refine(
  (value) => value === undefined || URL.canParse(value),
  "Invalid URL",
);

const QuotaWindowOverrideSchema = z
  .object({
    limit: z.number().int().positive().optional(),
    windowSeconds: z.number().int().positive().optional(),
  })
  .strict();

const QuotaProfileOverrideSchema = z
  .object({
    burst: QuotaWindowOverrideSchema.optional(),
    total: QuotaWindowOverrideSchema.optional(),
  })
  .strict();

const QuotaRouteOverridesSchema = z.record(
  z.string(),
  z
    .object({
      anonymous: QuotaProfileOverrideSchema.optional(),
      authenticated: QuotaProfileOverrideSchema.optional(),
    })
    .strict(),
);

const WebServerEnvSchema = z.object({
  KNOWLEDGE_WEB_COOKIE_DOMAIN: OptionalTrimmedStringSchema,
  KNOWLEDGE_WEB_COOKIE_SECURE: BooleanStringSchema,
  KNOWLEDGE_WEB_INTERNAL_API_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_LOGTO_APP_ID: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_APP_SECRET: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_ENDPOINT: z.string().trim().url(),
  KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT: OptionalUrlStringSchema,
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_API_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_ID: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_SECRET: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_RESOURCE: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_MANAGEMENT_TOKEN_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_ID: z.string().trim().min(1),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_SECRET: z.string().trim().min(1),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_RESOURCE: z.string().trim().min(1),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_SCOPES: z.string().trim().min(1),
  KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_TOKEN_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET: z.string().min(32),
  KNOWLEDGE_WEB_PUBLIC_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX: z
    .string()
    .trim()
    .min(1)
    .default("knowledge:web:quota:"),
  KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON: z.string().default("{}"),
  KNOWLEDGE_WEB_REDIS_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_SESSION_SECRET: z.string().min(32),
  KNOWLEDGE_WEB_TRUST_PROXY: BooleanStringSchema,
  KNOWLEDGE_WEB_ANON_BURST_LIMIT: z.coerce
    .number()
    .int()
    .positive()
    .default(20),
  KNOWLEDGE_WEB_ANON_BURST_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(60),
  KNOWLEDGE_WEB_ANON_TOTAL_LIMIT: z.coerce
    .number()
    .int()
    .positive()
    .default(200),
  KNOWLEDGE_WEB_ANON_TOTAL_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(86_400),
  KNOWLEDGE_WEB_AUTH_BURST_LIMIT: z.coerce
    .number()
    .int()
    .positive()
    .default(120),
  KNOWLEDGE_WEB_AUTH_BURST_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(60),
  KNOWLEDGE_WEB_AUTH_TOTAL_LIMIT: z.coerce
    .number()
    .int()
    .positive()
    .default(2_000),
  KNOWLEDGE_WEB_AUTH_TOTAL_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(86_400),
  KNOWLEDGE_WEB_IP_BURST_LIMIT: z.coerce.number().int().positive().default(240),
  KNOWLEDGE_WEB_IP_BURST_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(60),
  KNOWLEDGE_WEB_IP_TOTAL_LIMIT: z.coerce
    .number()
    .int()
    .positive()
    .default(5_000),
  KNOWLEDGE_WEB_IP_TOTAL_WINDOW_SECONDS: z.coerce
    .number()
    .int()
    .positive()
    .default(86_400),
  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),
});

export interface QuotaWindowConfig {
  readonly limit: number;
  readonly windowSeconds: number;
}

export interface QuotaProfileConfig {
  readonly burst: QuotaWindowConfig;
  readonly total: QuotaWindowConfig;
}

export interface QuotaRouteOverride {
  readonly anonymous?: Partial<
    Record<keyof QuotaProfileConfig, Partial<QuotaWindowConfig>>
  >;
  readonly authenticated?: Partial<
    Record<keyof QuotaProfileConfig, Partial<QuotaWindowConfig>>
  >;
}

export type QuotaRouteOverrides = Record<string, QuotaRouteOverride>;

export interface WebServerConfig {
  readonly anonymousQuota: QuotaProfileConfig;
  readonly authenticatedQuota: QuotaProfileConfig;
  readonly cookieDomain?: string;
  readonly cookieSecure: boolean;
  readonly host: string;
  readonly ipQuota: QuotaProfileConfig;
  readonly internalApiBaseUrl: string;
  readonly logtoAppId: string;
  readonly logtoAppSecret: string;
  readonly logtoEndpoint: string;
  readonly logtoInternalEndpoint?: string;
  readonly logtoManagementApiBaseUrl: string;
  readonly logtoManagementClientId: string;
  readonly logtoManagementClientSecret: string;
  readonly logtoManagementResource: string;
  readonly logtoManagementScopes: string;
  readonly logtoManagementTokenUrl: string;
  readonly mcpUsageSummaryBaseUrl: string;
  readonly mcpUsageSummaryClientId: string;
  readonly mcpUsageSummaryClientSecret: string;
  readonly mcpUsageSummaryResource: string;
  readonly mcpUsageSummaryScopes: string;
  readonly mcpUsageSummaryTokenUrl: string;
  readonly nodeEnv: "development" | "production" | "test";
  readonly patFingerprintSecret: string;
  readonly port: number;
  readonly publicBaseUrl: string;
  readonly quotaRedisPrefix: string;
  readonly quotaRouteOverrides: QuotaRouteOverrides;
  readonly redisUrl: string;
  readonly sessionSecret: string;
  readonly trustProxy: boolean;
}

export type WebServerEnv = Record<string, string | undefined>;

export function loadWebServerConfig(
  env: WebServerEnv = process.env,
): WebServerConfig {
  const parsed = WebServerEnvSchema.parse(env);
  const quotaRouteOverrides = QuotaRouteOverridesSchema.parse(
    JSON.parse(parsed.KNOWLEDGE_WEB_QUOTA_ROUTE_OVERRIDES_JSON),
  );

  return {
    anonymousQuota: {
      burst: {
        limit: parsed.KNOWLEDGE_WEB_ANON_BURST_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_ANON_BURST_WINDOW_SECONDS,
      },
      total: {
        limit: parsed.KNOWLEDGE_WEB_ANON_TOTAL_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_ANON_TOTAL_WINDOW_SECONDS,
      },
    },
    authenticatedQuota: {
      burst: {
        limit: parsed.KNOWLEDGE_WEB_AUTH_BURST_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_AUTH_BURST_WINDOW_SECONDS,
      },
      total: {
        limit: parsed.KNOWLEDGE_WEB_AUTH_TOTAL_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_AUTH_TOTAL_WINDOW_SECONDS,
      },
    },
    cookieDomain: parsed.KNOWLEDGE_WEB_COOKIE_DOMAIN,
    cookieSecure: parsed.KNOWLEDGE_WEB_COOKIE_SECURE,
    host: "0.0.0.0",
    ipQuota: {
      burst: {
        limit: parsed.KNOWLEDGE_WEB_IP_BURST_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_IP_BURST_WINDOW_SECONDS,
      },
      total: {
        limit: parsed.KNOWLEDGE_WEB_IP_TOTAL_LIMIT,
        windowSeconds: parsed.KNOWLEDGE_WEB_IP_TOTAL_WINDOW_SECONDS,
      },
    },
    internalApiBaseUrl: parsed.KNOWLEDGE_WEB_INTERNAL_API_BASE_URL,
    logtoAppId: parsed.KNOWLEDGE_WEB_LOGTO_APP_ID,
    logtoAppSecret: parsed.KNOWLEDGE_WEB_LOGTO_APP_SECRET,
    logtoEndpoint: parsed.KNOWLEDGE_WEB_LOGTO_ENDPOINT,
    logtoInternalEndpoint: parsed.KNOWLEDGE_WEB_LOGTO_INTERNAL_ENDPOINT,
    logtoManagementApiBaseUrl:
      parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_API_BASE_URL,
    logtoManagementClientId: parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_ID,
    logtoManagementClientSecret:
      parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_CLIENT_SECRET,
    logtoManagementResource: parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_RESOURCE,
    logtoManagementScopes: parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_SCOPES,
    logtoManagementTokenUrl: parsed.KNOWLEDGE_WEB_LOGTO_MANAGEMENT_TOKEN_URL,
    mcpUsageSummaryBaseUrl: parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_BASE_URL,
    mcpUsageSummaryClientId: parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_ID,
    mcpUsageSummaryClientSecret:
      parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_CLIENT_SECRET,
    mcpUsageSummaryResource: parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_RESOURCE,
    mcpUsageSummaryScopes: parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_SCOPES,
    mcpUsageSummaryTokenUrl: parsed.KNOWLEDGE_WEB_MCP_USAGE_SUMMARY_TOKEN_URL,
    nodeEnv: parsed.NODE_ENV,
    patFingerprintSecret: parsed.KNOWLEDGE_WEB_PAT_FINGERPRINT_SECRET,
    port: 5173,
    publicBaseUrl: parsed.KNOWLEDGE_WEB_PUBLIC_BASE_URL,
    quotaRedisPrefix: parsed.KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX,
    quotaRouteOverrides,
    redisUrl: parsed.KNOWLEDGE_WEB_REDIS_URL,
    sessionSecret: parsed.KNOWLEDGE_WEB_SESSION_SECRET,
    trustProxy: parsed.KNOWLEDGE_WEB_TRUST_PROXY,
  };
}
