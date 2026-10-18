output "s3_bucket_name" {
  value = aws_s3_bucket.bucket.bucket
}
output "ecr_repository_url" {
  value = aws_ecr_repository.repository.repository_url
}
output "vpc_id" {
  value = module.vpc.vpc_id
}
output "private_subnet_ids" {
  value = module.vpc.private_subnets
}
output "database_subnet_ids" {
  value = module.vpc.database_subnets
}
output "public_subnet_ids" {
  value = module.vpc.public_subnets
}
output "ecs_security_group_id" {
  value = aws_security_group.ecs_sg.id
}
output "rds_security_group_id" {
  value = aws_security_group.rds_sg.id
}
output "sqs_queue_url" {
  value = module.sqs.queue_url
}
output "sqs_queue_arn" {
  value = module.sqs.queue_arn
}