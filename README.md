# RootsAndQi

[![CI/CD Pipeline](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml)

An AI-powered wellness platform combining Traditional Chinese Medicine (TCM) syndrome differentiation with Indigenous herbal traditions. Built as a portfolio project to demonstrate a production-grade DevOps + MLOps stack.

> **Disclaimer:** For educational and portfolio purposes only. Not a medical diagnosis tool.

---

## What This Project Demonstrates

| Skill Area | Implementation |
|---|---|
| **Infrastructure as Code** | Terraform — VPC, EKS, ECR, IAM (25 resources, us-east-2) |
| **Container Orchestration** | Kubernetes on AWS EKS — Deployments, Services, Secrets, health probes |
| **CI/CD Pipeline** | GitHub Actions — lint, Trivy scan, Docker build (AMD64), ECR, EKS deploy |
| **Security Scanning** | Trivy scanning every image for HIGH/CRITICAL CVEs before deployment |
| **Observability** | Prometheus + Grafana via Helm — live cluster metrics |
| **MLOps Tracking** | MLflow — every /diagnose call logged with params, metrics, and tags |
| **MLOps Versioning** | DVC — herb knowledge base versioned with Google Drive remote |
| **MLOps Orchestration** | Airflow 2.10 — validate then reindex DAG with data quality gating |
| **Vector Database** | Qdrant — herb embeddings indexed via Ollama nomic-embed-text |
| **LLM Integration** | LangChain + Anthropic Claude — provider-agnostic, swap via .env |
| **API Design** | FastAPI — structured output, Pydantic validation, health checks |
| **Frontend** | React + Vite — two-tradition herb results layout |

---

## Architecture
Developer Laptop

git push to GitHub

|

v

GitHub Actions CI/CD Pipeline

Lint (ruff)
Trivy security scan
Docker build linux/amd64 and push to ECR
kubectl deploy to EKS

AWS EKS Cluster (us-east-2)

rootsandqi namespace

FastAPI Pod

LangChain + Anthropic Claude (syndrome mapping)

Qdrant client (herb vector retrieval)

MLflow (experiment tracking per request)

Qdrant Pod (vector database)

AWS LoadBalancer (public endpoint)

monitoring namespace

Prometheus (metrics scraping)

Grafana (Kubernetes cluster monitoring dashboard)
AWS Infrastructure via Terraform

VPC 10.0.0.0/16 with 2 public and 2 private subnets across 2 AZs

NAT Gateway for private node internet egress

EKS Cluster Kubernetes 1.31 with 2x t3.small worker nodes

ECR Repository with scan on push and 10-image lifecycle policy

IAM Roles with least-privilege for cluster and node group
Local Development

Airflow 2.10 via docker-compose (validate_herbs then index_herbs DAG)

DVC for herbs.json versioning with Google Drive remote

MLflow UI at localhost:5000

React + Vite frontend at localhost:5173

## Request Flow
User submits symptoms via React UI

FastAPI /diagnose endpoint

LangChain + Claude: syndrome classification, organs, confidence, reasoning

Qdrant: top herbs by vector similarity to syndrome pattern

MLflow: logs provider, model, confidence, herbs returned, traditions

Response returned to UI

## Project Structure
app/

api/diagnosis.py           POST /diagnose endpoint

core/prompts.py            TCM syndrome-mapping system prompt

data/herbs.json            15 TCM + Indigenous herbs (DVC-tracked)

services/syndrome_mapper.py    LangChain structured output

services/herb_retriever.py     Qdrant vector search

services/experiment_tracker.py MLflow run logging
infra/

terraform/   main.tf vpc.tf eks.tf ecr.tf variables.tf outputs.tf

k8s/         namespace.yaml api.yaml qdrant.yaml
.github/workflows/ci-cd.yml   4-job CI/CD pipeline

airflow/dags/reindex_herbs_dag.py

frontend/src/                  React + Vite UI

Dockerfile                     Multi-stage, non-root user, linux/amd64

BUILD_LOG.md                   25 issues documented across all milestones

## Quickstart (Local)

Prerequisites: Python 3.12, Docker, Node 18+, Ollama
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

Open http://localhost:5173

Example API call:
curl -X POST http://localhost:8000/diagnose

-H Content-Type: application/json

-d symptoms: Chronic fatigue and cold hands and feet

## Infrastructure Management

Spin up (~15 min, ~$0.15/hr while running):
cd infra/terraform

terraform init

terraform apply -auto-approve

aws eks update-kubeconfig --name rootsandqi-cluster --region us-east-2

kubectl apply -f ../k8s/namespace.yaml

kubectl apply -f ../k8s/qdrant.yaml

kubectl apply -f ../k8s/api.yaml

kubectl create secret generic rootsandqi-secrets --namespace rootsandqi --from-literal=anthropic-api-key=YOUR_KEY

Spin down (stops all billing):
cd infra/terraform && terraform destroy -auto-approve

## Known Limitations

- Herb recommendations rank all herbs by similarity without guaranteeing both traditions appear. Planned fix: top-N per tradition merged.
- Qdrant has no persistent storage on EKS. Requires reindexing after pod restart.
- t3.small nodes are cost-optimized for portfolio use. Production would use autoscaling with larger instances.

## Build Log

BUILD_LOG.md documents 25 issues encountered and resolved across all milestones including ARM64 vs AMD64 mismatch, Airflow 3.0 to 2.10 migration, and Prometheus PVC issues. Written as a real engineering log.

## Milestones

- [x] 1 - AI diagnostic core (FastAPI + LangChain + Qdrant)
- [x] 2 - TCM + Indigenous herb knowledge base
- [x] 3 - MLOps layer (MLflow, DVC, Airflow)
- [x] 4 - React + Vite frontend
- [x] 5 - AWS EKS deployment (Terraform, CI/CD, Trivy, Prometheus/Grafana)
- [ ] 6 - Compliance docs + polish
