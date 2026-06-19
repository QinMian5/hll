---
abstract: Cloudflare Tunnel production ingress design for the public Knowledge web, MCP, Logto, and webhook surfaces.
out_of_scope: Cloudflare account provisioning automation, Cloudflare Access authentication policy, Workers or Containers runtime migration, Logto tenant setup, and application route behavior.
---

# Design: cloudflare-ingress

## Active Truth Policy
- Keep only currently accepted decisions in this active document.
- Remove superseded decisions instead of keeping deprecation narratives.
- If decision status is unclear, require clarification before finalizing updates.

## Context
- **Purpose:** Define the production Cloudflare Tunnel ingress boundary that exposes accepted public Knowledge hostnames while keeping application routing, authentication, and service internals owned by the repository runtime.
- **Scope/Boundaries:** Covers the production `cloudflare-ingress` connector service, accepted Cloudflare DNS and Tunnel routing contract, hostname-to-service routing, connector secret boundary, relationship to project-local `nginx`, and validation expectations. Excludes Cloudflare account resource provisioning automation, Cloudflare Access policy, Cloudflare Workers or Containers migration, Logto tenant administration, and web or MCP application behavior.
- **Related Requirements:** R-001, R-005, R-006, R-007.

## Constraint Projection
- **Governing Constraints:** Production access must be reproducible through repository-owned runtime topology, infrastructure assets must remain isolated from application business logic, public access surfaces must be explicitly designated, and active specs must stay synchronized with deployment-affecting changes.
- **Detail Commitments:** Production uses a repository-owned `cloudflare-ingress` service running the official `cloudflare/cloudflared` image. The connector joins the project runtime networks required to reach the project-local `nginx` app gateway and to establish outbound Cloudflare Tunnel connections. Cloudflare DNS and Tunnel resources route `knowledge.orbitalis.org` and `knowledge-logto.orbitalis.org` to the Knowledge production connector. The connector forwards those hostnames to `http://nginx:80`; path routing remains owned by `infra/docker/nginx/default.conf`.
- **Update Rule:** Requirement-level public/private access constraints remain stable while connector service shape, accepted hostnames, Tunnel routing, DNS records, secret boundaries, and validation checks stay in this design document.

## Inputs & Outputs
- **Inputs:**
  - Cloudflare zone and Tunnel resources for `orbitalis.org`.
  - Production runtime value `CLOUDFLARE_TUNNEL_TOKEN`.
  - Production Compose topology.
  - Project-local `nginx` app-gateway routes.
  - Browser, MCP client, Logto, and webhook HTTP requests for accepted public hostnames.
- **Outputs:**
  - Public HTTPS access to `https://knowledge.orbitalis.org`.
  - Public HTTPS access to `https://knowledge-logto.orbitalis.org`.
  - Routed Web BFF, MCP, Logto, and accepted webhook traffic through project-local `nginx`.
  - Cloudflare edge errors when the connector or app gateway is unavailable.
- **Artifacts:**
  - `infra/compose/docker-compose.prod.yml`
  - `infra/env/.env.example`
  - `infra/docker/nginx/default.conf`
  - Cloudflare Tunnel named for the Knowledge production runtime.
  - Cloudflare DNS records for `knowledge.orbitalis.org` and `knowledge-logto.orbitalis.org`.

## Design Approach
- **Approach:** Keep application ingress simple by placing one production Cloudflare Tunnel connector in the Knowledge Compose topology and forwarding accepted public hostnames to the existing project-local `nginx` app gateway. The connector owns only transport from Cloudflare edge into the project network. The app gateway owns path routing. Existing Web BFF, Logto, and MCP authentication remain authoritative.
- **Key Elements:**
  - **Connector service:** `cloudflare-ingress` runs `cloudflare/cloudflared` with Tunnel execution arguments suitable for a remotely managed Cloudflare Tunnel. It starts after project-local `nginx` is healthy and restarts unless stopped.
  - **Network placement:** The connector joins the `edge` network to reach `nginx:80` and an outbound-capable network to establish Tunnel connections to Cloudflare.
  - **Tunnel routing:** The Cloudflare Tunnel routes `knowledge.orbitalis.org` to `http://nginx:80`, routes `knowledge-logto.orbitalis.org` to `http://nginx:80`, and rejects unmatched hostnames with a catch-all `404`.
  - **DNS routing:** Cloudflare DNS uses proxied records for `knowledge.orbitalis.org` and `knowledge-logto.orbitalis.org` that target the accepted Knowledge Tunnel.
  - **App gateway routing:** `nginx` routes `knowledge.orbitalis.org` web traffic to `web`, `knowledge.orbitalis.org/mcp` traffic to `mcp`, accepted webhook paths to receiver roles, and `knowledge-logto.orbitalis.org` traffic to Logto.
  - **Authentication boundary:** Cloudflare Access is not part of the baseline public Knowledge ingress. Browser authentication remains Web BFF plus Logto session. MCP authentication remains Logto Dashboard PAT bearer authentication. Dashboard token management remains BFF-managed Logto Management API orchestration.
  - **Secret boundary:** The connector receives only `CLOUDFLARE_TUNNEL_TOKEN`. It does not receive database URLs, Redis URLs, Logto client secrets, PAT fingerprint secrets, OpenAI keys, app service tokens, or application runtime credentials.
  - **Private service boundary:** FastAPI, PostgreSQL, Redis, MCP internal Dashboard endpoints, and internal service-to-service URLs remain private to repository networks.
  - **Failure behavior:** If the connector cannot reach Cloudflare or `nginx`, public requests fail at the Cloudflare edge or ingress layer while application containers keep their normal health semantics.
- **Interactions:**
  1. A browser or MCP client requests an accepted public Knowledge hostname.
  2. Cloudflare DNS and edge route the request to the accepted Knowledge Tunnel.
  3. `cloudflare-ingress` receives the Tunnel request and forwards it to `http://nginx:80`.
  4. Project-local `nginx` preserves the public Host and protocol context through proxy headers and routes the request to `web`, `mcp`, Logto, or an accepted webhook receiver.
  5. Web BFF, MCP, Logto, and receiver roles apply their existing authentication, authorization, quota, and error-response behavior.

## Validation
- **Checks:**
  - Production Compose rendering includes `cloudflare-ingress` only in the production overlay.
  - `cloudflare-ingress` uses `cloudflare/cloudflared`, starts after `nginx`, and receives only `CLOUDFLARE_TUNNEL_TOKEN`.
  - Production `nginx` remains the only repository app gateway for web, MCP, Logto, and webhook path routing.
  - Production `nginx` does not publish host `80/443` ports directly.
  - Cloudflare DNS records for `knowledge.orbitalis.org` and `knowledge-logto.orbitalis.org` target the accepted Knowledge Tunnel.
  - The accepted Cloudflare Tunnel routes both Knowledge hostnames to `http://nginx:80` and includes a catch-all rejection route.
  - `https://knowledge.orbitalis.org/` returns the web application shell.
  - `https://knowledge.orbitalis.org/docs` returns the product docs route.
  - `https://knowledge.orbitalis.org/web-api/auth/session` returns the browser-safe session contract.
  - `https://knowledge.orbitalis.org/mcp` reaches MCP and preserves existing bearer-token behavior.
  - `https://knowledge-logto.orbitalis.org/oidc/.well-known/openid-configuration` returns Logto OIDC metadata.
  - Public `/api/v1/*` routes remain unavailable through the public Knowledge host.
- **Evidence:**
  - Compose config output for the production overlay.
  - `nginx` configuration inspection.
  - Cloudflare Tunnel connection and configuration inspection.
  - External HTTP smoke checks for Web, MCP, Logto OIDC, and private API non-exposure.
