module "storage" {
  source = "../../../modules/storage"

  environment          = var.environment
  bucket_name          = var.bucket_name
  enable_replication   = false
  tags                 = var.tags
}

# MinIO is deployed via Helm (hcp-platform) or docker-compose for dev.
# Terraform records the logical bucket contract; runtime wiring uses PAL MinioStorageProvider.
output "bucket_name" {
  value = module.storage.bucket_name
}

output "minio_service" {
  value = "minio.${var.minio_namespace}.svc.cluster.local:9000"
}
