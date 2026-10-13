data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
resource "aws_s3_bucket" "bucket" {
  bucket                  = format("%s-%s-%s", var.aws_s3_bucket_name, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
  
}

resource "aws_ecr_repository" "repository" {
  name = var.aws_ecr_repository_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "ahadiiq-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.3.0/24", "10.0.4.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}


