"""Avro wire encoding for the event contracts in ``schemas/``."""

from __future__ import annotations

import io
import json
import os
import struct
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import httpx
from fastavro import parse_schema, schemaless_reader, schemaless_writer


def _schema_path(name: str) -> Path:
    configured = os.getenv("WIKIPULSE_SCHEMA_DIR")
    candidates = ([Path(configured)] if configured else []) + [
        Path.cwd() / "schemas",
        Path(__file__).resolve().parents[3] / "schemas",
    ]
    for directory in candidates:
        path = directory / f"{name}.avsc"
        if path.is_file():
            return path
    raise FileNotFoundError(f"Cannot find {name}.avsc; set WIKIPULSE_SCHEMA_DIR")


@lru_cache(maxsize=8)
def _schema(name: str) -> dict:
    return parse_schema(json.loads(_schema_path(name).read_text(encoding="utf-8")))


def _registry_url() -> str:
    return os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081").rstrip("/")


@lru_cache(maxsize=16)
def _register_schema(topic: str, name: str) -> int:
    schema_text = _schema_path(name).read_text(encoding="utf-8")
    subject = f"{topic}-value"
    with httpx.Client(timeout=10.0) as client:
        client.put(
            f"{_registry_url()}/config",
            json={"compatibility": "BACKWARD"},
        ).raise_for_status()
        response = client.post(
            f"{_registry_url()}/subjects/{quote(subject, safe='')}/versions",
            json={"schema": schema_text, "schemaType": "AVRO"},
            headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
        )
        response.raise_for_status()
    return int(response.json()["id"])


@lru_cache(maxsize=64)
def _schema_by_id(schema_id: int) -> dict:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{_registry_url()}/schemas/ids/{schema_id}")
        response.raise_for_status()
    return parse_schema(json.loads(response.json()["schema"]))


def encode_event(topic: str, name: str, event: dict) -> bytes:
    output = io.BytesIO()
    schemaless_writer(output, _schema(name), event)
    schema_id = _register_schema(topic, name)
    return b"\x00" + struct.pack(">I", schema_id) + output.getvalue()


def decode_event(value: bytes) -> dict:
    if len(value) < 5 or value[0] != 0:
        raise ValueError("message is missing the Confluent Avro wire header")
    schema_id = struct.unpack(">I", value[1:5])[0]
    return schemaless_reader(io.BytesIO(value[5:]), _schema_by_id(schema_id))
