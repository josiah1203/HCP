variable "environment" {
  type        = string
  description = "Deployment environment: dev, staging, prod"
}

variable "database_name" {
  type        = string
  description = "Postgres database name"
  default     = "hcp"
}

variable "instance_class" {
  type        = string
  description = "Database instance size (provider-specific)"
  default     = "small"
}

variable "multi_az" {
  type        = bool
  description = "Enable multi-AZ (prod)"
  default     = false
}

variable "tags" {
  type        = map(string)
  default     = {}
}
