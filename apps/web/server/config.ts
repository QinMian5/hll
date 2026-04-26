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

const WebServerEnvSchema = z.object({
  KNOWLEDGE_WEB_COOKIE_DOMAIN: OptionalTrimmedStringSchema,
  KNOWLEDGE_WEB_COOKIE_SECURE: BooleanStringSchema,
  KNOWLEDGE_WEB_HOST: z.string().trim().min(1).default("0.0.0.0"),
  KNOWLEDGE_WEB_INTERNAL_API_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_LOGTO_APP_ID: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_APP_SECRET: z.string().trim().min(1),
  KNOWLEDGE_WEB_LOGTO_ENDPOINT: z.string().trim().url(),
  KNOWLEDGE_WEB_PORT: z.coerce.number().int().positive().default(5173),
  KNOWLEDGE_WEB_PUBLIC_BASE_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_REDIS_URL: z.string().trim().url(),
  KNOWLEDGE_WEB_SESSION_SECRET: z.string().min(32),
  KNOWLEDGE_WEB_TRUST_PROXY: BooleanStringSchema,
  NODE_ENV: z
    .enum(["development", "production", "test"])
    .default("development"),
});

export interface WebServerConfig {
  readonly cookieDomain?: string;
  readonly cookieSecure: boolean;
  readonly host: string;
  readonly internalApiBaseUrl: string;
  readonly logtoAppId: string;
  readonly logtoAppSecret: string;
  readonly logtoEndpoint: string;
  readonly nodeEnv: "development" | "production" | "test";
  readonly port: number;
  readonly publicBaseUrl: string;
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
    cookieDomain: parsed.KNOWLEDGE_WEB_COOKIE_DOMAIN,
    cookieSecure: parsed.KNOWLEDGE_WEB_COOKIE_SECURE,
    host: parsed.KNOWLEDGE_WEB_HOST,
    internalApiBaseUrl: parsed.KNOWLEDGE_WEB_INTERNAL_API_BASE_URL,
    logtoAppId: parsed.KNOWLEDGE_WEB_LOGTO_APP_ID,
    logtoAppSecret: parsed.KNOWLEDGE_WEB_LOGTO_APP_SECRET,
    logtoEndpoint: parsed.KNOWLEDGE_WEB_LOGTO_ENDPOINT,
    nodeEnv: parsed.NODE_ENV,
    port: parsed.KNOWLEDGE_WEB_PORT,
    publicBaseUrl: parsed.KNOWLEDGE_WEB_PUBLIC_BASE_URL,
    redisUrl: parsed.KNOWLEDGE_WEB_REDIS_URL,
    sessionSecret: parsed.KNOWLEDGE_WEB_SESSION_SECRET,
    trustProxy: parsed.KNOWLEDGE_WEB_TRUST_PROXY,
  };
}
