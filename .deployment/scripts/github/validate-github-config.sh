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

# Required variables
REQUIRED_VARIABLES=(
    "GCP_PROJECT_ID"
)

# Required secrets
REQUIRED_SECRETS=(
    "GCP_SERVICE_ACCOUNT_KEY"
)

echo "🔧 Checking required variables..."
echo ""

ALL_VALID=true

for VARIABLE in "${REQUIRED_VARIABLES[@]}"; do
    if gh variable list --repo="$REPO" | grep -q "^$VARIABLE"; then
        echo "  ✅ $VARIABLE is set"
    else
        echo "  ❌ $VARIABLE is NOT set"
        ALL_VALID=false
    fi
done

echo ""
echo "🔐 Checking required secrets..."
echo ""

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
    echo "✅ All required configuration is present!"
    echo ""
    echo "📖 For deployment instructions, refer to:"
    echo "  .deployment/DEPLOYMENT.md - Phase 2: Deploy"
    echo ""
    exit 0
else
    echo "❌ Some configuration is missing!"
    echo ""
    echo "📌 Run the setup script to configure:"
    echo "  ./.deployment/scripts/github/setup-github-secrets.sh"
    exit 1
fi
