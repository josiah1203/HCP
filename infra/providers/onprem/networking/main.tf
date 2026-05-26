module "networking" {
  source = "../../../modules/networking"

  environment         = var.environment
  vpc_cidr            = var.cluster_cidr
  public_subnet_cidrs = []
  private_subnet_cidrs = [
    cidrsubnet(var.cluster_cidr, 8, 0),
    cidrsubnet(var.cluster_cidr, 8, 1),
  ]
  tags = var.tags
}

output "cluster_cidr" {
  value = module.networking.vpc_cidr
}

output "private_subnet_cidrs" {
  value = module.networking.private_subnet_cidrs
}
