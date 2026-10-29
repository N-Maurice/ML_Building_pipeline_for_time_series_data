CREATE DATABASE IF NOT EXISTS olist_project;
USE olist_project;

-- Table 1: Customers
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(40) PRIMARY KEY,
    customer_unique_id VARCHAR(40),
    customer_city VARCHAR(100),
    customer_state CHAR(2)
);

-- Table 2: Products
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(40) PRIMARY KEY,
    product_category_name VARCHAR(100),
    product_name_lenght INT,
    product_description_lenght INT,
    product_photos_qty INT,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);

-- Table 3: Orders
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(40) PRIMARY KEY,
    customer_id VARCHAR(40) NOT NULL,
    order_status VARCHAR(30),
    order_purchase_timestamp DATETIME,
    INDEX idx_purchase_timestamp (order_purchase_timestamp),
    INDEX idx_order_status (order_status),
    CONSTRAINT fk_orders_customers
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

-- Table 4: Order Items
CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR(40) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(40),
    seller_id VARCHAR(40),
    price DECIMAL(12,2) NOT NULL,
    freight_value DECIMAL(12,2),
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_product_id (product_id),
    INDEX idx_seller_id (seller_id),
    CONSTRAINT fk_items_orders
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
);

-- Verify database tables
SHOW TABLES;

-- Verify table structures
DESCRIBE customers;
DESCRIBE products;
DESCRIBE orders;
DESCRIBE order_items;