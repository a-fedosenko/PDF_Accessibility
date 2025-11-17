# Implementation Plan: Remove Limits & Integrate IdentityServer4 SSO

**Project**: PDF Accessibility Solutions
**Date**: November 17, 2025
**Region**: us-east-2
**Account ID**: 471414695760

---

## Table of Contents

1. [Overview](#overview)
2. [Change 1: Remove All Limits](#change-1-remove-all-upload-file-limits)
3. [Change 2: IdentityServer4 SSO Integration](#change-2-integrate-identityserver4-sso)
4. [Combined Implementation Timeline](#combined-implementation-timeline)
5. [Risk Assessment](#risk-assessment)
6. [Pre-Implementation Checklist](#pre-implementation-checklist)
7. [Next Steps](#next-steps)

---

## Overview

This document provides a comprehensive implementation plan for two critical changes to the PDF Accessibility Solutions platform:

### **Change 1: Remove All Limits (8 uploads, 10 pages, 25MB)**
- **Effort**: 4-6 hours
- **Complexity**: Low
- **Risk**: Low
- **Impact**: Allows unlimited PDF uploads and processing

### **Change 2: Integrate IdentityServer4 SSO**
- **Effort**: 24-32 hours
- **Complexity**: Medium-High
- **Risk**: Medium
- **Impact**: Replaces Cognito email/password with company SSO

**Total Estimated Time**: 34 hours (~1.5 weeks)

---

## Change 1: Remove All Upload File Limits

### Current State Analysis

Based on deep codebase exploration, here's what was found:

#### ✅ **Limits That DON'T Exist in Backend** (No Action Needed):
- **"8 uploads per person"** - Only an API endpoint exists; no enforcement in code
- **"25MB file size"** - Not explicitly enforced anywhere
- **"10 pages per PDF"** - Not found in code

#### ⚠️ **Limits That DO Exist** (Need Removal/Adjustment):

| Limit Type | Current Value | Location | Action Required |
|-----------|---------------|----------|-----------------|
| API Gateway Throttling | 5,000 burst, 10,000 req/sec | API Gateway config | Increase 10x |
| Image Size Limit | 4 MB | `bedrock_client.py:38` | Increase to 20MB |
| Lambda Timeouts | 900 seconds (15 min) | CDK stack | Keep or increase |
| Lambda Memory | 512-1024 MB | CDK stack | Increase to 3008 MB |
| Max Pages Config | 1000 pages | `.env` file | Change to 100,000 |
| PDF Chunk Size | 10 pages | `.env` file | Change to 200 |

---

### Implementation Steps

#### **Phase 1: Backend Code Changes** (2 hours)

##### Step 1.1: Increase Image Size Limit

**File**: `/home/andreyf/projects/PDF_Accessibility/pdf2html/content_accessibility_utility_on_aws/remediate/services/bedrock_client.py`

**Line 37-38**:
```python
# CURRENT:
MAX_IMAGE_SIZE = 4_000_000  # 4 MB

# CHANGE TO:
MAX_IMAGE_SIZE = 20_000_000  # 20 MB (Bedrock max is ~20MB)
```

**Why**: Allows processing of higher-resolution images for better accessibility.

---

##### Step 1.2: Update Environment Variables

**File**: `/home/andreyf/projects/PDF_Accessibility/.env`

```bash
# CURRENT:
PDF_CHUNK_SIZE=10
MAX_PAGES_PER_PDF=1000

# CHANGE TO:
PDF_CHUNK_SIZE=200  # Match the hardcoded value in split_pdf
MAX_PAGES_PER_PDF=100000  # Effectively unlimited (100k pages)
```

**Also update**: `/home/andreyf/projects/PDF_Accessibility/.env.example`

---

#### **Phase 2: Infrastructure Changes** (2 hours)

You have two options for updating infrastructure:

##### **Option A: Via CDK (Recommended for Production)**

**File**: `/home/andreyf/projects/PDF_Accessibility/app.py` (or the UI backend CDK stack)

Add or modify Lambda function definitions:

```python
from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as api_gateway,
)

# Update Lambda functions with increased resources
split_pdf_lambda = lambda_.Function(
    self, 'SplitPDFLambda',
    runtime=lambda_.Runtime.PYTHON_3_10,
    handler='main.lambda_handler',
    code=lambda_.Code.from_docker_build('lambda/split_pdf'),
    timeout=Duration.minutes(15),  # Keep at AWS max (15 minutes)
    memory_size=3008,  # Increase from 1024 MB to 3008 MB
    environment={
        'MAX_PAGES_PER_PDF': '100000',
        'PDF_CHUNK_SIZE': '200',
    }
)

# Similar updates for other Lambda functions:
# - add_title_lambda
# - java_merger_lambda
# - accessibility_checker_before
# - accessibility_checker_after
# - pdf2html_lambda

# Update API Gateway throttling limits
api = api_gateway.RestApi(
    self, 'PDFAccessibilityAPI',
    rest_api_name='PDF Accessibility API',
    deploy_options=api_gateway.StageOptions(
        stage_name='prod',
        throttling_rate_limit=100000,  # Increase from 10,000 to 100,000
        throttling_burst_limit=50000,  # Increase from 5,000 to 50,000
    )
)
```

**Then deploy**:
```bash
cd /home/andreyf/projects/PDF_Accessibility
cdk deploy
```

---

##### **Option B: Via AWS Console (Quick Fix)**

**API Gateway Throttling**:
1. Navigate to: https://console.aws.amazon.com/apigateway/home?region=us-east-2
2. Select your API: `CdkBackendStack-*` or similar
3. Click **Stages** → **prod**
4. Click **Settings** tab
5. Scroll to **Throttling**
6. Update:
   - **Rate**: 100,000 requests/second
   - **Burst**: 50,000 requests
7. Click **Save Changes**

**Lambda Configuration**:
1. Navigate to: https://console.aws.amazon.com/lambda/home?region=us-east-2
2. For each Lambda function (`PDFAccessibility-SplitPDF*`, etc.):
   - Click **Configuration** → **General configuration**
   - Click **Edit**
   - **Memory**: Increase to 3008 MB
   - **Timeout**: Keep at 15 minutes (or increase if needed)
   - **Environment variables**: Add/update:
     - `MAX_PAGES_PER_PDF` = `100000`
     - `PDF_CHUNK_SIZE` = `200`
   - Click **Save**

---

#### **Phase 3: Frontend Changes** (1-2 hours)

**Repository**: https://github.com/a-fedosenko/PDF_accessability_UI

**Access Required**: You'll need to clone and modify the frontend repository.

```bash
# Clone the frontend repository
git clone https://github.com/a-fedosenko/PDF_accessability_UI.git
cd PDF_accessability_UI
```

**Files to Search and Modify**:

Look for upload validation in files like:
- `src/components/Upload.jsx` or `src/components/UploadForm.jsx`
- `src/utils/validation.js`
- `src/services/api.js`
- `src/config/constants.js`

**Typical React Code to Find and Remove**:

```javascript
// BEFORE (Remove or comment out):

// File size validation
if (file.size > 25 * 1024 * 1024) {  // 25MB check
  alert("File too large! Maximum size is 25MB.");
  return false;
}

// Upload quota check
const uploadCount = await checkUploadQuota();
if (uploadCount >= 8) {
  alert("Upload limit reached! Maximum 8 uploads allowed.");
  return false;
}

// Page count validation
const pageCount = await getPageCount(file);
if (pageCount > 10) {
  alert("PDF has too many pages! Maximum 10 pages allowed.");
  return false;
}

// AFTER (Remove all validation or set to very high limits):

// Option 1: Remove validation entirely (recommended)
// Just delete the validation code

// Option 2: Set very high limits
const MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024; // 10 GB
const MAX_UPLOADS = 999999;
const MAX_PAGES = 100000;
```

**Remove API Calls to Upload Quota Endpoint**:

```javascript
// BEFORE:
const checkQuota = async () => {
  const response = await fetch(
    process.env.REACT_APP_CHECK_UPLOAD_QUOTA_ENDPOINT
  );
  const data = await response.json();
  return data;
};

// AFTER (stub it out or remove):
const checkQuota = async () => {
  return { quota: 999999, used: 0, remaining: 999999, unlimited: true };
};
```

**Update UI Messages**:
- Remove any "X uploads remaining" messages
- Remove file size warnings
- Remove page limit warnings

**Commit and Push**:
```bash
git add .
git commit -m "Remove upload quota, file size, and page limits"
git push origin main
```

**Trigger Amplify Build** (if CI/CD is enabled):
- Build should auto-trigger on push
- Or manually trigger from Amplify Console

---

#### **Phase 4: Remove/Stub Upload Quota API** (30 minutes)

The `/upload-quota` API endpoint exists but implementation may not be in the backend codebase.

**Option A: Create a Lambda that Always Returns Unlimited**

Create a new Lambda function or update existing one:

```python
# lambda/upload_quota/handler.py
import json

def lambda_handler(event, context):
    """
    Returns unlimited quota for all users.
    This effectively disables quota checking.
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        },
        'body': json.dumps({
            'quota': 999999,
            'used': 0,
            'remaining': 999999,
            'unlimited': True,
            'message': 'Unlimited uploads enabled'
        })
    }
```

**Deploy via CDK or AWS Console**.

---

**Option B: Remove the API Endpoint Entirely**

If you want to completely remove the quota check:

1. **Remove from API Gateway**:
   - Navigate to API Gateway Console
   - Find the `/upload-quota` resource
   - Delete the resource
   - Redeploy the API

2. **Update Frontend**:
   - Remove all calls to `REACT_APP_CHECK_UPLOAD_QUOTA_ENDPOINT`
   - Remove quota checking logic

---

#### **Phase 5: Testing and Validation** (2 hours)

**Test Cases**:

1. **Large File Upload** (>25MB):
   ```bash
   # Create a large test PDF
   # Upload via UI or AWS CLI
   aws s3 cp large-file.pdf s3://pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc/pdf/
   ```

2. **Multiple Uploads** (>8):
   - Upload 10+ PDFs via UI
   - Verify no quota error

3. **Large Page Count** (>10 pages):
   - Upload a PDF with 50+ pages
   - Verify processing completes

4. **Monitor Processing**:
   ```bash
   # Check CloudWatch logs
   aws logs tail /aws/lambda/PDFAccessibility-SplitPDF* --follow

   # Check Step Functions execution
   aws stepfunctions list-executions \
     --state-machine-arn arn:aws:states:us-east-2:471414695760:stateMachine:MyStateMachine \
     --max-items 5
   ```

5. **API Gateway Throttling**:
   - Use load testing tool (e.g., Apache Bench, JMeter)
   - Verify no throttling errors up to new limits

**Validation Checklist**:
- [ ] Large PDF (>25MB) uploads successfully
- [ ] More than 8 uploads allowed
- [ ] PDFs with >10 pages process correctly
- [ ] No quota errors in frontend
- [ ] API Gateway accepts high request rates
- [ ] Lambda functions don't timeout on large files
- [ ] CloudWatch logs show no errors
- [ ] S3 bucket stores all uploaded files
- [ ] Processing completes and results appear in `result/` folder

---

## Change 2: Integrate IdentityServer4 SSO

### Architecture Options

You have three main approaches for integrating IdentityServer4 with your AWS deployment:

#### **Option A: SAML Federation** ⭐ **RECOMMENDED**
```
User → IdentityServer4 (SAML IdP) → AWS Cognito (SAML SP) → API Gateway
```
**Pros**:
- Native Cognito support
- No custom code required
- Easier to maintain
- Standard enterprise SSO pattern

**Cons**:
- Requires IdentityServer4 SAML configuration
- Slightly more complex initial setup

---

#### **Option B: OIDC Federation**
```
User → IdentityServer4 (OIDC) → AWS Cognito (OIDC) → API Gateway
```
**Pros**:
- Modern protocol
- Better for API integrations
- JSON-based (easier debugging)

**Cons**:
- Requires Cognito User Pool federation setup
- May need custom attribute mapping

---

#### **Option C: Direct Integration (No Cognito)**
```
User → IdentityServer4 → API Gateway (Custom Authorizer) → Lambda
```
**Pros**:
- Full control over authentication flow
- No Cognito dependency
- Can customize token validation

**Cons**:
- More code to write and maintain
- Custom Lambda authorizer required
- Manual token validation and refresh logic

---

### Recommended Approach: **Option A (SAML Federation)**

This guide focuses on **SAML Federation** as it's the most enterprise-ready solution.

---

### Implementation Steps

#### **Phase 1: IdentityServer4 Configuration** (4 hours)

**Prerequisites**:
- IdentityServer4 admin access
- SAML plugin installed (e.g., `Rsk.Saml` or similar)
- Company SSO metadata URL

---

##### Step 1.1: Configure AWS Cognito as SAML Service Provider

**In your IdentityServer4 configuration** (typically in `Config.cs` or similar):

```csharp
using IdentityServer4.Models;

public static class Clients
{
    public static IEnumerable<Client> GetClients()
    {
        return new List<Client>
        {
            // ... existing clients ...

            // New SAML client for AWS Cognito
            new Client
            {
                ClientId = "aws-cognito-pdf-accessibility",
                ClientName = "PDF Accessibility Solutions",
                ProtocolType = ProtocolTypes.Saml2p,

                AllowedScopes = { "openid", "profile", "email" },

                // AWS Cognito SAML callback URL
                RedirectUris = {
                    "https://pdf-ui-auth1rc16k.auth.us-east-2.amazoncognito.com/saml2/idpresponse"
                },

                // Post-logout redirect
                PostLogoutRedirectUris = {
                    "https://main.d3althp551dv7h.amplifyapp.com",
                    "https://main.d3althp551dv7h.amplifyapp.com/logout"
                },

                // Enable SAML
                EnableLocalLogin = false,

                // Required claims
                AlwaysSendClientClaims = true,
                AlwaysIncludeUserClaimsInIdToken = true,

                Claims = new List<ClientClaim>
                {
                    new ClientClaim("email", "user.email"),
                    new ClientClaim("given_name", "user.given_name"),
                    new ClientClaim("family_name", "user.family_name"),
                    new ClientClaim("name", "user.name"),
                }
            }
        };
    }
}
```

---

##### Step 1.2: Configure SAML Assertion Attributes

Ensure IdentityServer4 sends these attributes in SAML assertions:

```csharp
public static class IdentityResources
{
    public static IEnumerable<IdentityResource> GetIdentityResources()
    {
        return new List<IdentityResource>
        {
            new IdentityResources.OpenId(),
            new IdentityResources.Profile(),
            new IdentityResources.Email(),

            // Custom claims for Cognito
            new IdentityResource
            {
                Name = "cognito",
                DisplayName = "Cognito Claims",
                UserClaims = new[]
                {
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
                    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
                }
            }
        };
    }
}
```

---

##### Step 1.3: Generate and Download SAML Metadata

**SAML Metadata URL**: Typically at:
```
https://your-identityserver4.company.com/.well-known/saml/metadata
```

**Download the metadata**:
```bash
curl -o identityserver4-saml-metadata.xml \
  https://your-identityserver4.company.com/.well-known/saml/metadata
```

**Important URLs to Note**:
- **Single Sign-On (SSO) URL**: `https://your-identityserver4.company.com/saml/sso`
- **Single Logout (SLO) URL**: `https://your-identityserver4.company.com/saml/logout`
- **Entity ID**: `https://your-identityserver4.company.com`

---

##### Step 1.4: Test IdentityServer4 SAML Configuration

**Verify metadata is accessible**:
```bash
curl https://your-identityserver4.company.com/.well-known/saml/metadata
```

**Check for required elements**:
- `EntityDescriptor`
- `IDPSSODescriptor`
- `SingleSignOnService`
- `X509Certificate` (signing certificate)

---

#### **Phase 2: AWS Cognito User Pool Updates** (8 hours)

Now configure AWS Cognito to trust IdentityServer4 as an identity provider.

---

##### Step 2.1: Update CDK Stack (Recommended)

**Find the CDK stack that creates Cognito**. This is likely in the UI backend repository, not the main backend.

**If you have access to the CDK code**:

```typescript
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as cdk from 'aws-cdk-lib';

export class CognitoSSOStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Existing User Pool
    const userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: 'pdf-accessibility-user-pool',
      signInAliases: { email: true },
      selfSignUpEnabled: false,  // ⚠️ Disable self-signup with SSO
      standardAttributes: {
        email: { required: true, mutable: true },
        givenName: { required: true, mutable: true },
        familyName: { required: true, mutable: true },
      },
    });

    // Add SAML Identity Provider
    const samlProvider = new cognito.UserPoolIdentityProviderSaml(this, 'SamlProvider', {
      userPool: userPool,
      name: 'CompanySSO',  // This will be the provider identifier

      // SAML metadata from IdentityServer4
      metadata: cognito.UserPoolIdentityProviderSamlMetadata.url(
        'https://your-identityserver4.company.com/.well-known/saml/metadata'
      ),

      // Or use file-based metadata:
      // metadata: cognito.UserPoolIdentityProviderSamlMetadata.file('./identityserver4-saml-metadata.xml'),

      // Map SAML attributes to Cognito attributes
      attributeMapping: {
        email: cognito.ProviderAttribute.other('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'),
        givenName: cognito.ProviderAttribute.other('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'),
        familyName: cognito.ProviderAttribute.other('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'),
        fullname: cognito.ProviderAttribute.other('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'),
      },

      // Optional: Map custom attributes
      // custom: {
      //   department: cognito.ProviderAttribute.other('http://schemas.company.com/claims/department'),
      // }
    });

    // Update App Client to use SAML
    const userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: userPool,
      userPoolClientName: 'pdf-accessibility-client',

      // ⚠️ Only allow SAML provider (remove Cognito native auth)
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.custom('CompanySSO'),
      ],

      // Configure OAuth settings
      oAuth: {
        flows: {
          authorizationCodeGrant: true,  // Recommended for web apps
          implicitCodeGrant: true,       // For SPA (optional)
        },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          'https://main.d3althp551dv7h.amplifyapp.com',
          'https://main.d3althp551dv7h.amplifyapp.com/callback',
          'http://localhost:3000',  // For local development
        ],
        logoutUrls: [
          'https://main.d3althp551dv7h.amplifyapp.com/logout',
          'http://localhost:3000/logout',
        ],
      },

      // Optional: Enable refresh tokens
      refreshTokenValidity: cdk.Duration.days(30),
      accessTokenValidity: cdk.Duration.hours(1),
      idTokenValidity: cdk.Duration.hours(1),
    });

    // Make sure the client depends on the SAML provider
    userPoolClient.node.addDependency(samlProvider);

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: userPoolClient.userPoolClientId,
      description: 'Cognito App Client ID',
    });

    new cdk.CfnOutput(this, 'CognitoSAMLMetadata', {
      value: `https://cognito-idp.us-east-2.amazonaws.com/${userPool.userPoolId}/saml2/metadata`,
      description: 'Cognito SAML Metadata URL (provide to IdentityServer4)',
    });
  }
}
```

**Deploy the updated stack**:
```bash
cd /path/to/ui-backend-cdk
npm install
cdk diff  # Review changes
cdk deploy
```

---

##### Step 2.2: Configure via AWS Console (Alternative)

If you don't have access to CDK code or prefer console:

**Step 2.2.1: Add SAML Identity Provider**

1. Navigate to: https://console.aws.amazon.com/cognito/v2/idp/user-pools
2. Select User Pool: `us-east-2_HJtK36MHO`
3. Click **Sign-in experience** tab
4. Scroll to **Federated identity provider sign-in**
5. Click **Add identity provider**
6. Select **SAML**
7. Configure:
   - **Provider name**: `CompanySSO` (use this exact name)
   - **Metadata document**: Upload `identityserver4-saml-metadata.xml`
   - Or **Metadata document endpoint URL**: `https://your-identityserver4.company.com/.well-known/saml/metadata`
8. Click **Add identity provider**

**Step 2.2.2: Configure Attribute Mapping**

1. After adding provider, click on **CompanySSO**
2. Scroll to **Attribute mapping**
3. Add mappings:

| SAML attribute | User pool attribute |
|----------------|---------------------|
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` | Email |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname` | Given name |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname` | Family name |
| `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name` | Name |

4. Click **Save changes**

**Step 2.2.3: Update App Client**

1. Go to **App integration** tab
2. Scroll to **App clients and analytics**
3. Click on your app client (Client ID: `7s84oe77h699j77oc6m8cbvogt`)
4. Click **Edit** in **Hosted UI settings**
5. Update:
   - **Identity providers**: Check **CompanySSO** (uncheck Cognito user pool if you want SSO-only)
   - **Allowed callback URLs**: Add `https://main.d3althp551dv7h.amplifyapp.com/callback`
   - **Allowed sign-out URLs**: Add `https://main.d3althp551dv7h.amplifyapp.com/logout`
   - **OAuth 2.0 grant types**: Check **Authorization code grant** and **Implicit grant**
   - **OpenID Connect scopes**: Check **openid**, **email**, **profile**
6. Click **Save changes**

**Step 2.2.4: Get Cognito SAML Metadata**

You need to provide this to your IdentityServer4 admin:

**Cognito SAML Metadata URL**:
```
https://cognito-idp.us-east-2.amazonaws.com/us-east-2_HJtK36MHO/saml2/metadata
```

**Download it**:
```bash
curl -o cognito-saml-metadata.xml \
  https://cognito-idp.us-east-2.amazonaws.com/us-east-2_HJtK36MHO/saml2/metadata
```

**Send this file to your IdentityServer4 admin** to complete the two-way trust.

---

##### Step 2.3: Configure IdentityServer4 with Cognito Metadata

**Provide to IdentityServer4 admin**:
- Cognito SAML Metadata URL or XML file
- Entity ID: `urn:amazon:cognito:sp:us-east-2_HJtK36MHO`
- Assertion Consumer Service (ACS) URL: `https://pdf-ui-auth1rc16k.auth.us-east-2.amazoncognito.com/saml2/idpresponse`

---

#### **Phase 3: Update Environment Variables** (1 hour)

Update all references in documentation and deployment files:

##### File 1: `_AWS_RESOURCES.md`

**Current** (Lines 198-218):
```markdown
### AWS Cognito

**User Pool**:
- **ID**: `us-east-2_HJtK36MHO`
- **Name**: Auto-generated by CDK
- **App Client ID**: `7s84oe77h699j77oc6m8cbvogt`
- **Domain**: `pdf-ui-auth1rc16k`
- **Purpose**: User authentication and management

**User Pool Features**:
- Email-based authentication
- Email verification required
- Password complexity requirements
- Multi-factor authentication (optional)
- User attributes: email, name, custom fields
```

**Update to**:
```markdown
### AWS Cognito

**User Pool**:
- **ID**: `us-east-2_HJtK36MHO`
- **Name**: Auto-generated by CDK
- **App Client ID**: `7s84oe77h699j77oc6m8cbvogt`
- **Domain**: `pdf-ui-auth1rc16k`
- **Purpose**: User authentication via Company SSO (IdentityServer4)

**Authentication Method**:
- **Primary**: SAML Federation with IdentityServer4
- **IdP**: Company IdentityServer4 (https://your-identityserver4.company.com)
- **Protocol**: SAML 2.0

**User Pool Features**:
- SSO via IdentityServer4 (SAML)
- No self-signup (SSO users only)
- Automatic user provisioning from SAML assertions
- User attributes: email, given_name, family_name, name
- Session management via Cognito
```

---

##### File 2: `_DEPLOYMENT_SUMMARY.md`

**Update** (Lines 49-76):
```markdown
### 2. Backend API & Authentication

**AWS Cognito Configuration**:
- **User Pool ID**: `us-east-2_HJtK36MHO`
- **User Pool Client ID**: `7s84oe77h699j77oc6m8cbvogt`
- **User Pool Domain**: `pdf-ui-auth1rc16k`
- **Identity Pool ID**: `us-east-2:c0f78434-f184-465f-8adb-ff2675227da2`
- **Authenticated Role**: `arn:aws:iam::471414695760:role/CdkBackendStack-CognitoDefaultAuthenticatedRoleC5D5-uIO7y0rrWVVH`
- **Authentication Method**: SAML Federation with Company IdentityServer4

**SSO Configuration**:
- **Identity Provider**: IdentityServer4
- **Provider Name**: CompanySSO
- **Protocol**: SAML 2.0
- **SSO URL**: https://your-identityserver4.company.com/saml/sso
- **Metadata URL**: https://your-identityserver4.company.com/.well-known/saml/metadata

**User Pool Features**:
- Single Sign-On (SSO) with company credentials
- Automatic user provisioning
- No email/password signup (SSO users only)
```

---

##### File 3: `cleanup.sh`

Ensure SAML provider is cleaned up when deleting resources:

```bash
#!/bin/bash

# ... existing cleanup code ...

# Delete SAML Identity Provider from Cognito
echo "Removing SAML Identity Provider from Cognito..."
aws cognito-idp describe-identity-provider \
  --user-pool-id us-east-2_HJtK36MHO \
  --provider-name CompanySSO \
  --region us-east-2 >/dev/null 2>&1

if [ $? -eq 0 ]; then
  aws cognito-idp delete-identity-provider \
    --user-pool-id us-east-2_HJtK36MHO \
    --provider-name CompanySSO \
    --region us-east-2
  echo "✓ SAML provider removed"
else
  echo "✓ SAML provider not found (already deleted)"
fi

# ... rest of cleanup code ...
```

---

#### **Phase 4: Frontend Integration** (6 hours)

Now update the React frontend to use SSO instead of email/password login.

**Repository**: https://github.com/a-fedosenko/PDF_accessability_UI

---

##### Step 4.1: Clone and Setup Frontend

```bash
# Clone the repository
git clone https://github.com/a-fedosenko/PDF_accessability_UI.git
cd PDF_accessability_UI

# Install dependencies
npm install

# Install AWS Amplify (if not already installed)
npm install aws-amplify @aws-amplify/ui-react
```

---

##### Step 4.2: Configure AWS Amplify

**Create or update**: `src/aws-exports.js` or `src/config/amplify.js`

```javascript
// src/aws-exports.js
const awsconfig = {
  Auth: {
    region: 'us-east-2',
    userPoolId: 'us-east-2_HJtK36MHO',
    userPoolWebClientId: '7s84oe77h699j77oc6m8cbvogt',

    // Cognito Hosted UI configuration
    oauth: {
      domain: 'pdf-ui-auth1rc16k.auth.us-east-2.amazoncognito.com',
      scope: ['openid', 'email', 'profile'],
      redirectSignIn: 'https://main.d3althp551dv7h.amplifyapp.com',
      redirectSignOut: 'https://main.d3althp551dv7h.amplifyapp.com/logout',
      responseType: 'code', // Authorization code grant
    }
  },

  // S3 bucket (if used for direct uploads)
  Storage: {
    AWSS3: {
      bucket: 'pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc',
      region: 'us-east-2',
    }
  },

  // API Gateway endpoints
  API: {
    endpoints: [
      {
        name: 'PDFAccessibilityAPI',
        endpoint: 'https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod',
        region: 'us-east-2',
      }
    ]
  }
};

export default awsconfig;
```

---

##### Step 4.3: Initialize Amplify in App

**Update**: `src/index.js` or `src/App.js`

```javascript
// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import awsconfig from './aws-exports';
import App from './App';
import './index.css';

// Configure Amplify
Amplify.configure(awsconfig);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

---

##### Step 4.4: Create SSO Login Component

**Create**: `src/components/SSOLogin.jsx`

```javascript
import React, { useState, useEffect } from 'react';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';

const SSOLogin = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user is already authenticated
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const user = await Auth.currentAuthenticatedUser();
      if (user) {
        // User is already logged in, redirect to home
        navigate('/');
      }
    } catch (err) {
      // User not logged in, show login button
      console.log('User not authenticated');
    }
  };

  const handleSSOLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // Redirect to IdentityServer4 via Cognito Hosted UI
      await Auth.federatedSignIn({ provider: 'CompanySSO' });

      // Note: User will be redirected away, so this code won't execute
      // After successful login, they'll be redirected back to the app
    } catch (err) {
      console.error('SSO Login failed:', err);
      setError('Failed to initiate SSO login. Please try again.');
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await Auth.signOut();
      navigate('/login');
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <div className="sso-login-container">
      <div className="login-card">
        <h1>PDF Accessibility Solutions</h1>
        <p>Sign in with your company credentials</p>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <button
          onClick={handleSSOLogin}
          disabled={loading}
          className="sso-login-button"
        >
          {loading ? 'Redirecting...' : 'Sign in with Company SSO'}
        </button>

        <p className="help-text">
          You will be redirected to your company's login page
        </p>
      </div>
    </div>
  );
};

export default SSOLogin;
```

---

##### Step 4.5: Update App Router

**Update**: `src/App.js`

```javascript
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Auth } from 'aws-amplify';

import SSOLogin from './components/SSOLogin';
import Dashboard from './components/Dashboard';
import UploadPDF from './components/UploadPDF';
import ProcessingStatus from './components/ProcessingStatus';
import PrivateRoute from './components/PrivateRoute';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const currentUser = await Auth.currentAuthenticatedUser();
      setUser(currentUser);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <Router>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<SSOLogin />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <PrivateRoute user={user}>
              <Dashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/upload"
          element={
            <PrivateRoute user={user}>
              <UploadPDF />
            </PrivateRoute>
          }
        />
        <Route
          path="/status"
          element={
            <PrivateRoute user={user}>
              <ProcessingStatus />
            </PrivateRoute>
          }
        />

        {/* Redirect to login if no match */}
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;
```

---

##### Step 4.6: Create Private Route Component

**Create**: `src/components/PrivateRoute.jsx`

```javascript
import React from 'react';
import { Navigate } from 'react-router-dom';

const PrivateRoute = ({ user, children }) => {
  if (!user) {
    // User not authenticated, redirect to login
    return <Navigate to="/login" replace />;
  }

  // User authenticated, render children
  return children;
};

export default PrivateRoute;
```

---

##### Step 4.7: Remove Old Email/Password Components

**Delete or comment out**:
- Email/password login forms
- Signup forms
- Password reset flows
- Any references to `Auth.signIn(email, password)`
- Any references to `Auth.signUp()`

**Example files to update**:
- `src/components/Login.jsx` → Replace with SSOLogin
- `src/components/Signup.jsx` → Delete (no signup with SSO)
- `src/components/ForgotPassword.jsx` → Delete (handled by SSO)

---

##### Step 4.8: Update API Calls to Use Auth Tokens

Ensure all API calls include the Cognito auth token:

```javascript
// src/services/api.js
import { Auth } from 'aws-amplify';

export const apiCall = async (endpoint, method = 'GET', body = null) => {
  try {
    // Get current session and auth token
    const session = await Auth.currentSession();
    const token = session.getIdToken().getJwtToken();

    const response = await fetch(
      `${process.env.REACT_APP_API_ENDPOINT}${endpoint}`,
      {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: body ? JSON.stringify(body) : null,
      }
    );

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API call error:', error);
    throw error;
  }
};

// Example usage:
export const checkUploadQuota = async () => {
  return await apiCall('/upload-quota', 'GET');
};

export const uploadPDF = async (file) => {
  // For file uploads, you might use S3 directly via Amplify Storage
  // Or multipart/form-data to API Gateway
};
```

---

##### Step 4.9: Test Locally

```bash
# Start local development server
npm start

# App should open at http://localhost:3000
# Click "Sign in with Company SSO"
# You should be redirected to IdentityServer4
```

**Note**: For local testing, update:
1. IdentityServer4 redirect URIs to include `http://localhost:3000`
2. Cognito app client callback URLs to include `http://localhost:3000`

---

##### Step 4.10: Build and Deploy

```bash
# Build production version
npm run build

# Commit changes
git add .
git commit -m "Integrate IdentityServer4 SSO authentication"
git push origin main

# If CI/CD is enabled, Amplify will auto-build and deploy
# Otherwise, manually deploy via Amplify console
```

---

#### **Phase 5: Testing & Validation** (6 hours)

**Test Plan**:

##### **5.1: SAML Metadata Validation** (30 min)

```bash
# Test IdentityServer4 metadata
curl https://your-identityserver4.company.com/.well-known/saml/metadata

# Test Cognito metadata
curl https://cognito-idp.us-east-2.amazonaws.com/us-east-2_HJtK36MHO/saml2/metadata

# Verify both are accessible and valid XML
```

---

##### **5.2: SSO Login Flow** (1 hour)

**Test Case 1: Initial Login**
1. Navigate to: https://main.d3althp551dv7h.amplifyapp.com
2. Click "Sign in with Company SSO"
3. Verify redirect to IdentityServer4
4. Enter company credentials
5. Verify redirect back to app
6. Check user is authenticated
7. Check user attributes (email, name) are populated

**Test Case 2: Already Authenticated**
1. Close browser (or tab)
2. Reopen: https://main.d3althp551dv7h.amplifyapp.com
3. Verify auto-login (no prompt if session valid)
4. Check user stays authenticated

**Test Case 3: Logout**
1. Click logout in app
2. Verify redirect to IdentityServer4 logout (if SLO configured)
3. Verify redirect back to login page
4. Verify user cannot access protected pages

---

##### **5.3: Token Validation** (1 hour)

```bash
# Get user info after login (via browser console)
# Open DevTools → Console → Run:
```

```javascript
// In browser console
import { Auth } from 'aws-amplify';

// Get current user
Auth.currentAuthenticatedUser().then(user => {
  console.log('User:', user);
  console.log('Username:', user.username);
  console.log('Attributes:', user.attributes);
});

// Get session tokens
Auth.currentSession().then(session => {
  console.log('Access Token:', session.getAccessToken().getJwtToken());
  console.log('ID Token:', session.getIdToken().getJwtToken());
  console.log('Refresh Token:', session.getRefreshToken().getToken());
});
```

**Verify**:
- ID token contains expected claims (email, name, etc.)
- Access token is valid
- Tokens have correct expiration times

---

##### **5.4: API Gateway Authorization** (1 hour)

```bash
# Test API with SSO-issued token
TOKEN="<paste_id_token_from_above>"

# Test upload quota endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod/upload-quota

# Expected: 200 OK with quota data

# Test without token (should fail)
curl https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod/upload-quota

# Expected: 401 Unauthorized
```

---

##### **5.5: End-to-End PDF Processing** (2 hours)

**Full Workflow Test**:
1. Login via SSO
2. Upload a PDF (small test file)
3. Monitor processing status
4. Download remediated PDF
5. Verify accessibility improvements
6. Check CloudWatch logs for errors

```bash
# Monitor Lambda logs
aws logs tail /aws/lambda/PDFAccessibility-SplitPDF* --follow

# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-2:471414695760:stateMachine:MyStateMachine \
  --max-items 5
```

---

##### **5.6: Error Scenarios** (30 min)

**Test Case 1: Invalid Token**
- Modify token in browser storage
- Try to access protected API
- Verify 401 error

**Test Case 2: Expired Session**
- Wait for token expiration (or manually expire)
- Try to access app
- Verify redirect to login

**Test Case 3: IdentityServer4 Down**
- (If possible) temporarily disable IdentityServer4
- Try to login
- Verify graceful error message

**Test Case 4: SAML Assertion Error**
- Check CloudWatch logs for SAML errors
- Verify attribute mapping issues are caught

---

##### **5.7: Rollback Testing** (30 min)

**Prepare rollback plan**:
1. Document current working state
2. Backup Cognito configuration
3. Test rollback procedure:
   - Disable SAML provider in Cognito
   - Re-enable email/password (if needed)
   - Redeploy previous frontend version

**Rollback script**:
```bash
#!/bin/bash
# rollback-sso.sh

echo "Rolling back SSO changes..."

# Disable SAML provider (don't delete, just disable in app client)
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-2_HJtK36MHO \
  --client-id 7s84oe77h699j77oc6m8cbvogt \
  --supported-identity-providers COGNITO \
  --region us-east-2

echo "✓ SAML provider disabled"

# Redeploy previous frontend version
# (Assuming you have tagged releases)
cd PDF_accessability_UI
git checkout <previous_version_tag>
git push origin main --force

echo "✓ Frontend rolled back"
echo "Rollback complete. Test the application."
```

---

#### **Phase 6: Documentation Updates** (2 hours)

Update all project documentation:

##### **File 1: README.md**

Add SSO section:

```markdown
## Authentication

This application uses **Single Sign-On (SSO)** via Company IdentityServer4.

### For Users

1. Navigate to https://main.d3althp551dv7h.amplifyapp.com
2. Click "Sign in with Company SSO"
3. Enter your company credentials
4. You will be redirected back to the app after authentication

### For Administrators

**SSO Configuration**:
- **Identity Provider**: Company IdentityServer4
- **Protocol**: SAML 2.0
- **User Pool**: us-east-2_HJtK36MHO
- **Provider Name**: CompanySSO

**To Update SSO Settings**:
1. Access AWS Cognito Console
2. Navigate to User Pool → Sign-in experience
3. Update SAML identity provider settings
4. Redeploy frontend if callback URLs change
```

---

##### **File 2: User Guide** (Create new)

**Create**: `docs/USER_GUIDE.md`

```markdown
# PDF Accessibility Solutions - User Guide

## Logging In

### Step 1: Access the Application
Navigate to: https://main.d3althp551dv7h.amplifyapp.com

### Step 2: Sign In with SSO
1. Click the "Sign in with Company SSO" button
2. You will be redirected to your company's login page
3. Enter your company email and password
4. If multi-factor authentication (MFA) is enabled, complete the MFA challenge
5. You will be automatically redirected back to the application

### Step 3: Start Using the App
Once logged in, you can:
- Upload PDF documents for accessibility remediation
- Monitor processing status
- Download remediated PDFs
- View accessibility reports

## Uploading PDFs

1. Click "Upload PDF" in the main menu
2. Select a PDF file from your computer
3. (Optional) Add notes or preferences
4. Click "Submit"
5. Processing will begin automatically

**Note**: There are no file size or page limits.

## Monitoring Processing

1. Navigate to "Processing Status"
2. View the status of your uploaded PDFs:
   - **Pending**: Waiting to be processed
   - **Processing**: Currently being remediated
   - **Completed**: Ready for download
   - **Failed**: Processing error (contact support)

## Downloading Results

1. Go to "Processing Status"
2. Find your completed PDF
3. Click "Download"
4. The remediated PDF will be saved to your Downloads folder
5. File name will have "COMPLIANT_" prefix

## Troubleshooting

### Cannot Login
- Verify you're using your company credentials
- Check with IT if your account is active
- Clear browser cache and try again

### Upload Failed
- Check your internet connection
- Verify the file is a valid PDF
- Try uploading again

### Processing Takes Too Long
- Large PDFs may take 10-15 minutes
- Check "Processing Status" for updates
- Contact support if stuck for >30 minutes

## Support

For technical support, contact:
- Email: ai-cic@amazon.com
- Internal IT Help Desk: ext. XXXX
```

---

##### **File 3: Admin Guide** (Create new)

**Create**: `docs/ADMIN_GUIDE_SSO.md`

```markdown
# SSO Administration Guide

## Overview

PDF Accessibility Solutions uses AWS Cognito federated with Company IdentityServer4 via SAML 2.0.

## Architecture

```
User → IdentityServer4 (IdP) → AWS Cognito (SP) → API Gateway → Lambda/ECS
```

## SSO Configuration Details

### IdentityServer4 Configuration
- **Client ID**: aws-cognito-pdf-accessibility
- **Entity ID**: https://your-identityserver4.company.com
- **SSO URL**: https://your-identityserver4.company.com/saml/sso
- **Metadata**: https://your-identityserver4.company.com/.well-known/saml/metadata

### AWS Cognito Configuration
- **User Pool ID**: us-east-2_HJtK36MHO
- **App Client ID**: 7s84oe77h699j77oc6m8cbvogt
- **Provider Name**: CompanySSO
- **Entity ID**: urn:amazon:cognito:sp:us-east-2_HJtK36MHO
- **ACS URL**: https://pdf-ui-auth1rc16k.auth.us-east-2.amazoncognito.com/saml2/idpresponse

### Attribute Mapping
| SAML Attribute | Cognito Attribute |
|----------------|-------------------|
| emailaddress   | email             |
| givenname      | given_name        |
| surname        | family_name       |
| name           | name              |

## Common Administrative Tasks

### Add New User
Users are automatically provisioned on first login via SSO.
No manual user creation needed in Cognito.

### Revoke User Access
Remove user from IdentityServer4. Their Cognito session will expire within 1 hour.

### Update SAML Metadata
If IdentityServer4 metadata changes:
1. Download new metadata XML
2. AWS Console → Cognito → User Pools → us-east-2_HJtK36MHO
3. Sign-in experience → CompanySSO → Edit
4. Upload new metadata
5. Save changes

### View Active Sessions
```bash
aws cognito-idp admin-list-user-auth-events \
  --user-pool-id us-east-2_HJtK36MHO \
  --username <user_email> \
  --region us-east-2
```

### Force User Logout
```bash
aws cognito-idp admin-user-global-sign-out \
  --user-pool-id us-east-2_HJtK36MHO \
  --username <user_email> \
  --region us-east-2
```

## Monitoring

### CloudWatch Logs
- **Cognito Authentication Events**: CloudWatch → Log Groups → aws/cognito/userpools/
- **SAML Errors**: Filter for "SAML" in logs

### Metrics to Monitor
- Login success rate
- Failed authentication attempts
- Token refresh failures
- API 401 errors

## Troubleshooting

### User Cannot Login
1. Verify user exists in IdentityServer4
2. Check Cognito logs for SAML errors
3. Verify attribute mapping is correct
4. Test SAML metadata URLs are accessible

### "Invalid SAML Response" Error
- SAML assertion expired (time sync issue)
- Certificate mismatch (check signing cert)
- Attribute mapping incorrect

### Tokens Not Working
- Check token expiration times
- Verify API Gateway authorizer configuration
- Check IAM roles for authenticated users

## Security Best Practices

1. **Rotate SAML Signing Certificates** annually
2. **Monitor Failed Login Attempts** (potential breach)
3. **Enable CloudTrail** for Cognito API calls
4. **Review IAM Policies** quarterly
5. **Test Disaster Recovery** procedure monthly

## Disaster Recovery

### Backup
- Export Cognito configuration (AWS CLI)
- Backup SAML metadata files
- Document all settings in this guide

### Restore
```bash
# Re-create Cognito User Pool (if deleted)
# Re-configure SAML provider
# Update frontend with new User Pool ID
```

## Contact

**Primary Admin**: [Your Name] (email@company.com)
**Backup Admin**: [Backup Name] (backup@company.com)
**IdentityServer4 Team**: sso-team@company.com
**AWS Support**: https://console.aws.amazon.com/support/
```

---

## Combined Implementation Timeline

### Week 1: Remove Limits
| Day | Task | Hours | Owner | Status |
|-----|------|-------|-------|--------|
| Mon | Backend limit removal | 2 | Backend Dev | Pending |
| Mon | Infrastructure updates (CDK/Console) | 2 | DevOps | Pending |
| Tue | Frontend validation removal | 2 | Frontend Dev | Pending |
| Tue | Testing and validation | 2 | QA | Pending |
| **Total** | | **8 hours** | | |

### Week 2: IdentityServer4 Integration
| Day | Task | Hours | Owner | Status |
|-----|------|-------|-------|--------|
| Mon | IdentityServer4 SAML setup | 4 | SSO Admin | Pending |
| Tue | Cognito User Pool config | 4 | DevOps | Pending |
| Wed | Cognito User Pool config (cont.) | 4 | DevOps | Pending |
| Thu | Frontend integration | 6 | Frontend Dev | Pending |
| Fri | Testing & validation | 6 | QA + Team | Pending |
| Fri | Documentation updates | 2 | Tech Writer | Pending |
| **Total** | | **26 hours** | | |

**Combined Total: 34 hours (~1.5 weeks)**

---

## Risk Assessment

### Change 1: Remove Limits

| Risk | Level | Impact | Mitigation |
|------|-------|--------|------------|
| Excessive storage costs | LOW | Medium | Monitor S3 usage, set up billing alerts |
| Lambda timeout on huge files | LOW | Medium | Increase timeout, optimize chunking |
| API Gateway throttling abuse | LOW | Low | CloudWatch alarms, rate limiting per user |
| Processing queue overload | MEDIUM | Medium | Add SQS queue, implement backpressure |

**Overall Risk**: **LOW**
**Rollback Time**: 15 minutes (revert environment variables)

---

### Change 2: SSO Integration

| Risk | Level | Impact | Mitigation |
|------|-------|--------|------------|
| SAML misconfiguration | HIGH | High | Test in dev first, phased rollout |
| Users cannot login | HIGH | High | Keep email/password temporarily, gradual migration |
| IdentityServer4 downtime | MEDIUM | High | Monitor IdP health, communicate outages |
| Token validation failures | MEDIUM | Medium | Comprehensive testing, error logging |
| Session timeout issues | LOW | Low | Configure appropriate token lifetimes |

**Overall Risk**: **MEDIUM**
**Rollback Time**: 30 minutes (disable SAML provider, redeploy frontend)

---

### Mitigation Strategies

1. **Test in Development First**
   - Deploy to dev/staging environment
   - Test with pilot users
   - Monitor logs for errors

2. **Gradual Rollout**
   - Enable SSO for test users first (10%)
   - Monitor for 48 hours
   - Gradually increase to 50%, then 100%

3. **Dual Authentication (Temporary)**
   - Keep Cognito email/password enabled during transition
   - Allow users to choose auth method
   - Disable email/password after 2 weeks of stable SSO

4. **Monitoring & Alerting**
   - CloudWatch alarms for authentication failures
   - SNS notifications for critical errors
   - Dashboard for real-time SSO health

5. **Communication Plan**
   - Email users 1 week before SSO switch
   - Provide user guide and training
   - Announce maintenance window

6. **Rollback Plan**
   - Document current state before changes
   - Test rollback procedure
   - Keep previous frontend version tagged in Git
   - Have runbook ready for emergency rollback

---

## Pre-Implementation Checklist

### For Limit Removal:

**Technical Prerequisites**:
- [ ] AWS CLI configured and tested
- [ ] Access to AWS Console (Lambda, API Gateway, S3)
- [ ] Access to frontend repository
- [ ] CDK or CloudFormation access (if using IaC)

**Testing Prerequisites**:
- [ ] Large test PDF files (>25MB, >100 pages)
- [ ] Load testing tools installed (optional)
- [ ] Monitoring dashboard access

**Operational Prerequisites**:
- [ ] Backup of current configuration
- [ ] S3 storage budget approved
- [ ] Billing alerts configured
- [ ] Stakeholder approval for unlimited uploads

---

### For SSO Integration:

**Access & Credentials**:
- [ ] IdentityServer4 admin credentials
- [ ] AWS Cognito admin access
- [ ] Frontend repository write access
- [ ] Test user accounts in IdentityServer4

**Technical Prerequisites**:
- [ ] SAML metadata URL from IdentityServer4
- [ ] IdentityServer4 SAML plugin installed
- [ ] SSL certificates valid and not expiring soon
- [ ] Network connectivity between IdentityServer4 and AWS

**Documentation**:
- [ ] IdentityServer4 SAML configuration documented
- [ ] Current Cognito configuration exported
- [ ] User communication plan drafted
- [ ] Rollback procedure documented

**Approvals**:
- [ ] Security team approval for SSO integration
- [ ] Legal/compliance review (if required)
- [ ] IT leadership approval
- [ ] User notification sent (1 week before)

**Testing Environment**:
- [ ] Dev/staging environment available
- [ ] Separate Cognito User Pool for testing (optional)
- [ ] Test users with SSO accounts
- [ ] Pilot user group identified (5-10 users)

---

## Next Steps

### Immediate Actions (This Week):

1. **Review this document** with the team (30 min)
2. **Get approvals** from stakeholders (2 days)
3. **Access credentials and repositories** (1 day)
4. **Set up testing environment** (1 day)

---

### Implementation Order:

#### Option A: Sequential (Safer)
1. Week 1: Remove limits
2. Week 2: Test limits removal in production
3. Week 3: Implement SSO in dev/staging
4. Week 4: Roll out SSO to production

**Total Time**: 4 weeks

---

#### Option B: Parallel (Faster)
1. Week 1: Remove limits + Start IdentityServer4 setup
2. Week 2: Test limits + Complete Cognito configuration
3. Week 3: Frontend SSO integration + Testing
4. Week 4: Production rollout

**Total Time**: 3 weeks

---

### Recommended Approach: **Option A (Sequential)**

**Reasoning**:
- Lower risk (changes isolated)
- Easier to troubleshoot issues
- Less coordination required
- Users adapt to one change at a time

---

### Next Decision Points:

**For You to Decide**:
1. Which implementation order? (Sequential or Parallel)
2. When to start? (This week or next week?)
3. Who will be the technical owners for each phase?
4. What is the pilot user group for SSO testing?

**For Me to Help With**:
1. Start implementing limit removal?
2. Create CDK code for SSO integration?
3. Generate detailed test scripts?
4. Help with IdentityServer4 configuration?
5. Review and modify frontend code?

---

## Quick Reference Commands

### Check Current Configuration

```bash
# Cognito User Pool info
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-2_HJtK36MHO \
  --region us-east-2

# API Gateway throttling settings
aws apigateway get-stage \
  --rest-api-id 6597iy1nhi \
  --stage-name prod \
  --region us-east-2

# Lambda configuration
aws lambda get-function-configuration \
  --function-name PDFAccessibility-SplitPDF* \
  --region us-east-2

# Check SAML provider (if exists)
aws cognito-idp describe-identity-provider \
  --user-pool-id us-east-2_HJtK36MHO \
  --provider-name CompanySSO \
  --region us-east-2
```

---

### Monitoring Commands

```bash
# Watch Lambda logs
aws logs tail /aws/lambda/PDFAccessibility-SplitPDF* --follow

# Check API Gateway requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=CdkBackendStack-API \
  --start-time 2025-11-17T00:00:00Z \
  --end-time 2025-11-17T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Check Cognito authentication events
aws cognito-idp admin-list-user-auth-events \
  --user-pool-id us-east-2_HJtK36MHO \
  --username user@example.com \
  --max-results 10 \
  --region us-east-2
```

---

### Emergency Rollback

```bash
# Disable SAML (emergency)
aws cognito-idp update-user-pool-client \
  --user-pool-id us-east-2_HJtK36MHO \
  --client-id 7s84oe77h699j77oc6m8cbvogt \
  --supported-identity-providers COGNITO \
  --region us-east-2

# Revert Lambda env vars
aws lambda update-function-configuration \
  --function-name PDFAccessibility-SplitPDF* \
  --environment Variables="{MAX_PAGES_PER_PDF=1000,PDF_CHUNK_SIZE=10}" \
  --region us-east-2

# Redeploy previous frontend
cd PDF_accessability_UI
git revert HEAD
git push origin main --force
```

---

## Support & Contacts

**Project Team**:
- **Project Lead**: [Your Name]
- **Backend Developer**: [Backend Dev]
- **Frontend Developer**: [Frontend Dev]
- **DevOps Engineer**: [DevOps]
- **QA Engineer**: [QA]

**External Dependencies**:
- **IdentityServer4 Admin**: sso-team@company.com
- **AWS Support**: https://console.aws.amazon.com/support/
- **Security Team**: security@company.com

**Documentation**:
- **GitHub Repository**: https://github.com/a-fedosenko/PDF_Accessibility
- **UI Repository**: https://github.com/a-fedosenko/PDF_accessability_UI
- **AWS Console**: https://console.aws.amazon.com (us-east-2)

---

## Appendix: Detailed File Locations

### Backend Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `pdf2html/content_accessibility_utility_on_aws/remediate/services/bedrock_client.py` | Increase MAX_IMAGE_SIZE to 20MB | HIGH |
| `.env` | Update MAX_PAGES_PER_PDF and PDF_CHUNK_SIZE | HIGH |
| `.env.example` | Update MAX_PAGES_PER_PDF and PDF_CHUNK_SIZE | MEDIUM |
| `app.py` (or CDK stack) | Increase Lambda memory and API Gateway throttling | HIGH |

### Frontend Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `src/components/Upload.jsx` | Remove file size validation | HIGH |
| `src/components/Upload.jsx` | Remove upload quota check | HIGH |
| `src/utils/validation.js` | Remove page count validation | MEDIUM |
| `src/services/api.js` | Update/remove quota API calls | MEDIUM |
| `src/config/constants.js` | Update limit constants | LOW |
| `src/components/SSOLogin.jsx` | Create new SSO login component | HIGH |
| `src/aws-exports.js` | Configure Amplify with SAML | HIGH |
| `src/App.js` | Update routing for SSO | HIGH |

### Documentation Files to Update

| File | Change | Priority |
|------|--------|----------|
| `_AWS_RESOURCES.md` | Update Cognito section with SSO info | HIGH |
| `_DEPLOYMENT_SUMMARY.md` | Update authentication instructions | HIGH |
| `README.md` | Add SSO section | MEDIUM |
| `cleanup.sh` | Add SAML provider cleanup | MEDIUM |
| `docs/USER_GUIDE.md` | Create new user guide for SSO | HIGH |
| `docs/ADMIN_GUIDE_SSO.md` | Create new admin guide | HIGH |

---

**Document Version**: 1.0
**Last Updated**: November 17, 2025
**Maintained By**: PDF Accessibility Solutions Team

---

**Ready to start implementation? Let me know which phase you'd like to begin with!**
