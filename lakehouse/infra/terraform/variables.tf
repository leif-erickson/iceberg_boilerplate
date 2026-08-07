variable "region" {
  description = "AWS region for the lakehouse."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix for resource names (globally-unique S3 bucket derives from this + account id)."
  type        = string
  default     = "acme-lakehouse"
}

variable "namespaces" {
  description = "Glue databases to create (one per medallion layer)."
  type        = list(string)
  default     = ["bronze", "silver", "gold"]
}

variable "lakeformation_admins" {
  description = "IAM principal ARNs to register as Lake Formation data lake admins."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default = {
    project = "lakehouse"
    managed = "terraform"
  }
}
