{% macro export_parquet(relation, destination_dir) %}
  COPY (SELECT * FROM {{ relation }})
  TO '{{ destination_dir }}/data.parquet'
  (FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE);
{% endmacro %}
