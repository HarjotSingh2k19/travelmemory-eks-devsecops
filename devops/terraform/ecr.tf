resource "aws_ecr_repository" "backend" {
  name                 = "travelmemory-backend"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Project = var.cluster_name }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "travelmemory-frontend"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = { Project = var.cluster_name }
}