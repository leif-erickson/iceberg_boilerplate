{% macro lake_path(entity) %}
  {{ return(var('lake_root') ~ '/' ~ entity ~ '/dt=' ~ var('ds') ~ '/*.parquet') }}
{% endmacro %}

{% macro lake_partition_path(entity) %}
  {{ return(var('lake_root') ~ '/' ~ entity ~ '/dt=' ~ var('ds')) }}
{% endmacro %}
