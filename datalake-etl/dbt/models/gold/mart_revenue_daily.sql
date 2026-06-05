{{ config(
    post_hook="{{ export_parquet(this, lake_partition_path('gold/mart_revenue_daily')) }}"
) }}

SELECT
    dt,
    count(*) AS order_count,
    round(sum(amount_usd), 2) AS revenue_usd
FROM {{ ref('orders') }}
GROUP BY dt
