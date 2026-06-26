terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "harjotsingh2k19-eks-pipeline-tfstate"
    key     = "eks-pipeline/terraform.tfstate"
    region  = "ap-south-1"
    encrypt = true
  }
}