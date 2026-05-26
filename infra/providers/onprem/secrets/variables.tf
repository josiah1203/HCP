variable "environment" {
  type = string
}

variable "service" {
  type    = string
  default = "api"
}

variable "use_vault" {
  type        = bool
  description = "Use HashiCorp Vault; false uses env-based secrets (compose dev)"
  default     = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
