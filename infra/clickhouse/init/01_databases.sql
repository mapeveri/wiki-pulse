-- Layered databases, following a raw -> staging -> marts flow.
--   raw     : data exactly as ingested (append-mostly, idempotent keys)
--   staging : cleaned, typed and deduplicated models (owned by dbt)
--   marts   : business aggregates that power the API and dashboard (owned by dbt)

CREATE DATABASE IF NOT EXISTS raw;
CREATE DATABASE IF NOT EXISTS staging;
CREATE DATABASE IF NOT EXISTS marts;
