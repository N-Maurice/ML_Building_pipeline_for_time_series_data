#!/usr/bin/env bash
# Exercise every Task 3 route against a running API.
# Usage: bash api/test_crud.sh
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"

echo "== health =="
health="$(curl -sS "$BASE/health")"
echo "$health" | python -m json.tool
python - "$health" <<'PY'
import json, sys
payload = json.loads(sys.argv[1])
missing = [name for name in ("mysql", "mongodb") if not payload.get(name)]
if missing:
    raise SystemExit(
        "Database not connected: " + ", ".join(missing)
        + ". Start Docker Desktop, run docker compose up -d, wait, then retry."
    )
PY

echo
echo "== seed demo rows in MySQL and MongoDB =="
curl -sS -X POST "$BASE/demo/seed" | python -m json.tool

test_store () {
  local prefix="$1"
  echo
  echo "======== ${prefix} CRUD ========"

  echo "-- list customers --"
  curl -sS "$BASE/${prefix}/customers?limit=5"

  echo
  echo "-- get customer --"
  curl -sS "$BASE/${prefix}/customers/demo-customer-001"

  echo
  echo "-- update customer --"
  curl -sS -X PUT "$BASE/${prefix}/customers/demo-customer-001" \
    -H 'Content-Type: application/json' \
    -d '{"customer_city":"campinas"}'

  echo
  echo "-- list products --"
  curl -sS "$BASE/${prefix}/products?limit=5"

  echo
  echo "-- get product --"
  curl -sS "$BASE/${prefix}/products/demo-product-001"

  echo
  echo "-- update product --"
  curl -sS -X PUT "$BASE/${prefix}/products/demo-product-001" \
    -H 'Content-Type: application/json' \
    -d '{"product_category_name":"bed_bath_table"}'

  echo
  echo "-- list orders --"
  curl -sS "$BASE/${prefix}/orders?limit=5"

  echo
  echo "-- get order --"
  curl -sS "$BASE/${prefix}/orders/demo-order-001"

  echo
  echo "-- latest order --"
  curl -sS "$BASE/${prefix}/orders/latest"

  echo
  echo "-- orders by date range --"
  curl -sS "$BASE/${prefix}/orders/range?start_date=2018-08-01&end_date=2018-08-31"

  echo
  echo "-- update order --"
  curl -sS -X PUT "$BASE/${prefix}/orders/demo-order-001" \
    -H 'Content-Type: application/json' \
    -d '{"order_status":"shipped"}'

  echo
  echo "-- list order items --"
  curl -sS "$BASE/${prefix}/order-items?order_id=demo-order-001"

  echo
  echo "-- get order item --"
  curl -sS "$BASE/${prefix}/order-items/demo-order-001/1"

  echo
  echo "-- update order item --"
  curl -sS -X PUT "$BASE/${prefix}/order-items/demo-order-001/1" \
    -H 'Content-Type: application/json' \
    -d '{"price":34.99}'

  echo
  echo "-- create extra order item --"
  curl -sS -X POST "$BASE/${prefix}/order-items" \
    -H 'Content-Type: application/json' \
    -d '{
      "order_id":"demo-order-001",
      "order_item_id":2,
      "product_id":"demo-product-001",
      "seller_id":"demo-seller-001",
      "price":10.50,
      "freight_value":2.00
    }'

  echo
  echo "-- daily sales range --"
  curl -sS "$BASE/${prefix}/sales/daily?start_date=2018-08-01&end_date=2018-08-31"

  echo
  echo "-- latest daily sales --"
  curl -sS "$BASE/${prefix}/sales/daily/latest"

  echo
  echo "-- delete extra order item --"
  curl -sS -o /dev/null -w "DELETE item HTTP %{http_code}\n" \
    -X DELETE "$BASE/${prefix}/order-items/demo-order-001/2"

  echo "-- create then delete a throwaway order --"
  curl -sS -X POST "$BASE/${prefix}/orders" \
    -H 'Content-Type: application/json' \
    -d '{
      "order_id":"demo-order-temp",
      "customer_id":"demo-customer-001",
      "order_status":"created",
      "order_purchase_timestamp":"2018-08-16T09:00:00",
      "items":[]
    }' > /dev/null
  curl -sS -o /dev/null -w "DELETE order HTTP %{http_code}\n" \
    -X DELETE "$BASE/${prefix}/orders/demo-order-temp"
}

test_store mysql
test_store mongo

echo
echo "Done. Demo customer/product/order were left in place for Swagger retries."
