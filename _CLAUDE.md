# CLAUDE.md - PDF Accessibility Solutions

## Project Overview

**PDF Accessibility Solutions** is a comprehensive AWS-based platform for PDF document accessibility remediation developed by Arizona State University's AI Cloud Innovation Center. The project provides two complementary approaches to making PDF documents comply with **WCAG 2.1 Level AA accessibility standards**:

1. **PDF-to-PDF Remediation**: Maintains PDF format while improving accessibility using Adobe PDF Services API
2. **PDF-to-HTML Remediation**: Converts PDFs to accessible HTML using AWS Bedrock Data Automation

**Repository**: https://github.com/a-fedosenko/PDF_Accessibility
**License**: Apache 2.0
**Primary Contact**: ai-cic@amazon.com

---

## Architecture & Technology Stack

### Core AWS Services
- **Amazon S3**: Document storage and processing
- **AWS Lambda**: Serverless compute (Python 3.10-3.12)
- **Amazon ECS Fargate**: Containerized processing tasks
- **AWS Step Functions**: Workflow orchestration
- **Amazon Bedrock**: AI/ML models for title generation, alt-text, and remediation
- **AWS Secrets Manager**: Secure credential storage
- **Amazon CloudWatch**: Monitoring and observability
- **AWS CDK**: Infrastructure as Code (Python + Node.js)

### Key Technologies
- **Languages**: Python (3.10-3.12), Java 17, JavaScript/Node.js
- **IaC**: AWS CDK (Python for PDF-to-PDF, Node.js for PDF-to-HTML)
- **Container Platforms**: Docker, Amazon ECR
- **Build Tools**: AWS CodeBuild, Maven (Java), npm
- **PDF Processing**: PyMuPDF (fitz), Adobe PDF Services API, Apache PDFBox
- **AI Models**:
  - AWS Bedrock Nova Pro (title generation)
  - AWS Bedrock Nova Lite (remediation)
  - Claude 3.5 Sonnet (image analysis)
  - Claude 3 Haiku (link generation)

---

## Project Structure

```
/home/andreyf/projects/PDF_Accessibility/
├── app.py                          # Main CDK entry point for PDF-to-PDF solution
├── deploy.sh                       # Interactive deployment script (PRIMARY INTERFACE)
├── buildspec-unified.yml           # AWS CodeBuild specification
├── requirements.txt                # Root Python dependencies (CDK)
├── cdk.json                        # CDK configuration
│
├── cdk/                            # CDK stack definitions
│   └── cdk_stack.py                # Python CDK stack class
│
├── lambda/                         # Lambda functions (PDF-to-PDF)
│   ├── split_pdf/                  # PDF splitter (Python)
│   ├── add_title/                  # Title generator with Bedrock Nova (Python 3.12)
│   ├── accessibility_checker_before_remidiation/  # Pre-check (Python 3.10)
│   ├── accessability_checker_after_remidiation/   # Post-check (Python 3.10)
│   └── java_lambda/PDFMergerLambda/  # PDF merger (Java 17 + Maven)
│
├── docker_autotag/                 # ECS Task 1: Python autotagging container
├── javascript_docker/              # ECS Task 2: JavaScript alt-text generation
│
├── pdf2html/                       # PDF-to-HTML solution
│   ├── README.md                   # Detailed PDF-to-HTML documentation
│   ├── lambda_function.py          # Lambda handler
│   ├── Dockerfile                  # Lambda container image
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Python package config
│   │
│   ├── content_accessibility_utility_on_aws/  # Core library
│   │   ├── api.py                  # Python API
│   │   ├── cli.py                  # Command-line interface
│   │   ├── pdf2html/               # PDF conversion module
│   │   ├── audit/                  # WCAG compliance checking
│   │   ├── remediate/              # AI-powered remediation
│   │   ├── batch/                  # Batch processing
│   │   └── utils/                  # Utility functions
│   │
│   └── cdk/                        # Node.js CDK stack for pdf2html
│       ├── bin/app.js              # CDK app entry
│       ├── lib/                    # CDK constructs
│       └── package.json            # Node.js dependencies
│
└── docs/                           # Documentation
    ├── IAM_PERMISSIONS.md          # Required AWS permissions
    ├── MANUAL_DEPLOYMENT.md        # Manual deployment guide
    ├── TROUBLESHOOTING_CDK_DEPLOY.md
    └── images/                     # Architecture diagrams
```

---

## Key Entry Points & Commands

### Primary Deployment Interface
**File**: `/home/andreyf/projects/PDF_Accessibility/deploy.sh`

Interactive one-click deployment script that:
1. Prompts for solution selection (PDF-to-PDF or PDF-to-HTML)
2. Handles solution-specific configuration
3. Creates IAM roles and policies
4. Deploys via AWS CodeBuild
5. Optionally deploys frontend UI

**Usage**:
```bash
cd /home/andreyf/projects/PDF_Accessibility
chmod +x deploy.sh
./deploy.sh
```

### AWS CDK Entry Points

**PDF-to-PDF Solution**:
```bash
# Main CDK app
python app.py

# Deploy directly with CDK
cdk deploy
```

**PDF-to-HTML Solution**:
```bash
cd pdf2html/cdk
npm install
cdk deploy
```

### Development Commands

**Install dependencies**:
```bash
# Root project (CDK)
pip install -r requirements.txt

# PDF-to-HTML
pip install -r pdf2html/requirements.txt

# Java Lambda
cd lambda/java_lambda/PDFMergerLambda
mvn clean package
```

**Run tests** (if available):
```bash
pytest tests/
```

**Build Docker images locally**:
```bash
# Python autotagging container
docker build -t pdf-autotag ./docker_autotag

# JavaScript alt-text container
docker build -t pdf-alttext ./javascript_docker

# PDF-to-HTML Lambda
docker build -t pdf2html-lambda ./pdf2html
```

---

## Solution Deep Dives

### PDF-to-PDF Remediation Solution

**Architecture Flow**:
```
S3 Upload (pdf/)
  → Split PDF Lambda
    → Step Functions State Machine
      → Parallel State:
        ├─ Pre-check Lambda (accessibility audit)
        └─ Map State (per chunk):
            ├─ ECS Task 1 (Python - autotagging + image extraction)
            └─ ECS Task 2 (JavaScript - LLM alt-text generation)
      → Java Merger Lambda
      → Add Title Lambda (Bedrock Nova)
      → Post-check Lambda
  → Result in S3 (result/)
```

**Key Components**:
- **Split PDF Lambda** (`lambda/split_pdf/main.py`): Splits large PDFs into manageable chunks
- **ECS Task 1** (`docker_autotag/autotag.py`): Uses Adobe PDF Services API for autotagging and image extraction
- **ECS Task 2** (`javascript_docker/`): Generates alt-text for images using Bedrock Claude models
- **Java Merger** (`lambda/java_lambda/`): Merges processed chunks using Apache PDFBox
- **Add Title Lambda** (`lambda/add_title/myapp.py`): Generates descriptive PDF titles using Bedrock Nova Pro
- **Accessibility Checkers**: Pre/post-remediation validation

**Key Files**:
- CDK Stack: `app.py` (lines 23-463)
- State Machine Definition: `app.py` (lines 209-355)
- CloudWatch Dashboard: `app.py` (lines 394-459)

**Environment Variables**:
- `STATE_MACHINE_ARN`: Step Functions ARN
- `S3_BUCKET_NAME`: Processing bucket
- `AWS_REGION`: Deployment region
- Model ARNs for Bedrock (configured in CDK)

**S3 Bucket Structure**:
```
s3://pdfaccessibility-{id}/
├── pdf/           # Input PDFs (upload here)
├── temp/          # Processing chunks
└── result/        # Remediated PDFs with "COMPLIANT" prefix
```

### PDF-to-HTML Remediation Solution

**Architecture Flow**:
```
S3 Upload (uploads/)
  → Lambda Function (containerized)
    → Bedrock Data Automation (BDA) - PDF parsing
    → PDF2HTML Module - HTML conversion
    → Audit Module - WCAG 2.1 compliance check
    → Remediate Module - LLM-powered fixes
  → Output to S3 (remediated/)
```

**Core Modules** (`pdf2html/content_accessibility_utility_on_aws/`):

1. **pdf2html/** - PDF to HTML conversion
   - Integrates with AWS Bedrock Data Automation
   - Extracts images and preserves layout
   - Supports single-page and multi-page output

2. **audit/** - Accessibility auditing
   - Checks WCAG 2.1 Level AA compliance
   - Issue severity classification (minor/major/critical)
   - Detailed context and remediation suggestions

3. **remediate/** - AI-powered remediation
   - Uses Bedrock models (Nova Lite by default)
   - Direct fixes for common issues
   - Advanced table structure remediation
   - Generates remediation reports

4. **batch/** - Batch processing orchestration
   - AWS service integrations (S3, Lambda, DynamoDB)
   - Job tracking and status management
   - Usage tracking for cost analysis

**Key Files**:
- Lambda Handler: `pdf2html/lambda_function.py`
- API: `pdf2html/content_accessibility_utility_on_aws/api.py`
- CLI: `pdf2html/content_accessibility_utility_on_aws/cli.py`
- CDK Stack: `pdf2html/cdk/bin/app.js`

**CLI Commands**:
```bash
# Convert PDF to HTML
content-accessibilty-utility-on-aws convert --input doc.pdf --output out/

# Audit HTML accessibility
content-accessibilty-utility-on-aws audit --input doc.html --output report.json

# Remediate issues
content-accessibilty-utility-on-aws remediate --input doc.html --output fixed.html

# Complete pipeline
content-accessibilty-utility-on-aws process --input doc.pdf --output out/
```

**S3 Bucket Structure**:
```
s3://pdf2html-bucket-{account}-{region}/
├── uploads/       # Input PDFs (upload here)
├── output/        # Intermediate BDA output
└── remediated/    # Final results (final_{filename}.zip)
    └── Contains:
        ├── remediated.html          # Final accessible HTML
        ├── result.html              # Original conversion
        ├── images/                  # Extracted images
        ├── remediation_report.html  # Detailed report
        └── usage_data.json          # Cost metrics
```

---

## Development Workflow

### Making Changes to PDF-to-PDF Solution

1. **Modify Lambda functions**:
   ```bash
   # Edit Lambda code
   vi lambda/split_pdf/main.py

   # Lambda code is deployed via Docker during CDK deploy
   # No separate build step needed for Python Lambdas
   ```

2. **Modify Java Lambda**:
   ```bash
   cd lambda/java_lambda/PDFMergerLambda
   # Edit Java code
   mvn clean package
   # Output: target/PDFMergerLambda-1.0-SNAPSHOT.jar
   ```

3. **Modify ECS containers**:
   ```bash
   # Edit Python container
   vi docker_autotag/autotag.py

   # Edit JavaScript container
   vi javascript_docker/package.json

   # Containers are built and pushed during CDK deploy
   ```

4. **Modify CDK infrastructure**:
   ```bash
   vi app.py
   # Make changes to Stack definition
   ```

5. **Deploy changes**:
   ```bash
   # Option 1: Via deploy script
   ./deploy.sh

   # Option 2: Direct CDK deploy
   cdk deploy

   # Option 3: Via CodeBuild
   aws codebuild start-build --project-name YOUR_PROJECT_NAME
   ```

### Making Changes to PDF-to-HTML Solution

1. **Modify Lambda/core library**:
   ```bash
   vi pdf2html/content_accessibility_utility_on_aws/pdf2html/converter.py

   # Test locally (if you have BDA access)
   cd pdf2html
   python -m content_accessibility_utility_on_aws.cli convert --input test.pdf
   ```

2. **Modify CDK infrastructure**:
   ```bash
   cd pdf2html/cdk
   vi lib/pdf2html-stack.js
   ```

3. **Build and deploy**:
   ```bash
   cd pdf2html/cdk
   npm install
   cdk deploy
   ```

### Testing Changes

**Local Testing** (limited without AWS resources):
```bash
# Test Python code
pytest lambda/split_pdf/test_main.py

# Test with mocked AWS services
python -m pytest --mock-aws
```

**Integration Testing**:
1. Deploy to AWS
2. Upload test PDF to S3 bucket
3. Monitor CloudWatch logs
4. Verify output in result/remediated folder

**CloudWatch Log Groups**:
- `/aws/lambda/PDFAccessibility-SplitPDF*`
- `/aws/lambda/PDFAccessibility-JavaLambda*`
- `/aws/lambda/PDFAccessibility-AddTitleLambda*`
- `/ecs/MyFirstTaskDef/PythonContainerLogGroup`
- `/ecs/MySecondTaskDef/JavaScriptContainerLogGroup`
- `/aws/states/MyStateMachine_PDFAccessibility`
- `/aws/lambda/Pdf2HtmlPipeline` (PDF-to-HTML)

---

## Common Development Tasks

### Adding a New Lambda Function

1. **Create Lambda directory**:
   ```bash
   mkdir lambda/new_function
   cd lambda/new_function
   ```

2. **Create handler**:
   ```python
   # main.py
   import json

   def lambda_handler(event, context):
       # Your logic here
       return {
           'statusCode': 200,
           'body': json.dumps('Hello from Lambda!')
       }
   ```

3. **Add to CDK stack** (`app.py`):
   ```python
   new_lambda = lambda_.Function(
       self, 'NewFunction',
       runtime=lambda_.Runtime.PYTHON_3_10,
       handler='main.lambda_handler',
       code=lambda_.Code.from_docker_build('lambda/new_function'),
       timeout=Duration.seconds(900),
       memory_size=512
   )

   # Grant permissions
   bucket.grant_read_write(new_lambda)
   ```

4. **Deploy**:
   ```bash
   cdk deploy
   ```

### Modifying Bedrock Models

**Location**: `app.py` lines 134-137

```python
model_id_image = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
model_id_link = 'us.anthropic.claude-3-haiku-20240307-v1:0'
model_arn_image = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_id_image}'
model_arn_link = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_id_link}'
```

**For PDF-to-HTML**, edit model references in:
- `pdf2html/content_accessibility_utility_on_aws/remediate/`

### Adding CloudWatch Metrics

**Example from existing code**:
```python
# Add policy to Lambda role
cloudwatch_logs_policy = iam.PolicyStatement(
    actions=["cloudwatch:PutMetricData"],
    resources=["*"],
)
my_lambda.add_to_role_policy(cloudwatch_logs_policy)

# In Lambda code
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='PDFAccessibility',
    MetricData=[{
        'MetricName': 'ProcessingTime',
        'Value': elapsed_time,
        'Unit': 'Seconds'
    }]
)
```

### Debugging Step Functions

1. **View execution in console**:
   ```
   AWS Console → Step Functions → State Machines → MyStateMachine
   ```

2. **Check execution logs**:
   ```bash
   aws logs tail /aws/states/MyStateMachine_PDFAccessibility --follow
   ```

3. **View execution details**:
   ```bash
   aws stepfunctions describe-execution --execution-arn <arn>
   ```

4. **Common issues**:
   - Check ECS task logs for container failures
   - Verify S3 permissions for Lambda/ECS roles
   - Check Bedrock model access in IAM policies

---

## Configuration & Secrets

### Adobe API Credentials (PDF-to-PDF)

**Storage**: AWS Secrets Manager
**Secret Name**: `/myapp/client_credentials`
**Format**:
```json
{
  "client_credentials": {
    "PDF_SERVICES_CLIENT_ID": "your-client-id",
    "PDF_SERVICES_CLIENT_SECRET": "your-secret"
  }
}
```

**Access in code**:
```python
import boto3
import json

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='/myapp/client_credentials')
credentials = json.loads(response['SecretString'])
```

**Managed by**: `deploy.sh` (lines 76-114)

### Bedrock Data Automation (PDF-to-HTML)

**Created by**: `deploy.sh` (lines 116-161)
**Project Configuration**:
```json
{
  "document": {
    "extraction": {
      "granularity": {"types": ["DOCUMENT", "PAGE", "ELEMENT"]},
      "boundingBox": {"state": "ENABLED"}
    },
    "generativeField": {"state": "DISABLED"},
    "outputFormat": {
      "textFormat": {"types": ["HTML"]},
      "additionalFileFormat": {"state": "ENABLED"}
    }
  }
}
```

### Environment Variables

**PDF-to-PDF Lambda environments set in Step Functions**:
- `S3_BUCKET_NAME`
- `S3_FILE_KEY`
- `S3_CHUNK_KEY`
- `model_arn_image`
- `model_arn_link`
- `AWS_REGION`

**PDF-to-HTML Lambda**:
- `BDA_S3_BUCKET`
- `BDA_PROJECT_ARN`
- `AWS_REGION`

---

## IAM Permissions

### Deployment Permissions

**Required for PDF-to-PDF**:
- S3, ECR, Lambda, ECS, EC2, Step Functions, IAM, CloudFormation
- Bedrock (including Data Automation)
- CloudWatch, Secrets Manager, Systems Manager

**Required for PDF-to-HTML**:
- S3, ECR, Lambda, IAM, CloudFormation
- Bedrock (including Data Automation)
- CloudWatch, Systems Manager

**Full details**: `/home/andreyf/projects/PDF_Accessibility/docs/IAM_PERMISSIONS.md`

### Runtime Permissions

**ECS Task Role** (`app.py` lines 77-95):
- Full Bedrock access
- S3 read/write on processing bucket
- Secrets Manager read for Adobe credentials

**Lambda Execution Roles**:
- S3 read/write
- CloudWatch logs
- Bedrock inference (where needed)
- Secrets Manager (for checkers)

---

## Monitoring & Troubleshooting

### CloudWatch Dashboard

**Auto-created**: `PDF_Processing_Dashboard-{timestamp}`

**Widgets**:
1. File status tracking (aggregated across all logs)
2. Split PDF Lambda logs
3. Step Functions execution logs
4. ECS Task 1 logs (Adobe autotagging)
5. ECS Task 2 logs (Alt-text generation)
6. Java Lambda logs (PDF merger)

**Location in code**: `app.py` lines 394-459

### Common Issues

**Issue**: ECS task fails with "CannotPullContainerError"
- **Cause**: ECR permissions or image not pushed
- **Fix**: Check ECR repository, verify task execution role has ECR pull permissions

**Issue**: Lambda timeout
- **Cause**: Large PDF processing
- **Fix**: Increase timeout in CDK (currently 900s), optimize chunk size in split logic

**Issue**: Bedrock "AccessDeniedException"
- **Cause**: Model not enabled in region
- **Fix**: Enable model access in Bedrock console → Model access

**Issue**: Step Functions fails with "Task timed out"
- **Cause**: ECS task taking too long
- **Fix**: Check ECS task logs, verify Adobe API credentials, increase Step Functions timeout (currently 150 min)

**Issue**: PDF-to-HTML Lambda fails
- **Cause**: BDA project misconfiguration or permissions
- **Fix**: Verify BDA project ARN, check Lambda IAM role has `bedrock-data-automation:*` permissions

### Log Analysis

**View recent errors**:
```bash
# PDF-to-PDF
aws logs filter-log-events \
  --log-group-name /aws/lambda/PDFAccessibility-SplitPDF* \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000

# PDF-to-HTML
aws logs filter-log-events \
  --log-group-name /aws/lambda/Pdf2HtmlPipeline \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Monitor Step Functions execution**:
```bash
aws stepfunctions list-executions \
  --state-machine-arn $(aws stepfunctions list-state-machines \
    --query 'stateMachines[?contains(name, `MyStateMachine`)].stateMachineArn' \
    --output text) \
  --max-items 5
```

---

## Cost Optimization

### Current Architecture Costs

**PDF-to-PDF Solution**:
- **NAT Gateway**: $0.045/hour (~$32/month) - HIGHEST COST
- **ECS Fargate**: Per-task execution (~$0.04 per task-hour)
- **Lambda**: Per-invocation + duration
- **S3**: Storage + requests
- **Bedrock**: Per-token pricing (Nova Pro ~$0.80/1M input, $3.20/1M output)
- **Adobe PDF Services API**: Enterprise pricing (external)

**PDF-to-HTML Solution** (more cost-effective):
- **Lambda**: Per-invocation (serverless, no idle costs)
- **Bedrock Data Automation**: Per-page pricing
- **Bedrock Models**: Per-token pricing (Nova Lite cheaper than Pro)
- **S3**: Storage + requests
- **No NAT Gateway required**

### Cost Reduction Strategies

1. **Remove NAT Gateway** (if outbound internet not needed):
   ```python
   # In app.py, change:
   vpc = ec2.Vpc(self, "MyVpc",
       max_azs=2,
       nat_gateways=0,  # Changed from 1
       # ...
   )
   # Note: Requires VPC endpoints for AWS services
   ```

2. **Use spot instances for ECS** (for non-critical workloads):
   ```python
   task_definition = ecs.FargateTaskDefinition(
       self, "MyTaskDef",
       # Add capacity provider strategy for Fargate Spot
   )
   ```

3. **Reduce Lambda memory** (if processing allows):
   ```python
   lambda_.Function(
       # ...
       memory_size=512,  # Reduced from 1024
   )
   ```

4. **S3 lifecycle policies**:
   ```python
   bucket.add_lifecycle_rule(
       transitions=[
           s3.Transition(
               storage_class=s3.StorageClass.GLACIER,
               transition_after=Duration.days(90)
           )
       ]
   )
   ```

5. **Use Bedrock Nova Lite instead of Nova Pro** (where accuracy allows):
   - Nova Lite: ~$0.16/1M input, $0.64/1M output
   - Nova Pro: ~$0.80/1M input, $3.20/1M output

---

## Testing & Validation

### End-to-End Testing

**PDF-to-PDF Solution**:
```bash
# 1. Get bucket name
BUCKET=$(aws s3 ls | grep pdfaccessibility | awk '{print $3}')

# 2. Upload test PDF
aws s3 cp test.pdf s3://$BUCKET/pdf/test.pdf

# 3. Monitor Step Functions
aws stepfunctions list-executions \
  --state-machine-arn <arn> \
  --max-items 1

# 4. Wait for completion (check CloudWatch dashboard)

# 5. Download result
aws s3 cp s3://$BUCKET/result/ ./output/ --recursive

# 6. Validate with accessibility checker
# Check logs in /aws/lambda/*accessibility_checker_after_remidiation*
```

**PDF-to-HTML Solution**:
```bash
# 1. Get bucket name
BUCKET=$(aws s3 ls | grep pdf2html-bucket | awk '{print $3}')

# 2. Upload test PDF
aws s3 cp test.pdf s3://$BUCKET/uploads/test.pdf

# 3. Monitor Lambda execution
aws logs tail /aws/lambda/Pdf2HtmlPipeline --follow

# 4. Download results
aws s3 cp s3://$BUCKET/remediated/ ./output/ --recursive

# 5. Extract and validate
unzip output/final_test.zip
# Review remediated.html and remediation_report.html
```

### Unit Testing

**Example test structure**:
```python
# tests/test_split_pdf.py
import pytest
from lambda.split_pdf import main

def test_calculate_chunks():
    result = main.calculate_chunks(total_pages=100, chunk_size=10)
    assert len(result) == 10

@pytest.fixture
def mock_s3():
    # Mock S3 operations
    pass
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] AWS account with appropriate IAM permissions
- [ ] AWS CLI configured (`aws configure`)
- [ ] Choose deployment region with Bedrock availability
- [ ] For PDF-to-PDF: Adobe API credentials ready
- [ ] For PDF-to-HTML: Verify Bedrock Data Automation access
- [ ] Sufficient service limits (especially Elastic IPs for NAT)

### Deployment

- [ ] Clone repository: `git clone https://github.com/a-fedosenko/PDF_Accessibility.git`
- [ ] Run deployment script: `./deploy.sh`
- [ ] Follow interactive prompts
- [ ] Monitor CodeBuild progress
- [ ] Note S3 bucket names from output

### Post-Deployment

- [ ] Access CloudWatch dashboard
- [ ] Upload test PDF to appropriate S3 folder
- [ ] Monitor processing logs
- [ ] Verify output in result/remediated folder
- [ ] Review accessibility compliance reports
- [ ] (Optional) Deploy frontend UI

### Cleanup

**To delete resources**:
```bash
# PDF-to-PDF
aws cloudformation delete-stack --stack-name PDFAccessibility

# PDF-to-HTML
cd pdf2html/cdk
cdk destroy

# Clean up CodeBuild projects
aws codebuild delete-project --name YOUR_PROJECT_NAME

# Clean up secrets
aws secretsmanager delete-secret --secret-id /myapp/client_credentials --force-delete-without-recovery

# Clean up BDA projects
aws bedrock-data-automation delete-data-automation-project \
  --project-arn <arn>
```

---

## Additional Resources

### Documentation Files
- **README.md**: Main project documentation
- **pdf2html/README.md**: Detailed PDF-to-HTML solution guide
- **docs/IAM_PERMISSIONS.md**: Complete IAM permission requirements
- **docs/MANUAL_DEPLOYMENT.md**: Step-by-step manual deployment
- **docs/TROUBLESHOOTING_CDK_DEPLOY.md**: CDK deployment issues

### External Links
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Adobe PDF Services API](https://developer.adobe.com/document-services/apis/pdf-services/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Key CDK Patterns

**VPC with NAT**:
```python
vpc = ec2.Vpc(self, "MyVpc",
    max_azs=2,
    nat_gateways=1,
    subnet_configuration=[
        ec2.SubnetConfiguration(subnet_type=ec2.SubnetType.PUBLIC, name="Public", cidr_mask=24),
        ec2.SubnetConfiguration(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, name="Private", cidr_mask=24),
    ]
)
```

**ECS Task with Step Functions**:
```python
ecs_task = tasks.EcsRunTask(
    self, "ECSTask",
    integration_pattern=sfn.IntegrationPattern.RUN_JOB,  # Wait for completion
    cluster=cluster,
    task_definition=task_def,
    container_overrides=[
        tasks.ContainerOverride(
            container_definition=container,
            environment=[
                tasks.TaskEnvironmentVariable(
                    name="VAR_NAME",
                    value=sfn.JsonPath.string_at("$.inputValue")  # From Step Functions input
                )
            ]
        )
    ],
    launch_target=tasks.EcsFargateLaunchTarget()
)
```

**Lambda from Docker**:
```python
lambda_.Function(
    self, 'MyLambda',
    runtime=lambda_.Runtime.PYTHON_3_10,
    handler='main.lambda_handler',
    code=lambda_.Code.from_docker_build('path/to/dockerfile'),  # Builds during synth
    timeout=Duration.seconds(900),
    memory_size=1024
)
```

---

## Contributing

When making contributions:

1. **Follow existing patterns**:
   - Python: PEP 8 style
   - JavaScript: ESLint/Prettier
   - Infrastructure: CDK best practices

2. **Document changes**:
   - Update README.md if user-facing
   - Update this CLAUDE.md for developer context
   - Add inline comments for complex logic

3. **Test thoroughly**:
   - Local testing where possible
   - Integration tests in dev environment
   - Verify monitoring and logs

4. **Consider costs**:
   - Evaluate impact on AWS costs
   - Optimize for serverless where possible
   - Document any new resources

5. **Security**:
   - Never commit credentials
   - Use Secrets Manager for sensitive data
   - Follow principle of least privilege for IAM

---

## Quick Reference

### Important ARNs and Names

**Step Functions State Machine**:
```
arn:aws:states:{region}:{account}:stateMachine:MyStateMachine
```

**S3 Buckets**:
- PDF-to-PDF: `pdfaccessibility-{unique-id}`
- PDF-to-HTML: `pdf2html-bucket-{account}-{region}`

**CloudWatch Dashboard**:
```
PDF_Processing_Dashboard-{timestamp}
```

### Bedrock Models Used

| Purpose | Model ID | Cost (approx) |
|---------|----------|---------------|
| Title Generation | us.amazon.nova-pro-v1:0 | $0.80/$3.20 per 1M tokens |
| Image Analysis | us.anthropic.claude-3-5-sonnet-20241022-v2:0 | Higher |
| Link Generation | us.anthropic.claude-3-haiku-20240307-v1:0 | Lower |
| HTML Remediation | us.amazon.nova-lite-v1:0 | $0.16/$0.64 per 1M tokens |

### File Size Limits

- **Lambda payload**: 6 MB synchronous, 256 KB async
- **S3 single PUT**: 5 GB
- **ECS task storage**: 200 GB max ephemeral
- **Step Functions payload**: 256 KB

### Timeout Limits

- **Lambda**: 900 seconds (15 minutes) max - currently set
- **Step Functions**: 150 minutes - currently set
- **ECS task**: No inherent limit, but Step Functions integration has timeout

---

## Version History

**Current Version**: Based on latest commit `9849a0f`

**Recent Changes**:
- Removed AWS Bedrock model access instructions from README
- Added pdf2html subtree integration
- Multiple PRs merged for improvements

For detailed version history, see:
```bash
git log --oneline
```

---

**Last Updated**: 2025-11-09
**Maintained By**: Arizona State University AI Cloud Innovation Center
**For Support**: ai-cic@amazon.com
