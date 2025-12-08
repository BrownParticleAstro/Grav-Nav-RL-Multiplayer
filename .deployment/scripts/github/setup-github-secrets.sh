#!/bin/bash
set -e

# ============================================================================
# GitHub Secrets Setup Script
# ============================================================================
# This script helps you set up GitHub Secrets required for deployment
# ============================================================================

echo "🔐 GitHub Secrets Setup for Grav Nav Deployment"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ ERROR: GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "🔑 You need to authenticate with GitHub first"
    echo "Running: gh auth login"
    gh auth login --scopes repo,workflow,admin:repo_hook
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

# Prompt for GCP Project ID
read -p "Enter your GCP Project ID: " GCP_PROJECT_ID

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "❌ ERROR: GCP Project ID cannot be empty"
    exit 1
fi

# Prompt for service account key file
echo ""
echo "🔑 Service Account Key"
echo "This should be the JSON key file created by setup-service-account.sh"
read -p "Enter path to service account key JSON file [./grav-nav-sa-key.json]: " SA_KEY_PATH
SA_KEY_PATH=${SA_KEY_PATH:-./grav-nav-sa-key.json}

if [ ! -f "$SA_KEY_PATH" ]; then
    echo "❌ ERROR: Service account key file not found: $SA_KEY_PATH"
    exit 1
fi

# Set GitHub Variables and Secrets
echo ""
echo "📝 Setting GitHub configuration..."

# GCP Project ID as a repository variable
echo "  → Setting GCP_PROJECT_ID (as repository variable)"
gh variable set GCP_PROJECT_ID --body="$GCP_PROJECT_ID" --repo="$REPO"

# Service Account Key as a secret
echo "  → Setting GCP_SERVICE_ACCOUNT_KEY (as secret)"
gh secret set GCP_SERVICE_ACCOUNT_KEY --repo="$REPO" < "$SA_KEY_PATH"

echo ""
echo "✅ GitHub configuration completed successfully!"
echo ""
echo "📋 Configuration set:"
echo "  • GCP_PROJECT_ID (repository variable)"
echo "  • GCP_SERVICE_ACCOUNT_KEY (secret)"
echo ""
echo "🔍 To verify:"
echo "  gh variable list --repo=$REPO"
echo "  gh secret list --repo=$REPO"
echo ""
echo "📖 For next steps, refer to:"
echo "  .deployment/DEPLOYMENT.md - Phase 1: Step 1.6 onwards"
echo ""
