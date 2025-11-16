# Multi-stage Dockerfile for Nuxt 4 frontend
# Stage 1: Build stage
FROM node:20-alpine as builder

# Set working directory
WORKDIR /build

# Copy package files
COPY package*.json ./

# Install dependencies (use ci for production)
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production runtime stage
FROM node:20-alpine

# Set environment variables
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

# Set working directory
WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache curl

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm ci --only=production && npm cache clean --force

# Copy built application from builder
COPY --from=builder /build/.output ./.output
COPY --from=builder /build/nuxt.config.ts ./nuxt.config.ts

# Create non-root user for security
# Use existing group if GID 1000 exists, otherwise create new group
RUN (addgroup -g 1001 appuser 2>/dev/null || true) && \
    adduser -D -u 1001 -G appuser appuser 2>/dev/null || adduser -D -u 1001 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start the application
CMD ["node", ".output/server/index.mjs"]
