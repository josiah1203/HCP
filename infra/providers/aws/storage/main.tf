module "storage" {
  source = "../../../modules/storage"

  environment        = var.environment
  bucket_name        = var.bucket_name
  enable_replication = var.enable_replication
  tags               = var.tags
}

resource "aws_s3_bucket" "artifacts" {
  bucket = var.bucket_name
  tags   = merge(var.tags, { Name = var.bucket_name, hcp_component = "object-store" })
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_arn
    }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.artifacts.id
}

output "bucket_arn" {
  value = aws_s3_bucket.artifacts.arn
}
