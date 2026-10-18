data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  region   = data.aws_region.current.region
  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 2)
}
resource "aws_s3_bucket" "bucket" {
  bucket = format("%s-%s-%s", var.aws_s3_bucket_name, data.aws_caller_identity.current.account_id, data.aws_region.current.region)

}

resource "aws_ecr_repository" "repository" {
  name                 = var.aws_ecr_repository_name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "ahadiiq-vpc"
  cidr = local.vpc_cidr

  azs              = local.azs
  private_subnets  = [for i in range(2) : cidrsubnet(local.vpc_cidr, 8, i)]
  database_subnets = [for i in range(2) : cidrsubnet(local.vpc_cidr, 8, i + 2)]
  public_subnets   = [for i in range(2) : cidrsubnet(local.vpc_cidr, 8, i + 4)]


  enable_nat_gateway = true
  single_nat_gateway = true


}

resource "aws_security_group" "ecs_sg" {
  name        = "ahadiiq-ecs-sg"
  description = "Security group for ECS cluster"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 8000
    to_port   = 8000
    protocol  = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "ahadiiq-rds-sg"
  description = "Security group for RDS instance"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
module "db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier                          = "ahadiiq-db"
  engine                              = "postgres"
  engine_version                      = "17"
  family                              = "postgres17"
  major_engine_version                = "17"
  instance_class                      = "db.t4g.micro"
  allocated_storage                   = 20
  iam_database_authentication_enabled = true
  subnet_ids                          = module.vpc.database_subnets
  create_db_instance                  = true
  publicly_accessible                 = false
  multi_az                            = false
  skip_final_snapshot                 = true
  manage_master_user_password         = true

}

module "sqs" {
  source  = "terraform-aws-modules/sqs/aws"
  version = "~> 5.2"

  name = "ahadi-sqs"

  create_dlq = true
  redrive_policy = {
    # default is 5 for this module
    maxReceiveCount = 3
  }
  visibility_timeout_seconds = 900
  message_retention_seconds = 345600
  dlq_message_retention_seconds = 1209600
}
