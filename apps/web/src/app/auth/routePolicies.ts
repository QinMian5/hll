// abstract: Route policy helpers for browser auth coordination.
// out_of_scope: Feature-specific authorization and backend access control.

const protectedRoutePrefixes = ["/dashboard", "/workspace", "/settings"];

export function isProtectedRoute(pathname: string): boolean {
  return protectedRoutePrefixes.some(
    (routePrefix) =>
      pathname === routePrefix || pathname.startsWith(`${routePrefix}/`),
  );
}

export function isPublicRoute(pathname: string): boolean {
  return !isProtectedRoute(pathname);
}
