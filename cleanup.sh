#!/bin/bash

# ========================================================================
# 🗑️  PDF Accessibility Solutions - Cleanup Script
# ========================================================================
#
# This script will remove ALL AWS resources created during deployment.
# USE WITH CAUTION - This action cannot be undone!
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
print_header "⚠️  PDF Accessibility Solutions - Resource Cleanup ⚠️"
print_header "======================================================="
echo ""
print_warning "This script will DELETE the following resources:"
echo ""
echo "  • CloudFormation Stacks (PDFAccessibility, CdkBackendStack)"
echo "  • S3 Buckets (with all contents)"
echo "  • Amplify Applications"
echo "  • Cognito User Pools"
echo "  • Lambda Functions"
echo "  • ECS Clusters and Task Definitions"
echo "  • Step Functions State Machines"
echo "  • API Gateway APIs"
echo "  • ECR Repositories (with all images)"
echo "  • CloudWatch Log Groups"
echo "  • Secrets Manager Secrets"
echo "  • IAM Roles and Policies"
echo "  • CodeBuild Projects"
echo "  • VPC and Networking Resources"
echo ""
print_error "⚠️  THIS ACTION CANNOT BE UNDONE! ⚠️"
echo ""

# Confirmation prompt
read -p "Are you ABSOLUTELY SURE you want to delete all resources? Type 'DELETE' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE" ]; then
    print_status "Cleanup cancelled. No resources were deleted."
    exit 0
fi

echo ""
print_warning "Final confirmation required!"
read -p "Type your AWS Account ID (471414695760) to proceed: " ACCOUNT_CONFIRM

if [ "$ACCOUNT_CONFIRM" != "471414695760" ]; then
    print_error "Account ID mismatch. Cleanup cancelled for safety."
    exit 1
fi

echo ""
print_status "Starting cleanup process..."
echo ""

# Get AWS region
REGION=$(aws configure get region 2>/dev/null || echo "us-east-2")
print_status "Using region: $REGION"
echo ""

# Track what was deleted
DELETED_RESOURCES=()
FAILED_DELETIONS=()

# ========================================================================
# 1. Delete Amplify Application
# ========================================================================
print_header "🗑️  Step 1: Deleting Amplify Application..."

AMPLIFY_APP_ID="d3althp551dv7h"
if aws amplify get-app --app-id "$AMPLIFY_APP_ID" --region "$REGION" >/dev/null 2>&1; then
    print_status "Deleting Amplify app: $AMPLIFY_APP_ID"
    if aws amplify delete-app --app-id "$AMPLIFY_APP_ID" --region "$REGION" 2>/dev/null; then
        print_success "✅ Amplify app deleted"
        DELETED_RESOURCES+=("Amplify App: $AMPLIFY_APP_ID")
    else
        print_error "❌ Failed to delete Amplify app"
        FAILED_DELETIONS+=("Amplify App: $AMPLIFY_APP_ID")
    fi
else
    print_status "Amplify app not found (may already be deleted)"
fi
echo ""

# ========================================================================
# 2. Delete CloudFormation Stacks
# ========================================================================
print_header "🗑️  Step 2: Deleting CloudFormation Stacks..."

# Delete CdkBackendStack (UI backend)
print_status "Deleting CDK Backend Stack..."
if aws cloudformation describe-stacks --stack-name CdkBackendStack --region "$REGION" >/dev/null 2>&1; then
    aws cloudformation delete-stack --stack-name CdkBackendStack --region "$REGION"
    print_status "Waiting for CdkBackendStack deletion (this may take 5-10 minutes)..."
    if aws cloudformation wait stack-delete-complete --stack-name CdkBackendStack --region "$REGION" 2>/dev/null; then
        print_success "✅ CdkBackendStack deleted"
        DELETED_RESOURCES+=("CloudFormation Stack: CdkBackendStack")
    else
        print_warning "⚠️  CdkBackendStack deletion may have failed or timed out"
        FAILED_DELETIONS+=("CloudFormation Stack: CdkBackendStack")
    fi
else
    print_status "CdkBackendStack not found"
fi

# Delete PDFAccessibility stack (PDF-to-PDF backend)
print_status "Deleting PDF Accessibility Stack..."
if aws cloudformation describe-stacks --stack-name PDFAccessibility --region "$REGION" >/dev/null 2>&1; then
    aws cloudformation delete-stack --stack-name PDFAccessibility --region "$REGION"
    print_status "Waiting for PDFAccessibility deletion (this may take 5-10 minutes)..."
    if aws cloudformation wait stack-delete-complete --stack-name PDFAccessibility --region "$REGION" 2>/dev/null; then
        print_success "✅ PDFAccessibility stack deleted"
        DELETED_RESOURCES+=("CloudFormation Stack: PDFAccessibility")
    else
        print_warning "⚠️  PDFAccessibility deletion may have failed or timed out"
        FAILED_DELETIONS+=("CloudFormation Stack: PDFAccessibility")
    fi
else
    print_status "PDFAccessibility stack not found"
fi
echo ""

# ========================================================================
# 3. Delete S3 Buckets (with all contents)
# ========================================================================
print_header "🗑️  Step 3: Deleting S3 Buckets..."

# Function to empty and delete S3 bucket
delete_s3_bucket() {
    local bucket_name=$1
    if aws s3api head-bucket --bucket "$bucket_name" --region "$REGION" 2>/dev/null; then
        print_status "Emptying bucket: $bucket_name"
        aws s3 rm "s3://$bucket_name" --recursive --region "$REGION" 2>/dev/null || true

        print_status "Deleting bucket: $bucket_name"
        if aws s3api delete-bucket --bucket "$bucket_name" --region "$REGION" 2>/dev/null; then
            print_success "✅ Bucket deleted: $bucket_name"
            DELETED_RESOURCES+=("S3 Bucket: $bucket_name")
        else
            print_warning "⚠️  Failed to delete bucket: $bucket_name (may need manual cleanup)"
            FAILED_DELETIONS+=("S3 Bucket: $bucket_name")
        fi
    else
        print_status "Bucket not found: $bucket_name"
    fi
}

# Delete known buckets
delete_s3_bucket "pdfaccessibility-pdfaccessibilitybucket149b7021e-lubumxxgw8nc"
delete_s3_bucket "pdf2html-bucket-471414695760-$REGION"

# Find and delete any remaining project buckets
print_status "Searching for other project-related buckets..."
for bucket in $(aws s3api list-buckets --query 'Buckets[?contains(Name, `pdfaccessibility`) || contains(Name, `pdf2html`) || contains(Name, `cdkbackendstack`)].Name' --output text 2>/dev/null); do
    delete_s3_bucket "$bucket"
done
echo ""

# ========================================================================
# 4. Delete CodeBuild Projects
# ========================================================================
print_header "🗑️  Step 4: Deleting CodeBuild Projects..."

for project in $(aws codebuild list-projects --region "$REGION" --query 'projects[?contains(@, `pdfremediation`) || contains(@, `pdf-ui`)]' --output text 2>/dev/null); do
    print_status "Deleting CodeBuild project: $project"
    if aws codebuild delete-project --name "$project" --region "$REGION" 2>/dev/null; then
        print_success "✅ Deleted: $project"
        DELETED_RESOURCES+=("CodeBuild Project: $project")
    else
        print_warning "⚠️  Failed to delete: $project"
        FAILED_DELETIONS+=("CodeBuild Project: $project")
    fi
done
echo ""

# ========================================================================
# 5. Delete ECR Repositories
# ========================================================================
print_header "🗑️  Step 5: Deleting ECR Repositories..."

ECR_REPOS=(
    "pdf-autotag"
    "pdf-alttext"
    "pdf2html-lambda"
    "java-lambda"
    "split-pdf-lambda"
    "add-title-lambda"
    "checker-before"
    "checker-after"
)

for repo in "${ECR_REPOS[@]}"; do
    if aws ecr describe-repositories --repository-names "$repo" --region "$REGION" >/dev/null 2>&1; then
        print_status "Deleting ECR repository: $repo"
        if aws ecr delete-repository --repository-name "$repo" --force --region "$REGION" 2>/dev/null; then
            print_success "✅ Deleted: $repo"
            DELETED_RESOURCES+=("ECR Repository: $repo")
        else
            print_warning "⚠️  Failed to delete: $repo"
            FAILED_DELETIONS+=("ECR Repository: $repo")
        fi
    fi
done
echo ""

# ========================================================================
# 6. Delete Secrets Manager Secrets
# ========================================================================
print_header "🗑️  Step 6: Deleting Secrets Manager Secrets..."

if aws secretsmanager describe-secret --secret-id "/myapp/client_credentials" --region "$REGION" >/dev/null 2>&1; then
    print_status "Deleting secret: /myapp/client_credentials"
    if aws secretsmanager delete-secret --secret-id "/myapp/client_credentials" --force-delete-without-recovery --region "$REGION" 2>/dev/null; then
        print_success "✅ Secret deleted"
        DELETED_RESOURCES+=("Secret: /myapp/client_credentials")
    else
        print_warning "⚠️  Failed to delete secret"
        FAILED_DELETIONS+=("Secret: /myapp/client_credentials")
    fi
else
    print_status "Secret not found"
fi
echo ""

# ========================================================================
# 7. Delete CloudWatch Log Groups
# ========================================================================
print_header "🗑️  Step 7: Deleting CloudWatch Log Groups..."

LOG_PATTERNS=(
    "/aws/lambda/PDFAccessibility"
    "/aws/lambda/CdkBackendStack"
    "/ecs/MyFirstTaskDef"
    "/ecs/MySecondTaskDef"
    "/aws/states/MyStateMachine"
    "/aws/codebuild/pdfremediation"
    "/aws/codebuild/pdf-ui"
)

for pattern in "${LOG_PATTERNS[@]}"; do
    for log_group in $(aws logs describe-log-groups --region "$REGION" --log-group-name-prefix "$pattern" --query 'logGroups[].logGroupName' --output text 2>/dev/null); do
        print_status "Deleting log group: $log_group"
        if aws logs delete-log-group --log-group-name "$log_group" --region "$REGION" 2>/dev/null; then
            print_success "✅ Deleted: $log_group"
            DELETED_RESOURCES+=("Log Group: $log_group")
        else
            print_warning "⚠️  Failed to delete: $log_group"
        fi
    done
done
echo ""

# ========================================================================
# 8. Delete IAM Roles and Policies
# ========================================================================
print_header "🗑️  Step 8: Deleting IAM Roles and Policies..."

# Function to delete IAM role with policies
delete_iam_role() {
    local role_name=$1
    if aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
        print_status "Deleting IAM role: $role_name"

        # Detach managed policies
        for policy_arn in $(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null); do
            aws iam detach-role-policy --role-name "$role_name" --policy-arn "$policy_arn" 2>/dev/null || true
        done

        # Delete inline policies
        for policy_name in $(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames[]' --output text 2>/dev/null); do
            aws iam delete-role-policy --role-name "$role_name" --policy-name "$policy_name" 2>/dev/null || true
        done

        # Delete role
        if aws iam delete-role --role-name "$role_name" 2>/dev/null; then
            print_success "✅ Deleted role: $role_name"
            DELETED_RESOURCES+=("IAM Role: $role_name")
        else
            print_warning "⚠️  Failed to delete role: $role_name"
            FAILED_DELETIONS+=("IAM Role: $role_name")
        fi
    fi
}

# Delete CodeBuild service roles
for role in $(aws iam list-roles --query 'Roles[?contains(RoleName, `pdfremediation`) || contains(RoleName, `pdf-ui`)].RoleName' --output text 2>/dev/null); do
    delete_iam_role "$role"
done

# Delete CDK-created roles (pattern-based)
for role in $(aws iam list-roles --query 'Roles[?contains(RoleName, `PDFAccessibility`) || contains(RoleName, `CdkBackendStack`)].RoleName' --output text 2>/dev/null); do
    delete_iam_role "$role"
done

# Delete custom policies
for policy_arn in $(aws iam list-policies --scope Local --query 'Policies[?contains(PolicyName, `pdfremediation`) || contains(PolicyName, `pdf-ui`) || contains(PolicyName, `PDFAccessibility`)].Arn' --output text 2>/dev/null); do
    print_status "Deleting IAM policy: $policy_arn"
    if aws iam delete-policy --policy-arn "$policy_arn" 2>/dev/null; then
        print_success "✅ Deleted policy"
        DELETED_RESOURCES+=("IAM Policy: $policy_arn")
    else
        print_warning "⚠️  Failed to delete policy: $policy_arn"
    fi
done
echo ""

# ========================================================================
# 9. Delete CloudWatch Dashboards
# ========================================================================
print_header "🗑️  Step 9: Deleting CloudWatch Dashboards..."

for dashboard in $(aws cloudwatch list-dashboards --region "$REGION" --query 'DashboardEntries[?contains(DashboardName, `PDF_Processing`)].DashboardName' --output text 2>/dev/null); do
    print_status "Deleting dashboard: $dashboard"
    if aws cloudwatch delete-dashboards --dashboard-names "$dashboard" --region "$REGION" 2>/dev/null; then
        print_success "✅ Deleted: $dashboard"
        DELETED_RESOURCES+=("Dashboard: $dashboard")
    fi
done
echo ""

# ========================================================================
# Summary
# ========================================================================
print_header "📊 Cleanup Summary"
print_header "=================="
echo ""

if [ ${#DELETED_RESOURCES[@]} -gt 0 ]; then
    print_success "✅ Successfully deleted ${#DELETED_RESOURCES[@]} resource(s):"
    for resource in "${DELETED_RESOURCES[@]}"; do
        echo "   • $resource"
    done
    echo ""
fi

if [ ${#FAILED_DELETIONS[@]} -gt 0 ]; then
    print_warning "⚠️  Failed to delete ${#FAILED_DELETIONS[@]} resource(s):"
    for resource in "${FAILED_DELETIONS[@]}"; do
        echo "   • $resource"
    done
    echo ""
    print_warning "Please check these resources manually in AWS Console"
    echo ""
fi

print_header "🔍 Manual Verification Required"
echo ""
echo "Please verify the following in AWS Console:"
echo "  1. VPC and NAT Gateway (may require manual deletion)"
echo "  2. Elastic IPs (check for any unattached IPs)"
echo "  3. Cognito User Pool: us-east-2_HJtK36MHO"
echo "  4. Any remaining Lambda functions"
echo "  5. Any remaining Step Functions state machines"
echo ""

print_status "Cleanup process completed!"
echo ""
print_warning "Note: Some resources may take additional time to fully delete."
print_status "Check AWS Console in 10-15 minutes to verify all resources are removed."
echo ""

exit 0
