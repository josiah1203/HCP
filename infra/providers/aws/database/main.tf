module "database" {
  source = "../../../modules/database"

  environment    = var.environment
  database_name  = var.database_name
  instance_class = var.instance_class
  multi_az       = var.multi_az
  tags           = var.tags
}

# Stub: RDS wiring completed when networking module provisions subnets + SGs.
resource "aws_db_subnet_group" "hcp" {
  name       = "hcp-${var.environment}"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

output "database_name" {
  value = module.database.database_name
}

output "connection_secret_name" {
  value = module.database.connection_secret_name
}

output "subnet_group_name" {
  value = aws_db_subnet_group.hcp.name
}
