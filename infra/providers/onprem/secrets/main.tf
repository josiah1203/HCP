module "secrets" {
  source = "../../../modules/secrets"

  environment = var.environment
  service     = var.service
  secret_names = [
    "database_url",
    "jwt_secret",
    "minio_access_key",
    "minio_secret_key",
  ]
  tags = var.tags
}

locals {
  vault_path_prefix = "secret/hcp/${var.environment}/${var.service}"
}

output "secret_paths" {
  value = module.secrets.secret_paths
}

output "vault_path_prefix" {
  value = var.use_vault ? local.vault_path_prefix : null
}

output "backend" {
  value = var.use_vault ? "vault" : "env"
}
