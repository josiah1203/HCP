variable "environment" {
  type = string
}

variable "cluster_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "tags" {
  type    = map(string)
  default = {}
}
