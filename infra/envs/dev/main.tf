terraform {
  required_version = ">= 1.7.0"
}

locals {
  environment = "dev"
  common_tags = {
    project     = "hcp"
    environment = local.environment
    managed_by  = "terraform"
  }
}

module "onprem_networking" {
  source = "../../providers/onprem/networking"

  environment  = local.environment
  cluster_cidr = "10.42.0.0/16"
  tags         = local.common_tags
}

module "onprem_storage" {
  source = "../../providers/onprem/storage"

  environment = local.environment
  bucket_name = "hcp-local"
  tags        = local.common_tags
}

module "onprem_database" {
  source = "../../providers/onprem/database"

  environment = local.environment
  tags        = local.common_tags
}

module "onprem_secrets" {
  source = "../../providers/onprem/secrets"

  environment = local.environment
  use_vault   = false
  tags        = local.common_tags
}

output "storage_bucket" {
  value = module.onprem_storage.bucket_name
}

output "postgres_host" {
  value = module.onprem_database.postgres_host
}

output "secret_paths" {
  value = module.onprem_secrets.secret_paths
}
