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

# Set GitHub Secrets
echo ""
echo "📝 Setting GitHub Secrets..."

# GCP Project ID
echo "  → Setting GCP_PROJECT_ID"
echo "$GCP_PROJECT_ID" | gh secret set GCP_PROJECT_ID --repo="$REPO"

# Service Account Key
echo "  → Setting GCP_SERVICE_ACCOUNT_KEY"
gh secret set GCP_SERVICE_ACCOUNT_KEY --repo="$REPO" < "$SA_KEY_PATH"

echo ""
echo "✅ GitHub Secrets configured successfully!"
echo ""
echo "📋 Secrets set:"
echo "  • GCP_PROJECT_ID"
echo "  • GCP_SERVICE_ACCOUNT_KEY"
echo ""
echo "🔍 To verify secrets:"
echo "  gh secret list --repo=$REPO"
echo ""
echo "📌 Next Steps:"
echo "  1. Verify secrets are set correctly:"
echo "     ./.deployment/scripts/github/validate-github-config.sh"
echo ""
echo "  2. Enable required GCP APIs:"
echo "     gcloud services enable run.googleapis.com"
echo "     gcloud services enable artifactregistry.googleapis.com"
echo "     gcloud services enable cloudbuild.googleapis.com"
echo ""
echo "  3. Create Artifact Registry repository:"
echo "     ./.deployment/scripts/gcp/setup-artifact-registry.sh"
echo ""
echo "  4. Trigger deployment from GitHub Actions"
echo ""
