variable "environment" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key for SSE-KMS"
  default     = null
}

variable "enable_replication" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
