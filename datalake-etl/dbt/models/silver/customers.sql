{{ config(
    post_hook="{{ export_parquet(this, lake_partition_path('silver/customers')) }}"
) }}

SELECT DISTINCT
    customer_id,
    min(event_ts) AS first_seen_at,
    max(event_ts) AS last_seen_at,
    dt
FROM {{ ref('orders') }}
GROUP BY customer_id, dt
