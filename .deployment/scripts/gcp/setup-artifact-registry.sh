#!/bin/bash
set -e

# ============================================================================
# GCP Artifact Registry Setup Script
# ============================================================================
# This script creates an Artifact Registry repository for Docker images
# ============================================================================

echo "🐳 Setting up GCP Artifact Registry"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ ERROR: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Prompt for details
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter GCP Region [us-east1]: " REGION
REGION=${REGION:-us-east1}

REPO_NAME="grav-nav-repo"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: Project ID cannot be empty"
    exit 1
fi

# Set the project
echo "📍 Setting project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Enable Artifact Registry API
echo "🔌 Enabling Artifact Registry API..."
gcloud services enable artifactregistry.googleapis.com --quiet

# Check if repository already exists
if gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &> /dev/null; then
    echo "⚠️  Repository $REPO_NAME already exists in $REGION"
    echo "✅ Setup complete - using existing repository"
    exit 0
fi

# Create Artifact Registry repository
echo "📦 Creating Artifact Registry repository: $REPO_NAME"
gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Docker repository for Grav Nav multiplayer game"

echo ""
echo "✅ Artifact Registry setup complete!"
echo ""
echo "📋 Repository Details:"
echo "  • Name: $REPO_NAME"
echo "  • Location: $REGION"
echo "  • Format: Docker"
echo "  • URL: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
echo ""
echo "📖 For next steps, refer to:"
echo "  .deployment/DEPLOYMENT.md - Phase 2: Deploy"
echo ""
