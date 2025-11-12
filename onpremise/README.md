# On-Premises Deployment - Support Files

This directory contains all the necessary configuration files and Dockerfiles to support the on-premises deployment of PDF Accessibility Solutions using Docker Compose.

## Directory Structure

```
onpremise/
├── api-gateway/              # API Gateway service
│   ├── Dockerfile            # FastAPI backend container
│   ├── main.py               # FastAPI application
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # Frontend web application
│   ├── Dockerfile            # React + Nginx container
│   ├── nginx.conf            # Nginx configuration
│   ├── env.sh                # Runtime environment injection
│   ├── package.json          # Node.js dependencies (placeholder)
│   └── README.md             # Frontend setup instructions
│
└── monitoring/               # Monitoring and observability
    ├── prometheus.yml        # Prometheus scrape configuration
    ├── loki-config.yml       # Loki log aggregation config
    └── grafana-dashboards/   # Grafana dashboard definitions
        ├── pdf-processing-dashboard.json
        └── system-overview-dashboard.json
```

## Components Overview

### API Gateway (`api-gateway/`)

**Purpose**: FastAPI-based REST API that replaces AWS API Gateway and Lambda functions for user-facing operations.

**Features**:
- PDF upload endpoint with authentication
- Job status tracking
- User quota management
- MinIO (S3-compatible) integration
- PostgreSQL database integration
- Redis job queue integration
- Keycloak authentication support

**Endpoints**:
- `GET /` - Health check
- `GET /health` - Detailed service health
- `POST /upload` - Upload PDF for processing
- `GET /jobs/{job_id}` - Get job status
- `GET /jobs` - List user's jobs
- `GET /user/info` - Get user information and quota
- `POST /user/update-quota` - Update user quota (admin only)

**Environment Variables**:
```bash
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET_NAME=pdfaccessibility
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=pdfuser
POSTGRES_PASSWORD=pdfpassword
POSTGRES_DB=pdf_accessibility
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=your-secret-key-change-me
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=pdf-accessibility
```

### Frontend (`frontend/`)

**Purpose**: React-based web UI served through Nginx that provides the user interface for PDF upload and management.

**Important Note**: The actual React source code needs to be cloned from:
```bash
cd onpremise/frontend
git clone https://github.com/a-fedosenko/PDF_accessability_UI .
```

The provided files (Dockerfile, nginx.conf, env.sh) will work with the cloned repository.

**Features**:
- User authentication with Keycloak
- PDF upload interface
- Job status monitoring
- Result download
- Responsive design
- API proxy through Nginx

**Environment Variables**:
```bash
REACT_APP_API_URL=http://localhost:8080
REACT_APP_KEYCLOAK_URL=http://localhost:8090
REACT_APP_KEYCLOAK_REALM=pdf-accessibility
REACT_APP_KEYCLOAK_CLIENT_ID=pdf-ui
REACT_APP_MINIO_URL=http://localhost:9000
```

### Monitoring (`monitoring/`)

**Purpose**: Complete observability stack with metrics, logs, and dashboards.

**Components**:

1. **Prometheus** (`prometheus.yml`)
   - Metrics collection from all services
   - 15-second scrape interval
   - Pre-configured for all PDF processing services
   - MinIO, PostgreSQL, Redis monitoring

2. **Loki** (`loki-config.yml`)
   - Log aggregation
   - 31-day retention
   - Filesystem-based storage
   - Automatic log rotation and compaction

3. **Grafana Dashboards** (`grafana-dashboards/`)
   - **PDF Processing Dashboard**: Queue length, job status, processing times, error rates
   - **System Overview Dashboard**: Service health, CPU/memory usage, network/disk I/O

## Usage

### Quick Start

1. **Start all services**:
```bash
cd /home/andreyf/projects/PDF_Accessibility
docker-compose -f docker-compose-onpremise.yml up -d
```

2. **Access services**:
- Frontend: http://localhost:3000
- API Gateway: http://localhost:8080
- MinIO Console: http://localhost:9001 (user: minioadmin, pass: minioadmin123)
- Keycloak: http://localhost:8090 (admin/admin123)
- Grafana: http://localhost:3001 (admin/admin123)
- Prometheus: http://localhost:9090

3. **Check service health**:
```bash
curl http://localhost:8080/health
```

4. **View logs**:
```bash
docker-compose -f docker-compose-onpremise.yml logs -f api-gateway
```

### Building Individual Services

**API Gateway**:
```bash
cd onpremise/api-gateway
docker build -t pdf-api-gateway .
```

**Frontend** (after cloning UI repository):
```bash
cd onpremise/frontend
git clone https://github.com/a-fedosenko/PDF_accessability_UI .
docker build -t pdf-frontend \
  --build-arg REACT_APP_API_URL=http://localhost:8080 \
  --build-arg REACT_APP_KEYCLOAK_URL=http://localhost:8090 \
  .
```

## Configuration

### SSL/TLS Setup (Production)

For production deployment, configure SSL/TLS certificates:

1. **Obtain certificates** (Let's Encrypt recommended):
```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d your-domain.com
```

2. **Update nginx.conf**:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... rest of configuration
}
```

3. **Update docker-compose-onpremise.yml** to mount certificates:
```yaml
frontend:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Keycloak Setup

1. **Access Keycloak admin console**: http://localhost:8090
2. **Login**: admin / admin123
3. **Create realm**: "pdf-accessibility"
4. **Create client**: "pdf-ui"
5. **Configure client**:
   - Client Protocol: openid-connect
   - Access Type: public
   - Valid Redirect URIs: http://localhost:3000/*
   - Web Origins: http://localhost:3000

### Database Backup

**Manual backup**:
```bash
docker exec pdf-postgres pg_dump -U pdfuser pdf_accessibility > backup.sql
```

**Automated backup** (add to crontab):
```bash
0 2 * * * docker exec pdf-postgres pg_dump -U pdfuser pdf_accessibility | gzip > /backups/pdf_db_$(date +\%Y\%m\%d).sql.gz
```

### Scaling Services

**Scale processing services**:
```bash
docker-compose -f docker-compose-onpremise.yml up -d --scale pdf-autotag=4 --scale pdf-alttext=4
```

**Update docker-compose-onpremise.yml for permanent scaling**:
```yaml
pdf-autotag:
  deploy:
    replicas: 4
```

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker-compose -f docker-compose-onpremise.yml logs service-name
```

**Common issues**:
- Port conflicts: Check if ports are already in use (`netstat -tuln | grep PORT`)
- Memory limits: Increase Docker memory allocation
- Volume permissions: Ensure Docker has write access to volume directories

### API Gateway Connection Errors

**Test MinIO connectivity**:
```bash
docker exec pdf-api-gateway curl http://minio:9000/minio/health/live
```

**Test PostgreSQL connectivity**:
```bash
docker exec pdf-api-gateway pg_isready -h postgres -U pdfuser
```

**Test Redis connectivity**:
```bash
docker exec pdf-api-gateway redis-cli -h redis ping
```

### Frontend Build Fails

**Ensure UI repository is cloned**:
```bash
ls onpremise/frontend/src  # Should show React source files
```

**Clear Docker cache and rebuild**:
```bash
docker-compose -f docker-compose-onpremise.yml build --no-cache frontend
```

## Maintenance

### Update Configuration

1. **Modify configuration files** in this directory
2. **Rebuild affected services**:
```bash
docker-compose -f docker-compose-onpremise.yml up -d --build service-name
```

### Clean Up Old Jobs

**Connect to PostgreSQL**:
```bash
docker exec -it pdf-postgres psql -U pdfuser -d pdf_accessibility
```

**Run cleanup function**:
```sql
SELECT cleanup_old_jobs(90);  -- Remove jobs older than 90 days
```

### Monitor Resource Usage

**View container stats**:
```bash
docker stats
```

**Check disk usage**:
```bash
docker system df
```

**Clean up unused resources**:
```bash
docker system prune -a --volumes
```

## Security Recommendations

1. **Change default passwords** in docker-compose-onpremise.yml:
   - MinIO: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
   - PostgreSQL: POSTGRES_PASSWORD
   - Keycloak: KEYCLOAK_ADMIN_PASSWORD
   - Grafana: GF_SECURITY_ADMIN_PASSWORD
   - JWT_SECRET_KEY

2. **Enable firewall**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

3. **Use secrets management** instead of environment variables in production

4. **Enable Keycloak MFA** for user accounts

5. **Regular security updates**:
```bash
docker-compose -f docker-compose-onpremise.yml pull
docker-compose -f docker-compose-onpremise.yml up -d
```

## Cost Estimation

**Hardware Requirements** (for 100 PDFs/day):
- CPU: 8-16 cores
- RAM: 32-64 GB
- Storage: 500 GB - 1 TB SSD
- Network: 100 Mbps

**Operating Costs**:
- AWS Bedrock (hybrid mode): ~$200-400/month
- Self-hosted everything: $0/month (hardware costs only)

## Additional Resources

- [Main Documentation](../ONPREMISE_DEPLOYMENT.md)
- [Docker Compose Configuration](../docker-compose-onpremise.yml)
- [PostgreSQL Schema](../init-db.sql)
- [AWS Resources](../AWS_RESOURCES.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/a-fedosenko/PDF_Accessibility/issues
- Email: ai-cic@amazon.com
