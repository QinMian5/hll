// abstract: Server-side user access-token retry helpers for BFF Logto operations.
// out_of_scope: Logto HTTP transport and route-level error rendering.

export interface UserAccessTokenClient {
  readonly clearAccessToken: () => Promise<void>;
  readonly getAccessToken: () => Promise<string>;
}

export interface UserAccessTokenRetryOptions {
  readonly isAccessTokenRejected?: (error: unknown) => boolean;
}

export class WebSessionExpiredError extends Error {
  constructor() {
    super("Session expired.");
    this.name = "WebSessionExpiredError";
  }
}

function isLogtoAuthRejected(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as { readonly code?: unknown }).code === "not_authenticated"
  );
}

function isAccessTokenRejected(
  error: unknown,
  options: UserAccessTokenRetryOptions,
): boolean {
  return options.isAccessTokenRejected?.(error) ?? isLogtoAuthRejected(error);
}

export async function resolveUserAccessTokenWithRetry(
  client: UserAccessTokenClient,
): Promise<string> {
  try {
    return await client.getAccessToken();
  } catch (error) {
    if (!isLogtoAuthRejected(error)) {
      throw error;
    }
  }

  await client.clearAccessToken();

  try {
    return await client.getAccessToken();
  } catch (error) {
    if (isLogtoAuthRejected(error)) {
      throw new WebSessionExpiredError();
    }

    throw error;
  }
}

export async function requestWithUserAccessTokenRetry<T>(
  client: UserAccessTokenClient,
  request: (accessToken: string) => Promise<T>,
  options: UserAccessTokenRetryOptions = {},
): Promise<T> {
  try {
    return await request(await resolveUserAccessTokenWithRetry(client));
  } catch (error) {
    if (!isAccessTokenRejected(error, options)) {
      throw error;
    }
  }

  await client.clearAccessToken();

  try {
    return await request(await resolveUserAccessTokenWithRetry(client));
  } catch (error) {
    if (isAccessTokenRejected(error, options)) {
      throw new WebSessionExpiredError();
    }

    throw error;
  }
}
