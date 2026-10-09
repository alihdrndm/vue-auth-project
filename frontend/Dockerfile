# syntax=docker/dockerfile:1
# Frontend image for the e2e Compose stack only (production runs on Vercel). Build context:
# the repository root, because the frontend is a package of the root pnpm workspace.

FROM node:24-slim AS build
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --filter frontend
COPY frontend frontend
RUN pnpm --filter frontend build

FROM node:24-slim AS runtime
WORKDIR /app
COPY --from=build --chown=node:node /app /app
USER node
WORKDIR /app/frontend
ENV API_PROXY_TARGET=http://api:8010
EXPOSE 3110
CMD ["node_modules/.bin/vite", "preview", "--host", "0.0.0.0", "--port", "3110"]
