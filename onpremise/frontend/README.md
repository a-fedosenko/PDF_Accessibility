# PDF Accessibility Frontend (On-Premises)

This directory contains a placeholder frontend configuration for the on-premises deployment.

## Important Note

The actual React application source code should be cloned from:
https://github.com/a-fedosenko/PDF_accessability_UI

## Build Instructions

To use this frontend:

1. Clone the UI repository into this directory:
```bash
cd onpremise/frontend
git clone https://github.com/a-fedosenko/PDF_accessability_UI .
```

2. Ensure the following files from this directory are preserved:
   - Dockerfile
   - nginx.conf
   - env.sh
   - This README.md

3. The Docker build process will:
   - Install dependencies
   - Build the React app
   - Configure Nginx
   - Inject runtime environment variables

## Environment Variables

The following environment variables can be configured in docker-compose-onpremise.yml:

- `REACT_APP_API_URL`: API Gateway URL (default: http://localhost:8080)
- `REACT_APP_KEYCLOAK_URL`: Keycloak authentication URL (default: http://localhost:8090)
- `REACT_APP_KEYCLOAK_REALM`: Keycloak realm (default: pdf-accessibility)
- `REACT_APP_KEYCLOAK_CLIENT_ID`: Keycloak client ID (default: pdf-ui)
- `REACT_APP_MINIO_URL`: MinIO console URL (default: http://localhost:9000)

## Alternative: Use Existing UI

If you've already deployed the UI to AWS Amplify, you can:

1. Remove the `frontend` service from docker-compose-onpremise.yml
2. Update the Amplify app to point to your on-premises API Gateway
3. Configure CORS on the API Gateway to allow requests from the Amplify URL
