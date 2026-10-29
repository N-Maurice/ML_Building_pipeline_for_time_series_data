from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from api.errors import StoreError
from api.settings import get_settings

EXCLUDED_STATUSES = ["canceled", "unavailable"]
DEMO_CUSTOMER_ID = "demo-customer-001"
DEMO_PRODUCT_ID = "demo-product-001"
DEMO_ORDER_ID = "demo-order-001"
DEMO_SELLER_ID = "demo-seller-001"

_client: MongoClient | None = None


def client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(get_settings().mongo_uri, serverSelectionTimeoutMS=3000)
    return _client


def db():
    try:
        mongo = client()
        mongo.admin.command("ping")
        return mongo[get_settings().mongo_database]
    except PyMongoError as exc:
        raise StoreError(
            "MongoDB is unavailable. Start it (open Docker Desktop, then "
            "`docker compose up -d`) and confirm MONGO_URI in .env. "
            f"Original error: {exc}",
            status_code=503,
        ) from exc


def ping() -> bool:
    return ping_detail()[0]


def ping_detail() -> tuple[bool, str | None]:
    try:
        db()
        return True, None
    except StoreError as exc:
        return False, exc.message


def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _clean(doc: dict | None, id_field: str | None = None) -> dict | None:
    if not doc:
        return None
    out = dict(doc)
    if id_field and id_field not in out and "_id" in out:
        out[id_field] = str(out["_id"])
    out.pop("_id", None)
    return out


def _timestamp_range(start_date: date, end_date: date) -> dict:
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    start_s = start.strftime("%Y-%m-%d %H:%M:%S")
    end_s = end.strftime("%Y-%m-%d %H:%M:%S")
    start_d = start_date.isoformat()
    end_exclusive = (end_date + timedelta(days=1)).isoformat()
    return {
        "$or": [
            {"order_purchase_timestamp": {"$gte": start, "$lt": end}},
            {"order_purchase_timestamp": {"$gte": start_s, "$lt": end_s}},
            {"order_purchase_timestamp": {"$gte": start_d, "$lt": end_exclusive}},
        ]
    }


def list_customers(limit: int = 50) -> list[dict]:
    return [_clean(doc, "customer_id") for doc in db().customers.find().limit(limit)]


def get_customer(customer_id: str) -> Optional[dict]:
    database = db()
    doc = database.customers.find_one({"customer_id": customer_id}) or database.customers.find_one({"_id": customer_id})
    return _clean(doc, "customer_id")


def create_customer(payload: dict) -> dict:
    if get_customer(payload["customer_id"]):
        raise StoreError(f"Customer {payload['customer_id']} already exists", status_code=409)
    document = dict(payload)
    document["_id"] = payload["customer_id"]
    try:
        db().customers.insert_one(document)
    except DuplicateKeyError as exc:
        raise StoreError(f"Customer {payload['customer_id']} already exists", status_code=409) from exc
    created = get_customer(payload["customer_id"])
    if created is None:
        raise StoreError("Customer was not created", status_code=500)
    return created


def update_customer(customer_id: str, fields: dict) -> dict:
    updates = {key: value for key, value in fields.items() if value is not None}
    result = db().customers.find_one_and_update(
        {"$or": [{"customer_id": customer_id}, {"_id": customer_id}]},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        raise StoreError(f"Customer {customer_id} was not found", status_code=404)
    return _clean(result, "customer_id")


def delete_customer(customer_id: str) -> None:
    related = db().orders.count_documents({"customer_id": customer_id})
    if related:
        raise StoreError(
            f"Cannot delete customer {customer_id} while {related} order(s) still reference it",
            status_code=409,
        )
    deleted = db().customers.delete_one({"$or": [{"customer_id": customer_id}, {"_id": customer_id}]})
    if deleted.deleted_count == 0:
        raise StoreError(f"Customer {customer_id} was not found", status_code=404)


def list_products(limit: int = 50) -> list[dict]:
    return [_clean(doc, "product_id") for doc in db().products.find().limit(limit)]


def get_product(product_id: str) -> Optional[dict]:
    database = db()
    doc = database.products.find_one({"product_id": product_id}) or database.products.find_one({"_id": product_id})
    return _clean(doc, "product_id")


def create_product(payload: dict) -> dict:
    if get_product(payload["product_id"]):
        raise StoreError(f"Product {payload['product_id']} already exists", status_code=409)
    document = dict(payload)
    document["_id"] = payload["product_id"]
    try:
        db().products.insert_one(document)
    except DuplicateKeyError as exc:
        raise StoreError(f"Product {payload['product_id']} already exists", status_code=409) from exc
    created = get_product(payload["product_id"])
    if created is None:
        raise StoreError("Product was not created", status_code=500)
    return created


def update_product(product_id: str, fields: dict) -> dict:
    updates = {key: value for key, value in fields.items() if value is not None}
    result = db().products.find_one_and_update(
        {"$or": [{"product_id": product_id}, {"_id": product_id}]},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        raise StoreError(f"Product {product_id} was not found", status_code=404)
    return _clean(result, "product_id")


def delete_product(product_id: str) -> None:
    deleted = db().products.delete_one({"$or": [{"product_id": product_id}, {"_id": product_id}]})
    if deleted.deleted_count == 0:
        raise StoreError(f"Product {product_id} was not found", status_code=404)


def _items(order_id: str) -> list[dict]:
    return [_clean(doc) for doc in db().order_items.find({"order_id": order_id}, {"_id": 0}).sort("order_item_id", 1)]


def list_order_items(order_id: str | None = None, limit: int = 50) -> list[dict]:
    query = {"order_id": order_id} if order_id else {}
    return [
        _clean(doc)
        for doc in db().order_items.find(query, {"_id": 0}).sort([("order_id", 1), ("order_item_id", 1)]).limit(limit)
    ]


def get_order_item(order_id: str, order_item_id: int) -> Optional[dict]:
    return _clean(
        db().order_items.find_one({"order_id": order_id, "order_item_id": order_item_id}, {"_id": 0})
    )


def create_order_item(payload: dict) -> dict:
    if get_order(payload["order_id"]) is None:
        raise StoreError(f"Order {payload['order_id']} was not found", status_code=404)
    if get_order_item(payload["order_id"], payload["order_item_id"]):
        raise StoreError(
            f"Item {payload['order_item_id']} already exists on order {payload['order_id']}",
            status_code=409,
        )
    document = dict(payload)
    document["_id"] = f"{payload['order_id']}:{payload['order_item_id']}"
    db().order_items.insert_one(document)
    created = get_order_item(payload["order_id"], payload["order_item_id"])
    if created is None:
        raise StoreError("Order item was not created", status_code=500)
    return created


def update_order_item(order_id: str, order_item_id: int, fields: dict) -> dict:
    updates = {key: value for key, value in fields.items() if value is not None}
    result = db().order_items.find_one_and_update(
        {"order_id": order_id, "order_item_id": order_item_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )
    if result is None:
        raise StoreError(f"Item {order_item_id} on order {order_id} was not found", status_code=404)
    return _clean(result)


def delete_order_item(order_id: str, order_item_id: int) -> None:
    deleted = db().order_items.delete_one({"order_id": order_id, "order_item_id": order_item_id})
    if deleted.deleted_count == 0:
        raise StoreError(f"Item {order_item_id} on order {order_id} was not found", status_code=404)


def list_orders(limit: int = 50) -> list[dict]:
    return [
        _clean(doc, "order_id")
        for doc in db().orders.find({}, {"_id": 0}).sort([("order_purchase_timestamp", -1), ("order_id", -1)]).limit(limit)
    ]


def get_order(order_id: str) -> Optional[dict]:
    order = db().orders.find_one({"order_id": order_id}, {"_id": 0})
    if order is None:
        order = db().orders.find_one({"_id": order_id}, {"_id": 0})
        if order is not None:
            order["order_id"] = order.get("order_id", order_id)
    if order is None:
        return None
    order["items"] = _items(order.get("order_id", order_id))
    return _clean(order, "order_id")


def create_order(payload: dict) -> dict:
    if get_order(payload["order_id"]):
        raise StoreError(f"Order {payload['order_id']} already exists", status_code=409)
    document = {
        "_id": payload["order_id"],
        "order_id": payload["order_id"],
        "customer_id": payload["customer_id"],
        "order_status": payload["order_status"],
        "order_purchase_timestamp": payload["order_purchase_timestamp"],
    }
    items = []
    for item in payload.get("items") or []:
        items.append(
            {
                "_id": f"{payload['order_id']}:{item['order_item_id']}",
                "order_id": payload["order_id"],
                "order_item_id": item["order_item_id"],
                "product_id": item.get("product_id"),
                "seller_id": item.get("seller_id"),
                "price": item["price"],
                "freight_value": item.get("freight_value"),
            }
        )
    database = db()
    try:
        database.orders.insert_one(document)
        if items:
            database.order_items.insert_many(items)
    except DuplicateKeyError as exc:
        raise StoreError(f"Order {payload['order_id']} already exists", status_code=409) from exc
    created = get_order(payload["order_id"])
    if created is None:
        raise StoreError("Order was not created", status_code=500)
    return created


def update_order(order_id: str, fields: dict) -> dict:
    updates = {key: value for key, value in fields.items() if value is not None}
    result = db().orders.find_one_and_update(
        {"$or": [{"order_id": order_id}, {"_id": order_id}]},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        raise StoreError(f"Order {order_id} was not found", status_code=404)
    updated = get_order(order_id)
    if updated is None:
        raise StoreError(f"Order {order_id} was not found", status_code=404)
    return updated


def delete_order(order_id: str) -> None:
    database = db()
    deleted = database.orders.delete_one({"$or": [{"order_id": order_id}, {"_id": order_id}]})
    database.order_items.delete_many({"order_id": order_id})
    if deleted.deleted_count == 0:
        raise StoreError(f"Order {order_id} was not found", status_code=404)


def latest_order() -> Optional[dict]:
    order = db().orders.find_one(
        {"order_purchase_timestamp": {"$ne": None}},
        {"_id": 0},
        sort=[("order_purchase_timestamp", -1), ("order_id", -1)],
    )
    if order is None:
        return None
    order["items"] = _items(order["order_id"])
    return _clean(order, "order_id")


def orders_in_range(start_date: date, end_date: date, limit: int) -> list[dict]:
    return [
        _clean(doc, "order_id")
        for doc in db()
        .orders.find(_timestamp_range(start_date, end_date), {"_id": 0})
        .sort([("order_purchase_timestamp", 1), ("order_id", 1)])
        .limit(limit)
    ]


def _daily_pipeline(match_extra: dict | None = None, limit: int | None = None, latest: bool = False):
    match_stage = {"order_status": {"$nin": EXCLUDED_STATUSES}}
    if match_extra:
        match_stage.update(match_extra)
    pipeline = [
        {
            "$lookup": {
                "from": "order_items",
                "localField": "order_id",
                "foreignField": "order_id",
                "as": "items",
            }
        },
        {"$match": match_stage},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": {"$substrBytes": [{"$toString": "$order_purchase_timestamp"}, 0, 10]},
                "total_orders": {"$addToSet": "$order_id"},
                "total_items": {"$sum": 1},
                "daily_sales": {"$sum": "$items.price"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "sales_date": "$_id",
                "total_orders": {"$size": "$total_orders"},
                "total_items": 1,
                "daily_sales": {"$round": ["$daily_sales", 2]},
            }
        },
        {"$sort": {"sales_date": -1 if latest else 1}},
    ]
    if limit:
        pipeline.append({"$limit": limit})
    return pipeline


def daily_sales(start_date: date | None = None, end_date: date | None = None, limit: int = 100) -> list[dict]:
    extra = {}
    if start_date is not None or end_date is not None:
        extra.update(_timestamp_range(start_date or date.min, end_date or date.max))
    return list(db().orders.aggregate(_daily_pipeline(extra, limit=limit)))


def latest_daily_sales() -> Optional[dict]:
    rows = list(db().orders.aggregate(_daily_pipeline(latest=True, limit=1)))
    return rows[0] if rows else None


def seed_demo() -> dict:
    created = []
    if get_customer(DEMO_CUSTOMER_ID) is None:
        create_customer(
            {
                "customer_id": DEMO_CUSTOMER_ID,
                "customer_unique_id": "demo-unique-001",
                "customer_city": "sao paulo",
                "customer_state": "SP",
            }
        )
        created.append("customer")
    if get_product(DEMO_PRODUCT_ID) is None:
        create_product(
            {
                "product_id": DEMO_PRODUCT_ID,
                "product_category_name": "housewares",
                "product_photos_qty": 1,
                "product_weight_g": 500,
            }
        )
        created.append("product")
    if get_order(DEMO_ORDER_ID) is None:
        create_order(
            {
                "order_id": DEMO_ORDER_ID,
                "customer_id": DEMO_CUSTOMER_ID,
                "order_status": "delivered",
                "order_purchase_timestamp": datetime(2018, 8, 15, 12, 0, 0),
                "items": [
                    {
                        "order_item_id": 1,
                        "product_id": DEMO_PRODUCT_ID,
                        "seller_id": DEMO_SELLER_ID,
                        "price": 29.99,
                        "freight_value": 8.72,
                    }
                ],
            }
        )
        created.append("order")
    return {
        "database": "mongo",
        "created": created or ["already present"],
        "customer_id": DEMO_CUSTOMER_ID,
        "product_id": DEMO_PRODUCT_ID,
        "order_id": DEMO_ORDER_ID,
        "order_item_id": 1,
    }
