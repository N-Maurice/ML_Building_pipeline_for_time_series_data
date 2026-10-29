# Olist Database Design

## 1. Introduction

This document presents the Olist database and the MongoDB queries used
to analyse orders and product sales.

## 2. Database structure

-   **Connection:** `Olist Local`
-   **Database:** `olist`

The database contains four collections:

  Collection      Description
  --------------- --------------------------------------------------
  `customers`     Customer information
  `orders`        Order information and status
  `order_items`   Products included in each order and their prices
  `products`      Product information and categories

## 3. MongoDB queries

### Query 1 --- Total product sales

**Purpose:** Calculate the total value of products and the number of
items sold. Canceled and unavailable orders are excluded.

``` javascript
[
  {
    $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
    }
  },
  {
    $match: {
      order_status: {
        $nin: ["canceled", "unavailable"]
      }
    }
  },
  { $unwind: "$items" },
  {
    $group: {
      _id: null,
      total_product_value: { $sum: "$items.price" },
      total_items: { $sum: 1 }
    }
  }
]
```

**Results:**

-   Total product value: **13,494,400.74**
-   Total items: **112,101**

### Query 2 --- Daily product sales

**Purpose:** Calculate the value of products sold and the number of
items sold each day.

``` javascript
[
  {
    $lookup: {
      from: "order_items",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
    }
  },
  {
    $match: {
      order_status: {
        $nin: ["canceled", "unavailable"]
      }
    }
  },
  { $unwind: "$items" },
  {
    $group: {
      _id: {
        $substrBytes: ["$order_purchase_timestamp", 0, 10]
      },
      daily_product_value: { $sum: "$items.price" },
      daily_items_sold: { $sum: 1 }
    }
  },
  { $sort: { _id: 1 } }
]
```

**Sample results:**

  Date           Product value   Items sold
  ------------ --------------- ------------
  2016-09-04             72.89            2
  2016-09-15            134.97            3
  2016-10-03            441.98            7
  2016-10-04          9,571.16           67
  2016-10-05          6,856.56           52

### Query 3 --- Orders by status

**Purpose:** Count the orders in each status.

``` javascript
[
  {
    $group: {
      _id: "$order_status",
      total_orders: { $sum: 1 }
    }
  },
  { $sort: { total_orders: -1 } }
]
```

**Results:**

  Order status     Number of orders
  -------------- ------------------
  delivered                  96,478
  shipped                     1,107
  canceled                      625
  unavailable                   609
  invoiced                      314
  processing                    301
  created                         5
  approved                        2

### Query 4 --- Sales by product category

**Purpose:** Calculate the total product value and number of items sold
in each product category. Canceled and unavailable orders are excluded.

``` javascript
[
  {
    $lookup: {
      from: "orders",
      localField: "order_id",
      foreignField: "order_id",
      as: "order"
    }
  },
  { $unwind: "$order" },
  {
    $match: {
      "order.order_status": {
        $nin: ["canceled", "unavailable"]
      }
    }
  },
  {
    $lookup: {
      from: "products",
      localField: "product_id",
      foreignField: "product_id",
      as: "product"
    }
  },
  { $unwind: "$product" },
  {
    $group: {
      _id: {
        $ifNull: ["$product.product_category_name", "unknown"]
      },
      total_product_value: { $sum: "$price" },
      items_sold: { $sum: 1 }
    }
  },
  { $sort: { total_product_value: -1 } }
]
```

**Results:** To be added after checking the output in MongoDB Compass.

## 4. Conclusion

The Olist database contains four collections. The MongoDB queries
analyse total product sales, daily sales, order statuses, and sales by
product category.

**Note:** The sales values in this document use product prices only.
They do not include shipping fees.
