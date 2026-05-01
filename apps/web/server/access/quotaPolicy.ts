// abstract: Quota policy expansion from configured limits to storage checks.
// out_of_scope: Redis mutation behavior and Express middleware response handling.

import type { QuotaProfileConfig, WebServerConfig } from "../config.js";
import type { QuotaPrincipal } from "./principal.js";
import type { QuotaConsumption, QuotaWindowName } from "./quotaStore.js";

export interface BuildQuotaConsumptionsInput {
  readonly cost: number;
  readonly principal: QuotaPrincipal;
  readonly routeGroup: string;
}

function applyWindowOverride(
  base: QuotaProfileConfig[QuotaWindowName],
  override: Partial<QuotaProfileConfig[QuotaWindowName]> | undefined,
): QuotaProfileConfig[QuotaWindowName] {
  return {
    limit: override?.limit ?? base.limit,
    windowSeconds: override?.windowSeconds ?? base.windowSeconds,
  };
}

function resolvePrincipalProfile(
  config: WebServerConfig,
  input: BuildQuotaConsumptionsInput,
): QuotaProfileConfig {
  const base =
    input.principal.kind === "authenticated"
      ? config.authenticatedQuota
      : config.anonymousQuota;
  const override =
    config.quotaRouteOverrides[input.routeGroup]?.[input.principal.kind];

  return {
    burst: applyWindowOverride(base.burst, override?.burst),
    total: applyWindowOverride(base.total, override?.total),
  };
}

function resolveIpProfile(
  config: WebServerConfig,
  input: BuildQuotaConsumptionsInput,
): QuotaProfileConfig {
  const override = config.quotaRouteOverrides[input.routeGroup]?.ip;

  return {
    burst: applyWindowOverride(config.ipQuota.burst, override?.burst),
    total: applyWindowOverride(config.ipQuota.total, override?.total),
  };
}

function buildKey(parts: readonly string[]): string {
  return parts.join(":");
}

function buildWindowConsumptions(options: {
  readonly cost: number;
  readonly keyPrefix: string;
  readonly principalKey: string;
  readonly profile: QuotaProfileConfig;
  readonly routeGroup: string;
  readonly scope: QuotaConsumption["scope"];
}): QuotaConsumption[] {
  return (["burst", "total"] as const).map((windowName) => {
    const window = options.profile[windowName];

    return {
      cost: options.cost,
      key: `${options.keyPrefix}${buildKey([
        options.scope,
        options.routeGroup,
        windowName,
        options.principalKey,
      ])}`,
      limit: window.limit,
      routeGroup: options.routeGroup,
      scope: options.scope,
      windowName,
      windowSeconds: window.windowSeconds,
    };
  });
}

export function buildQuotaConsumptions(
  config: WebServerConfig,
  input: BuildQuotaConsumptionsInput,
): QuotaConsumption[] {
  const principalProfile = resolvePrincipalProfile(config, input);
  const ipProfile = resolveIpProfile(config, input);

  return [
    ...buildWindowConsumptions({
      cost: input.cost,
      keyPrefix: config.quotaRedisPrefix,
      principalKey: input.principal.principalKey,
      profile: principalProfile,
      routeGroup: input.routeGroup,
      scope: "principal",
    }),
    ...buildWindowConsumptions({
      cost: input.cost,
      keyPrefix: config.quotaRedisPrefix,
      principalKey: input.principal.ipKey,
      profile: ipProfile,
      routeGroup: input.routeGroup,
      scope: "ip",
    }),
  ];
}
