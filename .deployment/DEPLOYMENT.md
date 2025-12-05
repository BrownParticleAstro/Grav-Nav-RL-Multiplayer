# 🚀 Deployment Guide: Grav Nav RL Multiplayer to Google Cloud Run

This guide provides complete instructions for deploying the Grav Nav RL Multiplayer game to Google Cloud Run using GitHub Actions for CI/CD.

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Architecture Overview](#-architecture-overview)
3. [Phase 1: 🔍 Prepare - Initial Setup](#phase-1--prepare---initial-setup)
4. [Phase 2: 🚀 Deploy - Automated Deployment](#phase-2--deploy---automated-deployment)
5. [Phase 3: 🧹 Teardown - Cleanup (Optional)](#phase-3--teardown---cleanup-optional)
6. [Troubleshooting](#-troubleshooting)
7. [Cost Estimation](#-cost-estimation)
8. [Security Considerations](#-security-considerations)

---

## 🎯 Prerequisites

Before starting, ensure you have:

- ✅ **Google Cloud Platform Account** with billing enabled
- ✅ **GitHub Account** with admin access to this repository
- ✅ **Local Tools Installed:**
  - `gcloud` CLI ([Install Guide](https://cloud.google.com/sdk/docs/install))
  - `gh` CLI ([Install Guide](https://cli.github.com/))
  - Docker (for local testing)
- ✅ **GCP APIs** to be enabled (done in setup scripts)
- ✅ **Brown University Region Requirement:** Deploy to `us-east1` region (closest to Providence, RI)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           GitHub Actions Workflow                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐      │  │
│  │  │ Prepare  │→ │  Deploy  │→ │   Teardown   │      │  │
│  │  │(Validate)│  │(Build+Run)│  │  (Cleanup)   │      │  │
│  │  └──────────┘  └──────────┘  └──────────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ Push Image
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Google Cloud Platform (us-east1)                  │
│  ┌──────────────────────┐      ┌──────────────────────┐    │
│  │  Artifact Registry   │      │    Cloud Run         │    │
│  │  (Docker Images)     │─────→│  (Game Server)       │    │
│  └──────────────────────┘      └──────────────────────┘    │
│                                           │                  │
│  ┌──────────────────────┐                │                  │
│  │   Cloud Storage      │←───────────────┘                  │
│  │ (Models & Data)      │  (Optional: Persistent Data)      │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
            🌐 Public Internet
         (Players connect via HTTPS)
```

### Key Components:

1. **GitHub Actions**: Automated CI/CD pipeline
2. **Artifact Registry**: Stores Docker container images
3. **Cloud Run**: Hosts the FastAPI/WebSocket game server
4. **Cloud Storage**: (Optional) Stores AI models and game data
5. **Service Account**: Authenticates GitHub Actions with GCP

---

## Phase 1: 🔍 PREPARE - Initial Setup

This phase sets up your GCP project and GitHub repository for automated deployments.

### Step 1.1: Authenticate with GCP

```bash
# Login to Google Cloud
gcloud auth login

# List your projects
gcloud projects list

# Set your project (create one if needed)
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID
```

### Step 1.2: Enable Required GCP APIs

```bash
# Enable all required APIs
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable iam.googleapis.com
```

### Step 1.3: Create Artifact Registry Repository

```bash
# Run the setup script
cd .deployment/scripts/gcp
./setup-artifact-registry.sh

# Or manually:
gcloud artifacts repositories create grav-nav-repo \
    --repository-format=docker \
    --location=us-east1 \
    --description="Docker repository for Grav Nav multiplayer game"
```

### Step 1.4: Create Service Account with Proper Permissions

```bash
# Run the automated setup script
./setup-service-account.sh

# This script will:
# 1. Create service account: grav-nav-cloud-run-sa
# 2. Assign required IAM roles:
#    - roles/run.admin (Deploy Cloud Run services)
#    - roles/iam.serviceAccountUser (Act as service account)
#    - roles/storage.admin (Manage Cloud Storage)
#    - roles/artifactregistry.writer (Push Docker images)
#    - roles/logging.logWriter (Write logs)
#    - roles/cloudtrace.agent (Send traces)
# 3. Generate and download key file: grav-nav-sa-key.json
```

**⚠️ IMPORTANT**: Keep the `grav-nav-sa-key.json` file secure! This is your authentication credential.

### Step 1.5: Authenticate GitHub CLI

```bash
# Login to GitHub with required scopes
gh auth login --scopes repo,workflow,admin:repo_hook

# Verify authentication
gh auth status
```

### Step 1.6: Configure GitHub Secrets

```bash
# Run the automated setup script
cd .deployment/scripts/github
./setup-github-secrets.sh

# The script will prompt for:
# 1. GCP Project ID
# 2. Path to service account key file
# 3. Repository name (auto-detected or manual input)

# It will create these secrets:
# - GCP_PROJECT_ID
# - GCP_SERVICE_ACCOUNT_KEY
```

### Step 1.7: Validate GitHub Configuration

```bash
# Verify all secrets are set correctly
./validate-github-config.sh

# Expected output:
#   ✅ GCP_PROJECT_ID is set
#   ✅ GCP_SERVICE_ACCOUNT_KEY is set
#   ✅ All required secrets are configured!
```

### Step 1.8: Configure Docker for Local Testing (Optional)

```bash
# Configure Docker to use Artifact Registry
gcloud auth configure-docker us-east1-docker.pkg.dev
```

---

## Phase 2: 🚀 DEPLOY - Automated Deployment

Once Phase 1 is complete, deployments are fully automated through GitHub Actions.

### Option A: Deploy via GitHub UI (Recommended)

1. **Navigate to GitHub Actions**
   - Go to your repository on GitHub
   - Click on the "Actions" tab

2. **Select Workflow**
   - Find "🚀 Deploy to Google Cloud Run" workflow
   - Click on it

3. **Run Workflow**
   - Click "Run workflow" button (right side)
   - Select parameters:
     - **Environment**: `production` or `staging`
     - **Region**: `us-east1` (required for Brown University)
   - Click "Run workflow"

4. **Monitor Progress**
   - Watch the workflow execute through 3 phases:
     - ✅ **Prepare**: Validates configuration
     - ✅ **Deploy**: Builds and deploys container
     - ✅ **Teardown**: (Only runs on failure)

5. **Get Service URL**
   - Once complete, check the workflow summary
   - Copy the service URL (e.g., `https://grav-nav-multiplayer-xxx-uc.a.run.app`)

### Option B: Deploy via CLI

```bash
# Trigger workflow from command line
gh workflow run deploy.yml \
    --field environment=production \
    --field region=us-east1

# Watch the workflow run
gh run watch

# Get the latest run status
gh run list --workflow=deploy.yml --limit 1
```

### Option C: Manual Deployment (Backup Method)

If GitHub Actions is unavailable, you can deploy manually:

```bash
# 1. Build Docker image
docker build -t grav-nav-multiplayer:latest .

# 2. Tag for Artifact Registry
docker tag grav-nav-multiplayer:latest \
    us-east1-docker.pkg.dev/$GCP_PROJECT_ID/grav-nav-repo/grav-nav-multiplayer:latest

# 3. Push to registry
docker push us-east1-docker.pkg.dev/$GCP_PROJECT_ID/grav-nav-repo/grav-nav-multiplayer:latest

# 4. Deploy to Cloud Run
gcloud run deploy grav-nav-multiplayer \
    --image=us-east1-docker.pkg.dev/$GCP_PROJECT_ID/grav-nav-repo/grav-nav-multiplayer:latest \
    --region=us-east1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300s \
    --port=8080 \
    --set-env-vars="PORT=8080,PYTHON_ENV=production" \
    --service-account=grav-nav-cloud-run-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com \
    --no-cpu-throttling \
    --execution-environment=gen2

# 5. Get service URL
gcloud run services describe grav-nav-multiplayer \
    --region=us-east1 \
    --format='value(status.url)'
```

---

## Phase 3: 🧹 TEARDOWN - Cleanup (Optional)

### Delete Cloud Run Service

```bash
# Delete the service
gcloud run services delete grav-nav-multiplayer \
    --region=us-east1 \
    --quiet
```

### Delete Container Images

```bash
# List images
gcloud artifacts docker images list \
    us-east1-docker.pkg.dev/$GCP_PROJECT_ID/grav-nav-repo/grav-nav-multiplayer

# Delete specific image
gcloud artifacts docker images delete \
    us-east1-docker.pkg.dev/$GCP_PROJECT_ID/grav-nav-repo/grav-nav-multiplayer:TAG \
    --quiet

# Or delete entire repository
gcloud artifacts repositories delete grav-nav-repo \
    --location=us-east1 \
    --quiet
```

### Delete Service Account (Use with Caution)

```bash
# List service accounts
gcloud iam service-accounts list

# Delete service account
gcloud iam service-accounts delete \
    grav-nav-cloud-run-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com \
    --quiet
```

### Delete GitHub Secrets

```bash
# Remove secrets from GitHub
gh secret remove GCP_PROJECT_ID
gh secret remove GCP_SERVICE_ACCOUNT_KEY
```

---

## 🔧 Troubleshooting

### Issue: "Permission Denied" Errors

**Solution:**
```bash
# Verify service account has correct roles
gcloud projects get-iam-policy $GCP_PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:grav-nav-cloud-run-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com"

# Re-run service account setup if needed
cd .deployment/scripts/gcp
./setup-service-account.sh
```

### Issue: "API Not Enabled" Errors

**Solution:**
```bash
# Enable all required APIs
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    iam.googleapis.com
```

### Issue: Container Fails to Start

**Check logs:**
```bash
# View logs in real-time
gcloud run services logs read grav-nav-multiplayer \
    --region=us-east1 \
    --follow

# Or view in GCP Console:
# https://console.cloud.google.com/run/detail/us-east1/grav-nav-multiplayer/logs
```

### Issue: WebSocket Connections Fail

**Cloud Run Considerations:**
- Cloud Run supports WebSockets (HTTP/1.1 with Upgrade header)
- Ensure client connects to `wss://` (secure WebSocket)
- Check that PORT environment variable is correctly set to 8080

### Issue: Models Not Loading

**Solution:**
```bash
# Check if models directory exists in container
gcloud run services describe grav-nav-multiplayer \
    --region=us-east1 \
    --format='value(status.url)'

# For persistent models, consider Cloud Storage:
# 1. Upload models to GCS bucket
# 2. Update server_multiship.py to load from GCS
```

---

## 💰 Cost Estimation

### Cloud Run Pricing (as of 2024)

**Free Tier (Monthly):**
- 2 million requests
- 360,000 GB-seconds
- 180,000 vCPU-seconds

**Beyond Free Tier:**
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GB-second
- **Requests**: $0.40 per million requests

### Example Monthly Costs (After Free Tier)

**Light Usage** (100 concurrent players, 2 hrs/day):
- ~$10-30/month

**Medium Usage** (500 concurrent players, 8 hrs/day):
- ~$100-200/month

**Heavy Usage** (1000+ concurrent players, 24/7):
- ~$500-1000/month

**Tips to Reduce Costs:**
1. Set `min-instances: 0` (scales to zero when idle)
2. Use `cpu-throttling: true` for non-real-time workloads
3. Optimize container size (remove unnecessary dependencies)
4. Monitor usage with Cloud Monitoring

---

## 🔐 Security Considerations

### Best Practices

1. **Service Account Keys**
   - ✅ Store keys securely (GitHub Secrets)
   - ✅ Never commit keys to repository
   - ✅ Rotate keys periodically (every 90 days)
   - ✅ Use least privilege principle

2. **Network Security**
   - ✅ Cloud Run supports HTTPS by default
   - ✅ WebSocket connections are encrypted (WSS)
   - ✅ Consider adding Cloud Armor for DDoS protection

3. **Authentication**
   - ✅ Currently allows unauthenticated access (public game)
   - ⚠️ Consider adding authentication for production
   - ✅ Use Firebase Auth or Cloud Identity Platform if needed

4. **Data Protection**
   - ✅ No sensitive data stored by default
   - ✅ If adding Cloud Storage, enable encryption at rest
   - ✅ Use signed URLs for model access

5. **Monitoring**
   - ✅ Enable Cloud Logging (automatic)
   - ✅ Set up Cloud Monitoring alerts
   - ✅ Review security scan results

---

## 📊 Monitoring & Observability

### View Logs

```bash
# Real-time logs
gcloud run services logs read grav-nav-multiplayer \
    --region=us-east1 \
    --follow

# Filter logs by severity
gcloud run services logs read grav-nav-multiplayer \
    --region=us-east1 \
    --log-filter="severity>=ERROR"
```

### View Metrics

```bash
# Get service metrics
gcloud run services describe grav-nav-multiplayer \
    --region=us-east1 \
    --format="table(status.traffic[].latestRevision,status.traffic[].percent)"
```

**GCP Console Links:**
- **Service Dashboard**: `https://console.cloud.google.com/run/detail/us-east1/grav-nav-multiplayer/metrics`
- **Logs**: `https://console.cloud.google.com/run/detail/us-east1/grav-nav-multiplayer/logs`
- **Revisions**: `https://console.cloud.google.com/run/detail/us-east1/grav-nav-multiplayer/revisions`

---

## 🎮 Using Cloud Storage for Persistent Data

The game may benefit from Cloud Storage for:
1. **AI Models**: Store trained PPO models
2. **Game State**: Persist multiplayer sessions
3. **Leaderboards**: Store historical scores

### Setup Cloud Storage

```bash
# Create bucket (replace with unique name)
gsutil mb -p $GCP_PROJECT_ID -l us-east1 gs://grav-nav-game-data

# Set lifecycle rule (optional - auto-delete old data)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://grav-nav-game-data

# Upload models
gsutil -m cp -r models/* gs://grav-nav-game-data/models/

# Set permissions (public read for models, if needed)
gsutil iam ch allUsers:objectViewer gs://grav-nav-game-data
```

### Update Deployment to Use Cloud Storage

Add to `cloudrun.yaml` or deployment command:
```yaml
env:
- name: GCS_BUCKET_NAME
  value: grav-nav-game-data
- name: MODEL_PATH
  value: gs://grav-nav-game-data/models/ppo_orbital_model.zip
```

---

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Guide](https://cloud.google.com/artifact-registry/docs)
- [Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)

---

## 🆘 Support

If you encounter issues:

1. **Check Logs**: Always start with Cloud Run logs
2. **Review Documentation**: Refer to this guide and GCP docs
3. **Validate Configuration**: Run `validate-github-config.sh`
4. **Test Locally**: Build and run Docker container locally
5. **Create Issue**: Open a GitHub issue with error logs

---

## 📝 Summary Checklist

### One-Time Setup (Phase 1)
- [ ] GCP project created with billing enabled
- [ ] Required APIs enabled
- [ ] Artifact Registry repository created
- [ ] Service account created with proper roles
- [ ] Service account key downloaded and secured
- [ ] GitHub CLI authenticated
- [ ] GitHub Secrets configured and validated

### Each Deployment (Phase 2)
- [ ] Trigger GitHub Actions workflow
- [ ] Monitor workflow progress
- [ ] Verify deployment success
- [ ] Test service URL
- [ ] Check logs for errors

### Maintenance
- [ ] Monitor costs monthly
- [ ] Review logs for errors
- [ ] Rotate service account keys every 90 days
- [ ] Update dependencies regularly
- [ ] Scale resources based on usage

---

**🎉 Congratulations!** Your Grav Nav RL Multiplayer game is now deployed to Google Cloud Run!

For questions or issues, please open a GitHub issue or contact the development team.
