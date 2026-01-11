# Dependencies layer
FROM node:22-alpine AS deps
WORKDIR /app

# Install only the files that affect package resolution to leverage Docker-layer caching
COPY package.json package-lock.json* pnpm-lock.yaml* bun.lockb* ./

# Install all dependencies (we'll clean up runtime deps later)
RUN npm install --ignore-scripts

# Builder layer
FROM node:22-alpine AS builder
WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

# Re-use previously cached node_modules, then copy rest of the codebase
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Optional: output=standalone gives a self-contained server folder
# RUN npx next build --turbo --output standalone
RUN npm run build

# Development runner (no build, just dev server) 
FROM node:22-alpine AS dev
WORKDIR /app

ENV NODE_ENV=development \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000
CMD ["npm", "run", "dev"]

# Production runner
FROM node:22-alpine AS runner
WORKDIR /app

# ---- Runtime env ----
ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Copy the minimal runtime artefacts
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

# Add an unprivileged user for security first
RUN addgroup -g 1001 -S nextjs && adduser -S nextjs -G nextjs -u 1001

# Change ownership of the app directory to the nextjs user
RUN chown -R nextjs:nextjs /app

# Switch to the nextjs user
USER nextjs

# If built with --output standalone, uncomment:
# COPY --from=builder /app/.next/standalone ./ 
# COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["npm", "start"]