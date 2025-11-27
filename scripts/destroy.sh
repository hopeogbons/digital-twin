#!/bin/bash
set -e

# Check if environment parameter is provided
if [ $# -eq 0 ]; then
    echo "❌ Error: Environment parameter is required"
    echo "Usage: $0 <environment>"
    echo "Example: $0 dev"
    echo "Available environments: dev, test, prod"
    exit 1
fi

ENVIRONMENT=$1
PROJECT_NAME=${2:-twin}

echo "🗑️ Preparing to destroy ${PROJECT_NAME}-${ENVIRONMENT} infrastructure..."

# Navigate to terraform directory
cd "$(dirname "$0")/../terraform"

# Check if workspace exists
if ! terraform workspace list | grep -q "$ENVIRONMENT"; then
    echo "❌ Error: Workspace '$ENVIRONMENT' does not exist"
    echo "Available workspaces:"
    terraform workspace list
    exit 1
fi

# Select the workspace
terraform workspace select "$ENVIRONMENT"

echo "📦 Emptying S3 buckets..."

# Get AWS Account ID for bucket names
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get bucket names with account ID
FRONTEND_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-frontend-${AWS_ACCOUNT_ID}"
MEMORY_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-memory-${AWS_ACCOUNT_ID}"

# Empty frontend bucket if it exists
if aws s3 ls "s3://$FRONTEND_BUCKET" 2>/dev/null; then
    echo "  Emptying $FRONTEND_BUCKET..."
    aws s3 rm "s3://$FRONTEND_BUCKET" --recursive
else
    echo "  Frontend bucket not found or already empty"
fi

# Empty memory bucket if it exists
if aws s3 ls "s3://$MEMORY_BUCKET" 2>/dev/null; then
    echo "  Emptying $MEMORY_BUCKET..."
    aws s3 rm "s3://$MEMORY_BUCKET" --recursive
else
    echo "  Memory bucket not found or already empty"
fi

echo "🔥 Running terraform destroy..."

# Run terraform destroy with auto-approve
if [ "$ENVIRONMENT" = "prod" ] && [ -f "prod.tfvars" ]; then
    terraform destroy -var-file=prod.tfvars -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT" -auto-approve
else
    terraform destroy -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT" -auto-approve
fi

echo "✅ Infrastructure for ${ENVIRONMENT} has been destroyed!"
echo ""
echo "💡 To remove the workspace completely, run:"
echo "   terraform workspace select default"
echo "   terraform workspace delete $ENVIRONMENT"
```

Make it executable:
```bash
chmod +x scripts/destroy.sh
```

### Step 2: Create Destroy Script for Windows

Create `scripts/destroy.ps1`:

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Environment,
    [string]$ProjectName = "twin"
)

# Validate environment parameter
if ($Environment -notmatch '^(dev|test|prod)$') {
    Write-Host "Error: Invalid environment '$Environment'" -ForegroundColor Red
    Write-Host "Available environments: dev, test, prod" -ForegroundColor Yellow
    exit 1
}

Write-Host "Preparing to destroy $ProjectName-$Environment infrastructure..." -ForegroundColor Yellow

# Navigate to terraform directory
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) "terraform")

# Check if workspace exists
$workspaces = terraform workspace list
if (-not ($workspaces | Select-String $Environment)) {
    Write-Host "Error: Workspace '$Environment' does not exist" -ForegroundColor Red
    Write-Host "Available workspaces:" -ForegroundColor Yellow
    terraform workspace list
    exit 1
}

# Select the workspace
terraform workspace select $Environment

Write-Host "Emptying S3 buckets..." -ForegroundColor Yellow

# Get AWS Account ID for bucket names
$awsAccountId = aws sts get-caller-identity --query Account --output text

# Define bucket names with account ID
$FrontendBucket = "$ProjectName-$Environment-frontend-$awsAccountId"
$MemoryBucket = "$ProjectName-$Environment-memory-$awsAccountId"

# Empty frontend bucket if it exists
try {
    aws s3 ls "s3://$FrontendBucket" 2>$null | Out-Null
    Write-Host "  Emptying $FrontendBucket..." -ForegroundColor Gray
    aws s3 rm "s3://$FrontendBucket" --recursive
} catch {
    Write-Host "  Frontend bucket not found or already empty" -ForegroundColor Gray
}

# Empty memory bucket if it exists
try {
    aws s3 ls "s3://$MemoryBucket" 2>$null | Out-Null
    Write-Host "  Emptying $MemoryBucket..." -ForegroundColor Gray
    aws s3 rm "s3://$MemoryBucket" --recursive
} catch {
    Write-Host "  Memory bucket not found or already empty" -ForegroundColor Gray
}

Write-Host "Running terraform destroy..." -ForegroundColor Yellow

# Run terraform destroy with auto-approve
if ($Environment -eq "prod" -and (Test-Path "prod.tfvars")) {
    terraform destroy -var-file=prod.tfvars -var="project_name=$ProjectName" -var="environment=$Environment" -auto-approve
} else {
    terraform destroy -var="project_name=$ProjectName" -var="environment=$Environment" -auto-approve
}

Write-Host "Infrastructure for $Environment has been destroyed!" -ForegroundColor Green
Write-Host ""
Write-Host "  To remove the workspace completely, run:" -ForegroundColor Cyan
Write-Host "   terraform workspace select default" -ForegroundColor White
Write-Host "   terraform workspace delete $Environment" -ForegroundColor White