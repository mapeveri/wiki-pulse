# Event schemas

These Avro schema (`.avsc`) files define the contracts for Kafka events:

- `pageviews.avsc`: `pageviews.raw` events
- `articles.avsc`: `articles.raw` events
- `dlq.avsc`: `<source-topic>.dlq` failure envelopes

The Python producer and Go crawler register their schemas with Redpanda Schema
Registry and publish Confluent wire-format Avro (magic byte + schema ID + Avro
datum). The sink and DLQ CLI resolve that ID through Schema Registry before
decoding. DLQ envelopes store original key/value bytes, so replay preserves the
original event exactly.

The clients set the registry compatibility mode to `BACKWARD` before
registering. When adding a field, give it a default (for example,
`{"type": ["null", "string"], "default": null}`) so new readers can read
older records. Avoid changing a field's type or removing it without a migration
plan.

The schemas are loaded from `schemas/` by both runtimes. In containers this
directory is copied to `/app/schemas` and `WIKIPULSE_SCHEMA_DIR` points there.
Set `SCHEMA_REGISTRY_URL` to the registry endpoint; local default is
`http://localhost:8081`.
