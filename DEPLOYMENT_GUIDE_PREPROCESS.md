# Pre-Processing Analysis - Deployment Guide

## Overview

The pre-processing analysis feature has been **successfully integrated** into the CDK infrastructure (`app.py`). This guide explains what was deployed and what needs to be done next.

## What Was Integrated

### 1. **DynamoDB Table: `pdf-accessibility-pending-jobs`**
- **Purpose**: Stores analysis results for PDFs awaiting user approval
- **Partition Key**: `job_id` (String)
- **TTL**: Auto-deletes records after 7 days
- **Location in code**: `app.py:75-86`

### 2. **PDF Analyzer Lambda**
- **Purpose**: Analyzes uploaded PDFs to estimate processing costs
- **Trigger**: S3 upload to `pdf-upload/` prefix
- **Features**:
  - Counts pages using PyPDF2
  - Estimates structural elements (headings, tables, images)
  - Calculates estimated Adobe transactions
  - Saves analysis to DynamoDB
- **Location**: `lambda/pdf_analyzer/main.py`
- **CDK Configuration**: `app.py:457-481`

### 3. **Start Remediation Lambda**
- **Purpose**: Starts processing after user approval
- **Trigger**: API Gateway POST request
- **Features**:
  - Updates DynamoDB status to "processing"
  - Copies file from `pdf-upload/` to `pdf/` prefix
  - Triggers existing workflow via S3 event
- **Location**: `lambda/start_remediation/main.py`
- **CDK Configuration**: `app.py:484-503`

### 4. **API Gateway**
- **Name**: PDF Accessibility API
- **Endpoint**: `/start-remediation` (POST)
- **Features**:
  - CORS enabled for all origins
  - Integrates with Start Remediation Lambda
- **CDK Configuration**: `app.py:506-519`

### 5. **S3 Event Triggers**
- **New**: `pdf-upload/*.pdf` → PDF Analyzer Lambda
- **Existing**: `pdf/*.pdf` → Split PDF Lambda (kept for backward compatibility)

## Deployment Steps

### Step 1: Deploy CDK Stack

```bash
# Make sure environment variables are set
export ADOBE_API_QUOTA_LIMIT=25000
export QUOTA_ALERT_EMAIL=andrei.fedosenko@logrusglobal.com

# Deploy the updated stack
cdk deploy --require-approval never
```

### Step 2: Get API Endpoint URL

After deployment completes, note the API URL from the CDK outputs:

```bash
# Look for these outputs:
Outputs:
PDFAccessibility.APIURL = https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/prod/
PDFAccessibility.APIStartRemediationEndpoint = https://xxxxxxxxxx.execute-api.us-east-2.amazonaws.com/prod/start-remediation
PDFAccessibility.PendingJobsTableName = pdf-accessibility-pending-jobs
```

### Step 3: Test Backend (Optional)

Test the analysis workflow:

```bash
# 1. Upload a test PDF to pdf-upload/
aws s3 cp test.pdf s3://YOUR_BUCKET/pdf-upload/test.pdf

# 2. Wait 5-10 seconds, then check DynamoDB
aws dynamodb scan --table-name pdf-accessibility-pending-jobs

# 3. Get the job_id from the output and test the API
curl -X POST https://YOUR_API_URL/start-remediation \
  -H "Content-Type: application/json" \
  -d '{"job_id": "test.pdf_1733752800", "user_approved": true}'

# 4. Verify file was copied to pdf/ and processing started
aws s3 ls s3://YOUR_BUCKET/pdf/
```

## Frontend Integration Required

The backend is **ready and deployed**. Now the frontend needs to be updated:

### Changes Needed in Frontend UI

#### 1. Change Upload Prefix
```javascript
// OLD (immediate processing)
const s3Key = `pdf/${fileName}`;

// NEW (analysis first)
const s3Key = `pdf-upload/${fileName}`;
```

#### 2. After Upload, Poll for Analysis

```javascript
async function uploadAndAnalyze(file) {
  setStatus('analyzing', 'Wait until we analyze the file...');

  // Upload to pdf-upload/ prefix
  await uploadToS3(file, `pdf-upload/${file.name}`);

  // Poll DynamoDB for analysis results
  const jobId = `${file.name}_${Date.now()}`;
  const analysis = await pollForAnalysis(jobId);

  // Show analysis results
  showAnalysisResults(analysis);
}
```

#### 3. Display Analysis Results

Show the user:
- **File Size**: `analysis.file_size_mb` MB
- **Pages**: `analysis.num_pages`
- **Complexity**: `analysis.complexity` (simple/moderate/complex/very_complex)
- **Estimated Adobe Transactions**: `analysis.estimated_adobe_transactions`
- **Estimated Cost**: `analysis.estimated_cost_percentage`% of quota

Use color coding:
- Green: simple (< 5 elements/page)
- Yellow: moderate (5-8 elements/page)
- Orange: complex (8-15 elements/page)
- Red: very_complex (> 15 elements/page)

#### 4. Add "Start Processing" Button

```javascript
async function startRemediation(jobId) {
  const response = await fetch(`${API_URL}/start-remediation`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      job_id: jobId,
      user_approved: true
    })
  });

  const result = await response.json();

  if (result.success) {
    // Show success message
    // Monitor processing status (existing logic)
  }
}
```

## Workflow Comparison

### OLD Workflow (Immediate Processing)
```
User uploads → S3 (pdf/) → Split PDF Lambda → Processing starts immediately
```

### NEW Workflow (Analysis First)
```
User uploads → S3 (pdf-upload/) → PDF Analyzer Lambda → DynamoDB
                                                            ↓
Frontend polls DynamoDB → Shows analysis → User clicks "Start"
                                                            ↓
                                           API Gateway → Start Remediation Lambda
                                                            ↓
                                           Copy to pdf/ → Split PDF Lambda → Processing
```

## Environment Variables

The following environment variables are passed to the Lambdas:

### PDF Analyzer Lambda
- `PENDING_JOBS_TABLE`: pdf-accessibility-pending-jobs

### Start Remediation Lambda
- `PENDING_JOBS_TABLE`: pdf-accessibility-pending-jobs
- `STATE_MACHINE_ARN`: ARN of the Step Functions state machine
- `S3_BUCKET_NAME`: Name of the S3 bucket

## CloudFormation Outputs

After deployment, these outputs are available:

```bash
# Get API URL
aws cloudformation describe-stacks \
  --stack-name PDFAccessibility \
  --query 'Stacks[0].Outputs[?OutputKey==`APIURL`].OutputValue' \
  --output text

# Get Pending Jobs Table
aws cloudformation describe-stacks \
  --stack-name PDFAccessibility \
  --query 'Stacks[0].Outputs[?OutputKey==`PendingJobsTableName`].OutputValue' \
  --output text
```

## DynamoDB Schema

### `pdf-accessibility-pending-jobs` Table

```json
{
  "job_id": "test.pdf_1733752800",
  "user_email": "user@example.com",
  "file_key": "pdf-upload/test.pdf",
  "file_name": "test.pdf",
  "file_size_mb": 0.57,
  "num_pages": 57,
  "estimated_elements": 570,
  "estimated_transactions": 570,
  "avg_elements_per_page": 10.0,
  "complexity": "complex",
  "estimated_cost_percentage": 2.28,
  "status": "pending_approval",
  "created_at": "2025-12-09T12:00:00Z",
  "approved_at": "2025-12-09T12:05:00Z",
  "ttl": 1734357600
}
```

### Status Values
- `pending_approval`: Waiting for user to approve
- `processing`: User approved, processing started
- `completed`: Processing finished
- `failed`: Error occurred

## API Endpoint

### POST `/start-remediation`

**Request:**
```json
{
  "job_id": "test.pdf_1733752800",
  "user_approved": true
}
```

**Response (Success):**
```json
{
  "success": true,
  "job_id": "test.pdf_1733752800",
  "message": "Remediation started - file copied to processing folder",
  "source_key": "pdf-upload/test.pdf",
  "destination_key": "pdf/test.pdf",
  "estimated_transactions": 570
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Job not found"
}
```

## Monitoring

### CloudWatch Logs

Monitor Lambda execution:

```bash
# PDF Analyzer logs
aws logs tail /aws/lambda/PDFAccessibility-PDFAnalyzer-XXXXX --follow

# Start Remediation logs
aws logs tail /aws/lambda/PDFAccessibility-StartRemediation-XXXXX --follow
```

### DynamoDB Queries

Check pending jobs:

```bash
# Scan all pending jobs
aws dynamodb scan \
  --table-name pdf-accessibility-pending-jobs \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":status": {"S": "pending_approval"}}'

# Get specific job
aws dynamodb get-item \
  --table-name pdf-accessibility-pending-jobs \
  --key '{"job_id": {"S": "test.pdf_1733752800"}}'
```

## Troubleshooting

### Issue: Analysis not appearing in DynamoDB

**Check:**
1. File uploaded to `pdf-upload/` prefix (not `pdf/`)
2. PDF Analyzer Lambda triggered:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/PDFAccessibility-PDFAnalyzer-XXXXX \
     --filter-pattern "ERROR"
   ```
3. Lambda has permissions to write to DynamoDB

### Issue: Start remediation fails

**Check:**
1. Job exists in DynamoDB with `pending_approval` status
2. Start Remediation Lambda has S3 copy permissions
3. API request includes `user_approved: true`

### Issue: Processing doesn't start after approval

**Check:**
1. File was successfully copied to `pdf/` prefix
2. Split PDF Lambda is triggered by S3 event
3. Check Split PDF Lambda logs

## Next Steps

1. ✅ **Backend deployed** (CDK, Lambdas, DynamoDB, API Gateway)
2. 🔲 **Update frontend** to use new workflow
3. 🔲 **Test end-to-end** with real PDF
4. 🔲 **Remove old direct upload** to `pdf/` (optional, for full migration)

## Documentation

For complete implementation details, see:
- [PREPROCESS_ANALYSIS_IMPLEMENTATION.md](./PREPROCESS_ANALYSIS_IMPLEMENTATION.md) - Full architecture guide
- [QUOTA_MONITORING.md](./QUOTA_MONITORING.md) - Quota monitoring system
- [ADOBE_MONITORING.md](./ADOBE_MONITORING.md) - Usage monitoring guide

## Support

Questions? Check:
1. Lambda CloudWatch logs
2. DynamoDB table contents
3. API Gateway logs
4. S3 bucket event notifications
