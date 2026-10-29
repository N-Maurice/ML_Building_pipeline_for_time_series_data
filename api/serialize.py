from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson import ObjectId


def jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


def record_payload(row: dict | None, id_field: str | None = None) -> dict:
    if not row:
        return {}
    payload = jsonable(dict(row))
    if id_field and id_field not in payload and "_id" in payload:
        payload[id_field] = payload["_id"]
    payload.pop("_id", None)
    return payload


def order_payload(order: dict, items: list[dict] | None = None) -> dict:
    payload = record_payload(order, "order_id")
    payload["items"] = [record_payload(item, "order_id") for item in (items if items is not None else payload.get("items") or [])]
    return payload
