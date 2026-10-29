data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_iam_role" "ecs_task_execution_role" {
  name = "ECS_Task_Execution_Role"
}
data "aws_iam_role" "ecs_task_role_api" {
  name = "API_task_role"
}
data "aws_iam_role" "ecs_task_role_worker" {
  name = "Ingestion_worker_task_role"
}
data "aws_iam_role" "ecs_notifier_task_role" {
  name = "Notifier_task_role"
}
data "aws_iam_role" "ecs_event_scheduler" {
  name = "EventBridge_invocation_role"
}
locals {
  region   = data.aws_region.current.region
  vpc_cidr = "10.0.0.0/16"
  azs      = slice(data.aws_availability_zones.available.names, 0, 2)
  db_name  = "ahadiiq"
  db_user  = "ahadiiq_admin"
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
  database_subnet_group_name = "ahadiiq-db-subnet-group"
  create_database_subnet_group = true

  enable_nat_gateway = true
  single_nat_gateway = true


}


resource "aws_security_group" "ecs_sg" {
  name        = "ahadiiq-ecs-sg"
  description = "Security group for ECS cluster"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [module.alb.security_group_id]
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
  version = "~> 7.2"
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
  db_subnet_group_name = module.vpc.database_subnet_group_name
  publicly_accessible                 = false
  multi_az                            = false
  skip_final_snapshot                 = true
  manage_master_user_password         = true
  username                            = local.db_user
  db_name                             = local.db_name
  kms_key_id                          = aws_kms_key.rds.arn
  master_user_secret_kms_key_id       = aws_kms_key.rds.arn
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

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
  visibility_timeout_seconds    = 900
  message_retention_seconds     = 345600
  dlq_message_retention_seconds = 1209600
}


module "ecs" {
  source  = "terraform-aws-modules/ecs/aws"
  version = "~> 7.6.1"

  cluster_name = "ahadiiq-ecs-cluster"

  # Cluster capacity providers
  cluster_capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  default_capacity_provider_strategy = {
    FARGATE = {
      weight = 100
      base   = 1
    }
  }

}

resource "aws_ecs_task_definition" "worker_task" {
  family                   = "ahadiiq-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = data.aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = data.aws_iam_role.ecs_task_role_worker.arn
  cpu                      = 1024
  memory                   = 2048

  container_definitions = jsonencode([
    {
      name      = "ahadiiq-worker"
      image     = "${aws_ecr_repository.repository.repository_url}:v7"
      essential = true
      command   = ["python", "-m", "app.workers.processor"]

      environment = [
        { name = "AWS_REGION", value = "${data.aws_region.current.region}" },
        { name = "POSTGRES_HOST", value = tostring(module.db.db_instance_address) },
        { name = "POSTGRES_PORT", value = tostring(module.db.db_instance_port) },
        { name = "POSTGRES_DB", value = tostring(module.db.db_instance_name) },
        { name = "S3_BUCKET_NAME", value = tostring(aws_s3_bucket.bucket.bucket) },
        { name = "QUEUE_URL", value = tostring(module.sqs.queue_url) }
      ]

      secrets = [
        { name = "POSTGRES_USER", valueFrom = "${module.db.db_instance_master_user_secret_arn}:username::" },
        { name = "POSTGRES_PASSWORD", valueFrom = "${module.db.db_instance_master_user_secret_arn}:password::" },
        { name = "ANTHROPIC_API_KEY", valueFrom = "${aws_secretsmanager_secret.anthropic.arn}"}
      ]


      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = "${data.aws_region.current.region}"
          "awslogs-stream-prefix" = "worker"
        }
      }
    }
  ])

}

resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "ahadiiq/anthropic-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id                = aws_secretsmanager_secret.anthropic.id
  secret_string_wo         = var.anthropic_api_key # write-only → NOT in state
  secret_string_wo_version = 2                     # bump this number to push a new value
}
resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/ahadiiq-worker"
  retention_in_days = 14
}

resource "aws_ecs_service" "worker_service" {
  name            = "ahadiiq-worker-service"
  cluster         = module.ecs.cluster_id
  task_definition = aws_ecs_task_definition.worker_task.arn
  desired_count   = 1
  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  depends_on = [module.ecs]
}

resource "aws_ecs_task_definition" "api_task" {
  family                   = "ahadiiq-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = data.aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = data.aws_iam_role.ecs_task_role_api.arn
  cpu                      = 256
  memory                   = 512

  container_definitions = jsonencode([
    {
      name      = "ahadiiq-api"
      image     = "${aws_ecr_repository.repository.repository_url}:v7"
      essential = true
      command   = ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

      environment = [
        { name = "AWS_REGION", value = "${data.aws_region.current.region}" },
        { name = "POSTGRES_HOST", value = tostring(module.db.db_instance_address) },
        { name = "POSTGRES_PORT", value = tostring(module.db.db_instance_port) },
        { name = "POSTGRES_DB", value = tostring(module.db.db_instance_name) },
        { name = "S3_BUCKET_NAME", value = tostring(aws_s3_bucket.bucket.bucket) },
        { name = "QUEUE_URL", value = tostring(module.sqs.queue_url) },
        { name = "RUN_MIGRATIONS", value = "true" }

      ]

      secrets = [
        { name = "POSTGRES_USER", valueFrom = "${module.db.db_instance_master_user_secret_arn}:username::" },
        { name = "POSTGRES_PASSWORD", valueFrom = "${module.db.db_instance_master_user_secret_arn}:password::" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = "${data.aws_region.current.region}"
          "awslogs-stream-prefix" = "api"
        }
      }
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
        }
      ]
    }
  ])

}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/ahadiiq-api"
  retention_in_days = 14
}

module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name                       = "ahadiiq-alb"
  vpc_id                     = module.vpc.vpc_id
  subnets                    = module.vpc.public_subnets
  enable_deletion_protection = false

  # Security Group
  security_group_ingress_rules = {
    all_http = {
      from_port   = 80
      to_port     = 80
      ip_protocol = "tcp"
      description = "HTTP web traffic"
      cidr_ipv4   = "0.0.0.0/0"
    }
    all_https = {
      from_port   = 443
      to_port     = 443
      ip_protocol = "tcp"
      description = "HTTPS web traffic"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }
  security_group_egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = local.vpc_cidr
    }
  }


  listeners = {
    http = {
      port     = 80
      protocol = "HTTP"
      forward = {
        target_group_key = "api_task"
      }
    }

  }

  target_groups = {
    api_task = {
      name              = "ahadiiq-api-tg"
      protocol          = "HTTP"
      port              = 8000
      target_type       = "ip"
      create_attachment = false
      health_check = {
        path    = "/health"
        matcher = "200"
      }
    }

  }

}

resource "aws_ecs_service" "api_service" {
  name            = "ahadiiq-api-service"
  cluster         = module.ecs.cluster_id
  task_definition = aws_ecs_task_definition.api_task.arn
  desired_count   = 1
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = module.alb.target_groups["api_task"].arn
    container_name   = "ahadiiq-api"
    container_port   = 8000
  }
  depends_on = [module.ecs, module.alb]
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for AhadiIQ RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "rds" {
  name          = "alias/ahadiiq-rds"
  target_key_id = aws_kms_key.rds.key_id
}