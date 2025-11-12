# On-Premises Deployment Guide
# PDF Accessibility Solutions - Docker-Based Installation

**Version**: 1.0
**Last Updated**: November 12, 2025
**Target Audience**: System Administrators, DevOps Engineers

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment Options](#deployment-options)
5. [Installation Steps](#installation-steps)
6. [Configuration](#configuration)
7. [Alternative: Fully Self-Hosted (No AWS)](#alternative-fully-self-hosted)
8. [Monitoring & Maintenance](#monitoring--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Cost Comparison](#cost-comparison)

---

## Overview

This guide provides instructions for deploying PDF Accessibility Solutions on your own infrastructure using Docker and Docker Compose, with **minimal AWS dependency**.

### What's Included

✅ **Self-Hosted Components**:
- MinIO (S3-compatible storage)
- PostgreSQL (database)
- Redis (job queue)
- Temporal (workflow orchestration)
- Keycloak (authentication)
- All PDF processing services
- Frontend web application
- Monitoring stack (Prometheus, Grafana, Loki)

⚠️ **AWS Services Still Required** (Hybrid Approach):
- AWS Bedrock (AI models for alt-text and title generation)
- Adobe PDF Services API (external, not AWS-specific)

💡 **Why Keep AWS Bedrock?**
- State-of-the-art AI models (Claude, Nova)
- No GPU infrastructure required
- Pay-per-use pricing (~$0.01-0.10 per PDF)
- Easier to maintain than self-hosted LLMs

---

## Architecture

### Hybrid Architecture (Recommended)

```
┌─────────────────────────────────────────────────────────┐
│                  Your Company Servers                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Frontend   │  │ API Gateway  │  │  Keycloak    │ │
│  │  (React/Nginx│  │  (FastAPI)   │  │   (Auth)     │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │          │
│  ┌──────▼──────────────────▼──────────────────▼───────┐│
│  │            PDF Processing Services                  ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ││
│  │  │Splitter │ │Auto-tag │ │ Merger  │ │ Checker │ ││
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ ││
│  └─────────────────────────────────────────────────────┘│
│         │                  │                  │          │
│  ┌──────▼───────┐  ┌───────▼──────┐  ┌───────▼──────┐ │
│  │    MinIO     │  │  PostgreSQL  │  │    Redis     │ │
│  │  (Storage)   │  │  (Database)  │  │   (Queue)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐│
│  │         Monitoring Stack (Grafana/Prometheus)      ││
│  └────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS/API calls
                          ▼
            ┌──────────────────────────────┐
            │       AWS Cloud (Minimal)    │
            │  ┌─────────────────────────┐ │
            │  │   Amazon Bedrock        │ │
            │  │   (AI Models)           │ │
            │  │   - Claude 3.5 Sonnet   │ │
            │  │   - Nova Pro/Lite       │ │
            │  └─────────────────────────┘ │
            └──────────────────────────────┘
```

---

## Prerequisites

### Hardware Requirements

**Minimum (for testing)**:
- CPU: 8 cores
- RAM: 16 GB
- Storage: 100 GB SSD
- Network: 100 Mbps

**Recommended (for production)**:
- CPU: 16+ cores
- RAM: 32+ GB
- Storage: 500 GB SSD (1TB for large volumes)
- Network: 1 Gbps
- Backup storage: Separate volume/NAS

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Linux OS | Ubuntu 20.04+ / RHEL 8+ | Server OS |
| Git | 2.0+ | Code repository |
| OpenSSL | 1.1+ | SSL certificates |

### Network Requirements

- **Outbound**: Access to AWS Bedrock API (if using hybrid approach)
- **Inbound**: Ports 80, 443, 3000, 8080 (configurable)
- **Internal**: Docker network (no special requirements)

### AWS Requirements (Hybrid Approach)

- AWS Account (for Bedrock API access only)
- IAM user with Bedrock permissions
- Bedrock models enabled in your region (Claude, Nova)

**Cost**: ~$0.01-0.10 per PDF processed (Bedrock API calls only)

---

## Deployment Options

### Option 1: Hybrid Deployment (Recommended) ⭐

**Pros**:
- Best AI model quality (Claude, Nova)
- No GPU required
- Lower operational complexity
- Cost-effective for most use cases

**Cons**:
- Requires AWS account
- Data sent to AWS for AI processing (can be anonymized)

**Best For**: Most organizations, production deployments

### Option 2: Fully Self-Hosted

**Pros**:
- Complete data sovereignty
- No external dependencies
- No per-use costs

**Cons**:
- Requires GPU servers (for LLM inference)
- Complex setup and maintenance
- Higher infrastructure costs
- Model quality may be lower

**Best For**: High-security environments, air-gapped networks

---

## Installation Steps

### Step 1: Clone Repository

```bash
cd /opt
git clone https://github.com/a-fedosenko/PDF_Accessibility.git
cd PDF_Accessibility
```

### Step 2: Create Environment File

```bash
cp .env.example .env.onpremise
```

Edit `.env.onpremise`:

```bash
# Adobe PDF Services API (required)
PDF_SERVICES_CLIENT_ID=your-adobe-client-id
PDF_SERVICES_CLIENT_SECRET=your-adobe-client-secret

# AWS Credentials (for Bedrock only - Hybrid approach)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-2

# Bedrock Model ARNs
BEDROCK_MODEL_ARN_IMAGE=arn:aws:bedrock:us-east-2:YOUR_ACCOUNT:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MODEL_ARN_LINK=arn:aws:bedrock:us-east-2:YOUR_ACCOUNT:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0

# Security
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Optional: Custom domain
DOMAIN=pdf.yourcompany.com
```

### Step 3: Initialize Database

Create `init-db.sql`:

```sql
-- Database initialization
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    pdf_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user ON jobs(user_id);
```

### Step 4: Build and Start Services

```bash
# Build all Docker images
docker-compose -f docker-compose-onpremise.yml build

# Start services
docker-compose -f docker-compose-onpremise.yml up -d

# Check status
docker-compose -f docker-compose-onpremise.yml ps

# View logs
docker-compose -f docker-compose-onpremise.yml logs -f
```

### Step 5: Initialize MinIO Buckets

MinIO buckets are automatically created by the `minio-init` container. Verify:

```bash
# Access MinIO console
open http://localhost:9001

# Login: minioadmin / minioadmin123

# Verify buckets exist:
# - pdfaccessibility
# - pdf
# - temp
# - result
```

### Step 6: Configure Keycloak (Authentication)

```bash
# Access Keycloak admin console
open http://localhost:8090

# Login: admin / admin123

# Create realm: pdf-accessibility
# Create client: pdf-ui
#   - Client Protocol: openid-connect
#   - Access Type: public
#   - Valid Redirect URIs: http://localhost:3000/*
#   - Web Origins: http://localhost:3000

# Create test user
```

### Step 7: Access Frontend

```bash
open http://localhost:3000
```

**Services Available**:
- **Frontend**: http://localhost:3000
- **API Gateway**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **Keycloak**: http://localhost:8090
- **Grafana**: http://localhost:3001
- **Prometheus**: http://localhost:9090

---

## Configuration

### Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `PDF_SERVICES_CLIENT_ID` | Yes | Adobe API client ID | - |
| `PDF_SERVICES_CLIENT_SECRET` | Yes | Adobe API secret | - |
| `AWS_ACCESS_KEY_ID` | Yes* | AWS access key (Bedrock) | - |
| `AWS_SECRET_ACCESS_KEY` | Yes* | AWS secret key (Bedrock) | - |
| `AWS_REGION` | Yes* | AWS region | us-east-2 |
| `BEDROCK_MODEL_ARN_IMAGE` | Yes* | Bedrock model for images | - |
| `BEDROCK_MODEL_ARN_LINK` | Yes* | Bedrock model for links | - |
| `JWT_SECRET_KEY` | Yes | JWT signing key | - |
| `DOMAIN` | No | Custom domain | localhost |
| `MINIO_ROOT_USER` | No | MinIO admin user | minioadmin |
| `MINIO_ROOT_PASSWORD` | No | MinIO admin password | minioadmin123 |

*Required only for Hybrid approach (recommended)

### Scaling Configuration

Edit `docker-compose-onpremise.yml` to scale services:

```yaml
services:
  pdf-autotag:
    deploy:
      replicas: 4  # Increase for higher throughput
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

Or use Docker Compose scale command:

```bash
docker-compose -f docker-compose-onpremise.yml up -d --scale pdf-autotag=4
```

### SSL/TLS Configuration

For production, use a reverse proxy (Nginx/Traefik) with Let's Encrypt:

```bash
# Install Nginx
sudo apt install nginx certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d pdf.yourcompany.com

# Configure Nginx reverse proxy
sudo nano /etc/nginx/sites-available/pdf-accessibility
```

Example Nginx config:

```nginx
server {
    listen 443 ssl http2;
    server_name pdf.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/pdf.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pdf.yourcompany.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /minio {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Alternative: Fully Self-Hosted (No AWS)

For organizations that cannot use any AWS services, you can replace Bedrock with self-hosted LLMs.

### Additional Requirements

**Hardware** (for LLM hosting):
- GPU: NVIDIA A100 (40GB) or equivalent
- RAM: 64GB+
- Storage: 500GB+ (for model weights)

### Step 1: Deploy Ollama or vLLM

```yaml
# Add to docker-compose-onpremise.yml
  llm-server:
    image: ollama/ollama:latest
    container_name: pdf-llm
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    networks:
      - pdf-network
    restart: unless-stopped
```

### Step 2: Download Models

```bash
# Pull Llama 3 70B or similar
docker exec pdf-llm ollama pull llama3:70b

# Pull vision model for image analysis
docker exec pdf-llm ollama pull llava:34b
```

### Step 3: Modify PDF Services

Update `pdf-alttext` and `pdf-title-generator` services to use local LLM:

```python
# Replace Bedrock calls with Ollama API
import requests

def generate_alt_text(image_data):
    response = requests.post(
        'http://llm-server:11434/api/generate',
        json={
            'model': 'llava:34b',
            'prompt': 'Describe this image for accessibility:',
            'images': [image_data]
        }
    )
    return response.json()['response']
```

### Pros & Cons of Fully Self-Hosted

**Pros**:
- ✅ Complete data sovereignty
- ✅ No external API calls
- ✅ No per-use costs
- ✅ Works in air-gapped environments

**Cons**:
- ❌ Requires expensive GPU hardware ($10K-30K)
- ❌ Complex model management
- ❌ Higher power consumption
- ❌ May have lower quality outputs
- ❌ Requires ML expertise for optimization

---

## Monitoring & Maintenance

### Accessing Monitoring Dashboards

**Grafana** (http://localhost:3001):
- Username: `admin`
- Password: `admin123`
- Pre-configured dashboards for all services

**Prometheus** (http://localhost:9090):
- Metrics collection and querying
- Alerts configuration

### Health Checks

```bash
# Check all services
docker-compose -f docker-compose-onpremise.yml ps

# Check specific service health
docker exec pdf-api-gateway curl -f http://localhost:8080/health

# Check MinIO
docker exec pdf-minio curl -f http://localhost:9000/minio/health/live

# Check PostgreSQL
docker exec pdf-postgres pg_isready -U pdfuser
```

### Backup Strategy

```bash
# Backup MinIO data
docker exec pdf-minio mc mirror /data /backup/minio-$(date +%Y%m%d)

# Backup PostgreSQL
docker exec pdf-postgres pg_dump -U pdfuser pdf_accessibility > backup/db-$(date +%Y%m%d).sql

# Backup Redis (if persistence enabled)
docker exec pdf-redis redis-cli SAVE
docker cp pdf-redis:/data/dump.rdb backup/redis-$(date +%Y%m%d).rdb
```

### Log Rotation

Configure log rotation to prevent disk space issues:

```bash
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  }
}

# Restart Docker
sudo systemctl restart docker
```

### Updates

```bash
# Pull latest images
docker-compose -f docker-compose-onpremise.yml pull

# Rebuild custom images
docker-compose -f docker-compose-onpremise.yml build

# Restart with new images
docker-compose -f docker-compose-onpremise.yml up -d
```

---

## Troubleshooting

### Common Issues

**Issue**: Services can't connect to MinIO
```bash
# Solution: Check MinIO is running
docker-compose -f docker-compose-onpremise.yml logs minio

# Verify network
docker network inspect pdf_pdf-network
```

**Issue**: Out of memory errors
```bash
# Solution: Increase Docker resources
# Edit /etc/docker/daemon.json
{
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

**Issue**: PDF processing fails
```bash
# Check logs for specific service
docker-compose -f docker-compose-onpremise.yml logs pdf-autotag

# Check Adobe API credentials
docker exec pdf-autotag env | grep PDF_SERVICES
```

**Issue**: Slow performance
```bash
# Check resource usage
docker stats

# Scale up processing services
docker-compose -f docker-compose-onpremise.yml up -d --scale pdf-autotag=4 --scale pdf-alttext=4
```

### Debug Mode

Enable debug logging:

```bash
# Add to .env.onpremise
LOG_LEVEL=DEBUG

# Restart services
docker-compose -f docker-compose-onpremise.yml restart
```

---

## Cost Comparison

### AWS-Hosted (Current Deployment)

**Fixed Costs**:
- NAT Gateway: $32/month
- Amplify: $15/month
- **Total Fixed**: ~$47/month

**Variable Costs**:
- Per PDF: $0.10-0.30

**Annual Cost** (1000 PDFs/month):
- Fixed: $564/year
- Variable: $1,200-3,600/year
- **Total**: $1,764-4,164/year

### Hybrid On-Premises (Recommended)

**Infrastructure** (one-time/amortized):
- Server: $3,000-5,000 (amortized over 3 years = $1,000-1,667/year)
- Storage: $500/year
- Network: $100/year
- **Total Infrastructure**: $1,600-2,267/year

**Operational**:
- Electricity: $200-500/year
- Maintenance: $500/year
- **Total Operational**: $700-1,000/year

**AWS Costs** (Bedrock only):
- Per PDF: $0.01-0.05
- 1000 PDFs/month: $120-600/year

**Total Annual Cost**: $2,420-3,867/year

**Savings**: Can be neutral to 10% savings, but with:
- ✅ Better control
- ✅ Data sovereignty
- ✅ Customization options

### Fully Self-Hosted (No AWS)

**Infrastructure** (one-time/amortized):
- Server with GPU: $15,000-30,000 (amortized over 3 years = $5,000-10,000/year)
- Storage: $1,000/year
- Network: $100/year
- **Total Infrastructure**: $6,100-11,100/year

**Operational**:
- Electricity (GPU): $1,000-2,000/year
- Maintenance: $1,000/year
- ML Engineering: $5,000/year (part-time consultant)
- **Total Operational**: $7,000-8,000/year

**Total Annual Cost**: $13,100-19,100/year

**Verdict**: Only cost-effective at very high volumes (>10,000 PDFs/month) or when data sovereignty is mandatory.

---

## Production Checklist

Before deploying to production:

- [ ] Configure SSL/TLS certificates
- [ ] Set up automated backups
- [ ] Configure monitoring alerts
- [ ] Implement log rotation
- [ ] Set up firewall rules
- [ ] Configure resource limits
- [ ] Test disaster recovery procedures
- [ ] Document custom configurations
- [ ] Set up user access controls
- [ ] Configure rate limiting
- [ ] Test with production-like load
- [ ] Set up health check endpoints
- [ ] Configure auto-scaling (if using Kubernetes)
- [ ] Review security hardening
- [ ] Set up monitoring dashboards

---

## Support & Resources

**Documentation**:
- Main README: `/home/andreyf/projects/PDF_Accessibility/README.md`
- AWS Deployment: `/home/andreyf/projects/PDF_Accessibility/DEPLOYMENT_SUMMARY.md`
- AWS Resources: `/home/andreyf/projects/PDF_Accessibility/AWS_RESOURCES.md`

**Community**:
- GitHub Issues: https://github.com/a-fedosenko/PDF_Accessibility/issues
- Email: ai-cic@amazon.com

**External Dependencies**:
- Adobe PDF Services: https://developer.adobe.com/document-services/
- Docker Documentation: https://docs.docker.com/
- MinIO Documentation: https://min.io/docs/minio/
- Keycloak Documentation: https://www.keycloak.org/documentation

---

**Document Version**: 1.0
**Last Updated**: November 12, 2025
**Maintained By**: Arizona State University AI Cloud Innovation Center

---

## Quick Start Summary

```bash
# 1. Clone repository
git clone https://github.com/a-fedosenko/PDF_Accessibility.git
cd PDF_Accessibility

# 2. Create environment file
cp .env.example .env.onpremise
# Edit .env.onpremise with your credentials

# 3. Start services
docker-compose -f docker-compose-onpremise.yml up -d

# 4. Access UI
open http://localhost:3000

# 5. Upload PDF and process
# Files go to MinIO bucket: pdfaccessibility/pdf/
# Results appear in: pdfaccessibility/result/
```

That's it! Your on-premises PDF accessibility solution is ready! 🚀
