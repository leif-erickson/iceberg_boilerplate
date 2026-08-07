data "aws_caller_identity" "current" {}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  warehouse_name = "${var.name_prefix}-warehouse-${local.account_id}"
}

# ---------------------------------------------------------------------------
# Iceberg warehouse bucket (S3).
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "warehouse" {
  bucket = local.warehouse_name
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "warehouse" {
  bucket = aws_s3_bucket.warehouse.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "warehouse" {
  bucket = aws_s3_bucket.warehouse.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "warehouse" {
  bucket                  = aws_s3_bucket.warehouse.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# Glue Data Catalog: the Iceberg catalog in prod (one database per layer).
# Iceberg *tables* are created at runtime by the engine (PyIceberg/Athena/Spark)
# and governed by the data contracts, so they are not declared here.
# ---------------------------------------------------------------------------
resource "aws_glue_catalog_database" "layer" {
  for_each = toset(var.namespaces)
  name     = "${replace(var.name_prefix, "-", "_")}_${each.value}"

  location_uri = "s3://${aws_s3_bucket.warehouse.id}/${each.value}"
}

# ---------------------------------------------------------------------------
# IAM role assumed by the pipeline (Dagster on ECS / Glue job).
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com", "glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "pipeline" {
  name               = "${var.name_prefix}-pipeline"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

data "aws_iam_policy_document" "pipeline" {
  statement {
    sid       = "WarehouseObjectAccess"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.warehouse.arn}/*"]
  }
  statement {
    sid       = "WarehouseListAccess"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [aws_s3_bucket.warehouse.arn]
  }
  statement {
    sid    = "GlueCatalogAccess"
    effect = "Allow"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases",
      "glue:GetTable", "glue:GetTables",
      "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
    ]
    resources = ["*"]
  }
  statement {
    sid    = "LakeFormationAccess"
    effect = "Allow"
    actions = [
      "lakeformation:GetDataAccess",
      "lakeformation:GetResourceLFTags",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "pipeline" {
  name   = "${var.name_prefix}-pipeline"
  role   = aws_iam_role.pipeline.id
  policy = data.aws_iam_policy_document.pipeline.json
}

# ---------------------------------------------------------------------------
# Lake Formation: fine-grained governance over the catalog.
# ---------------------------------------------------------------------------
resource "aws_lakeformation_data_lake_settings" "this" {
  admins = length(var.lakeformation_admins) > 0 ? var.lakeformation_admins : [data.aws_caller_identity.current.arn]
}

resource "aws_lakeformation_permissions" "pipeline_layer" {
  for_each    = aws_glue_catalog_database.layer
  principal   = aws_iam_role.pipeline.arn
  permissions = ["ALL"]

  database {
    name = each.value.name
  }

  depends_on = [aws_lakeformation_data_lake_settings.this]
}
