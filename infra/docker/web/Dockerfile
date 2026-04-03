# abstract: Multi-stage image for web development and production runtime with source-based builds.
# out_of_scope: Edge gateway termination and reverse-proxy deployment policy.
FROM node:24-bookworm-slim AS base

WORKDIR /workspace

RUN corepack enable && corepack use pnpm@10.33.0

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml /workspace/
COPY apps/web/package.json /workspace/apps/web/package.json
COPY packages/contracts/package.json /workspace/packages/contracts/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web /workspace/apps/web
COPY packages/contracts /workspace/packages/contracts

FROM base AS dev

WORKDIR /workspace/apps/web
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0", "--port", "5173"]

FROM base AS prod

WORKDIR /workspace/apps/web
RUN pnpm run build

EXPOSE 4173

CMD ["pnpm", "preview", "--host", "0.0.0.0", "--port", "4173"]
