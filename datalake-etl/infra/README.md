# AWS deployment sketch

Prod runs the same container image as local. Only `LAKE_ROOT`, `DS`, and IAM role differ.

## Resources

| Resource | Purpose |
|----------|---------|
| S3 bucket | `s3://company-datalake` — same folder layout as `./lake` |
| Glue databases | `bronze_db`, `silver_db`, `gold_db` — external tables with partition projection on `dt` |
| ECR | `datalake-etl` image from `datalake-etl/Dockerfile` |
| ECS Fargate scheduled task | Runs `python scripts/run_pipeline.py all` |
| IAM task role | `s3:GetObject/PutObject` on lake prefix; optional `glue:*` on catalog |
| CloudWatch | Log group + alarm on task exit code != 0 |

## ECS task overrides (prod)

```bash
LAKE_ROOT=s3://company-datalake
DS=2026-06-05
DBT_TARGET=prod
AWS_REGION=us-east-1
```

The task uses the instance/task IAM role — no static AWS keys in the container.

## Glue external table example (silver.orders)

```sql
CREATE EXTERNAL TABLE silver_db.orders (
  order_id string,
  customer_id string,
  amount_usd double,
  status string,
  event_ts timestamp,
  dt date,
  _ingested_at timestamp,
  _source_file string
)
PARTITIONED BY (dt)
STORED AS PARQUET
LOCATION 's3://company-datalake/silver/orders/'
TBLPROPERTIES (
  'projection.enabled'='true',
  'projection.dt.type'='date',
  'projection.dt.range'='2024-01-01,2030-12-31',
  'projection.dt.format'='yyyy-MM-dd',
  'storage.location.template'='s3://company-datalake/silver/orders/dt=${dt}'
);
```

## Optional orchestration

- **Simple:** EventBridge cron → ECS RunTask (one pipeline).
- **Multi-source DAG:** Step Functions calling the same image with `stage` arg (`bronze`, `silver`, `gold`).

Add CDK/Terraform here when you are ready to provision; the application contract is unchanged.
