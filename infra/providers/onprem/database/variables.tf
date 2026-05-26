variable "environment" {
  type = string
}

variable "database_name" {
  type    = string
  default = "hcp"
}

variable "postgres_namespace" {
  type    = string
  default = "hcp"
}

variable "tags" {
  type    = map(string)
  default = {}
}
