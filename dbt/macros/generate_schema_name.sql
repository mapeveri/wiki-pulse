{- Use the custom schema name verbatim so models land in the `staging` and
   `marts` databases instead of the dbt default "<target_schema>_<custom>". -}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
