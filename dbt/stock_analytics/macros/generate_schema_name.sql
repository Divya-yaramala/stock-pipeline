{% macro generate_schema_name(custom_schema_name, node) -%}
    {#
      Override default dbt schema-naming so models land in the exact schema
      specified in dbt_project.yml (e.g. "staging", "intermediate", "mart")
      rather than "<target_schema>_<custom_schema>".
    #}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
