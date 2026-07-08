# 🧳 TravelMemory — EKS DevSecOps Pipeline (Application Repo)

[![Node](https://img.shields.io/badge/Node.js-Express-339933?logo=nodedotjs&logoColor=white)](#)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)](#)
[![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED?logo=docker&logoColor=white)](#)
[![Jenkins](https://img.shields.io/badge/CI-Jenkins%20on%20K8s-D24939?logo=jenkins&logoColor=white)](#)
[![ArgoCD](https://img.shields.io/badge/CD-ArgoCD-EF7B4D?logo=argo&logoColor=white)](#)
[![EKS](https://img.shields.io/badge/Runtime-Amazon%20EKS-FF9900?logo=amazonaws&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](#)

> **Application source** for a production-style, security-conscious CI/CD pipeline on Amazon EKS.
> This repo owns the **app code** — a Node/Express + React MERN stack, its Dockerfiles, its
> Jenkinsfile, and its two AI scripts. All infrastructure and deployment manifests live in the
> companion repo: **[travelmemory-eks-devsecops-gitops](https://github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops)**.
>
> This README is written so **anyone can follow along end-to-end** — every command below is a real
> command that was actually run, in the order it was run.

---

## 📖 What is this?

TravelMemory is an open-source travel-journaling app (forked from
[UnpredictablePrashant/TravelMemory](https://github.com/UnpredictablePrashant/TravelMemory)) —
users log trips, add notes and photos, and browse past experiences.

The application itself is a normal MERN app. What makes this repo interesting is **everything
around it**: every Dockerfile, Jenkinsfile, test harness, and AI triage script here was built
from scratch to turn a simple app into the subject of a real, multi-stage DevSecOps pipeline
running on Amazon EKS.

---

## ✅ Prerequisites

Install and verify these before running anything below:

| Tool | Version used | Verify with |
|---|---|---|
| Node.js | 20.x (matches the Dockerfiles' `node:20-alpine`) | `node --version` |
| Docker Desktop (with `buildx`) | v24+ | `docker buildx version` |
| AWS CLI | v2.x (only needed for the ECR push step) | `aws --version` |
| Git | any recent version | `git --version` |

You'll also need:
- Push access to an Amazon ECR registry (see the [gitops repo](https://github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops) for how the repos are provisioned).
- A running Kubernetes cluster with the companion gitops repo's manifests applied, if you want to
  deploy rather than just run this locally.

Throughout this guide, replace `<YOUR_AWS_ACCOUNT_ID>` with your own 12-digit AWS account ID
(`aws sts get-caller-identity --query Account`).

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph AppRepo["📦 App Repo (this repo)"]
        A1[React frontend] --> A2[Nginx multi-stage build]
        A3[Express backend] --> A4[Node single-stage build]
        A5[scripts/scan-triage.py<br/>AI #1 · Gemini]
        A6[scripts/anomaly-detector.py<br/>AI #2 · CloudWatch]
        A7[Jenkinsfile<br/>8-stage pipeline]
    end

    subgraph Registry["🐳 Amazon ECR"]
        R1[travelmemory-backend]
        R2[travelmemory-frontend]
    end

    subgraph GitOpsRepo["🔧 GitOps Repo (infra + manifests)"]
        G1[Helm values.yaml<br/>image tags updated by CI]
        G2[Terraform: VPC · EKS · DocumentDB · ECR · Bastion]
    end

    subgraph Cluster["☸️ Amazon EKS"]
        C1[ArgoCD watches GitOps repo]
        C2[Backend + Frontend pods]
        C3[DocumentDB via Secrets Manager CSI]
    end

    A2 --> A7
    A4 --> A7
    A7 -->|Kaniko build, no privileged mode| R1
    A7 --> R2
    A7 -->|Stage 7: AI triage gate| A5
    A7 -->|bump image tag| G1
    G1 --> C1 --> C2
    C2 --> C3
    C2 --> A6
```

---

## 📁 Repository structure

```text
travelmemory-eks-devsecops/
├── .gitignore
├── LICENSE
├── README.md
├── Jenkinsfile                  ← 8-stage pipeline (build → scan → triage → deploy trigger)
├── docker-compose.yml           ← local-only validation, not used in the cluster
├── backend/
│   ├── Dockerfile               ← single-stage Node
│   ├── .dockerignore
│   ├── .gitignore
│   ├── conn.js                  ← DocumentDB connection (connects at import time)
│   ├── index.js                 ← entrypoint; exports `app` for Supertest
│   ├── package.json / package-lock.json
│   ├── controllers/
│   │   └── trip.controller.js
│   ├── models/
│   │   └── trip.model.js
│   ├── routes/
│   │   └── trip.routes.js
│   └── tests/
│       └── trip.test.js         ← Jest + Supertest
├── frontend/
│   ├── Dockerfile               ← multi-stage React → Nginx
│   ├── nginx.conf                ← /api/ rewrite → backend service
│   ├── .gitignore
│   ├── README.md
│   ├── package.json / package-lock.json
│   ├── public/                  ← CRA static assets
│   └── src/
│       ├── App.js / App.css / App.test.js
│       ├── index.js / index.css
│       ├── url.js               ← API base URL (previously hardcoded — see Known Issues)
│       └── components/
│           ├── UIC/             ← Card, FeaturedCard, Header
│           └── pages/           ← Home, AddExperience, ExperienceDetails
└── scripts/                     ← lives at repo root, NOT under backend/
    ├── scan-triage.py           ← AI #1
    └── anomaly-detector.py      ← AI #2
```

---

## 🧭 Full Walkthrough — every command, in order

### Step 1 — Dockerfiles

**`backend/Dockerfile`** (single-stage Node):

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]
```

**`frontend/Dockerfile`** (multi-stage React → Nginx):

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

`frontend/nginx.conf` serves static files at `/` with SPA fallback, and proxies `/api/` to
`http://backend:3000`, rewriting the path so it matches the backend's actual route prefix.

### Step 2 — Local validation with Docker Compose

```bash
docker compose up --build
```

**✅ Expected output** (once both containers are healthy):

```text
backend_1   | Server running on port 3000
backend_1   | Connected to MongoDB
frontend_1  | /docker-entrypoint.sh: Configuration complete; ready for start up
```

```bash
curl http://localhost:8080/api/trip/
# []   ← empty array = frontend → Nginx → backend → DB chain all working
```

Three real bugs were hit and fixed here — kept in the table below for anyone debugging the same
class of issue:

| # | Bug | Fix |
|---|-----|-----|
| 1 | Frontend hardcoded `http://localhost:3001` in `src/url.js` | Exported a relative `baseUrl = '/api'` instead — same variable name, since existing components import it exactly |
| 2 | React calls `/api/trip`, backend mounts at `/trip` (no prefix) → 404s | Fixed entirely in `nginx.conf`: `location /api/ { rewrite ^/api/(.*)$ /$1 break; proxy_pass http://backend:3000; }` — zero app code changes |
| 3 | `POST /trip` returned 200 but nothing was persisted | Silent Mongoose validation failure on an invalid date (end before start); the existing `catch` block only logged the word `"ERROR"`, discarding the real error object |

> 💡 Diagnostic discipline that found bug #3: verify each layer independently before moving to the
> next — Nginx received the request OK, backend received the body OK, only then look at the
> actual data being sent.
>
> ⚠️ Port 80 is often already bound on a Mac (Apache, a previous container). Map host `8080` to
> container `80` in `docker-compose.yml` (`8080:80`) — the container still listens on 80.

### Step 3 — Push to ECR (and the arm64 → amd64 lesson)

The first push worked fine from an Apple Silicon Mac. The first EKS deployment then failed with
`no match for platform in manifest: not found` — Apple Silicon builds `arm64` images by default;
EKS `t3.medium` nodes are `amd64`.

```bash
docker buildx build --platform linux/amd64 -t travelmemory-backend:v2 ./backend --load
docker buildx build --platform linux/amd64 -t travelmemory-frontend:v2 ./frontend --load

# Re-tag and push as :v2 — ECR's IMMUTABLE tags block overwriting :v1
docker tag travelmemory-backend:v2 <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/travelmemory-backend:v2
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/travelmemory-backend:v2
```

**✅ Expected output:**

```text
v2: digest: sha256:9f2c1e4b... size: 1786
```

```bash
# From an EKS node (or any amd64 host) — confirms the fix:
docker run --rm --platform linux/amd64 <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com/travelmemory-backend:v2 node --version
# v20.x.x   ← runs cleanly, no "exec format error"
```

### Step 4 — Local dev & tests

```bash
# Backend
cd backend
npm install
echo "MONGO_URI=mongodb://localhost:27017/test" > .env
echo "PORT=3000" >> .env
npm test               # jest --forceExit
```

**✅ Expected output:**

```text
PASS  tests/trip.test.js
  Trip API
    ✓ GET /trip returns an array (42 ms)
    ✓ POST /trip creates a new trip (18 ms)

Test Suites: 1 passed, 1 total
Tests:       2 passed, 2 total
```

```bash
npm start

# Frontend
cd frontend
npm install
npm start
```

> `conn.js` connects to MongoDB unconditionally at import time, so tests point at a throwaway
> local URI and Jest runs with `--forceExit` to avoid hanging on the open connection handle.
> `module.exports = app` was added to `index.js` specifically so Supertest could exercise routes
> without a real server listening.

### Step 5 — The 8-stage Jenkinsfile

Jenkins runs **inside** the EKS cluster. Each stage uses a dedicated, already-running container
from the pod template (`sleep 9999999` keeps each tool container alive so Jenkins can `exec` into
it via `container('name') { sh '...' }`):

```groovy
pipeline {
  agent {
    kubernetes {
      serviceAccount 'jenkins-agent-sa'
      yaml '''
        containers:
          - name: kaniko
            image: gcr.io/kaniko-project/executor:debug
            command: ['sleep'] args: ['9999999']
          - name: trivy
            image: aquasec/trivy:latest
            command: ['sleep'] args: ['9999999']
          - name: checkov
            image: bridgecrew/checkov:latest
            command: ['sleep'] args: ['9999999']
          - name: node
            image: node:20-alpine
            command: ['sleep'] args: ['9999999']
          - name: gitleaks
            image: zricethezav/gitleaks:latest
            command: ['sleep'] args: ['9999999']
          - name: python
            image: python:3.12-slim
            command: ['sleep'] args: ['9999999']
      '''
    }
  }
  environment {
    IMAGE_TAG    = "${BUILD_NUMBER}"
    ECR_REGISTRY = "<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.ap-south-1.amazonaws.com"
  }
  stages {
    stage('1 - Checkout') { steps { checkout scm } }

    stage('2 - Unit Tests') {
      steps { container('node') { sh '''
        cd backend
        echo "MONGO_URI=mongodb://localhost:27017/test" > .env
        echo "PORT=3000" >> .env
        npm ci && npm test
      ''' } }
    }

    stage('3 - Secrets Scan') {
      steps { container('gitleaks') { sh '''
        gitleaks detect --source . --report-format json \
          --report-path gitleaks-report.json --exit-code 0
      ''' } }
    }

    stage('4 - IaC Scan') {
      steps { container('checkov') { sh '''
        checkov -d devops/terraform --output json \
          --output-file-path console > checkov-report.json || true
      ''' } }
    }

    stage('5 - Build & Push Images') {
      steps { container('kaniko') { sh '''
        /kaniko/executor \
          --context=`pwd`/backend \
          --dockerfile=`pwd`/backend/Dockerfile \
          --destination=${ECR_REGISTRY}/travelmemory-backend:${IMAGE_TAG}
        /kaniko/executor \
          --context=`pwd`/frontend \
          --dockerfile=`pwd`/frontend/Dockerfile \
          --destination=${ECR_REGISTRY}/travelmemory-frontend:${IMAGE_TAG}
      ''' } }
    }

    stage('6 - Image Scan') {
      steps { container('trivy') { sh '''
        trivy image --format json -o trivy-backend.json \
          ${ECR_REGISTRY}/travelmemory-backend:${IMAGE_TAG} || true
        trivy image --format json -o trivy-frontend.json \
          ${ECR_REGISTRY}/travelmemory-frontend:${IMAGE_TAG} || true
      ''' } }
    }

    stage('7 - AI Triage Gate') {
      steps { container('python') {
        withCredentials([string(credentialsId: 'gemini-api-key',
                                variable: 'GEMINI_API_KEY')]) {
          sh '''
            pip install --quiet requests
            python3 scripts/scan-triage.py trivy-backend.json \
              checkov-report.json gitleaks-report.json
          '''
        }
      } }
    }

    stage('8 - Update GitOps Repo') {
      steps {
        withCredentials([usernamePassword(
            credentialsId: 'github-pat',
            usernameVariable: 'GIT_USER',
            passwordVariable: 'GIT_PAT')]) {
          sh '''
            git clone https://${GIT_USER}:${GIT_PAT}@github.com/\
              HarjotSingh2k19/travelmemory-eks-devsecops-gitops.git
            cd travelmemory-eks-devsecops-gitops
            sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/g" \
              devops/helm/travelmemory/values.yaml
            git config user.email "jenkins@travelmemory.local"
            git config user.name "Jenkins CI"
            git commit -am "ci: bump image tag to ${IMAGE_TAG} [skip ci]"
            git push
          '''
        }
      }
    }
  }
}
```

**Jenkins credentials required** (Manage Jenkins → Credentials → global):

| ID | Kind | Value |
|---|---|---|
| `github-pat` | Username with password | Username `HarjotSingh2k19`, password = a GitHub PAT with `repo` scope |
| `gemini-api-key` | Secret text | A Gemini API key from `aistudio.google.com/apikey` |

> ⚠️ **Known limitation, kept intentional for now:** Stage 8's `sed -i "s/tag:.*/tag: \"${IMAGE_TAG}\"/g"`
> is a global, blind text replace — it rewrites *every* `tag:` line in `values.yaml`. That's fine
> today because this chart only has two images (backend, frontend) and no subcharts. It would
> **not** be safe the moment a subchart (e.g. Redis, a Mongo sidecar) introduces its own `tag:`
> key, since this same regex would silently overwrite that third-party tag too. The correct
> long-term fix is a proper YAML-aware tool like [`yq`](https://github.com/mikefarah/yq)
> (e.g. `yq -i '.backend.image.tag = "${IMAGE_TAG}"' values.yaml`) that edits a specific path
> instead of pattern-matching text. `sed` was a deliberate, acknowledged shortcut for this scale of
> project — worth calling out proactively in an interview rather than waiting to be asked.

> 💡 Stage order matters: scans run **before** images are pushed. Stages 3–6 use `--exit-code 0` /
> `|| true` — they're report-only. The real block/pass decision is Stage 7's AI triage gate, which
> genuinely stops the pipeline (`sys.exit(1)`) on a `BLOCK` verdict.

### Step 6 — AI #1: `scripts/scan-triage.py`

Turns three noisy JSON scan reports (Trivy, Checkov, gitleaks) into one ranked, human-readable
verdict. Provider: Google Gemini, model `gemini-2.5-flash-lite` (chosen after `gemini-2.0-flash`
hit a `limit: 0` free-tier wall on this GCP project).

```python
url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
       f"gemini-2.5-flash-lite:generateContent?key={api_key}")

# Verified locally before committing:
# BLOCK test: trivy with CVE + checkov with open SG → BLOCK, exit 1 ✓
# PASS test:  all empty findings → PASS, exit 0 ✓
```

Key design choices, all deliberate:

- **Fails closed** if `GEMINI_API_KEY` is missing or the API call errors — `sys.exit(1)` blocks
  the pipeline rather than silently passing.
- **Fails closed** if any scan report file is missing — a missing report is *not* treated as "no
  findings." (An earlier version silently returned `None`, sent null data to Gemini, and got back
  a meaningless `PASS` — this was caught and fixed.)
- Slack webhook is optional; the script works without it.
- Prompt requires strict JSON only (`{verdict, summary, top_findings}`); the response is stripped
  of markdown fences before parsing.

### Step 7 — AI #2: `scripts/anomaly-detector.py`

This script is maintained here, in the app repo, for version control and code review alongside the
application it monitors — but it **runs** as a Kubernetes CronJob deployed from the
[gitops repo](https://github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops#step-9--ai-2-anomaly-detection-cronjob),
which renders its contents into a ConfigMap via Helm. Runs every 15 minutes, pulling 7 days of hourly
CloudWatch Container Insights datapoints for `pod_cpu_utilization`, `pod_memory_utilization`,
`node_cpu_utilization`, and `node_memory_utilization`, then computes a rolling z-score:

```python
def z_score_latest(values):
    if len(values) < 10: return 0.0   # not enough history
    baseline = values[:-1]
    latest   = values[-1]
    mean  = statistics.mean(baseline)
    stdev = statistics.stdev(baseline) or 1e-6   # avoid div/0 on flat metrics
    return (latest - mean) / stdev
```

Threshold is ±3.0 standard deviations (configurable via `Z_SCORE_THRESHOLD`). Sends a Slack alert
with the exact numbers (latest value, baseline mean, z-score) when triggered. Authenticated via
IRSA (`anomaly-detector-sa`, CloudWatch read-only — `GetMetricStatistics`, `GetMetricData`,
`ListMetrics` only).

---

## 🐛 Real bugs hit & fixed (kept for posterity)

| # | Bug | Root cause | Fix |
|---|-----|------------|-----|
| 1 | Frontend calling `http://localhost:3001` in-cluster | Hardcoded `baseUrl` in `src/url.js` | Made the API base URL relative, routed through Nginx |
| 2 | 404s on all `/api/*` calls from the frontend pod | Nginx path didn't match backend's mounted route prefix | Corrected `nginx.conf` rewrite rule |
| 3 | Invalid trip dates silently accepted | Mongoose schema validation wasn't surfaced; `catch` block discarded the real error | Used logically valid test dates; hardened error logging |
| 4 | `exec format error` on EKS nodes | Images built natively on Apple Silicon (ARM64), nodes are amd64 | `docker buildx build --platform linux/amd64` |
| 5 | Supertest couldn't hit the Express app | `index.js` didn't export the app instance | Added `module.exports = app` |
| 6 | AI triage gate returned `PASS` with a missing scan report | Missing file silently treated as "no findings" | Made the script fail-closed on missing reports |
| 7 | CSI-driver-mounted secret volume stuck in `ContainerCreating` (gitops-side) | `tokenRequests` missing from the `CSIDriver` object | `kubectl patch csidriver ...` — documented in the gitops repo |

---

## 🧹 Cleaning up locally

```bash
docker compose down -v          # stop containers and remove volumes
docker image prune -f           # reclaim space from dangling build layers
```

For tearing down the actual **cloud infrastructure** this app deploys to (EKS, DocumentDB, ECR,
NAT Gateway, etc. — the resources that actually cost money if left running), see the
**[Tear-Down section of the gitops repo README](https://github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops#-tear-down--do-this-before-you-close-the-laptop)**.

---

## 🔗 Related repos

- **GitOps / Infra repo:** [travelmemory-eks-devsecops-gitops](https://github.com/HarjotSingh2k19/travelmemory-eks-devsecops-gitops) — Terraform, Ansible, Helm, K8s manifests, ArgoCD `Application`, full service-access instructions (Jenkins, ArgoCD, Grafana, Prometheus).
- **Original upstream app:** [UnpredictablePrashant/TravelMemory](https://github.com/UnpredictablePrashant/TravelMemory)
- **Sibling project:** GitOps Factory — a self-hosted Jenkins → ArgoCD → KIND-on-EC2 pipeline, documented separately.

## 📜 License

MIT — see [`LICENSE`](./LICENSE).
