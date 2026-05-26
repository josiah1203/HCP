output "secret_paths" {
  value = [for n in var.secret_names : "hcp/${var.environment}/${var.service}/${n}"]
}
