# RootsAndQi

[![CI/CD Pipeline](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ao93/rootsandqi/actions/workflows/ci-cd.yml)

AI-powered wellness insights combining Traditional Chinese Medicine (TCM) syndrome differentiation with Indigenous herbal traditions, built on a production-style FastAPI + LangChain + MLOps stack deployed on AWS EKS.

> **Disclaimer:** This project is for educational and portfolio purposes. It does not provide medical diagnoses and is not a substitute for professional medical care.

## Status: Milestone 5 Complete — Production Deployment on AWS EKS

- **Live API:** FastAPI on AWS EKS (us-east-2), served via AWS LoadBalancer
- **CI/CD:** GitHub Actions — lint → Trivy scan → Docker build (AMD64) → ECR → EKS
- **Infrastructure:** Terraform-provisioned VPC, EKS cluster, ECR repository (25 resources)
- **Observability:** Prometheus + Grafana via Helm (44.8% cluster memory utilization)
- **Security:** Trivy scans every image for HIGH/CRITICAL CVEs before deployment
- **MLOps:** MLflow tracking, DVC versioning, Airflow orchestration
- **Frontend:** React + Vite UI with two-tradition herb results layout

## Roadmap

- [x] Milestone 1: AI diagnostic core (FastAPI + LangChain syndrome mapping)
- [x] Milestone 2: Indigenous + TCM herb knowledge base (Qdrant retrieval)
- [x] Milestone 3: MLOps layer (MLflow, DVC, Airflow)
- [x] Milestone 4: React + Vite frontend
- [x] Milestone 5: DevOps/infra (Terraform, EKS, CI/CD, Trivy, Prometheus/Grafana)
- [ ] Milestone 6: Compliance docs + polish

## Build Log

See [BUILD_LOG.md](BUILD_LOG.md) for 25 issues documented across Milestones 1-5.
