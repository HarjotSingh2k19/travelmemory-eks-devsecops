module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.34"

  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private[*].id # nodes go in PRIVATE subnets

  enable_irsa = true # creates the OIDC provider — required for IRSA later

  cluster_endpoint_public_access  = false # we'll flip this to false once the bastion exists
  cluster_endpoint_private_access = true

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }

  tags = {
    Project = var.cluster_name
  }
}