// abstract: Quota consumption storage contract and Redis implementation.
// out_of_scope: Principal derivation and Express middleware response handling.

import { createClient } from "redis";

import type { WebServerConfig } from "../config.js";

export type QuotaScope = "ip" | "principal";
export type QuotaWindowName = "burst" | "total";

export interface QuotaConsumption {
  readonly cost: number;
  readonly key: string;
  readonly limit: number;
  readonly routeGroup: string;
  readonly scope: QuotaScope;
  readonly windowName: QuotaWindowName;
  readonly windowSeconds: number;
}

export interface QuotaConsumptionResult {
  readonly allowed: boolean;
  readonly remaining: number;
  readonly retryAfterSeconds: number;
}

export interface QuotaStore {
  readonly consume: (
    consumption: QuotaConsumption,
  ) => Promise<QuotaConsumptionResult>;
}

export interface RedisQuotaClient {
  readonly expire: (key: string, seconds: number) => Promise<unknown>;
  readonly incrBy: (key: string, increment: number) => Promise<number>;
  readonly ttl: (key: string) => Promise<number>;
}

export class RedisQuotaStore implements QuotaStore {
  private readonly client: RedisQuotaClient;

  constructor(client: RedisQuotaClient) {
    this.client = client;
  }

  async consume(
    consumption: QuotaConsumption,
  ): Promise<QuotaConsumptionResult> {
    const count = await this.client.incrBy(consumption.key, consumption.cost);

    if (count === consumption.cost) {
      await this.client.expire(consumption.key, consumption.windowSeconds);
    }

    const ttl = await this.client.ttl(consumption.key);
    const retryAfterSeconds = ttl > 0 ? ttl : consumption.windowSeconds;

    return {
      allowed: count <= consumption.limit,
      remaining: Math.max(consumption.limit - count, 0),
      retryAfterSeconds,
    };
  }
}

export async function createRedisQuotaStore(
  config: WebServerConfig,
): Promise<QuotaStore> {
  const redisClient = createClient({ url: config.redisUrl });
  await redisClient.connect();

  return new RedisQuotaStore(redisClient);
}
