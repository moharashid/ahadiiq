output "s3_bucket_name" {
  value = aws_s3_bucket.bucket.bucket
}
output "ecr_repository_url" {
  value = aws_ecr_repository.repository.repository_url
}