# Task 3 — CRUD and time-series endpoints

FastAPI service for the four Task 2 stores, on **both MySQL and MongoDB**:

- `customers`
- `products`
- `orders`
- `order_items`

Every resource has **POST, GET (list + one), PUT, DELETE**. Orders also have **latest record** and **date-range** queries. Daily sales endpoints reuse Task 2 Query 3 (exclude `canceled` / `unavailable`, sum item `price` only).

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## 1. Start the databases

Open **Docker Desktop**, wait until it is running, then from the repository root:

```bash
docker compose up -d
```

| Service | Port | Database | Login |
| --- | --- | --- | --- |
| MySQL 8 | 3306 | `olist_project` | user `root`, empty password |
| MongoDB 7 | 27017 | `olist` | no auth |

`Database/Schema.sql` is applied the first time the MySQL volume is created. If tables are missing after you changed the schema, remove the volume and start again:

```bash
docker compose down -v
docker compose up -d
```

Copy `.env.example` to `.env` if needed. Defaults already match docker compose.

## 2. Start the API

From the repository root (not from `api/`):

```bash
python -m pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

Check both databases:

```bash
curl -s http://127.0.0.1:8000/health
```

You need `"mysql": true` and `"mongodb": true`. If either is `false`, read `mysql_detail` / `mongodb_detail`. A 503 on a CRUD route means that database is still down.

`GET /` redirects to `/docs`.

## 3. Load demo rows (required before MySQL orders)

MySQL orders require a real `customers.customer_id` because of the foreign key. Seed both databases with matching demo IDs:

```bash
curl -s -X POST http://127.0.0.1:8000/demo/seed
```

| Field | Demo value |
| --- | --- |
| `customer_id` | `demo-customer-001` |
| `product_id` | `demo-product-001` |
| `order_id` | `demo-order-001` |
| `order_item_id` | `1` |
| purchase time | `2018-08-15 12:00:00` |

The seed is idempotent: running it again does not duplicate rows.

To exercise **every** route in one pass:

```bash
bash api/test_crud.sh
```

## 4. Route map

Replace `{mysql|mongo}` with `mysql` or `mongo`. The two prefixes are mirrors.

### Customers

| Action | Request |
| --- | --- |
| Create | `POST /{mysql\|mongo}/customers` |
| List | `GET /{mysql\|mongo}/customers?limit=50` |
| Read one | `GET /{mysql\|mongo}/customers/{customer_id}` |
| Update | `PUT /{mysql\|mongo}/customers/{customer_id}` |
| Delete | `DELETE /{mysql\|mongo}/customers/{customer_id}` |

Create body:

```json
{
  "customer_id": "demo-customer-002",
  "customer_unique_id": "demo-unique-002",
  "customer_city": "rio de janeiro",
  "customer_state": "RJ"
}
```

PUT must include at least one of `customer_unique_id`, `customer_city`, `customer_state`. Delete fails with 409 if orders still reference the customer.

### Products

| Action | Request |
| --- | --- |
| Create | `POST /{mysql\|mongo}/products` |
| List | `GET /{mysql\|mongo}/products?limit=50` |
| Read one | `GET /{mysql\|mongo}/products/{product_id}` |
| Update | `PUT /{mysql\|mongo}/products/{product_id}` |
| Delete | `DELETE /{mysql\|mongo}/products/{product_id}` |

Column names keep the Olist spelling `product_name_lenght` / `product_description_lenght`.

### Orders

| Action | Request |
| --- | --- |
| Create | `POST /{mysql\|mongo}/orders` |
| List | `GET /{mysql\|mongo}/orders?limit=50` |
| Read one | `GET /{mysql\|mongo}/orders/{order_id}` |
| Update | `PUT /{mysql\|mongo}/orders/{order_id}` |
| Delete | `DELETE /{mysql\|mongo}/orders/{order_id}` |
| Latest | `GET /{mysql\|mongo}/orders/latest` |
| Date range | `GET /{mysql\|mongo}/orders/range?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` |

`start_date` and `end_date` are **inclusive calendar days**. `limit` defaults to 100 (max 1000). Latest uses `order_purchase_timestamp`. GET one returns nested `items`. DELETE removes the order **and** its items.

Create body (MySQL `customer_id` must already exist):

```json
{
  "order_id": "demo-order-002",
  "customer_id": "demo-customer-001",
  "order_status": "created",
  "order_purchase_timestamp": "2018-08-16T09:00:00",
  "items": [
    {
      "order_item_id": 1,
      "product_id": "demo-product-001",
      "seller_id": "demo-seller-001",
      "price": 19.9,
      "freight_value": 5.0
    }
  ]
}
```

PUT must include at least one of `customer_id`, `order_status`, `order_purchase_timestamp`.

### Order items

| Action | Request |
| --- | --- |
| Create | `POST /{mysql\|mongo}/order-items` |
| List | `GET /{mysql\|mongo}/order-items?order_id=optional&limit=50` |
| Read one | `GET /{mysql\|mongo}/order-items/{order_id}/{order_item_id}` |
| Update | `PUT /{mysql\|mongo}/order-items/{order_id}/{order_item_id}` |
| Delete | `DELETE /{mysql\|mongo}/order-items/{order_id}/{order_item_id}` |

The parent order must exist. The pair `(order_id, order_item_id)` is unique.

### Daily sales (time series for Task 4)

| Action | Request |
| --- | --- |
| Latest day | `GET /{mysql\|mongo}/sales/daily/latest` |
| Date range | `GET /{mysql\|mongo}/sales/daily?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` |

## 5. Manual curl sequence (MySQL)

After seed, this is a complete CRUD pass. Repeat with `/mongo` instead of `/mysql`.

```bash
# Read
curl -s http://127.0.0.1:8000/mysql/customers/demo-customer-001
curl -s http://127.0.0.1:8000/mysql/products/demo-product-001
curl -s http://127.0.0.1:8000/mysql/orders/demo-order-001
curl -s http://127.0.0.1:8000/mysql/order-items/demo-order-001/1

# Update
curl -s -X PUT http://127.0.0.1:8000/mysql/customers/demo-customer-001 \
  -H 'Content-Type: application/json' -d '{"customer_city":"campinas"}'
curl -s -X PUT http://127.0.0.1:8000/mysql/products/demo-product-001 \
  -H 'Content-Type: application/json' -d '{"product_category_name":"bed_bath_table"}'
curl -s -X PUT http://127.0.0.1:8000/mysql/orders/demo-order-001 \
  -H 'Content-Type: application/json' -d '{"order_status":"shipped"}'
curl -s -X PUT http://127.0.0.1:8000/mysql/order-items/demo-order-001/1 \
  -H 'Content-Type: application/json' -d '{"price":34.99}'

# Time series
curl -s http://127.0.0.1:8000/mysql/orders/latest
curl -s 'http://127.0.0.1:8000/mysql/orders/range?start_date=2018-08-01&end_date=2018-08-31'
curl -s http://127.0.0.1:8000/mysql/sales/daily/latest
curl -s 'http://127.0.0.1:8000/mysql/sales/daily?start_date=2018-08-01&end_date=2018-08-31'

# Create + delete a throwaway order (does not remove the demo row)
curl -s -X POST http://127.0.0.1:8000/mysql/orders \
  -H 'Content-Type: application/json' \
  -d '{"order_id":"demo-order-temp","customer_id":"demo-customer-001","order_status":"created","order_purchase_timestamp":"2018-08-16T09:00:00","items":[]}'
curl -s -X DELETE http://127.0.0.1:8000/mysql/orders/demo-order-temp -o /dev/null -w "%{http_code}\n"
```

Swagger: pick a `/mysql` or `/mongo` tag, then **Try it out**. For DELETE, HTTP **204** with an empty body is success.

## 6. Status codes

| Code | Meaning |
| --- | --- |
| 200 | GET/PUT success |
| 201 | POST created |
| 204 | DELETE success (empty body) |
| 400 | `end_date` before `start_date`, or MySQL foreign-key failure (unknown `customer_id` / delete customer with orders) |
| 404 | Unknown id, or no rows for latest |
| 409 | Duplicate primary key |
| 422 | Invalid JSON, missing fields, or empty PUT body |
| 503 | Database is not reachable |

## 7. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| POST `/mysql/orders` → 503 | MySQL is not running | Start Docker Desktop, `docker compose up -d`, wait, then `/health` |
| POST `/mysql/orders` → 400 `customer_id ... does not exist` | No parent customer | `POST /demo/seed` or `POST /mysql/customers` first |
| Latest/range → 404 | Empty `orders` table | Seed or POST an order |
| Health 200 but `"mysql": false` | API is up; database is not | Read `mysql_detail` |
| Tables missing | Compose volume was created before `Schema.sql` existed | `docker compose down -v && docker compose up -d` |
| Swagger POST fails on MySQL only | Used a random `customer_id` | Use `demo-customer-001` after seed |

MongoDB does not enforce the customer foreign key. The API still uses the same request bodies so both stores can be tested the same way.

## 8. Code layout

| File | Role |
| --- | --- |
| `api/main.py` | App, `/health`, `/demo/seed` |
| `api/db_routes.py` | Shared CRUD + time-series routes |
| `api/mysql_repo.py` / `api/mongo_repo.py` | Database access |
| `api/schemas.py` | Request validation |
| `api/test_crud.sh` | End-to-end curl pass |
