from __future__ import annotations

from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query, Response

from api.errors import StoreError
from api.schemas import (
    CustomerCreate,
    CustomerUpdate,
    OrderCreate,
    OrderItemCreate,
    OrderItemUpdate,
    OrderUpdate,
    ProductCreate,
    ProductUpdate,
)
from api.serialize import jsonable, order_payload, record_payload


def _call(func: Callable, *args, **kwargs) -> Any:
    try:
        return func(*args, **kwargs)
    except StoreError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


def _require(result, detail: str):
    if result is None:
        raise HTTPException(status_code=404, detail=detail)
    return result


def _range_guard(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")


def build_router(prefix: str, repo) -> APIRouter:
    router = APIRouter(prefix=f"/{prefix}", tags=[prefix])

    @router.post("/customers", status_code=201)
    def create_customer(body: CustomerCreate) -> dict:
        return record_payload(_call(repo.create_customer, body.model_dump()), "customer_id")

    @router.get("/customers")
    def list_customers(limit: int = Query(50, ge=1, le=500)) -> dict:
        rows = _call(repo.list_customers, limit)
        return {"count": len(rows), "records": [record_payload(row, "customer_id") for row in rows]}

    @router.get("/customers/{customer_id}")
    def get_customer(customer_id: str) -> dict:
        row = _require(_call(repo.get_customer, customer_id), f"Customer {customer_id} was not found")
        return record_payload(row, "customer_id")

    @router.put("/customers/{customer_id}")
    def update_customer(customer_id: str, body: CustomerUpdate) -> dict:
        row = _call(repo.update_customer, customer_id, body.model_dump(exclude_none=True))
        return record_payload(row, "customer_id")

    @router.delete("/customers/{customer_id}", status_code=204)
    def delete_customer(customer_id: str) -> Response:
        _call(repo.delete_customer, customer_id)
        return Response(status_code=204)

    @router.post("/products", status_code=201)
    def create_product(body: ProductCreate) -> dict:
        return record_payload(_call(repo.create_product, body.model_dump()), "product_id")

    @router.get("/products")
    def list_products(limit: int = Query(50, ge=1, le=500)) -> dict:
        rows = _call(repo.list_products, limit)
        return {"count": len(rows), "records": [record_payload(row, "product_id") for row in rows]}

    @router.get("/products/{product_id}")
    def get_product(product_id: str) -> dict:
        row = _require(_call(repo.get_product, product_id), f"Product {product_id} was not found")
        return record_payload(row, "product_id")

    @router.put("/products/{product_id}")
    def update_product(product_id: str, body: ProductUpdate) -> dict:
        row = _call(repo.update_product, product_id, body.model_dump(exclude_none=True))
        return record_payload(row, "product_id")

    @router.delete("/products/{product_id}", status_code=204)
    def delete_product(product_id: str) -> Response:
        _call(repo.delete_product, product_id)
        return Response(status_code=204)

    @router.post("/orders", status_code=201)
    def create_order(body: OrderCreate) -> dict:
        created = _call(repo.create_order, body.model_dump())
        return order_payload(created, created.get("items"))

    @router.get("/orders")
    def list_orders(limit: int = Query(50, ge=1, le=500)) -> dict:
        rows = _call(repo.list_orders, limit)
        return {"count": len(rows), "records": [record_payload(row, "order_id") for row in rows]}

    @router.get("/orders/latest")
    def latest_order() -> dict:
        order = _require(_call(repo.latest_order), "No orders found")
        return order_payload(order, order.get("items"))

    @router.get("/orders/range")
    def orders_range(
        start_date: date = Query(..., description="Inclusive start date (YYYY-MM-DD)"),
        end_date: date = Query(..., description="Inclusive end date (YYYY-MM-DD)"),
        limit: int = Query(100, ge=1, le=1000),
    ) -> dict:
        _range_guard(start_date, end_date)
        rows = _call(repo.orders_in_range, start_date, end_date, limit)
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "count": len(rows),
            "records": [record_payload(row, "order_id") for row in rows],
        }

    @router.get("/orders/{order_id}")
    def get_order(order_id: str) -> dict:
        order = _require(_call(repo.get_order, order_id), f"Order {order_id} was not found")
        return order_payload(order, order.get("items"))

    @router.put("/orders/{order_id}")
    def update_order(order_id: str, body: OrderUpdate) -> dict:
        updated = _call(repo.update_order, order_id, body.model_dump(exclude_none=True))
        return order_payload(updated, updated.get("items"))

    @router.delete("/orders/{order_id}", status_code=204)
    def delete_order(order_id: str) -> Response:
        _call(repo.delete_order, order_id)
        return Response(status_code=204)

    @router.post("/order-items", status_code=201)
    def create_order_item(body: OrderItemCreate) -> dict:
        return record_payload(_call(repo.create_order_item, body.model_dump()))

    @router.get("/order-items")
    def list_order_items(
        order_id: str | None = Query(default=None),
        limit: int = Query(50, ge=1, le=500),
    ) -> dict:
        rows = _call(repo.list_order_items, order_id, limit)
        return {"count": len(rows), "records": [record_payload(row) for row in rows]}

    @router.get("/order-items/{order_id}/{order_item_id}")
    def get_order_item(order_id: str, order_item_id: int) -> dict:
        row = _require(
            _call(repo.get_order_item, order_id, order_item_id),
            f"Item {order_item_id} on order {order_id} was not found",
        )
        return record_payload(row)

    @router.put("/order-items/{order_id}/{order_item_id}")
    def update_order_item(order_id: str, order_item_id: int, body: OrderItemUpdate) -> dict:
        row = _call(repo.update_order_item, order_id, order_item_id, body.model_dump(exclude_none=True))
        return record_payload(row)

    @router.delete("/order-items/{order_id}/{order_item_id}", status_code=204)
    def delete_order_item(order_id: str, order_item_id: int) -> Response:
        _call(repo.delete_order_item, order_id, order_item_id)
        return Response(status_code=204)

    @router.get("/sales/daily/latest")
    def latest_daily_sales() -> dict:
        row = _require(_call(repo.latest_daily_sales), "No daily sales found")
        return jsonable(row)

    @router.get("/sales/daily")
    def daily_sales(
        start_date: date = Query(..., description="Inclusive start date (YYYY-MM-DD)"),
        end_date: date = Query(..., description="Inclusive end date (YYYY-MM-DD)"),
        limit: int = Query(400, ge=1, le=2000),
    ) -> dict:
        _range_guard(start_date, end_date)
        rows = _call(repo.daily_sales, start_date, end_date, limit)
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "count": len(rows),
            "records": jsonable(rows),
        }

    return router
