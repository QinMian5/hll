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

const PositiveIntegerEnvSchema = z.coerce.number().int().positive();

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
  KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_PUBLIC_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX: z.string().trim().min(1),
  KNOWLEDGE_WEB_REDIS_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_SESSION_SECRET: z.string().min(32),
  KNOWLEDGE_WEB_TRUST_PROXY: BooleanStringSchema,
  KNOWLEDGE_WEB_ANON_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_ANON_BURST_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_ANON_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_ANON_TOTAL_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_AUTH_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_AUTH_BURST_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_AUTH_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_AUTH_TOTAL_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_IP_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_IP_BURST_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_IP_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_IP_TOTAL_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_WINDOW_SECONDS:
    PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_WINDOW_SECONDS:
    PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_WINDOW_SECONDS:
    PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_WINDOW_SECONDS:
    PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_WINDOW_SECONDS: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_LIMIT: PositiveIntegerEnvSchema,
  KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_WINDOW_SECONDS: PositiveIntegerEnvSchema,
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
  readonly ip?: Partial<
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
  readonly mcpPublicBaseUrl: string;
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
    mcpPublicBaseUrl: parsed.KNOWLEDGE_WEB_MCP_PUBLIC_BASE_URL,
    port: 5173,
    publicBaseUrl: parsed.KNOWLEDGE_WEB_PUBLIC_BASE_URL,
    quotaRedisPrefix: parsed.KNOWLEDGE_WEB_QUOTA_REDIS_PREFIX,
    quotaRouteOverrides: {
      "taxonomy-view": {
        anonymous: {
          burst: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_BURST_WINDOW_SECONDS,
          },
          total: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_ANON_TOTAL_WINDOW_SECONDS,
          },
        },
        authenticated: {
          burst: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_BURST_WINDOW_SECONDS,
          },
          total: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_AUTH_TOTAL_WINDOW_SECONDS,
          },
        },
        ip: {
          burst: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_BURST_WINDOW_SECONDS,
          },
          total: {
            limit: parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_LIMIT,
            windowSeconds:
              parsed.KNOWLEDGE_WEB_TAXONOMY_VIEW_IP_TOTAL_WINDOW_SECONDS,
          },
        },
      },
    },
    redisUrl: parsed.KNOWLEDGE_WEB_REDIS_URL,
    sessionSecret: parsed.KNOWLEDGE_WEB_SESSION_SECRET,
    trustProxy: parsed.KNOWLEDGE_WEB_TRUST_PROXY,
  };
}
