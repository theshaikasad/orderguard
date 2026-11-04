FROM node:24-bookworm-slim AS dependencies
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund --fetch-retries=2 --fetch-timeout=60000 --maxsockets=3

FROM dependencies AS build
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/ ./
RUN npm run build -- --webpack

FROM node:24-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
