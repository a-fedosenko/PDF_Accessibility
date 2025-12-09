# PDF Pre-Processing Analysis Implementation Guide

This document describes the implementation of the pre-processing analysis feature that estimates Adobe API costs before processing PDFs.

## Overview

### Problem
- Users upload PDFs that immediately start processing
- No visibility into processing costs before committing
- Adobe charges per structural element (~10x page count)
- Example: 57-page PDF = 570 transactions

### Solution
**Two-Step Workflow:**
1. **Analyze First**: Upload → Analyze → Show Statistics → User Approves
2. **Process Second**: Start remediation only after approval

## Architecture

```
┌─────────────┐
│  User       │
│  Uploads    │
│  PDF        │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  S3 Bucket: pdf-upload/            │  (New bucket or prefix)
└──────┬──────────────────────────────┘
       │ S3 Event
       ▼
┌─────────────────────────────────────┐
│  PDF Analyzer Lambda                │
│  - Count pages                      │
│  - Estimate elements                │
│  - Calculate transactions           │
│  - Save to DynamoDB                 │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  DynamoDB: pending-jobs             │
│  {                                  │
│    job_id, file_key, pages,         │
│    estimated_transactions,          │
│    complexity, status               │
│  }                                  │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend UI                        │
│  Shows:                             │
│  - Pages: 57                        │
│  - Est. Transactions: 570           │
│  - Complexity: Complex              │
│  - Cost: 2.28% of quota             │
│  [Start Processing] button          │
└──────┬──────────────────────────────┘
       │ User clicks "Start"
       ▼
┌─────────────────────────────────────┐
│  Start Remediation Lambda           │
│  - Update status to processing      │
│  - Copy file to pdf/ prefix         │
│  - Trigger existing workflow        │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Existing Step Functions Workflow   │
│  (split_pdf → ECS → merge → ...)    │
└─────────────────────────────────────┘
```

## Components Created

### 1. PDF Analyzer Lambda (`lambda/pdf_analyzer/`)

**Purpose**: Analyze PDF files without processing them

**Features**:
- Uses PyPDF2 to read PDF metadata
- Counts pages
- Estimates structural elements per page
- Calculates estimated Adobe transactions
- Saves analysis to DynamoDB
- Returns analysis results to frontend

**Input** (S3 Event):
```json
{
  "Records": [{
    "s3": {
      "bucket": {"name": "bucket-name"},
      "object": {"key": "pdf-upload/test.pdf"}
    }
  }]
}
```

**Output** (DynamoDB + Response):
```json
{
  "job_id": "test.pdf_1733752800",
  "file_name": "test.pdf",
  "file_size_mb": 0.57,
  "num_pages": 57,
  "estimated_elements": 570,
  "avg_elements_per_page": 10.0,
  "estimated_adobe_transactions": 570,
  "estimated_cost_percentage": 2.28,
  "complexity": "complex",
  "status": "pending_approval"
}
```

**Element Estimation Logic**:
```python
# Per page:
- Headings (short, capitalized lines)
- Text blocks (paragraphs)
- Tables (lines with multiple spaces)
- Table cells (estimated)
- Images (from XObject resources)

# Minimum 5 elements/page, samples first 10 pages
```

### 2. Start Remediation Lambda (`lambda/start_remediation/`)

**Purpose**: Manually trigger processing for approved PDFs

**Features**:
- Receives job_id from frontend
- Updates DynamoDB status to "processing"
- Copies file from upload prefix to processing prefix
- Returns success confirmation

**Input** (API Gateway):
```json
{
  "job_id": "test.pdf_1733752800",
  "user_approved": true
}
```

**Output**:
```json
{
  "success": true,
  "job_id": "test.pdf_1733752800",
  "message": "Remediation started",
  "estimated_transactions": 570
}
```

### 3. DynamoDB Table: `pdf-accessibility-pending-jobs`

**Schema**:
```
Partition Key: job_id (String)
Sort Key: None

Attributes:
- job_id: "test.pdf_1733752800"
- user_email: "user@example.com"
- file_key: "pdf-upload/test.pdf"
- file_name: "test.pdf"
- file_size_mb: 0.57
- num_pages: 57
- estimated_transactions: 570
- complexity: "complex" | "moderate" | "simple" | "very_complex"
- status: "pending_approval" | "processing" | "completed" | "failed"
- created_at: "2025-12-09T12:00:00Z"
- approved_at: "2025-12-09T12:05:00Z" (optional)
- ttl: 1734357600 (auto-delete after 7 days)
```

**TTL (Time To Live)**:
- Items auto-delete after 7 days
- Prevents database growth
- Keeps only recent analysis results

## CDK Infrastructure Changes

### Add to `app.py`:

```python
# 1. Create DynamoDB Table for Pending Jobs
pending_jobs_table = dynamodb.Table(
    self, "PendingJobsTable",
    table_name="pdf-accessibility-pending-jobs",
    partition_key=dynamodb.Attribute(
        name="job_id",
        type=dynamodb.AttributeType.STRING
    ),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=cdk.RemovalPolicy.RETAIN,
    time_to_live_attribute="ttl"
)

# 2. Create PDF Analyzer Lambda
pdf_analyzer_lambda = lambda_.Function(
    self, 'PDFAnalyzer',
    runtime=lambda_.Runtime.PYTHON_3_10,
    handler='main.lambda_handler',
    code=lambda_.Code.from_docker_build("lambda/pdf_analyzer"),
    timeout=Duration.seconds(300),
    memory_size=1024,
    environment={
        'PENDING_JOBS_TABLE': pending_jobs_table.table_name
    },
    architecture=lambda_arch
)

# Grant permissions
bucket.grant_read(pdf_analyzer_lambda)
pending_jobs_table.grant_read_write_data(pdf_analyzer_lambda)

# Add S3 trigger for pdf-upload/ prefix
bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(pdf_analyzer_lambda),
    s3.NotificationKeyFilter(prefix="pdf-upload/"),
    s3.NotificationKeyFilter(suffix=".pdf")
)

# 3. Create Start Remediation Lambda
start_remediation_lambda = lambda_.Function(
    self, 'StartRemediation',
    runtime=lambda_.Runtime.PYTHON_3_10,
    handler='main.lambda_handler',
    code=lambda_.Code.from_docker_build("lambda/start_remediation"),
    timeout=Duration.seconds(60),
    memory_size=512,
    environment={
        'PENDING_JOBS_TABLE': pending_jobs_table.table_name,
        'STATE_MACHINE_ARN': state_machine.state_machine_arn
    },
    architecture=lambda_arch
)

# Grant permissions
pending_jobs_table.grant_read_write_data(start_remediation_lambda)
bucket.grant_read_write(start_remediation_lambda)
state_machine.grant_start_execution(start_remediation_lambda)

# 4. Remove auto-trigger from pdf/ prefix
# IMPORTANT: Comment out or remove the existing S3 trigger:
# bucket.add_event_notification(
#     s3.EventType.OBJECT_CREATED,
#     s3n.LambdaDestination(split_pdf_lambda),
#     s3.NotificationKeyFilter(prefix="pdf/"),  # OLD - remove this
#     s3.NotificationKeyFilter(suffix=".pdf")
# )

# 5. Create API Gateway for Start Remediation
api = apigateway.RestApi(
    self, "PDFAccessibilityAPI",
    rest_api_name="PDF Accessibility API",
    description="API for PDF accessibility processing",
    default_cors_preflight_options=apigateway.CorsOptions(
        allow_origins=apigateway.Cors.ALL_ORIGINS,
        allow_methods=apigateway.Cors.ALL_METHODS
    )
)

start_integration = apigateway.LambdaIntegration(start_remediation_lambda)
api.root.add_resource("start-remediation").add_method("POST", start_integration)

# Export API URL
cdk.CfnOutput(self, "APIURL",
    value=api.url,
    description="PDF Accessibility API URL"
)
```

## Frontend Integration

### Current Workflow (Immediate Processing):
```
Upload → S3 (pdf/) → Auto-trigger split_pdf Lambda → Processing
```

### New Workflow (Analysis First):
```
Upload → S3 (pdf-upload/) → Analyzer Lambda → Show Stats → Wait for approval
                                                             ↓
                                             [Start] → API Gateway → Start Lambda → Copy to pdf/ → Processing
```

### Frontend Changes Needed:

#### 1. Upload to Different Prefix
```javascript
// OLD
const s3Key = `pdf/${fileName}`;

// NEW
const s3Key = `pdf-upload/${fileName}`;
```

#### 2. After Upload, Poll for Analysis
```javascript
async function uploadAndAnalyze(file) {
  // Show spinner
  setStatus('analyzing', 'Wait until we analyze the file...');

  // Upload to pdf-upload/ prefix
  await uploadToS3(file, `pdf-upload/${file.name}`);

  // Poll DynamoDB or wait for Lambda response
  const analysis = await pollForAnalysis(file.name);

  // Show analysis results
  showAnalysisResults(analysis);
}
```

#### 3. Display Analysis Results
```javascript
function showAnalysisResults(analysis) {
  return (
    <div className="analysis-results">
      <h3>PDF Analysis Complete</h3>

      <div className="stats">
        <div className="stat">
          <label>File Size:</label>
          <value>{analysis.file_size_mb} MB</value>
        </div>

        <div className="stat">
          <label>Pages:</label>
          <value>{analysis.num_pages}</value>
        </div>

        <div className="stat">
          <label>Complexity:</label>
          <value className={`complexity-${analysis.complexity}`}>
            {analysis.complexity}
          </value>
        </div>

        <div className="stat important">
          <label>Estimated Adobe Transactions:</label>
          <value>{analysis.estimated_adobe_transactions}</value>
        </div>

        <div className="stat important">
          <label>Estimated Cost:</label>
          <value>
            {analysis.estimated_cost_percentage}% of monthly quota
          </value>
        </div>
      </div>

      <div className="breakdown">
        <p>
          Your PDF has approximately {analysis.avg_elements_per_page} structural
          elements per page (headings, tables, images, etc.).
          Adobe charges per element, not per page.
        </p>
      </div>

      <div className="actions">
        <button onClick={() => startRemediation(analysis.job_id)}>
          Start Remediation Process
        </button>
        <button onClick={() => cancel()}>
          Cancel
        </button>
      </div>
    </div>
  );
}
```

#### 4. Start Remediation on Approval
```javascript
async function startRemediation(jobId) {
  setStatus('processing', 'Starting remediation...');

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
    // Monitor processing status
    monitorProcessing(jobId);
  }
}
```

### Complexity Indicators (CSS):
```css
.complexity-simple {
  color: #28a745;  /* Green */
}

.complexity-moderate {
  color: #ffc107;  /* Yellow */
}

.complexity-complex {
  color: #fd7e14;  /* Orange */
}

.complexity-very_complex {
  color: #dc3545;  /* Red */
}
```

## Deployment Steps

### 1. Deploy Backend Changes

```bash
# Add new environment variables if needed
export PENDING_JOBS_TABLE=pdf-accessibility-pending-jobs

# Deploy CDK stack
cdk deploy
```

### 2. Update Frontend

```bash
# Update environment variables with new API URL
REACT_APP_API_URL=https://{api-id}.execute-api.us-east-2.amazonaws.com/prod

# Rebuild and deploy frontend
npm run build
```

### 3. Test Workflow

```bash
# 1. Upload test PDF to pdf-upload/ prefix
aws s3 cp test.pdf s3://{bucket}/pdf-upload/test.pdf

# 2. Check analyzer Lambda logs
aws logs tail /aws/lambda/{analyzer-function-name} --follow

# 3. Query DynamoDB for analysis
aws dynamodb get-item \
  --table-name pdf-accessibility-pending-jobs \
  --key '{"job_id": {"S": "test.pdf_1733752800"}}'

# 4. Manually trigger remediation
curl -X POST {api-url}/start-remediation \
  -H "Content-Type: application/json" \
  -d '{"job_id": "test.pdf_1733752800", "user_approved": true}'

# 5. Verify processing started
aws logs tail /aws/lambda/{split-pdf-function-name} --follow
```

## Benefits

1. **Cost Transparency**: Users see estimated costs before processing
2. **Informed Decisions**: Can choose not to process expensive documents
3. **Quota Management**: Prevents accidental quota exhaustion
4. **User Control**: Two-step workflow gives users full control
5. **Better Planning**: Can batch process based on quota availability

## Cost Analysis Examples

| Pages | Complexity | Elements/Page | Est. Transactions | % of 25K Quota |
|-------|------------|---------------|-------------------|----------------|
| 10    | Simple     | 3             | 30                | 0.12%          |
| 50    | Moderate   | 6             | 300               | 1.20%          |
| 57    | Complex    | 10            | 570               | 2.28%          |
| 100   | Very Complex| 20           | 2000              | 8.00%          |
| 500   | Complex    | 10            | 5000              | 20.00%         |

## Troubleshooting

### Analysis Not Appearing

**Check**:
1. PDF uploaded to `pdf-upload/` prefix (not `pdf/`)
2. Analyzer Lambda triggered (check CloudWatch Logs)
3. DynamoDB table exists and has read/write permissions
4. Lambda has S3 read permissions

**Debug**:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/{analyzer-name} \
  --filter-pattern "Error"
```

### Remediation Not Starting

**Check**:
1. Job exists in DynamoDB with `pending_approval` status
2. Start Remediation Lambda has permissions
3. API Gateway endpoint is correct
4. User sent `user_approved: true`

**Debug**:
```bash
aws logs tail /aws/lambda/{start-remediation-name} --follow
```

### Inaccurate Estimates

**Reality**: Estimates will vary based on document structure

**Adjustments**:
- Simple PDFs: Multiply pages × 3-5
- Average PDFs: Multiply pages × 6-10
- Complex PDFs: Multiply pages × 10-20

**Improve Accuracy**:
- Sample more pages (increase from 10 to 20)
- Add document type detection
- Learn from actual Adobe usage data

## Future Enhancements

1. **Machine Learning**: Learn actual transaction counts from Adobe API
2. **Document Type Detection**: Different estimates for reports vs. forms
3. **Batch Processing**: Queue multiple documents
4. **Cost Prediction History**: Track accuracy over time
5. **Auto-Approval Threshold**: Auto-process documents under X transactions
6. **Budget Limits**: Set monthly budget, reject when exceeded

## Related Documentation

- [QUOTA_MONITORING.md](./QUOTA_MONITORING.md) - Quota tracking system
- [ADOBE_MONITORING.md](./ADOBE_MONITORING.md) - Usage monitoring guide
- [README.md](./README.md) - Main project documentation

## Support

For implementation questions:
1. Check Lambda logs for errors
2. Verify DynamoDB table structure
3. Test API endpoints with curl/Postman
4. Review frontend console for API errors
