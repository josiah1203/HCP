variable "environment" {
  type = string
}

variable "service" {
  type    = string
  default = "api"
}

variable "secret_names" {
  type    = list(string)
  default = ["database_url", "jwt_secret"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
