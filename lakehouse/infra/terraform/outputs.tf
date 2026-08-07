output "warehouse_bucket" {
  description = "S3 bucket backing the Iceberg warehouse."
  value       = aws_s3_bucket.warehouse.id
}

output "warehouse_uri" {
  description = "Set ICEBERG_WAREHOUSE to this in prod."
  value       = "s3://${aws_s3_bucket.warehouse.id}"
}

output "glue_databases" {
  description = "Glue Data Catalog databases (Iceberg namespaces) per layer."
  value       = { for layer, db in aws_glue_catalog_database.layer : layer => db.name }
}

output "pipeline_role_arn" {
  description = "IAM role the pipeline assumes."
  value       = aws_iam_role.pipeline.arn
}
