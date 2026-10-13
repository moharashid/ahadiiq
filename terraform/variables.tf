variable "aws_s3_bucket_name" {
  description = "The name of the S3 bucket to create"
  type        = string
  default     = "my-terraform-bucket"

}

variable "aws_ecr_repository_name" {
  description = "The name of the ECR repository to create"
  type        = string
  default     = "ahadiiq"
}