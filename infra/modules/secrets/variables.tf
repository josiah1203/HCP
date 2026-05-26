variable "environment" {
  type = string
}

variable "service" {
  type        = string
  description = "HCP service name (api, parser, graph)"
}

variable "secret_names" {
  type        = list(string)
  description = "Secret leaf names under hcp/{env}/{service}/"
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}
