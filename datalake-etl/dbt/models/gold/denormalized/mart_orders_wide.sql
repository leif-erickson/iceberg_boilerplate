{{ config(
    tags=['denormalized'],
    post_hook="{{ export_parquet(this, lake_partition_path('gold/denormalized/mart_orders_wide')) }}"
) }}

SELECT
    o.order_id,
    o.customer_id,
    o.amount_usd,
    o.status,
    o.event_ts,
    o.dt,
    c.first_seen_at AS customer_first_seen_at,
    c.last_seen_at AS customer_last_seen_at,
    date_diff('day', c.first_seen_at::DATE, o.event_ts::DATE) AS customer_tenure_days
FROM {{ ref('orders') }} AS o
LEFT JOIN {{ ref('customers') }} AS c
    ON o.customer_id = c.customer_id
   AND o.dt = c.dt
