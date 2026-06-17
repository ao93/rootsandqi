# ── RootsAndQi — Terraform Infrastructure ────────────────────────────────────
# Provisions: VPC, EKS cluster, ECR repositories, IAM roles
# Region: us-east-2
# Profile: rootsandqi (IAM user, not root)

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "rootsandqi"
}

# ── Data sources ──────────────────────────────────────────────────────────────

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
