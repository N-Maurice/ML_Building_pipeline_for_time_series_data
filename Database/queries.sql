
USE olist_project;

-- Query 1: Count orders by day
SELECT
    DATE(order_purchase_timestamp) AS purchase_date,
    COUNT(*) AS order_count
FROM orders
WHERE order_purchase_timestamp IS NOT NULL
GROUP BY DATE(order_purchase_timestamp)
ORDER BY purchase_date;

-- Query 2: Count orders by status
SELECT
    order_status,
    COUNT(*) AS orders_count
FROM orders
GROUP BY order_status
ORDER BY orders_count DESC;

-- Query 3: Daily product sales value
SELECT
    DATE(o.order_purchase_timestamp) AS sales_date,
    ROUND(SUM(oi.price), 2) AS daily_sales,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(*) AS total_items
FROM orders o
JOIN order_items oi
    ON o.order_id = oi.order_id
WHERE o.order_purchase_timestamp >= '2017-01-01'
  AND o.order_purchase_timestamp < '2018-09-01'
GROUP BY DATE(o.order_purchase_timestamp)
ORDER BY sales_date;

-- Query 4: Top 10 product categories by sales value
SELECT
    COALESCE(p.product_category_name, 'unknown') AS product_category,
    ROUND(SUM(oi.price), 2) AS total_product_value,
    COUNT(*) AS items_sold
FROM order_items oi
JOIN orders o
    ON oi.order_id = o.order_id
LEFT JOIN products p
    ON oi.product_id = p.product_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
GROUP BY COALESCE(p.product_category_name, 'unknown')
ORDER BY total_product_value DESC
LIMIT 10;
