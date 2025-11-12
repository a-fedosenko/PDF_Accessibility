#!/bin/sh
# Script to inject runtime environment variables into React app

# Create env-config.js with runtime environment variables
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  REACT_APP_API_URL: "${REACT_APP_API_URL:-http://localhost:8080}",
  REACT_APP_KEYCLOAK_URL: "${REACT_APP_KEYCLOAK_URL:-http://localhost:8090}",
  REACT_APP_KEYCLOAK_REALM: "${REACT_APP_KEYCLOAK_REALM:-pdf-accessibility}",
  REACT_APP_KEYCLOAK_CLIENT_ID: "${REACT_APP_KEYCLOAK_CLIENT_ID:-pdf-ui}",
  REACT_APP_MINIO_URL: "${REACT_APP_MINIO_URL:-http://localhost:9000}"
};
EOF

echo "Environment configuration injected:"
cat /usr/share/nginx/html/env-config.js
