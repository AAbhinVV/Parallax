# syntax=docker/dockerfile:1.7

# =============================================================================
# FRONTEND BUILD (Next.js)
# =============================================================================
ARG NODE_VERSION=22.14.0

FROM node:${NODE_VERSION}-alpine AS frontend-base
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1

# Install the complete dependency graph needed by `next build`.
FROM frontend-base AS frontend-dependencies
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

# Compile the production Next.js application.
FROM frontend-base AS frontend-builder
COPY --from=frontend-dependencies /app/frontend/node_modules ./node_modules
COPY . .
RUN npm run build

# Keep only packages required by `next start` in the runtime image.
FROM frontend-base AS frontend-production-dependencies
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --omit=dev && npm cache clean --force

FROM node:${NODE_VERSION}-alpine AS frontend-runner
WORKDIR /app/frontend

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=frontend-production-dependencies --chown=node:node /app/frontend/node_modules ./node_modules
COPY --from=frontend-builder --chown=node:node /app/frontend/.next ./.next
COPY --from=frontend-builder --chown=node:node /app/frontend/public ./public
COPY --from=frontend-builder --chown=node:node /app/frontend/package.json ./package.json

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD wget --quiet --output-document=- "http://127.0.0.1:${PORT}/login" > /dev/null || exit 1

CMD ["npm", "start"]

# =============================================================================
# BACKEND BUILD (Python/FastAPI)
# =============================================================================
FROM python:3.12-slim AS backend-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]