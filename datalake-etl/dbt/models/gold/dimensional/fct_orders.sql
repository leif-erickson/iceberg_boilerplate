{{ config(
    tags=['dimensional'],
    post_hook="{{ export_parquet(this, lake_partition_path('gold/dimensional/fct_orders')) }}"
) }}

SELECT
    o.order_id,
    o.customer_id,
    o.amount_usd,
    o.status,
    o.event_ts,
    o.dt,
    c.first_seen_at AS customer_first_seen_at
FROM {{ ref('orders') }} AS o
LEFT JOIN {{ ref('dim_customer') }} AS c
    ON o.customer_id = c.customer_id
   AND o.dt = c.dt
