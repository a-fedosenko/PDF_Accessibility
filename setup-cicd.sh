#!/bin/bash

# ========================================================================
# PDF Accessibility Solutions - CI/CD Setup Script
# ========================================================================
# This script sets up continuous deployment for the UI from GitHub
# ========================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${CYAN}$1${NC}"; }

echo ""
print_header "🔄 PDF Accessibility Solutions - CI/CD Setup"
print_header "=============================================="
echo ""

# Configuration
REGION="us-east-2"
AMPLIFY_APP_ID="d3althp551dv7h"
BRANCH_NAME="main"

# Get GitHub repository from user
echo ""
print_status "Current Amplify App ID: $AMPLIFY_APP_ID"
print_status "Branch: $BRANCH_NAME"
echo ""

# Check if we need GitHub token
print_header "Step 1: GitHub Repository Configuration"
echo ""
print_status "Your forked repository: https://github.com/a-fedosenko/PDF_accessability_UI"
echo ""

read -p "Is this the correct repository? (y/n): " CONFIRM_REPO

if [ "$CONFIRM_REPO" != "y" ]; then
    read -p "Enter your GitHub repository URL: " GITHUB_REPO
else
    GITHUB_REPO="https://github.com/a-fedosenko/PDF_accessability_UI"
fi

echo ""
print_header "Step 2: GitHub Personal Access Token"
echo ""
print_warning "To enable CI/CD, AWS Amplify needs access to your GitHub repository."
echo ""
echo "You need to create a GitHub Personal Access Token with these permissions:"
echo "  • repo (Full control of private repositories)"
echo "  • admin:repo_hook (Read/write repository hooks)"
echo ""
echo "To create a token:"
echo "  1. Go to: https://github.com/settings/tokens"
echo "  2. Click 'Generate new token' → 'Generate new token (classic)'"
echo "  3. Give it a name: 'AWS Amplify CI/CD'"
echo "  4. Select scopes: 'repo' and 'admin:repo_hook'"
echo "  5. Click 'Generate token'"
echo "  6. Copy the token (you won't see it again!)"
echo ""
read -sp "Enter your GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    print_error "GitHub token is required. Exiting."
    exit 1
fi

echo ""
print_header "Step 3: Connecting GitHub Repository to Amplify"
echo ""

# Update Amplify app to connect to GitHub
print_status "Updating Amplify app configuration..."

# First, update the app's repository
aws amplify update-app \
    --app-id "$AMPLIFY_APP_ID" \
    --region "$REGION" \
    --repository "$GITHUB_REPO" \
    --access-token "$GITHUB_TOKEN" \
    --enable-auto-branch-creation \
    --auto-branch-creation-patterns "main" "develop" "feature/*" \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "✅ Repository connected successfully"
else
    print_warning "⚠️  Repository connection may have failed (check if already connected)"
fi

echo ""
print_header "Step 4: Enabling Auto-Build on Main Branch"
echo ""

# Enable auto-build on main branch
print_status "Enabling automatic builds on push to $BRANCH_NAME..."

aws amplify update-branch \
    --app-id "$AMPLIFY_APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --region "$REGION" \
    --enable-auto-build \
    --enable-notification \
    --enable-pull-request-preview \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "✅ Auto-build enabled for $BRANCH_NAME branch"
else
    print_error "❌ Failed to enable auto-build"
    exit 1
fi

echo ""
print_header "Step 5: Creating Webhook"
echo ""

# Create webhook
print_status "Creating GitHub webhook for automatic deployments..."

WEBHOOK_RESULT=$(aws amplify create-webhook \
    --app-id "$AMPLIFY_APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --region "$REGION" \
    --output json 2>/dev/null)

if [ $? -eq 0 ]; then
    WEBHOOK_URL=$(echo "$WEBHOOK_RESULT" | jq -r '.webhook.webhookUrl')
    print_success "✅ Webhook created successfully"
    echo ""
    print_status "Webhook URL: $WEBHOOK_URL"
else
    print_warning "⚠️  Webhook may already exist or creation failed"
fi

echo ""
print_header "Step 6: Testing CI/CD Setup"
echo ""

# Get current branch info
BRANCH_INFO=$(aws amplify get-branch \
    --app-id "$AMPLIFY_APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --region "$REGION" \
    --output json)

AUTO_BUILD=$(echo "$BRANCH_INFO" | jq -r '.branch.enableAutoBuild')

if [ "$AUTO_BUILD" = "true" ]; then
    print_success "✅ CI/CD is now enabled!"
else
    print_error "❌ CI/CD setup failed"
    exit 1
fi

echo ""
print_header "📊 CI/CD Configuration Summary"
print_header "================================"
echo ""
print_success "✅ Repository: $GITHUB_REPO"
print_success "✅ Branch: $BRANCH_NAME"
print_success "✅ Auto-build: Enabled"
print_success "✅ Pull request previews: Enabled"
print_success "✅ Notifications: Enabled"
echo ""

print_header "🚀 How to Use CI/CD"
print_header "==================="
echo ""
echo "Now, whenever you push changes to your GitHub repository:"
echo ""
echo "1. Make changes to your UI code locally:"
echo "   cd /path/to/PDF_accessability_UI"
echo "   # Edit your React files"
echo ""
echo "2. Commit and push to GitHub:"
echo "   git add ."
echo "   git commit -m \"Update UI\""
echo "   git push origin main"
echo ""
echo "3. Amplify will automatically:"
echo "   • Detect the push via webhook"
echo "   • Start a new build"
echo "   • Deploy the changes to: https://main.d3althp551dv7h.amplifyapp.com"
echo ""
echo "4. Monitor the build:"
echo "   • AWS Console: https://console.aws.amazon.com/amplify/home?region=us-east-2#/d3althp551dv7h"
echo "   • Or run: aws amplify list-jobs --app-id $AMPLIFY_APP_ID --branch-name $BRANCH_NAME --region $REGION"
echo ""

print_header "📝 Additional Configuration"
print_header "==========================="
echo ""
echo "View build logs:"
echo "  aws amplify get-job --app-id $AMPLIFY_APP_ID --branch-name $BRANCH_NAME --job-id <JOB_ID> --region $REGION"
echo ""
echo "Trigger manual build:"
echo "  aws amplify start-job --app-id $AMPLIFY_APP_ID --branch-name $BRANCH_NAME --job-type RELEASE --region $REGION"
echo ""
echo "Disable auto-build:"
echo "  aws amplify update-branch --app-id $AMPLIFY_APP_ID --branch-name $BRANCH_NAME --no-enable-auto-build --region $REGION"
echo ""

print_success "🎉 CI/CD setup complete!"
echo ""

# Optional: Trigger a test build
echo ""
read -p "Would you like to trigger a test build now? (y/n): " TRIGGER_BUILD

if [ "$TRIGGER_BUILD" = "y" ]; then
    print_status "Triggering test build..."

    BUILD_RESULT=$(aws amplify start-job \
        --app-id "$AMPLIFY_APP_ID" \
        --branch-name "$BRANCH_NAME" \
        --job-type RELEASE \
        --region "$REGION" \
        --output json)

    if [ $? -eq 0 ]; then
        JOB_ID=$(echo "$BUILD_RESULT" | jq -r '.jobSummary.jobId')
        print_success "✅ Build started! Job ID: $JOB_ID"
        echo ""
        print_status "Monitor build progress:"
        echo "  https://console.aws.amazon.com/amplify/home?region=us-east-2#/d3althp551dv7h/main/$JOB_ID"
    else
        print_error "❌ Failed to start build"
    fi
fi

echo ""
print_status "Setup complete!"
echo ""

exit 0
