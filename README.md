# 🌿 RootsAndQi

[![CI/CD Pipeline](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml)

An AI-powered wellness platform combining Traditional Chinese Medicine (TCM) syndrome differentiation with Indigenous herbal traditions. Built as a portfolio project to demonstrate a production-grade DevOps + MLOps stack on AWS EKS.

> **Disclaimer:** For educational and portfolio purposes only. Not a medical diagnosis tool. See [DISCLAIMER.md](DISCLAIMER.md) for full compliance notice.

---

## 🏗️ Architecture

Developer → GitHub → GitHub Actions → Amazon ECR → Amazon EKS → Live App

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI + Pydantic |
| **AI / LLM** | LangChain + Anthropic Claude |
| **Vector Database** | Qdrant |
| **Frontend** | React + Vite |
| **CI/CD** | GitHub Actions |
| **Security Scan** | Trivy |
| **Container Registry** | Amazon ECR |
| **Orchestration** | Amazon EKS (Kubernetes 1.31) |
| **Infrastructure** | Terraform (VPC, EKS, ECR, IAM) |
| **Observability** | Prometheus + Grafana (Helm) |
| **Experiment Tracking** | MLflow |
| **Dataset Versioning** | DVC (Google Drive remote) |
| **ML Orchestration** | Airflow 2.10 |

---

## 🔄 DevSecOps Pipeline

Every `git push` to `main` triggers the full pipeline:

1. **Lint** — ruff checks Python code quality
2. **Trivy Scan** — container vulnerability scan (HIGH/CRITICAL CVEs)
3. **Docker Build** — multi-stage build, linux/amd64, non-root user
4. **Push to ECR** — image tagged with git SHA for traceability
5. **Deploy to EKS** — kubectl rolling update with health check verification

---

## 🧠 Request Flow

```
User submits symptoms (React UI)
    ↓
FastAPI /diagnose endpoint
    ↓
LangChain + Anthropic Claude
    → Syndrome classification (primary pattern, organs, confidence, reasoning)
    ↓
Qdrant vector search
    → Herb recommendations (TCM + Indigenous, ranked by relevance score)
    ↓
MLflow
    → Logs provider, model, confidence, herbs returned, traditions
    ↓
Response returned to UI
```

---

## 📁 Repository Structure

```
rootsandqi/
├── app/
│   ├── api/diagnosis.py           # POST /diagnose endpoint
│   ├── core/prompts.py            # TCM syndrome-mapping system prompt
│   ├── data/herbs.json            # 15 TCM + Indigenous herbs (DVC-tracked)
│   └── services/
│       ├── syndrome_mapper.py     # LangChain structured output pipeline
│       ├── herb_retriever.py      # Qdrant vector search
│       └── experiment_tracker.py  # MLflow run logging
│
├── infra/
│   ├── terraform/                 # main.tf, vpc.tf, eks.tf, ecr.tf
│   └── k8s/                       # namespace.yaml, api.yaml, qdrant.yaml
│
├── .github/workflows/ci-cd.yml    # 4-job CI/CD pipeline
├── airflow/dags/                   # validate_herbs then index_herbs DAG
├── frontend/src/                   # React + Vite UI
├── Dockerfile                      # Multi-stage, non-root, linux/amd64
├── DISCLAIMER.md                   # Compliance and medical disclaimer
└── BUILD_LOG.md                    # 25 issues documented across all milestones
```

---

## ☁️ AWS Infrastructure

| Resource | Type | Purpose |
|---|---|---|
| EKS Cluster | Kubernetes 1.31 | App hosting |
| EKS Nodes | 2x t3.small | Worker nodes |
| ECR | Private registry | Docker images |
| VPC | 10.0.0.0/16 | Network isolation |
| NAT Gateway | — | Private node egress |
| Load Balancer | AWS ELB | Public API endpoint |

---

## 🔐 Security

- Trivy scans every Docker image for OS and library CVEs before deployment
- IAM least-privilege — separate roles for cluster and node group
- Non-root container user (uid 1001) in production Dockerfile
- Kubernetes Secrets — Anthropic API key never hardcoded
- Private ECR — container images not publicly accessible
- Multi-stage Docker build — no build tools in final image

---

## 📊 MLOps Layer

| Component | Tool | What It Does |
|---|---|---|
| Experiment Tracking | MLflow | Logs every /diagnose call — provider, model, confidence, herbs returned |
| Dataset Versioning | DVC | Versions herbs.json with Google Drive remote |
| Pipeline Orchestration | Airflow 2.10 | Validates herb data then reindexes Qdrant — bad data never reaches production |

---

## 📈 Observability

Prometheus + Grafana installed via Helm on the EKS cluster:
- Live cluster memory utilization (44.8% across 2 nodes during deployment)
- Kubernetes cluster monitoring dashboard (ID 3119)
- Node-level CPU and network I/O metrics

---

## 🚀 Quickstart (Local)

**Prerequisites:** Python 3.12, Docker, Node 18+, Ollama

```bash
git clone https://github.com/ao93/rootsandqi.git
cd rootsandqi
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

ollama pull llama3
ollama pull nomic-embed-text
docker run -p 6333:6333 qdrant/qdrant

python -m scripts.index_herbs
python -m uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

**Example request:**
```bash
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "symptoms": "Chronic fatigue and cold hands and feet",
    "tongue_observation": {
      "color": "pale",
      "coating": "thin white",
      "shape": "slightly swollen",
      "moisture": "normal"
    }
  }'
```

---

## 🏗️ Infrastructure Management

**Spin up (~15 min, ~$0.15/hr while running):**
```bash
cd infra/terraform
terraform init && terraform apply -auto-approve
aws eks update-kubeconfig --name rootsandqi-cluster --region us-east-2
kubectl apply -f ../k8s/namespace.yaml
kubectl apply -f ../k8s/qdrant.yaml
kubectl apply -f ../k8s/api.yaml
kubectl create secret generic rootsandqi-secrets \
  --namespace rootsandqi \
  --from-literal=anthropic-api-key=YOUR_KEY
```

**Spin down (stops all billing):**
```bash
cd infra/terraform && terraform destroy -auto-approve
```

---

## 🐛 Build Log

[BUILD_LOG.md](BUILD_LOG.md) documents **25 issues** encountered and resolved across all milestones — including ARM64 vs AMD64 platform mismatch, Airflow 3.0 to 2.10 migration, Prometheus PVC issues, t3.micro Free Tier restriction, and more.

---

## 🗺️ Milestones

- [x] Milestone 1 — AI diagnostic core (FastAPI + LangChain + Qdrant)
- [x] Milestone 2 — TCM + Indigenous herb knowledge base
- [x] Milestone 3 — MLOps layer (MLflow, DVC, Airflow)
- [x] Milestone 4 — React + Vite frontend
- [x] Milestone 5 — AWS EKS deployment (Terraform, CI/CD, Trivy, Prometheus/Grafana)
- [x] Milestone 6 — Compliance docs + polish

---

## 👨‍💻 Engineer

**Adolfo Ovalles**
DevOps / MLOps Engineer
[LinkedIn](https://linkedin.com/in/aovalles/) | [GitHub](https://github.com/ao93)

---

## 🔮 Roadmap / Future Improvements

- **Per-tradition herb retrieval** — retrieve top-N per tradition and merge, guaranteeing both TCM and Indigenous herbs always appear
- **Qdrant persistence on EKS** — EBS CSI driver + PersistentVolumeClaim for durable storage
- **Frontend deployment to EKS** — containerize React app and deploy alongside the API
- **CKA certification** — pursuing Certified Kubernetes Administrator to deepen EKS/Kubernetes operations
