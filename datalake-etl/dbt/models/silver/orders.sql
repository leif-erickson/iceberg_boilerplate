{{ config(
    post_hook="{{ export_parquet(this, lake_partition_path('silver/orders')) }}"
) }}

WITH raw AS (
    SELECT *
    FROM read_parquet('{{ lake_path('bronze/orders') }}', union_by_name = true)
),
deduped AS (
    SELECT * EXCLUDE (rn)
    FROM (
        SELECT
            *,
            row_number() OVER (
                PARTITION BY order_id
                ORDER BY _ingested_at DESC
            ) AS rn
        FROM raw
    )
    WHERE rn = 1
)

SELECT
    order_id,
    customer_id,
    amount_usd,
    status,
    event_ts,
    dt,
    _ingested_at,
    _source_file
FROM deduped
WHERE status = 'paid'
