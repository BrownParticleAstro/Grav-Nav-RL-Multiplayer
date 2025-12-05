#!/bin/bash
set -e

# ============================================================================
# GitHub Configuration Validation Script
# ============================================================================
# This script validates that all required GitHub Secrets are configured
# ============================================================================

echo "🔍 Validating GitHub Configuration"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ ERROR: GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ ERROR: Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")

if [ -z "$REPO" ]; then
    echo "⚠️  Could not auto-detect repository"
    read -p "Enter repository (owner/name): " REPO
fi

echo "📁 Repository: $REPO"
echo ""

# Required secrets
REQUIRED_SECRETS=(
    "GCP_PROJECT_ID"
    "GCP_SERVICE_ACCOUNT_KEY"
)

echo "🔐 Checking required secrets..."
echo ""

ALL_VALID=true

for SECRET in "${REQUIRED_SECRETS[@]}"; do
    if gh secret list --repo="$REPO" | grep -q "^$SECRET"; then
        echo "  ✅ $SECRET is set"
    else
        echo "  ❌ $SECRET is NOT set"
        ALL_VALID=false
    fi
done

echo ""

if [ "$ALL_VALID" = true ]; then
    echo "✅ All required secrets are configured!"
    echo ""
    echo "📌 You're ready to deploy!"
    echo ""
    echo "To trigger a deployment:"
    echo "  1. Go to GitHub Actions in your repository"
    echo "  2. Select 'Deploy to Google Cloud Run' workflow"
    echo "  3. Click 'Run workflow'"
    echo "  4. Select environment and region"
    echo "  5. Click 'Run workflow' button"
    exit 0
else
    echo "❌ Some secrets are missing!"
    echo ""
    echo "📌 Run the setup script to configure secrets:"
    echo "  ./deployment/scripts/github/setup-github-secrets.sh"
    exit 1
fi
