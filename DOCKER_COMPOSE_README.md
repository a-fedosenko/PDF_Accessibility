# Docker Compose Setup for PDF Accessibility Solutions

This guide explains how to run the PDF Accessibility Solutions using Docker Compose for both local development and production deployment.

## Deployment Modes

This project includes **two Docker Compose configurations**:

1. **`local.yml`** - Local development with LocalStack (AWS emulator)
2. **`docker-compose.yml`** - Production deployment with real AWS services

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Local Development](#local-development)
  - [Production Deployment](#production-deployment-with-docker-compose)
- [Architecture Overview](#architecture-overview)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [AWS Deployment](#aws-deployment)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **AWS CLI** (for testing with real AWS services)
- **Adobe PDF Services API Credentials** (for PDF-to-PDF solution)

### System Requirements

- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: At least 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

---

## Quick Start

### Local Development

Use `local.yml` for local development with LocalStack (no AWS account required).

#### 1. Clone the Repository

```bash
git clone https://github.com/a-fedosenko/PDF_Accessibility.git
cd PDF_Accessibility
```

#### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Important**: You must set the following values in `.env`:
- `PDF_SERVICES_CLIENT_ID` - Your Adobe PDF Services Client ID
- `PDF_SERVICES_CLIENT_SECRET` - Your Adobe PDF Services Client Secret

For local development, the AWS credentials can remain as `test`.

#### 3. Start All Services (Local Mode)

```bash
# Start all services in detached mode using local.yml
docker-compose -f local.yml up -d

# Check service status
docker-compose -f local.yml ps

# View logs
docker-compose -f local.yml logs -f
```

#### 4. Verify LocalStack is Running

```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# List S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls
```

### Production Deployment with Docker Compose

Use `docker-compose.yml` for production deployment with real AWS services.

#### 1. Prerequisites

- AWS account with appropriate IAM permissions
- AWS credentials configured (IAM roles recommended for EC2/ECS)
- ECR repositories created for all container images
- S3 buckets, Secrets Manager secrets, and other AWS resources set up

#### 2. Configure Production Environment

```bash
# Copy and edit .env for production
cp .env.example .env
nano .env
```

**Required Production Variables**:
```env
# ECR Configuration
ECR_REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
ECR_REPOSITORY_AUTOTAG=pdf-autotag
ECR_REPOSITORY_ALTTEXT=pdf-alttext
ECR_REPOSITORY_PDF2HTML=pdf2html-lambda
ECR_REPOSITORY_JAVA_LAMBDA=java-lambda
ECR_REPOSITORY_SPLIT_PDF=split-pdf-lambda
ECR_REPOSITORY_ADD_TITLE=add-title-lambda
ECR_REPOSITORY_CHECKER_BEFORE=checker-before
ECR_REPOSITORY_CHECKER_AFTER=checker-after
IMAGE_TAG=latest

# AWS Configuration (use IAM roles, not hardcoded credentials)
AWS_REGION=us-east-1
S3_BUCKET_NAME=pdfaccessibility-prod-12345
BDA_S3_BUCKET=pdf2html-bucket-prod-12345

# Real AWS ARNs
STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine
BDA_PROJECT_ARN=arn:aws:bedrock:us-east-1:123456789012:data-automation-project/abc123
BEDROCK_MODEL_ARN_IMAGE=arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MODEL_ARN_LINK=arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0
SECRET_NAME=/myapp/client_credentials
```

#### 3. Build and Push Images to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build all images
docker-compose build

# Push all images to ECR
docker-compose push
```

#### 4. Start Production Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs (CloudWatch integration enabled)
docker-compose logs -f
```

---

## Architecture Overview

The Docker Compose setup includes the following services:

### Core Services

| Service | Description | Port | Container Name |
|---------|-------------|------|----------------|
| **localstack** | AWS service emulator | 4566 | pdf-accessibility-localstack |
| **pdf-autotag** | Python autotagging (ECS Task 1) | - | pdf-accessibility-autotag |
| **pdf-alttext** | JavaScript alt-text generation (ECS Task 2) | - | pdf-accessibility-alttext |
| **pdf2html-lambda** | PDF-to-HTML conversion | 9000 | pdf-accessibility-pdf2html |
| **java-lambda** | PDF merger (Java) | - | pdf-accessibility-java-merger |
| **split-pdf-lambda** | PDF splitter | - | pdf-accessibility-split-pdf |
| **add-title-lambda** | Title generator | - | pdf-accessibility-add-title |
| **accessibility-checker-before** | Pre-remediation checker | - | pdf-accessibility-checker-before |
| **accessibility-checker-after** | Post-remediation checker | - | pdf-accessibility-checker-after |

### Initialization Services

| Service | Description | Runs Once |
|---------|-------------|-----------|
| **s3-init** | Creates S3 buckets and folders | Yes |
| **secrets-init** | Creates Adobe API secret | Yes |

### Network and Volumes

- **Network**: `pdf-accessibility-network` (bridge mode)
- **Volumes**:
  - `pdf-accessibility-temp` - Temporary processing storage
  - `pdf-accessibility-output` - Output storage

---

## Configuration

### Environment Variables

The `.env` file contains all configuration. Key sections:

#### AWS Configuration

```env
AWS_ACCESS_KEY_ID=test              # Use 'test' for LocalStack
AWS_SECRET_ACCESS_KEY=test          # Use 'test' for LocalStack
AWS_REGION=us-east-1                # Your preferred region
AWS_ACCOUNT_ID=123456789012         # Your AWS account (for production)
```

#### Adobe PDF Services

```env
PDF_SERVICES_CLIENT_ID=your-client-id
PDF_SERVICES_CLIENT_SECRET=your-secret
```

Get credentials from: https://developer.adobe.com/document-services/apis/pdf-services/

#### S3 Buckets

```env
S3_BUCKET_NAME=pdfaccessibility-local
BDA_S3_BUCKET=pdf2html-bucket-local
```

#### Bedrock Models

```env
BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
BEDROCK_TITLE_MODEL_ID=us.amazon.nova-pro-v1:0
BEDROCK_MODEL_ARN_IMAGE=arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MODEL_ARN_LINK=arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0
```

#### LocalStack Endpoint

```env
LOCALSTACK_ENDPOINT=http://localstack:4566
```

---

## Usage

### Starting Services

#### Local Development (with LocalStack)

```bash
# Start all services (local mode)
docker-compose -f local.yml up -d

# Start specific services only
docker-compose -f local.yml up -d localstack pdf-autotag pdf-alttext

# View logs for all services
docker-compose -f local.yml logs -f

# View logs for specific service
docker-compose -f local.yml logs -f pdf-autotag
```

#### Production Deployment

```bash
# Start all services (production mode)
docker-compose up -d

# Start with monitoring profile
docker-compose --profile monitoring up -d

# Start with frontend profile
docker-compose --profile frontend up -d

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f pdf-autotag
```

### Stopping Services

#### Local Development

```bash
# Stop all services
docker-compose -f local.yml down

# Stop and remove volumes (clears all data)
docker-compose -f local.yml down -v

# Stop specific service
docker-compose -f local.yml stop pdf-autotag
```

#### Production

```bash
# Stop all services (preserves data)
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Stop specific service
docker-compose stop pdf-autotag
```

### Rebuilding Services

#### Local Development

```bash
# Rebuild all containers
docker-compose -f local.yml build

# Rebuild specific service
docker-compose -f local.yml build pdf-autotag

# Rebuild and restart
docker-compose -f local.yml up -d --build
```

#### Production

```bash
# Rebuild all containers
docker-compose build

# Rebuild and push to ECR
docker-compose build
docker-compose push

# Rebuild specific service
docker-compose build pdf-autotag

# Rebuild and restart
docker-compose up -d --build
```

---

## Testing

### 1. Upload a Test PDF (PDF-to-PDF Solution)

```bash
# Upload to LocalStack S3
aws --endpoint-url=http://localhost:4566 s3 cp test.pdf s3://pdfaccessibility-local/pdf/test.pdf

# Verify upload
aws --endpoint-url=http://localhost:4566 s3 ls s3://pdfaccessibility-local/pdf/
```

### 2. Process PDF with Containers

```bash
# Execute processing in pdf-autotag container
docker exec -it pdf-accessibility-autotag python /app/autotag.py

# Execute processing in pdf-alttext container
docker exec -it pdf-accessibility-alttext node /app/index.js

# Merge PDFs with Java Lambda
docker exec -it pdf-accessibility-java-merger java -jar /app/target/PDFMergerLambda-1.0-SNAPSHOT.jar
```

### 3. Download Results

```bash
# List processed files
aws --endpoint-url=http://localhost:4566 s3 ls s3://pdfaccessibility-local/result/

# Download result
aws --endpoint-url=http://localhost:4566 s3 cp s3://pdfaccessibility-local/result/COMPLIANT_test.pdf ./output/
```

### 4. Test PDF-to-HTML Solution

```bash
# Upload test PDF
aws --endpoint-url=http://localhost:4566 s3 cp test.pdf s3://pdf2html-bucket-local/uploads/test.pdf

# Trigger Lambda (using Lambda Runtime Interface Emulator)
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"bucket":"pdf2html-bucket-local","key":"uploads/test.pdf"}'

# Download results
aws --endpoint-url=http://localhost:4566 s3 cp s3://pdf2html-bucket-local/remediated/ ./output/ --recursive
```

### 5. Monitor Logs

```bash
# Real-time logs from all services
docker-compose logs -f

# Filter logs for errors
docker-compose logs | grep -i error

# View logs for specific container
docker-compose logs -f pdf-autotag

# Follow last 100 lines
docker-compose logs --tail=100 -f
```

---

## Troubleshooting

### LocalStack Not Starting

**Issue**: LocalStack container fails to start or is unhealthy

**Solutions**:
```bash
# Check container status
docker-compose ps

# View LocalStack logs
docker-compose logs localstack

# Restart LocalStack
docker-compose restart localstack

# Check if port 4566 is already in use
netstat -an | grep 4566
```

### S3 Buckets Not Created

**Issue**: S3 buckets don't exist in LocalStack

**Solutions**:
```bash
# Check s3-init logs
docker-compose logs s3-init

# Manually create buckets
aws --endpoint-url=http://localhost:4566 s3 mb s3://pdfaccessibility-local
aws --endpoint-url=http://localhost:4566 s3 mb s3://pdf2html-bucket-local

# Re-run initialization
docker-compose up s3-init
```

### Container Memory Issues

**Issue**: Container crashes with OOM (Out of Memory)

**Solutions**:
```bash
# Check Docker memory limits
docker stats

# Increase Docker Desktop memory allocation (Settings > Resources)
# Recommended: 8GB minimum, 16GB for production workloads

# Reduce memory-intensive services
docker-compose up -d localstack pdf-autotag  # Start only needed services
```

### Adobe API Authentication Fails

**Issue**: Adobe PDF Services API returns authentication errors

**Solutions**:
```bash
# Verify credentials in .env file
cat .env | grep PDF_SERVICES

# Check secret in LocalStack
aws --endpoint-url=http://localhost:4566 secretsmanager get-secret-value \
  --secret-id /myapp/client_credentials

# Update secret manually
aws --endpoint-url=http://localhost:4566 secretsmanager update-secret \
  --secret-id /myapp/client_credentials \
  --secret-string '{"client_credentials":{"PDF_SERVICES_CLIENT_ID":"your-id","PDF_SERVICES_CLIENT_SECRET":"your-secret"}}'
```

### Permission Denied Errors

**Issue**: Docker containers can't access mounted volumes

**Solutions**:
```bash
# Fix volume permissions
sudo chmod -R 755 ./docker_autotag
sudo chmod -R 755 ./javascript_docker
sudo chmod -R 755 ./lambda

# On Linux, add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port Conflicts

**Issue**: Port 4566 or 9000 already in use

**Solutions**:
```bash
# Find process using port
lsof -i :4566
lsof -i :9000

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
# Edit the ports section for the conflicting service
```

### Container Exits Immediately

**Issue**: Lambda containers exit right after starting

**Solution**: This is expected behavior. The containers are configured with `command: tail -f /dev/null` to keep them running. If they exit:

```bash
# Check logs for errors
docker-compose logs <service-name>

# Restart the service
docker-compose restart <service-name>
```

---

## AWS Deployment

You have **three options** for deploying to AWS:

### Option 1: Docker Compose with AWS Services (docker-compose.yml)

Best for: Running containers on EC2 instances or ECS with Docker Compose integration.

**Advantages**:
- Simple deployment model
- Easy to update and redeploy
- CloudWatch logging built-in
- Good for small to medium workloads

**Requirements**:
- EC2 instance or ECS cluster
- ECR repositories for all images
- IAM roles with appropriate permissions
- Pre-created AWS resources (S3, Secrets Manager, etc.)

See [Production Deployment with Docker Compose](#production-deployment-with-docker-compose) section above.

### Option 2: AWS CDK Deployment (Recommended for Production)

Best for: Full production deployment with auto-scaling, Step Functions orchestration, and complete AWS integration.

**Advantages**:
- Infrastructure as Code
- Auto-scaling and fault tolerance
- Step Functions workflow orchestration
- VPC networking and security
- CloudWatch dashboards and monitoring
- Cost-optimized architecture

**Deploy PDF-to-PDF Solution**:
```bash
# Interactive deployment (recommended)
./deploy.sh

# Or manually with CDK
cdk deploy
```

**Deploy PDF-to-HTML Solution**:
```bash
cd pdf2html/cdk
npm install
cdk deploy
```

### Option 3: Hybrid Approach

Use AWS CDK for infrastructure (S3, Step Functions, VPC) and Docker Compose for container orchestration.

### Production Best Practices

Regardless of deployment method:

#### Security
- **Use IAM roles** instead of hardcoded credentials
- **Never use LocalStack** in production
- **Use AWS Secrets Manager** for credential storage
- **Enable VPC security groups** and NACLs
- **Use AWS KMS** for encryption at rest
- **Enable S3 bucket encryption** and versioning

#### Monitoring
- **Enable CloudWatch monitoring** and alarms
- **Set up CloudWatch dashboards** for visibility
- **Configure CloudWatch Logs** retention policies
- **Set up SNS alerts** for failures
- **Use AWS X-Ray** for distributed tracing

#### Cost Optimization
- **Implement VPC endpoints** instead of NAT Gateway (saves ~$32/month)
- **Use S3 lifecycle policies** for archival
- **Enable ECS Fargate Spot** for non-critical tasks
- **Use Bedrock Nova Lite** instead of Nova Pro where possible
- **Set appropriate Lambda timeouts** to avoid unnecessary charges

#### Reliability
- **Implement proper error handling** and retry logic
- **Enable S3 versioning** and lifecycle policies
- **Use Step Functions** for workflow orchestration
- **Configure auto-scaling** for ECS tasks
- **Set up health checks** and monitoring

### Migration from Docker Compose to AWS

#### Step 1: Build and Push Images to ECR

```bash
# Create ECR repositories
aws ecr create-repository --repository-name pdf-autotag
aws ecr create-repository --repository-name pdf-alttext
aws ecr create-repository --repository-name pdf2html-lambda
aws ecr create-repository --repository-name java-lambda
aws ecr create-repository --repository-name split-pdf-lambda
aws ecr create-repository --repository-name add-title-lambda
aws ecr create-repository --repository-name checker-before
aws ecr create-repository --repository-name checker-after

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Build and push all images
docker-compose build
docker-compose push
```

#### Step 2: Create AWS Resources

```bash
# Run the interactive deployment script
./deploy.sh

# This will create:
# - S3 buckets
# - Secrets Manager secrets (Adobe credentials)
# - Bedrock Data Automation projects
# - IAM roles and policies
# - Step Functions state machine
# - Lambda functions
# - ECS cluster and task definitions
```

#### Step 3: Update Environment Variables

Edit `.env` file with production values:
```env
ECR_REGISTRY=123456789012.dkr.ecr.us-east-1.amazonaws.com
S3_BUCKET_NAME=pdfaccessibility-prod-xyz
BDA_S3_BUCKET=pdf2html-bucket-prod-xyz
STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:MyStateMachine
# ... etc
```

#### Step 4: Deploy with CDK or Docker Compose

```bash
# Option A: CDK deployment
cdk deploy

# Option B: Docker Compose on EC2/ECS
docker-compose up -d
```

---

## Additional Resources

### Docker Compose Commands Reference

#### Local Development Commands

```bash
# View all running containers
docker-compose -f local.yml ps

# View resource usage
docker stats

# Execute command in running container
docker-compose -f local.yml exec <service> <command>

# View container environment variables
docker-compose -f local.yml exec <service> env

# Restart specific service
docker-compose -f local.yml restart <service>

# Remove stopped containers
docker-compose -f local.yml rm

# Validate local.yml
docker-compose -f local.yml config
```

#### Production Commands

```bash
# View all running containers
docker-compose ps

# Execute command in running container
docker-compose exec <service> <command>

# View container environment variables
docker-compose exec <service> env

# Restart specific service
docker-compose restart <service>

# Scale services (if supported)
docker-compose up -d --scale pdf-autotag=3

# Pull latest images from ECR
docker-compose pull

# Push images to ECR
docker-compose push

# Validate docker-compose.yml
docker-compose config
```

### LocalStack Commands

```bash
# List all S3 buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List Lambda functions
aws --endpoint-url=http://localhost:4566 lambda list-functions

# List secrets
aws --endpoint-url=http://localhost:4566 secretsmanager list-secrets

# Check Step Functions
aws --endpoint-url=http://localhost:4566 stepfunctions list-state-machines
```

### Useful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# LocalStack AWS CLI
alias awslocal="aws --endpoint-url=http://localhost:4566"

# Docker Compose shortcuts - Local Development
alias dcl-up="docker-compose -f local.yml up -d"
alias dcl-down="docker-compose -f local.yml down"
alias dcl-logs="docker-compose -f local.yml logs -f"
alias dcl-ps="docker-compose -f local.yml ps"
alias dcl-restart="docker-compose -f local.yml restart"

# Docker Compose shortcuts - Production
alias dcp-up="docker-compose up -d"
alias dcp-down="docker-compose down"
alias dcp-logs="docker-compose logs -f"
alias dcp-ps="docker-compose ps"
alias dcp-restart="docker-compose restart"
alias dcp-push="docker-compose push"
alias dcp-pull="docker-compose pull"
```

### File Structure Summary

```
project-root/
├── local.yml                    # Local development with LocalStack
├── docker-compose.yml           # Production deployment with AWS
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Environment template
├── DOCKER_COMPOSE_README.md     # This documentation
└── ... (other project files)
```

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: https://github.com/a-fedosenko/PDF_Accessibility/issues
- **Email**: ai-cic@amazon.com
- **Documentation**: See `CLAUDE.md` for comprehensive project documentation

---

## License

Apache 2.0 - See LICENSE file for details

**Maintained By**: Arizona State University AI Cloud Innovation Center

**Last Updated**: 2025-11-09
