variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "eks-pipeline"
}

variable "key_name" {
  description = "EC2 key pair name for bastion SSH access"
  type        = string
}

variable "my_home_ip" {
  description = "Your current public IP, for restricting bastion SSH access"
  type        = string
}

variable "docdb_username" {
  description = "DocumentDB master username"
  type        = string
  sensitive   = true
}

variable "docdb_password" {
  description = "DocumentDB master password"
  type        = string
  sensitive   = true
}