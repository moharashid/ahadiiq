data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
resource "aws_s3_bucket" "bucket" {
  bucket                  = format("%s-%s-%s", var.aws_s3_bucket_name, data.aws_caller_identity.current.account_id, data.aws_region.current.region)
  
}