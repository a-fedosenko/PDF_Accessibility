FROM node:18 AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app with environment variables
ARG REACT_APP_API_URL
ARG REACT_APP_KEYCLOAK_URL
ARG REACT_APP_KEYCLOAK_REALM
ARG REACT_APP_KEYCLOAK_CLIENT_ID

ENV REACT_APP_API_URL=${REACT_APP_API_URL}
ENV REACT_APP_KEYCLOAK_URL=${REACT_APP_KEYCLOAK_URL}
ENV REACT_APP_KEYCLOAK_REALM=${REACT_APP_KEYCLOAK_REALM}
ENV REACT_APP_KEYCLOAK_CLIENT_ID=${REACT_APP_KEYCLOAK_CLIENT_ID}

RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy environment variable injection script
COPY env.sh /docker-entrypoint.d/40-env.sh
RUN chmod +x /docker-entrypoint.d/40-env.sh

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
