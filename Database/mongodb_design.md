# MongoDB Design

## 1. Database Collections

Database name: `olist`

The database contains these collections:
- `orders`
- `order_items`
- `customers`
- `products`
- `orders_embedded`

## 2. Data Structure

We created `orders_embedded` by joining `orders` with `order_items` using `$lookup` on `order_id`.

We used `$out` to save the result in the new collection.

Each order now contains an `items` array with product IDs, prices and freight values.

## 3. Sample Data

### Order (`orders_embedded`)
- Order ID: `e481f51c-bdc5-4678-b7cc-49136f2d6af7`
- Status: `delivered`
- Purchase date: `2017-10-02 10:56:33`
- Item price: `29.99`
- Freight value: `8.72`

### Customer (`customers`)
- Customer ID: `06b8999e2fba1a1fbc88172c00ba8bc7`
- City: `franca`
- State: `SP`
- ZIP code prefix: `14409`

### Product (`products`)
- Product ID: `1e9e8ef04dbcff4541ed26657ea517e5`
- Category: `perfumaria`
- Weight: `225 g`
- Dimensions: `16 × 10 × 14 cm`

## 4. MongoDB Queries

### Query 1: Find the Latest Order

```javascript
db.orders_embedded.find()
  .sort({ order_purchase_timestamp: -1 })
  .limit(1)
```

Result:
- Date: `2018-10-17 17:30:18`
- Status: `canceled`

### Query 2: Find Orders in a Date Range

```javascript
db.orders_embedded.find({
  order_purchase_timestamp: {
    $gte: "2018-08-01",
    $lt: "2018-08-08"
  }
}).sort({ order_purchase_timestamp: 1 })
```

Sample result:
- Date: `2018-08-07 23:54:36`
- Status: `delivered`
- Item price: `330`
- Freight value: `24.24`

### Query 3: Daily Merchandise Aggregation

We used these aggregation stages:
- `$match`
- `$unwind`
- `$group`
- `$project`
- `$sort`

The aggregation calculates daily sales value, order count and item count.

Sample result:

| Date | Sales value | Order count | Item count |
|---|---:|---:|---:|
| 2017-01-05 | 396.90 | 32 | 32 |

## 5. Conclusion

We created `orders_embedded` to store order items inside each order. We also used MongoDB queries to find the latest order, filter orders by date and calculate daily sales.