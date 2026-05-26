output "database_name" {
  value = var.database_name
}

output "connection_secret_name" {
  description = "Secrets manager path for DATABASE_URL"
  value       = "hcp/${var.environment}/api/database_url"
}
