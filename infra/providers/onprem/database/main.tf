module "database" {
  source = "../../../modules/database"

  environment    = var.environment
  database_name  = var.database_name
  instance_class = "small"
  multi_az       = false
  tags           = var.tags
}

output "database_name" {
  value = module.database.database_name
}

output "connection_secret_name" {
  value = module.database.connection_secret_name
}

output "postgres_host" {
  value = "postgres.${var.postgres_namespace}.svc.cluster.local"
}
