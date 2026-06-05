{{ config(
    tags=['denormalized'],
    post_hook="{{ export_parquet(this, lake_partition_path('gold/denormalized/mart_revenue_daily')) }}"
) }}

SELECT
    dt,
    count(*) AS order_count,
    count(DISTINCT customer_id) AS customer_count,
    round(sum(amount_usd), 2) AS revenue_usd,
    round(avg(amount_usd), 2) AS avg_order_usd
FROM {{ ref('orders') }}
GROUP BY dt
