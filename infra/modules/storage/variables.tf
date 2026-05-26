variable "environment" {
  type        = string
  description = "Deployment environment: dev, staging, prod"
}

variable "bucket_name" {
  type        = string
  description = "Logical object storage bucket name"
}

variable "enable_replication" {
  type        = bool
  description = "Enable cross-region replication (prod only)"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Common resource tags"
  default     = {}
}
