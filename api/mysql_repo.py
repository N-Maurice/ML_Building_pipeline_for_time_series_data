from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import IntegrityError, OperationalError, ProgrammingError

from api.errors import StoreError
from api.settings import get_settings

EXCLUDED_STATUSES = ("canceled", "unavailable")
DEMO_CUSTOMER_ID = "demo-customer-001"
DEMO_PRODUCT_ID = "demo-product-001"
DEMO_ORDER_ID = "demo-order-001"
DEMO_SELLER_ID = "demo-seller-001"

CUSTOMER_COLUMNS = ["customer_id", "customer_unique_id", "customer_city", "customer_state"]
PRODUCT_COLUMNS = [
    "product_id",
    "product_category_name",
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]
ORDER_COLUMNS = ["order_id", "customer_id", "order_status", "order_purchase_timestamp"]
ITEM_COLUMNS = ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"]


def connect():
    settings = get_settings()
    try:
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            cursorclass=DictCursor,
            charset="utf8mb4",
            autocommit=False,
        )
    except OperationalError as exc:
        raise StoreError(
            "MySQL is unavailable. Start it (open Docker Desktop, then "
            "`docker compose up -d`) and confirm MYSQL_* in .env. "
            f"Original error: {exc}",
            status_code=503,
        ) from exc


def _run(query: str, params: tuple = (), fetch: str = "none"):
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetch == "one":
                row = cursor.fetchone()
            elif fetch == "all":
                row = cursor.fetchall()
            else:
                row = {"rowcount": cursor.rowcount}
        conn.commit()
        return row
    except IntegrityError as exc:
        conn.rollback()
        message = str(exc)
        if "foreign key" in message.lower():
            raise StoreError(message, status_code=400) from exc
        raise StoreError(message, status_code=409) from exc
    except (OperationalError, ProgrammingError) as exc:
        conn.rollback()
        raise StoreError(f"MySQL error: {exc}", status_code=503) from exc
    finally:
        conn.close()


def ping() -> bool:
    return ping_detail()[0]


def ping_detail() -> tuple[bool, str | None]:
    try:
        _run("SELECT 1 AS ok", fetch="one")
        return True, None
    except StoreError as exc:
        return False, exc.message


def _insert(table: str, columns: list[str], payload: dict) -> None:
    values = tuple(payload.get(column) for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    col_sql = ", ".join(columns)
    _run(f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})", values)


def _update(table: str, pk_clause: str, pk_values: tuple, fields: dict, allowed: list[str]) -> None:
    assignments = []
    values: list[Any] = []
    for column in allowed:
        if column in fields and fields[column] is not None:
            assignments.append(f"{column} = %s")
            values.append(fields[column])
    if not assignments:
        return
    values.extend(pk_values)
    _run(f"UPDATE {table} SET {', '.join(assignments)} WHERE {pk_clause}", tuple(values))


def list_customers(limit: int = 50) -> list[dict]:
    return list(_run("SELECT * FROM customers ORDER BY customer_id LIMIT %s", (limit,), fetch="all") or [])


def get_customer(customer_id: str) -> Optional[dict]:
    return _run("SELECT * FROM customers WHERE customer_id = %s", (customer_id,), fetch="one")


def create_customer(payload: dict) -> dict:
    if get_customer(payload["customer_id"]):
        raise StoreError(f"Customer {payload['customer_id']} already exists", status_code=409)
    _insert("customers", CUSTOMER_COLUMNS, payload)
    created = get_customer(payload["customer_id"])
    if created is None:
        raise StoreError("Customer was not created", status_code=500)
    return created


def update_customer(customer_id: str, fields: dict) -> dict:
    if get_customer(customer_id) is None:
        raise StoreError(f"Customer {customer_id} was not found", status_code=404)
    _update("customers", "customer_id = %s", (customer_id,), fields, CUSTOMER_COLUMNS[1:])
    updated = get_customer(customer_id)
    if updated is None:
        raise StoreError(f"Customer {customer_id} was not found", status_code=404)
    return updated


def delete_customer(customer_id: str) -> None:
    if get_customer(customer_id) is None:
        raise StoreError(f"Customer {customer_id} was not found", status_code=404)
    related = _run(
        "SELECT COUNT(*) AS n FROM orders WHERE customer_id = %s",
        (customer_id,),
        fetch="one",
    )
    if related and related["n"]:
        raise StoreError(
            f"Cannot delete customer {customer_id} while {related['n']} order(s) still reference it",
            status_code=409,
        )
    _run("DELETE FROM customers WHERE customer_id = %s", (customer_id,))


def list_products(limit: int = 50) -> list[dict]:
    return list(_run("SELECT * FROM products ORDER BY product_id LIMIT %s", (limit,), fetch="all") or [])


def get_product(product_id: str) -> Optional[dict]:
    return _run("SELECT * FROM products WHERE product_id = %s", (product_id,), fetch="one")


def create_product(payload: dict) -> dict:
    if get_product(payload["product_id"]):
        raise StoreError(f"Product {payload['product_id']} already exists", status_code=409)
    _insert("products", PRODUCT_COLUMNS, payload)
    created = get_product(payload["product_id"])
    if created is None:
        raise StoreError("Product was not created", status_code=500)
    return created


def update_product(product_id: str, fields: dict) -> dict:
    if get_product(product_id) is None:
        raise StoreError(f"Product {product_id} was not found", status_code=404)
    _update("products", "product_id = %s", (product_id,), fields, PRODUCT_COLUMNS[1:])
    updated = get_product(product_id)
    if updated is None:
        raise StoreError(f"Product {product_id} was not found", status_code=404)
    return updated


def delete_product(product_id: str) -> None:
    if get_product(product_id) is None:
        raise StoreError(f"Product {product_id} was not found", status_code=404)
    _run("DELETE FROM products WHERE product_id = %s", (product_id,))


def get_items(order_id: str) -> list[dict]:
    return list(
        _run(
            """
            SELECT order_id, order_item_id, product_id, seller_id, price, freight_value
            FROM order_items
            WHERE order_id = %s
            ORDER BY order_item_id
            """,
            (order_id,),
            fetch="all",
        )
        or []
    )


def list_order_items(order_id: str | None = None, limit: int = 50) -> list[dict]:
    if order_id:
        return get_items(order_id)[:limit]
    return list(
        _run(
            """
            SELECT order_id, order_item_id, product_id, seller_id, price, freight_value
            FROM order_items
            ORDER BY order_id, order_item_id
            LIMIT %s
            """,
            (limit,),
            fetch="all",
        )
        or []
    )


def get_order_item(order_id: str, order_item_id: int) -> Optional[dict]:
    return _run(
        """
        SELECT order_id, order_item_id, product_id, seller_id, price, freight_value
        FROM order_items
        WHERE order_id = %s AND order_item_id = %s
        """,
        (order_id, order_item_id),
        fetch="one",
    )


def create_order_item(payload: dict) -> dict:
    if get_order(payload["order_id"]) is None:
        raise StoreError(f"Order {payload['order_id']} was not found", status_code=404)
    if get_order_item(payload["order_id"], payload["order_item_id"]):
        raise StoreError(
            f"Item {payload['order_item_id']} already exists on order {payload['order_id']}",
            status_code=409,
        )
    _insert("order_items", ITEM_COLUMNS, payload)
    created = get_order_item(payload["order_id"], payload["order_item_id"])
    if created is None:
        raise StoreError("Order item was not created", status_code=500)
    return created


def update_order_item(order_id: str, order_item_id: int, fields: dict) -> dict:
    if get_order_item(order_id, order_item_id) is None:
        raise StoreError(f"Item {order_item_id} on order {order_id} was not found", status_code=404)
    _update(
        "order_items",
        "order_id = %s AND order_item_id = %s",
        (order_id, order_item_id),
        fields,
        ["product_id", "seller_id", "price", "freight_value"],
    )
    updated = get_order_item(order_id, order_item_id)
    if updated is None:
        raise StoreError(f"Item {order_item_id} on order {order_id} was not found", status_code=404)
    return updated


def delete_order_item(order_id: str, order_item_id: int) -> None:
    if get_order_item(order_id, order_item_id) is None:
        raise StoreError(f"Item {order_item_id} on order {order_id} was not found", status_code=404)
    _run("DELETE FROM order_items WHERE order_id = %s AND order_item_id = %s", (order_id, order_item_id))


def list_orders(limit: int = 50) -> list[dict]:
    return list(
        _run(
            """
            SELECT order_id, customer_id, order_status, order_purchase_timestamp
            FROM orders
            ORDER BY order_purchase_timestamp DESC, order_id DESC
            LIMIT %s
            """,
            (limit,),
            fetch="all",
        )
        or []
    )


def get_order(order_id: str) -> Optional[dict]:
    order = _run(
        """
        SELECT order_id, customer_id, order_status, order_purchase_timestamp
        FROM orders
        WHERE order_id = %s
        """,
        (order_id,),
        fetch="one",
    )
    if not order:
        return None
    order["items"] = get_items(order_id)
    return order


def create_order(payload: dict) -> dict:
    if get_order(payload["order_id"]):
        raise StoreError(f"Order {payload['order_id']} already exists", status_code=409)
    if get_customer(payload["customer_id"]) is None:
        raise StoreError(
            f"customer_id {payload['customer_id']} does not exist. "
            "POST /mysql/customers first, or POST /demo/seed.",
            status_code=400,
        )
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (order_id, customer_id, order_status, order_purchase_timestamp)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    payload["order_id"],
                    payload["customer_id"],
                    payload["order_status"],
                    payload["order_purchase_timestamp"],
                ),
            )
            for item in payload.get("items") or []:
                cursor.execute(
                    """
                    INSERT INTO order_items
                        (order_id, order_item_id, product_id, seller_id, price, freight_value)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload["order_id"],
                        item["order_item_id"],
                        item.get("product_id"),
                        item.get("seller_id"),
                        item["price"],
                        item.get("freight_value"),
                    ),
                )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        message = str(exc)
        if "foreign key" in message.lower():
            raise StoreError(message, status_code=400) from exc
        raise StoreError(message, status_code=409) from exc
    finally:
        conn.close()
    created = get_order(payload["order_id"])
    if created is None:
        raise StoreError("Order was not created", status_code=500)
    return created


def update_order(order_id: str, fields: dict) -> dict:
    current = get_order(order_id)
    if current is None:
        raise StoreError(f"Order {order_id} was not found", status_code=404)
    _update("orders", "order_id = %s", (order_id,), fields, ["customer_id", "order_status", "order_purchase_timestamp"])
    updated = get_order(order_id)
    if updated is None:
        raise StoreError(f"Order {order_id} was not found", status_code=404)
    return updated


def delete_order(order_id: str) -> None:
    if get_order(order_id) is None:
        raise StoreError(f"Order {order_id} was not found", status_code=404)
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM order_items WHERE order_id = %s", (order_id,))
            cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        conn.commit()
    finally:
        conn.close()


def latest_order() -> Optional[dict]:
    order = _run(
        """
        SELECT order_id, customer_id, order_status, order_purchase_timestamp
        FROM orders
        WHERE order_purchase_timestamp IS NOT NULL
        ORDER BY order_purchase_timestamp DESC, order_id DESC
        LIMIT 1
        """,
        fetch="one",
    )
    if not order:
        return None
    order["items"] = get_items(order["order_id"])
    return order


def orders_in_range(start_date: date, end_date: date, limit: int) -> list[dict]:
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    rows = _run(
        """
        SELECT order_id, customer_id, order_status, order_purchase_timestamp
        FROM orders
        WHERE order_purchase_timestamp >= %s
          AND order_purchase_timestamp < %s
        ORDER BY order_purchase_timestamp, order_id
        LIMIT %s
        """,
        (start, end, limit),
        fetch="all",
    )
    return list(rows or [])


def daily_sales(start_date: date | None = None, end_date: date | None = None, limit: int = 100) -> list[dict]:
    clauses = ["o.order_status NOT IN %s"]
    params: list[Any] = [EXCLUDED_STATUSES]
    if start_date is not None:
        clauses.append("DATE(o.order_purchase_timestamp) >= %s")
        params.append(start_date)
    if end_date is not None:
        clauses.append("DATE(o.order_purchase_timestamp) <= %s")
        params.append(end_date)
    where = " AND ".join(clauses)
    params.append(limit)
    rows = _run(
        f"""
        SELECT
            DATE(o.order_purchase_timestamp) AS sales_date,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(oi.order_id) AS total_items,
            ROUND(SUM(oi.price), 2) AS daily_sales
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE {where}
        GROUP BY DATE(o.order_purchase_timestamp)
        ORDER BY sales_date
        LIMIT %s
        """,
        tuple(params),
        fetch="all",
    )
    return list(rows or [])


def latest_daily_sales() -> Optional[dict]:
    rows = _run(
        """
        SELECT
            DATE(o.order_purchase_timestamp) AS sales_date,
            COUNT(DISTINCT o.order_id) AS total_orders,
            COUNT(oi.order_id) AS total_items,
            ROUND(SUM(oi.price), 2) AS daily_sales
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status NOT IN %s
          AND o.order_purchase_timestamp IS NOT NULL
        GROUP BY DATE(o.order_purchase_timestamp)
        ORDER BY sales_date DESC
        LIMIT 1
        """,
        (EXCLUDED_STATUSES,),
        fetch="all",
    )
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
        "database": "mysql",
        "created": created or ["already present"],
        "customer_id": DEMO_CUSTOMER_ID,
        "product_id": DEMO_PRODUCT_ID,
        "order_id": DEMO_ORDER_ID,
        "order_item_id": 1,
    }
