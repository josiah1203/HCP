variable "environment" {
  type = string
}

variable "bucket_name" {
  type    = string
  default = "hcp-local"
}

variable "minio_namespace" {
  type    = string
  default = "hcp"
}

variable "tags" {
  type    = map(string)
  default = {}
}
