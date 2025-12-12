# Adobe AutoTag and AI Post-Processing in PDF Accessibility

## Overview

This document explains why the PDF accessibility remediation system uses Adobe PDF Services API (specifically AutoTag) alongside AI models, and how they work together to create WCAG 2.1 Level AA compliant PDFs.

## Why Adobe API is Used

The system uses **Adobe PDF Services API** for two critical operations that AI models cannot perform:

1. **AutoTag PDF** - Adds XML structure tags and accessibility metadata to PDFs
2. **Extract PDF** - Extracts structured data including text, tables, figures, and images

## Why AutoTag API is Necessary (Even With AI Models)

**Adobe AutoTag and AI models solve different, complementary problems:**

### What Adobe AutoTag Does

- **Structural tagging** - Adds XML tags (`<P>`, `<H1>`, `<Table>`, etc.) inside the PDF format itself
- **Document hierarchy** - Creates proper heading levels and reading order
- **Semantic structure** - Marks which elements are content vs decorative artifacts
- **PDF-level accessibility** - Modifies the internal PDF structure for screen readers
- **Table extraction** - Identifies and extracts table structures programmatically
- **Figure detection** - Locates images and figures that need alt text

### What AI Models Do (Claude/Nova via Bedrock)

- **Content analysis** - Understands what images show semantically
- **Alt text generation** - Creates descriptive, contextual text for images
- **Link descriptions** - Generates meaningful link text for accessibility
- **Title generation** - Creates descriptive titles for documents
- **Context understanding** - Interprets content in relation to surrounding text

## The Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ PDF Input                                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────▼──────────────────┐
         │  Stage 1: Adobe AutoTag          │
         │  ✓ Structural tagging            │
         │  ✓ Accessibility metadata        │
         │  ✓ Table/figure extraction       │
         └────────────┬──────────────────────┘
                      │
    ┌─────────────────▼──────────────────┐
    │  Stage 2: Extract PDF (Adobe)      │
    │  ✓ Get images from documents       │
    │  ✓ Extract text content            │
    │  ✓ Get table renditions            │
    └──────────────┬──────────────────────┘
                   │
   ┌───────────────▼──────────────────────┐
   │  Stage 3: AI Model Processing        │
   │  • Claude 3.5 Sonnet (Images)        │
   │  • Claude 3 Haiku (Links)            │
   │  • Nova Pro (Titles)                 │
   │  ✓ Generate WCAG alt text            │
   │  ✓ Analyze image content             │
   │  ✓ Create descriptive titles         │
   │  ✓ Generate link descriptions        │
   └────────────┬─────────────────────────┘
                │
   ┌────────────▼──────────────────────────┐
   │  Stage 4: Merge & Finalize            │
   │  ✓ Add alt text to PDFs               │
   │  ✓ Insert generated content           │
   │  ✓ Add metadata                       │
   └───────────────┬──────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Remediated PDF    │
         │  (WCAG 2.1 AA)     │
         └────────────────────┘
```

## Technical Implementation

### Stage 1: Adobe AutoTag

**Location:** `docker_autotag/autotag.py:231-234`

```python
autotag_pdf_params = AutotagPDFParams(
    generate_report=True,      # Creates Excel report with tagging details
    shift_headings=True        # Fixes heading hierarchy
)
```

**What Happens:**
- Adobe's ML models analyze the PDF structure
- XML tags are added to the PDF format for accessibility
- A detailed report is generated showing what was tagged
- Heading levels are corrected for proper document hierarchy
- The PDF internal structure is modified for screen reader compatibility

### Stage 2: Adobe Extract

**Location:** `docker_autotag/autotag.py`

**What Happens:**
- Images are extracted from the tagged PDF
- Text content is extracted with positioning information
- Table structures are identified and exported
- Figure renditions are created for AI analysis

### Stage 3: AI Processing

**Location:** `docker_js_bedrock/` container

**Models Used:**
- **Claude 3.5 Sonnet** (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`) - Image analysis and alt text
- **Claude 3 Haiku** (`us.anthropic.claude-3-haiku-20240307-v1:0`) - Link descriptions
- **Amazon Nova Pro** - Document title generation

**What Happens:**
- Images from Adobe Extract are sent to Claude Sonnet
- AI generates descriptive, WCAG-compliant alt text
- Link URLs are analyzed to create meaningful descriptions
- Results are stored in SQLite database for merging

### Stage 4: Merge and Finalize

**Location:** Java Lambda functions

**What Happens:**
- AI-generated alt text is inserted into the tagged PDF
- Link descriptions are added
- Document title is updated
- Final accessibility check is performed
- Compliant PDF is uploaded to S3

## Why AI Cannot Replace Adobe AutoTag

### Technical Limitations

1. **PDF Structure Modification**
   - AI models cannot directly modify PDF internal structure
   - XML tags must be embedded in the PDF format itself
   - Screen readers rely on these structural tags for navigation

2. **Format Expertise**
   - Adobe's solution understands PDF format intricacies
   - Handles edge cases across millions of PDF variations
   - Maintains PDF validity while adding accessibility features

3. **Different Problem Domains**
   - Adobe: Structural accessibility (format-level)
   - AI: Content accessibility (semantic-level)
   - Both are required for WCAG 2.1 compliance

### Complementary Strengths

| Component | Input | Role | Output |
|-----------|-------|------|--------|
| **Adobe AutoTag** | Raw PDF | Structural accessibility | Tagged PDF + Report |
| **Adobe Extract** | Tagged PDF | Data extraction | Images, text, tables |
| **AI Models** | Extracted images/data | Content analysis | Alt text, descriptions |
| **PDF Merge** | Components | Assembly | Final PDF |

## Step Function Execution Flow

From `app.py` (cdk_stack.py:590):

```
1. Input PDF uploaded to S3
   ↓
2. Split PDF Lambda
   └─ Chunks large PDFs for parallel processing
   ↓
3. Parallel Execution (per chunk):
   ├─ ECS Task 1: Python Container (Adobe)
   │  ├─ autotag_pdf_with_options() → Adobe AutoTag API
   │  ├─ extract_api() → Adobe Extract API
   │  └─ Process extracted data
   │
   └─ ECS Task 2: JavaScript Container (Bedrock)
      ├─ Fetch images from AutoTag report
      ├─ generateAltText() → Claude Sonnet via Bedrock
      ├─ generateAltTextForLink() → Claude Haiku via Bedrock
      └─ Store in SQLite database
   ↓
4. Java Lambda
   └─ Merge chunks back together
   ↓
5. Add Title Lambda
   └─ generateTitle() → Nova Pro via Bedrock
   ↓
6. Modify PDF with alt text
   └─ Insert AI-generated content into PDF
   ↓
7. Accessibility Checker (Post)
   └─ Validate WCAG 2.1 compliance
   ↓
8. Upload to S3 (result/)
   └─ COMPLIANT_filename.pdf
```

## Configuration

### Adobe API Configuration

From `.env.example`:

```env
PDF_SERVICES_CLIENT_ID=your-adobe-client-id-here
PDF_SERVICES_CLIENT_SECRET=your-adobe-client-secret-here
ADOBE_API_QUOTA_LIMIT=0  # Monthly API call limit (0 = no limit)
QUOTA_ALERT_EMAIL=your-email@example.com
```

### Bedrock AI Models Configuration

```env
BEDROCK_MODEL_ARN_IMAGE=arn:aws:bedrock:...:us.anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MODEL_ARN_LINK=arn:aws:bedrock:...:us.anthropic.claude-3-haiku-20240307-v1:0
```

## Quota Management

### Why Quota Monitoring?

- Adobe API uses monthly call limits (e.g., 500 free tier, 25,000 paid)
- Each PDF requires 2 API calls (AutoTag + Extract)
- System prevents hitting quota limits with pre-check validation

### Implementation

**Location:** `docker_autotag/autotag.py:102-120`

```python
if QuotaMonitor:
    adobe_quota_limit = int(os.environ.get('ADOBE_API_QUOTA_LIMIT', '0'))
    quota_monitor = QuotaMonitor(
        api_name="AdobeAPI",
        quota_limit=adobe_quota_limit,
        warning_threshold=0.8,      # Alert at 80% usage
        critical_threshold=0.95     # Critical at 95% usage
    )
```

### Monitoring Points

- **Pre-call check:** `quota_monitor.check_quota_available()` (line 203)
- **Post-call tracking:** `quota_monitor.track_api_call(operation="AutotagPDF", success=True)` (line 262)
- **Storage:** DynamoDB table for usage metrics
- **Alerts:** SNS notifications for threshold breaches
- **Visualization:** CloudWatch dashboard widgets

See `ADOBE_MONITORING.md` for detailed quota monitoring documentation.

## Cost Considerations

### Adobe API Costs
- Quota-limited (monthly call caps)
- Each PDF = 2 calls (AutoTag + Extract)
- Free tier: 500 calls/month
- Paid tier: Scales with volume

### AWS Bedrock Costs
- Pay-per-invocation model
- No strict quota limits
- Variable cost based on:
  - Number of images (Claude Sonnet invocations)
  - Number of links (Claude Haiku invocations)
  - Title generation (Nova Pro invocations)

## Key Takeaways

1. **Adobe AutoTag is essential** - AI cannot modify PDF structure or add XML tags
2. **AI models are essential** - Adobe cannot understand image content or generate contextual descriptions
3. **Hybrid approach is required** - Both technologies solve different parts of the accessibility problem
4. **Sequential processing** - Adobe must run first to structure the PDF, then AI analyzes content
5. **WCAG 2.1 compliance** - Requires both structural tags (Adobe) and meaningful alt text (AI)

## The Key Insight

**Adobe AutoTag makes the PDF structurally accessible** (so screen readers can navigate it), while **AI models make the content accessible** (so users understand what images show). Both are required for full WCAG 2.1 Level AA compliance.

This hybrid solution leverages:
- Adobe's expertise in PDF format manipulation
- AI's capability for semantic content understanding
- AWS infrastructure for scalable, parallel processing
