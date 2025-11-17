# CI/CD Setup Guide for PDF Accessibility Solutions

This guide explains how to set up continuous integration and continuous deployment (CI/CD) for the PDF Accessibility Solutions UI.

---

## Overview

Currently, your UI is deployed but **not automatically updated** when you push changes to GitHub. This guide will help you enable automatic deployments.

**Current Status**:
- ✅ Amplify App Deployed: https://main.d3althp551dv7h.amplifyapp.com
- ❌ Auto-build: Disabled
- ❌ GitHub webhook: Not configured

**After CI/CD Setup**:
- ✅ Amplify App Deployed: https://main.d3althp551dv7h.amplifyapp.com
- ✅ Auto-build: Enabled
- ✅ GitHub webhook: Configured
- ✅ Automatic deployments on every `git push`

---

## Quick Setup (Automated)

### Option 1: Use the Setup Script

I've created a script that automates the entire CI/CD setup process.

**Prerequisites**:
1. GitHub Personal Access Token (see below for how to create)
2. Fork of the UI repository: https://github.com/a-fedosenko/PDF_accessability_UI

**Steps**:

1. **Create GitHub Personal Access Token**:
   - Go to: https://github.com/settings/tokens
   - Click **"Generate new token"** → **"Generate new token (classic)"**
   - Give it a name: `AWS Amplify CI/CD`
   - Select scopes:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `admin:repo_hook` (Read/write repository hooks)
   - Click **"Generate token"**
   - **Copy the token** (you won't see it again!)

2. **Run the setup script**:
```bash
cd /home/andreyf/projects/PDF_Accessibility
chmod +x setup-cicd.sh
./setup-cicd.sh
```

3. **Follow the prompts**:
   - Confirm your repository URL
   - Paste your GitHub token
   - Optionally trigger a test build

4. **Done!** Your CI/CD is now configured.

---

## Manual Setup (Step-by-Step)

If you prefer to configure CI/CD manually, follow these steps:

### Step 1: Create GitHub Personal Access Token

Same as above (see Option 1, Step 1).

### Step 2: Connect GitHub Repository to Amplify

```bash
# Set your variables
AMPLIFY_APP_ID="d3althp551dv7h"
REGION="us-east-2"
GITHUB_REPO="https://github.com/a-fedosenko/PDF_accessability_UI"
GITHUB_TOKEN="your_token_here"  # Replace with your actual token

# Update Amplify app to connect to GitHub
aws amplify update-app \
    --app-id "$AMPLIFY_APP_ID" \
    --region "$REGION" \
    --repository "$GITHUB_REPO" \
    --access-token "$GITHUB_TOKEN" \
    --enable-auto-branch-creation
```

### Step 3: Enable Auto-Build on Main Branch

```bash
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --enable-auto-build \
    --enable-notification \
    --enable-pull-request-preview
```

### Step 4: Create GitHub Webhook

```bash
aws amplify create-webhook \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2
```

This will return a webhook URL. Save it for reference.

### Step 5: Verify Configuration

```bash
aws amplify get-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --query 'branch.enableAutoBuild'
```

Should return: `true`

---

## Using CI/CD After Setup

### Workflow

Once CI/CD is enabled, your workflow becomes:

```bash
# 1. Clone your forked repository (if not already done)
git clone https://github.com/a-fedosenko/PDF_accessability_UI.git
cd PDF_accessability_UI

# 2. Make your changes
vi src/App.js  # or any other file

# 3. Test locally (optional)
npm install
npm start

# 4. Commit and push
git add .
git commit -m "Update UI: add new feature"
git push origin main

# 5. Amplify automatically:
#    - Detects the push via webhook
#    - Starts a new build
#    - Runs tests (if configured)
#    - Deploys to https://main.d3althp551dv7h.amplifyapp.com
```

### Monitoring Builds

**AWS Console**:
```
https://console.aws.amazon.com/amplify/home?region=us-east-2#/d3althp551dv7h
```

**CLI - List recent builds**:
```bash
aws amplify list-jobs \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --max-results 10
```

**CLI - Get build details**:
```bash
# Replace JOB_ID with the ID from list-jobs
aws amplify get-job \
    --app-id d3althp551dv7h \
    --branch-name main \
    --job-id <JOB_ID> \
    --region us-east-2
```

**CLI - Watch build logs in real-time**:
```bash
# Get the latest job ID
JOB_ID=$(aws amplify list-jobs \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --max-results 1 \
    --query 'jobSummaries[0].jobId' \
    --output text)

# Watch the build
watch -n 5 "aws amplify get-job \
    --app-id d3althp551dv7h \
    --branch-name main \
    --job-id $JOB_ID \
    --region us-east-2 \
    --query 'job.summary.status'"
```

---

## Advanced CI/CD Features

### Manual Trigger

Trigger a build without pushing code:

```bash
aws amplify start-job \
    --app-id d3althp551dv7h \
    --branch-name main \
    --job-type RELEASE \
    --region us-east-2
```

### Environment Variables

Update environment variables without redeploying:

```bash
# Set a new environment variable
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --environment-variables REACT_APP_MY_VAR=my_value

# List all environment variables
aws amplify get-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --query 'branch.environmentVariables'
```

### Multiple Branch Deployments

Deploy different branches for testing:

```bash
# Create a new branch deployment for 'develop'
aws amplify create-branch \
    --app-id d3althp551dv7h \
    --branch-name develop \
    --region us-east-2 \
    --enable-auto-build

# This creates: https://develop.d3althp551dv7h.amplifyapp.com
```

### Pull Request Previews

Pull request previews are already enabled! When you create a PR on GitHub:
1. Amplify automatically creates a preview deployment
2. URL format: `https://pr-<PR_NUMBER>.d3althp551dv7h.amplifyapp.com`
3. Preview is updated with each push to the PR branch
4. Preview is deleted when PR is merged/closed

### Build Notifications

Enable email notifications for build status:

```bash
# Update notification settings
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --enable-notification \
    --notification-arn <SNS_TOPIC_ARN>
```

First, create an SNS topic:
```bash
# Create SNS topic
aws sns create-topic \
    --name amplify-build-notifications \
    --region us-east-2

# Subscribe your email
aws sns subscribe \
    --topic-arn <TOPIC_ARN> \
    --protocol email \
    --notification-endpoint your-email@example.com \
    --region us-east-2
```

---

## Build Configuration

### Custom Build Settings

Your current build uses `buildspec-frontend.yml`. You can customize the build process:

**Location**: In your UI repository root: `buildspec-frontend.yml`

**Current configuration**:
```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

**Common customizations**:

1. **Add tests before build**:
```yaml
preBuild:
  commands:
    - npm ci
    - npm test -- --watchAll=false
```

2. **Add linting**:
```yaml
preBuild:
  commands:
    - npm ci
    - npm run lint
```

3. **Environment-specific builds**:
```yaml
build:
  commands:
    - |
      if [ "$AWS_BRANCH" = "main" ]; then
        npm run build:prod
      else
        npm run build:dev
      fi
```

### Build Performance

**Current build time**: ~3-5 minutes

**Optimization tips**:

1. **Enable caching** (already configured):
```yaml
cache:
  paths:
    - node_modules/**/*
```

2. **Use Amplify's build image cache**:
```bash
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --enable-performance-mode
```

3. **Reduce dependencies**: Remove unused packages from `package.json`

---

## Troubleshooting

### Build Fails After Push

**Check build logs**:
```bash
# Get latest job ID
JOB_ID=$(aws amplify list-jobs \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --max-results 1 \
    --query 'jobSummaries[0].jobId' \
    --output text)

# Get full logs
aws amplify get-job \
    --app-id d3althp551dv7h \
    --branch-name main \
    --job-id $JOB_ID \
    --region us-east-2
```

**Common issues**:

1. **npm install fails**: Check `package.json` for syntax errors
2. **Build fails**: Check React code for compilation errors
3. **Tests fail**: Fix failing tests or disable tests in buildspec

### Auto-Build Not Triggering

**Verify webhook exists**:
```bash
aws amplify list-webhooks \
    --app-id d3althp551dv7h \
    --region us-east-2
```

**Check GitHub webhook**:
1. Go to: https://github.com/a-fedosenko/PDF_accessability_UI/settings/hooks
2. Look for webhook pointing to AWS Amplify
3. Check "Recent Deliveries" for errors

**Re-create webhook**:
```bash
# Delete old webhook
aws amplify delete-webhook \
    --webhook-id <WEBHOOK_ID> \
    --region us-east-2

# Create new webhook
aws amplify create-webhook \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2
```

### Build Takes Too Long

**Increase compute resources**:
```bash
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --build-spec "$(cat <<EOF
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: build
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
compute:
  type: BUILD_GENERAL1_LARGE
EOF
)"
```

---

## Disabling CI/CD

If you need to temporarily disable automatic builds:

```bash
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --no-enable-auto-build
```

To re-enable:
```bash
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2 \
    --enable-auto-build
```

---

## Best Practices

### 1. Branch Strategy

**Recommended workflow**:
- `main` branch → Production (https://main.d3althp551dv7h.amplifyapp.com)
- `develop` branch → Staging (https://develop.d3althp551dv7h.amplifyapp.com)
- `feature/*` branches → PR previews

### 2. Testing Before Deployment

Add automated tests to catch issues before production:

```yaml
# In buildspec-frontend.yml
preBuild:
  commands:
    - npm ci
    - npm test -- --watchAll=false --coverage
```

### 3. Environment Management

Use different environment variables per branch:

```bash
# Production (main branch)
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name main \
    --environment-variables \
        REACT_APP_ENV=production \
        REACT_APP_API_URL=https://api.production.com

# Staging (develop branch)
aws amplify update-branch \
    --app-id d3althp551dv7h \
    --branch-name develop \
    --environment-variables \
        REACT_APP_ENV=staging \
        REACT_APP_API_URL=https://api.staging.com
```

### 4. Rollback Strategy

If a deployment breaks production:

```bash
# List recent builds
aws amplify list-jobs \
    --app-id d3althp551dv7h \
    --branch-name main \
    --region us-east-2

# Redeploy a previous successful build
aws amplify start-job \
    --app-id d3althp551dv7h \
    --branch-name main \
    --job-type RETRY \
    --job-id <PREVIOUS_SUCCESSFUL_JOB_ID> \
    --region us-east-2
```

---

## Summary

**What you get with CI/CD enabled**:
- ✅ Automatic deployments on every push to `main`
- ✅ PR preview environments
- ✅ Build status notifications
- ✅ Rollback capability
- ✅ Environment variable management
- ✅ Build caching for faster deploys

**Time to deployment**: 3-5 minutes after push

**Cost**: Included in Amplify pricing (~$0.01 per build minute + hosting costs)

---

## Quick Reference

**Current Deployment**:
- App ID: `d3althp551dv7h`
- URL: https://main.d3althp551dv7h.amplifyapp.com
- Region: us-east-2
- Repository: https://github.com/a-fedosenko/PDF_accessability_UI

**Useful Commands**:
```bash
# Check auto-build status
aws amplify get-branch --app-id d3althp551dv7h --branch-name main --region us-east-2 --query 'branch.enableAutoBuild'

# Trigger manual build
aws amplify start-job --app-id d3althp551dv7h --branch-name main --job-type RELEASE --region us-east-2

# View latest build status
aws amplify list-jobs --app-id d3althp551dv7h --branch-name main --region us-east-2 --max-results 1

# Open Amplify console
xdg-open "https://console.aws.amazon.com/amplify/home?region=us-east-2#/d3althp551dv7h"
```

---

## Support

For issues or questions:
- AWS Amplify Documentation: https://docs.aws.amazon.com/amplify/
- GitHub Issues: https://github.com/a-fedosenko/PDF_Accessibility/issues
- Email: ai-cic@amazon.com
