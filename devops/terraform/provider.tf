provider "aws" {
  region = var.aws_region
}

# checks AZs are currently available in this region -> ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
data "aws_availability_zones" "available" {
  state = "available"
}