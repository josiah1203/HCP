module "secrets" {
  source = "../../../modules/secrets"

  environment  = var.environment
  service      = var.service
  secret_names = var.secret_names
  tags         = var.tags
}

resource "aws_secretsmanager_secret" "hcp" {
  for_each = toset(var.secret_names)
  name     = "hcp/${var.environment}/${var.service}/${each.key}"
  tags     = var.tags
}

output "secret_paths" {
  value = module.secrets.secret_paths
}

output "secret_arns" {
  value = { for k, s in aws_secretsmanager_secret.hcp : k => s.arn }
}
