# ── Build stage ───────────────────────────────────────────────────────────
# Compiles the React app into a static bundle. Nothing from this stage ships
# in the final image except the contents of /app/dist.
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .

# VITE_API_BASE_URL defaults to '/api' (see src/api/client.js), which matches
# nginx's reverse-proxy routing in this compose setup, so no build arg is
# required for the standard deployment. Override at build time if needed:
#   docker build --build-arg VITE_API_BASE_URL=https://example.com/api .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ── Runtime stage ────────────────────────────────────────────────────────
# Previously this image ran `npm run dev` (Vite's dev server) as the
# production container — unminified, no code-splitting/caching headers, and
# it rebuilds/serves from source on every request. This stage instead serves
# the pre-built static bundle from a minimal nginx image.
FROM nginx:1.25-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.static.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1
