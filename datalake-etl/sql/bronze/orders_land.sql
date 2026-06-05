-- Land staging orders into bronze for one partition date.
-- Vars: lake_root, ds, source_uri

INSTALL httpfs;
LOAD httpfs;

COPY (
    SELECT
        order_id,
        customer_id,
        amount_usd::DOUBLE AS amount_usd,
        status,
        event_ts::TIMESTAMP AS event_ts,
        '{{ ds }}'::DATE AS dt,
        current_timestamp AS _ingested_at,
        '{{ source_uri }}' AS _source_file
    FROM read_parquet('{{ lake_root }}/staging/orders/{{ ds }}/*.parquet', union_by_name = true)
) TO '{{ lake_root }}/bronze/orders/dt={{ ds }}/orders.parquet'
(FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE);
