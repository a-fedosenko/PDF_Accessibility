# AWS Resources - PDF Accessibility Solutions

**Project**: PDF Accessibility Solutions
**Deployment Date**: November 12, 2025
**Region**: us-east-2
**Account ID**: 471414695760

This document provides a complete inventory of all AWS resources used in this project.

---

## Table of Contents

1. [Compute Resources](#compute-resources)
2. [Storage Resources](#storage-resources)
3. [Networking Resources](#networking-resources)
4. [Security & Identity](#security--identity)
5. [Monitoring & Logging](#monitoring--logging)
6. [Developer Tools](#developer-tools)
7. [AI/ML Services](#aiml-services)
8. [Frontend & API](#frontend--api)
9. [Cost Breakdown](#cost-breakdown)
10. [Resource Dependencies](#resource-dependencies)

---

## Compute Resources

### AWS Lambda Functions

| Function Name | Runtime | Memory | Timeout | Purpose |
|---------------|---------|--------|---------|---------|
| PDFAccessibility-SplitPDF* | Python 3.10 | 1024 MB | 900s | Split large PDFs into chunks for parallel processing |
| PDFAccessibility-JavaLambda* | Java 21 | 1024 MB | 900s | Merge processed PDF chunks back together |
| PDFAccessibility-AddTitleLambda* | Python 3.12 | 1024 MB | 900s | Generate descriptive titles using Bedrock Nova Pro |
| PDFAccessibility-CheckerBefore* | Python 3.10 | 512 MB | 900s | Pre-remediation accessibility audit |
| PDFAccessibility-CheckerAfter* | Python 3.10 | 512 MB | 900s | Post-remediation accessibility validation |
| CdkBackendStack-*-Lambda* | Various | Various | Various | Backend API functions (upload, quota, attributes) |

**Total Lambda Functions**: ~10-15 (exact count depends on CDK deployment)

### Amazon ECS (Fargate)

**Cluster**: FargateCluster

**Task Definitions**:
1. **MyFirstTaskDef** (Python Container)
   - CPU: 256
   - Memory: 1024 MB
   - Purpose: Adobe PDF Services autotagging and image extraction
   - Image: ECR `pdf-autotag`

2. **MySecondTaskDef** (JavaScript Container)
   - CPU: 256
   - Memory: 1024 MB
   - Purpose: LLM-powered alt-text generation for images
   - Image: ECR `pdf-alttext`

**Task Execution Role**: Includes permissions for ECS, S3, Bedrock, Secrets Manager

---

## Storage Resources

### Amazon S3 Buckets

| Bucket Name | Purpose | Encryption | Versioning |
|-------------|---------|------------|------------|
| `pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc` | PDF-to-PDF processing and storage | S3-Managed | Disabled |
| CDK Staging Buckets | CloudFormation template storage | S3-Managed | Enabled |
| Amplify Deployment Buckets | Frontend code and assets | S3-Managed | Enabled |

**S3 Folder Structure** (Main Bucket):
```
pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc/
├── pdf/           # Input folder (upload PDFs here)
├── temp/          # Temporary processing files
│   └── chunks/    # Split PDF chunks
├── result/        # Output folder (COMPLIANT_* prefix)
└── images/        # Extracted images for alt-text generation
```

**S3 Features Enabled**:
- CORS Configuration (for web UI uploads)
- Lifecycle Policies (optional, for cost optimization)
- Event Notifications (triggers Lambda on upload)
- SSL/TLS Enforcement

### Amazon ECR Repositories

| Repository Name | Purpose | Image Count |
|----------------|---------|-------------|
| `pdf-autotag` | Python autotagging container | 1+ |
| `pdf-alttext` | JavaScript alt-text generator | 1+ |
| `pdf2html-lambda` | PDF-to-HTML Lambda container | 1+ |
| `java-lambda` | Java PDF merger | 1+ |
| `split-pdf-lambda` | PDF splitter Lambda | 1+ |
| `add-title-lambda` | Title generator Lambda | 1+ |
| `checker-before` | Pre-check Lambda | 1+ |
| `checker-after` | Post-check Lambda | 1+ |

**Total Repositories**: 8
**Registry URL**: `471414695760.dkr.ecr.us-east-2.amazonaws.com`

---

## Networking Resources

### Amazon VPC

**VPC**: MyVpc (created by CDK)
- **CIDR Block**: 172.31.0.0/16 (or similar, depending on CDK defaults)
- **Availability Zones**: 2
- **Purpose**: Isolate ECS tasks and provide secure networking

### Subnets

| Type | CIDR Mask | Count | Purpose |
|------|-----------|-------|---------|
| Public Subnets | /24 | 2 | Internet-facing resources |
| Private Subnets (with Egress) | /24 | 2 | ECS tasks, Lambda functions |

### NAT Gateway

- **Count**: 1
- **Location**: Public subnet
- **Purpose**: Allow private subnet resources to access internet (Docker pulls, AWS API calls)
- **Cost**: ~$0.045/hour + data transfer (~$32/month minimum)
- **Associated Elastic IP**: 1

### Security Groups

Multiple security groups created by CDK for:
- ECS tasks
- Lambda functions
- VPC endpoints (if configured)

### Route Tables

- **Public Route Table**: Routes traffic to Internet Gateway
- **Private Route Table**: Routes traffic to NAT Gateway

---

## Security & Identity

### AWS IAM Roles

#### Service Roles

| Role Name | Service | Purpose |
|-----------|---------|---------|
| `pdfremediation-*-codebuild-service-role` | CodeBuild | PDF-to-PDF deployment permissions |
| `pdf-ui-*-service-role` | CodeBuild | UI deployment permissions |
| `PDFAccessibility-EcsTaskRole-*` | ECS Tasks | Runtime permissions for containers |
| `PDFAccessibility-EcsTaskExecutionRole-*` | ECS | Task execution, ECR pulls, CloudWatch logs |
| `PDFAccessibility-LambdaRole-*` | Lambda | Lambda execution permissions |
| `CdkBackendStack-CognitoDefaultAuthenticatedRole-*` | Cognito | Authenticated user permissions |
| `CdkBackendStack-CognitoDefaultUnauthenticatedRole-*` | Cognito | Unauthenticated user permissions |

#### Permissions Overview

**ECS Task Role Permissions**:
- `bedrock:*` - Full Bedrock access
- `s3:*` - Full S3 access to processing bucket
- `secretsmanager:GetSecretValue` - Read Adobe credentials
- `logs:CreateLogStream`, `logs:PutLogEvents` - CloudWatch logging

**Lambda Execution Role Permissions**:
- `s3:GetObject`, `s3:PutObject` - S3 read/write
- `states:StartExecution` - Trigger Step Functions
- `bedrock:InvokeModel` - AI model inference
- `cloudwatch:PutMetricData` - Custom metrics
- `secretsmanager:GetSecretValue` - Read secrets

**CodeBuild Service Role Permissions**:
- `iam:*` - IAM management
- `cloudformation:*` - Stack deployment
- `s3:*`, `ecr:*`, `lambda:*` - Resource management
- Full service access for deployment

### AWS Secrets Manager

| Secret Name | Type | Purpose |
|-------------|------|---------|
| `/myapp/client_credentials` | JSON | Adobe PDF Services API credentials |

**Secret Structure**:
```json
{
  "client_credentials": {
    "PDF_SERVICES_CLIENT_ID": "32cc479d5d89416f923ae7e38721d05d",
    "PDF_SERVICES_CLIENT_SECRET": "p8e-odUbDQx57apD30VC4N-L7NGax19lQQ95"
  }
}
```

### AWS Cognito

**User Pool**:
- **ID**: `us-east-2_HJtK36MHO`
- **Name**: Auto-generated by CDK
- **App Client ID**: `7s84oe77h699j77oc6m8cbvogt`
- **Domain**: `pdf-ui-auth1rc16k`
- **Purpose**: User authentication and management

**Identity Pool**:
- **ID**: `us-east-2:c0f78434-f184-465f-8adb-ff2675227da2`
- **Purpose**: Temporary AWS credentials for authenticated users
- **Authentication Providers**: Cognito User Pool

**User Pool Features**:
- Email-based authentication
- Email verification required
- Password complexity requirements
- Multi-factor authentication (optional)
- User attributes: email, name, custom fields

---

## Monitoring & Logging

### Amazon CloudWatch Log Groups

| Log Group Name | Retention | Purpose |
|----------------|-----------|---------|
| `/aws/lambda/PDFAccessibility-SplitPDF*` | 7 days | PDF splitting logs |
| `/aws/lambda/PDFAccessibility-JavaLambda*` | 7 days | PDF merging logs |
| `/aws/lambda/PDFAccessibility-AddTitleLambda*` | 7 days | Title generation logs |
| `/aws/lambda/PDFAccessibility-CheckerBefore*` | 7 days | Pre-check logs |
| `/aws/lambda/PDFAccessibility-CheckerAfter*` | 7 days | Post-check logs |
| `/ecs/MyFirstTaskDef/PythonContainerLogGroup` | 7 days | Adobe autotagging logs |
| `/ecs/MySecondTaskDef/JavaScriptContainerLogGroup` | 7 days | Alt-text generation logs |
| `/aws/states/MyStateMachine_PDFAccessibility` | 7 days | Step Functions execution logs |
| `/aws/codebuild/pdfremediation-*` | Indefinite | Build logs for backend |
| `/aws/codebuild/pdf-ui-*` | Indefinite | Build logs for UI |
| `/aws/lambda/CdkBackendStack-*` | Default | Backend API logs |

**Total Log Groups**: 15-20

### CloudWatch Dashboards

**Dashboard Name**: `PDF_Processing_Dashboard-*` (with timestamp)

**Widgets**:
1. File Status Tracking (aggregated logs)
2. Split PDF Lambda Logs
3. Step Functions Execution Logs
4. ECS Task 1 Logs (Adobe Autotagging)
5. ECS Task 2 Logs (LLM Alt-text)
6. Java Lambda Logs (PDF Merger)

**Refresh Rate**: Real-time
**Query Language**: CloudWatch Logs Insights

### CloudWatch Metrics

**Custom Metrics** (via Lambda):
- `PDFAccessibility/ProcessingTime` - Time to process PDFs
- `PDFAccessibility/ChunkCount` - Number of chunks created
- `PDFAccessibility/ErrorCount` - Processing errors
- `PDFAccessibility/SuccessRate` - Success percentage

**AWS Service Metrics** (automatic):
- Lambda invocations, duration, errors, throttles
- ECS CPU utilization, memory utilization
- S3 requests, data transfer
- Step Functions executions, failures

---

## Developer Tools

### AWS CodeBuild Projects

| Project Name | Buildspec | Purpose | Status |
|--------------|-----------|---------|--------|
| `pdfremediation-20251112150436` | `buildspec-unified.yml` | Deploy PDF-to-PDF backend | Complete |
| `pdf-ui-20251112155128-backend` | `buildspec.yml` | Deploy UI backend (CDK) | Complete |
| `pdf-ui-20251112155128-frontend` | `buildspec-frontend.yml` | Deploy UI frontend (Amplify) | Complete |

**Build Configuration**:
- **Environment**: Amazon Linux 2, Standard 5.0
- **Compute**: BUILD_GENERAL1_SMALL to MEDIUM
- **Runtime**: Python 3.11, Node.js 18
- **Privileged Mode**: True (for Docker builds)

**Environment Variables**:
- `DEPLOYMENT_TYPE` - Solution type (pdf2pdf, pdf2html)
- `ACCOUNT_ID`, `REGION` - AWS account details
- `BUCKET_NAME` - S3 bucket for processing
- `BDA_PROJECT_ARN` - Bedrock Data Automation project (if used)
- `AMPLIFY_APP_ID` - Amplify application ID
- React app configuration variables

### AWS Step Functions

**State Machine**: `MyStateMachine`

**State Machine ARN**: `arn:aws:states:us-east-2:471414695760:stateMachine:MyStateMachine`

**Execution Timeout**: 150 minutes

**State Machine Flow**:
```
START
  ↓
Parallel State
  ├─→ Accessibility Pre-Check Lambda
  └─→ Map State (per chunk)
        ├─→ ECS Task 1 (Adobe Autotagging)
        └─→ ECS Task 2 (LLM Alt-text)
  ↓
Java Merger Lambda
  ↓
Add Title Lambda (Bedrock)
  ↓
Accessibility Post-Check Lambda
  ↓
END
```

**Input Schema**:
```json
{
  "s3_bucket": "bucket-name",
  "s3_key": "pdf/file.pdf",
  "chunks": [
    {"s3_key": "temp/chunk_0.pdf", "chunk_key": "chunk_0"},
    {"s3_key": "temp/chunk_1.pdf", "chunk_key": "chunk_1"}
  ]
}
```

**Output Schema**:
```json
{
  "statusCode": 200,
  "result_key": "result/COMPLIANT_file.pdf",
  "accessibility_report": {...}
}
```

---

## AI/ML Services

### Amazon Bedrock

**Models Used**:

| Model ID | Purpose | Cost (approx) | Invocations |
|----------|---------|---------------|-------------|
| `us.amazon.nova-pro-v1:0` | PDF title generation | $0.80/$3.20 per 1M tokens | Per PDF |
| `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Image analysis (alt-text) | Higher rate | Per image |
| `us.anthropic.claude-3-haiku-20240307-v1:0` | Link text generation | Lower rate | Per link |
| `us.amazon.nova-lite-v1:0` | HTML remediation (if used) | $0.16/$0.64 per 1M tokens | Per HTML page |

**Model ARNs**:
- Nova Pro: `arn:aws:bedrock:us-east-2:471414695760:inference-profile/us.amazon.nova-pro-v1:0`
- Claude Sonnet: `arn:aws:bedrock:us-east-2:471414695760:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- Claude Haiku: `arn:aws:bedrock:us-east-2:471414695760:inference-profile/us.anthropic.claude-3-haiku-20240307-v1:0`

**Bedrock Usage**:
- **Request Volume**: Scales with PDF processing volume
- **Model Access**: Must be enabled in Bedrock Console
- **Regions**: Models must be available in deployment region

### Adobe PDF Services API (External)

**Service**: Adobe Document Cloud API
**Purpose**: PDF autotagging and accessibility features
**Authentication**: OAuth 2.0 (credentials in Secrets Manager)
**Endpoint**: https://pdf-services.adobe.io/

**API Operations Used**:
- Auto-tag PDF
- Extract PDF structure
- Add accessibility tags
- Image extraction

---

## Frontend & API

### AWS Amplify

**Application**:
- **App ID**: `d3althp551dv7h`
- **URL**: `https://main.d3althp551dv7h.amplifyapp.com`
- **Branch**: main
- **Framework**: React
- **Build Settings**: Automatic from `buildspec-frontend.yml`

**Features Enabled**:
- Continuous deployment from GitHub
- Custom domain support (optional)
- HTTPS/SSL (automatic)
- Environment variables injection
- Branch-based deployments

**Environment Variables** (injected at build):
- `REACT_APP_USER_POOL_ID`
- `REACT_APP_USER_POOL_CLIENT_ID`
- `REACT_APP_IDENTITY_POOL_ID`
- `REACT_APP_UPDATE_FIRST_SIGN_IN_ENDPOINT`
- `REACT_APP_CHECK_UPLOAD_QUOTA_ENDPOINT`
- `REACT_APP_UPDATE_ATTRIBUTES_API_ENDPOINT`

### Amazon API Gateway

**APIs Created by CDK**:

1. **Update Attributes API**
   - **Endpoint**: `https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod/`
   - **Stage**: prod
   - **Resources**:
     - `/update-first-sign-in` (POST) - Update user attributes on first sign-in
     - `/upload-quota` (GET) - Check user upload quota
     - `/` (Various) - General API operations

**API Features**:
- CORS enabled
- Lambda proxy integration
- Cognito authorizer
- Request/response validation
- API keys (optional)
- Usage plans and throttling

**Throttling Limits**:
- Burst: 5000 requests
- Rate: 10000 requests per second

---

## Cost Breakdown

### Fixed Monthly Costs

| Resource | Cost | Notes |
|----------|------|-------|
| NAT Gateway | ~$32.40 | $0.045/hour + data transfer |
| Amplify Hosting | ~$12-15 | Based on build minutes and bandwidth |
| CloudWatch Logs (retention) | ~$1-5 | Depends on log volume |
| **Total Fixed** | **~$45-52/month** | Minimum if unused |

### Variable Costs (per PDF processed)

| Resource | Cost Range | Notes |
|----------|-----------|-------|
| Lambda Invocations | $0.0001-0.001 | Depends on duration |
| ECS Fargate | ~$0.04 | Per task execution (~5-10 min) |
| Bedrock API (Nova Pro) | $0.01-0.10 | Depends on PDF size and tokens |
| Bedrock API (Claude) | $0.01-0.05 | Per image analyzed |
| Adobe PDF Services | Variable | External API cost |
| S3 Storage | $0.023/GB | Standard storage |
| S3 Requests | Minimal | GET/PUT operations |
| Data Transfer | Minimal | Within region is free |
| **Total per PDF** | **$0.10-0.30** | Approximate |

### Cost Optimization Tips

1. **Delete Temp Files**: Set S3 lifecycle policy to delete temp/ after 7 days
2. **Reduce Retention**: Lower CloudWatch log retention to 3-7 days
3. **Use Bedrock Efficiently**: Batch requests, optimize prompts
4. **Remove NAT Gateway**: If not needed, use VPC endpoints instead
5. **Monitor Usage**: Set up billing alerts and budgets

---

## Resource Dependencies

### Deployment Order

```
1. VPC & Networking (NAT, Subnets, Security Groups)
   ↓
2. ECR Repositories (for Docker images)
   ↓
3. S3 Buckets
   ↓
4. Secrets Manager (Adobe credentials)
   ↓
5. IAM Roles & Policies
   ↓
6. Lambda Functions (from ECR images)
   ↓
7. ECS Task Definitions (from ECR images)
   ↓
8. Step Functions State Machine
   ↓
9. S3 Event Notifications (trigger Lambda)
   ↓
10. CloudWatch Dashboards
   ↓
11. Cognito User Pool & Identity Pool
   ↓
12. API Gateway
   ↓
13. Amplify Application
```

### Critical Dependencies

**Step Functions depends on**:
- Lambda functions (all 5)
- ECS task definitions (2)
- IAM roles with proper permissions

**ECS Tasks depend on**:
- VPC with private subnets
- NAT Gateway for internet access
- ECR repositories with images
- S3 bucket for data
- Secrets Manager for Adobe credentials
- Bedrock model access

**Amplify depends on**:
- Cognito User Pool
- API Gateway endpoints
- GitHub repository access

**Lambda Functions depend on**:
- S3 bucket
- IAM execution roles
- CloudWatch Log Groups
- ECR images (if containerized)

### Cleanup Order (Reverse)

```
1. Amplify Application
   ↓
2. API Gateway
   ↓
3. CloudFormation Stacks (deletes most resources)
   ↓
4. S3 Buckets (must be empty first)
   ↓
5. ECR Repositories (can delete with images)
   ↓
6. CloudWatch Log Groups
   ↓
7. Secrets Manager Secrets
   ↓
8. IAM Roles & Policies
   ↓
9. VPC & Networking (last, may require manual)
```

---

## Resource Tags

**Recommended Tags** (apply to all resources):
```json
{
  "Project": "PDF-Accessibility-Solutions",
  "Environment": "Production",
  "Owner": "ai-cic@amazon.com",
  "CostCenter": "AI-CIC",
  "ManagedBy": "AWS-CDK",
  "DeploymentDate": "2025-11-12",
  "Region": "us-east-2"
}
```

---

## Resource Limits & Quotas

### Service Limits to Monitor

| Service | Limit | Current Usage | Notes |
|---------|-------|---------------|-------|
| Lambda Concurrent Executions | 1000 | ~10-50 | Request increase if needed |
| ECS Tasks per Service | 1000 | 2 task defs | Should be sufficient |
| S3 Buckets per Account | 100 | ~5 | Well within limits |
| VPC per Region | 5 | 1 | OK |
| NAT Gateways per AZ | 5 | 1 | OK |
| Elastic IPs | 5 | 1 | May need more in us-east-1 |
| API Gateway Requests | 10,000 RPS | Low | Increase if needed |
| Cognito Users | 50,000 (free tier) | <100 | Scales to millions |

**To Check Limits**:
```bash
aws service-quotas list-service-quotas --service-code lambda --region us-east-2
```

---

## Compliance & Security

### Security Best Practices Implemented

✅ **Encryption at Rest**:
- S3 buckets use SSE-S3
- Secrets Manager encrypts secrets
- EBS volumes encrypted (for ECS)

✅ **Encryption in Transit**:
- SSL/TLS for all API calls
- HTTPS-only for S3 buckets
- TLS 1.2+ for Amplify

✅ **Access Control**:
- IAM roles with least privilege
- Cognito for user authentication
- Security groups restrict network access
- S3 bucket policies prevent public access

✅ **Monitoring**:
- CloudWatch logs for all services
- CloudWatch alarms (can be configured)
- AWS CloudTrail (can be enabled)

✅ **Compliance**:
- WCAG 2.1 Level AA compliance (output)
- HIPAA eligible services (if configured)
- GDPR considerations for user data

---

## Disaster Recovery

### Backup Strategy

**What to Backup**:
- S3 bucket contents (source PDFs)
- Cognito user data (export via CLI)
- Secrets Manager secrets
- Infrastructure as Code (CDK/CloudFormation)

**Backup Methods**:
```bash
# Backup S3 bucket
aws s3 sync s3://pdfaccessibility-* ./backup/s3/

# Export Cognito users
aws cognito-idp list-users --user-pool-id us-east-2_HJtK36MHO > users-backup.json

# Export secrets
aws secretsmanager get-secret-value --secret-id /myapp/client_credentials > secrets-backup.json
```

### Recovery Strategy

**RTO (Recovery Time Objective)**: ~30 minutes
**RPO (Recovery Point Objective)**: Depends on S3 sync frequency

**Recovery Steps**:
1. Re-run `./deploy.sh` (creates all infrastructure)
2. Restore S3 data from backup
3. Restore Cognito users (if needed)
4. Update DNS/domain settings (if using custom domain)

---

## Additional Resources

### Documentation
- **Project README**: `/home/andreyf/projects/PDF_Accessibility/README.md`
- **Deployment Summary**: `/home/andreyf/projects/PDF_Accessibility/DEPLOYMENT_SUMMARY.md`
- **IAM Permissions**: `/home/andreyf/projects/PDF_Accessibility/docs/IAM_PERMISSIONS.md`
- **Cleanup Script**: `/home/andreyf/projects/PDF_Accessibility/cleanup.sh`

### External APIs
- **Adobe PDF Services**: https://developer.adobe.com/document-services/
- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/

### Support
- **Project Repository**: https://github.com/a-fedosenko/PDF_Accessibility
- **UI Repository**: https://github.com/a-fedosenko/PDF_accessability_UI
- **Contact**: ai-cic@amazon.com

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2025-11-12 | Initial deployment to us-east-2 | Deployment Script |
| 2025-11-12 | UI deployment completed | Deployment Script |

---

**Document Version**: 1.0
**Last Updated**: November 12, 2025
**Maintained By**: Arizona State University AI Cloud Innovation Center

---

## Quick Reference

### Key ARNs
```
User Pool: arn:aws:cognito-idp:us-east-2:471414695760:userpool/us-east-2_HJtK36MHO
Identity Pool: arn:aws:cognito-identity:us-east-2:471414695760:identitypool/us-east-2:c0f78434-f184-465f-8adb-ff2675227da2
State Machine: arn:aws:states:us-east-2:471414695760:stateMachine:MyStateMachine
S3 Bucket: arn:aws:s3:::pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc
```

### Key URLs
```
Frontend: https://main.d3althp551dv7h.amplifyapp.com
API Gateway: https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod/
Cognito Domain: https://pdf-ui-auth1rc16k.auth.us-east-2.amazoncognito.com
```

### AWS Console Links
```
Amplify: https://console.aws.amazon.com/amplify/home?region=us-east-2#/d3althp551dv7h
Cognito: https://console.aws.amazon.com/cognito/v2/idp/user-pools/us-east-2_HJtK36MHO
S3: https://s3.console.aws.amazon.com/s3/buckets/pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc
CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=us-east-2
Step Functions: https://console.aws.amazon.com/states/home?region=us-east-2
```

---

*This document provides a comprehensive inventory of all AWS resources. Keep it updated as the infrastructure evolves.*
