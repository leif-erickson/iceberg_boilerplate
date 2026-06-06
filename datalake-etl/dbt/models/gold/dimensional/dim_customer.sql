{{ config(
    tags=['dimensional'],
    post_hook="{{ export_parquet(this, lake_partition_path('gold/dimensional/dim_customer')) }}"
) }}

SELECT
    customer_id,
    first_seen_at,
    last_seen_at,
    dt
FROM {{ ref('customers') }}
