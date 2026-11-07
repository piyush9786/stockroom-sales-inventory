-- MySQL 8.0.16+ (CHECK enforcement), InnoDB, one currency and one location.
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin', 'Sales User') NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL,
    mobile VARCHAR(30) NOT NULL,
    city VARCHAR(120) NOT NULL,
    status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
    INDEX idx_customer_status_name (status, name),
    INDEX idx_customer_email (email),
    INDEX idx_customer_mobile (mobile)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(16,2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
    CONSTRAINT ck_product_price CHECK (price >= 0),
    CONSTRAINT ck_product_stock CHECK (stock_quantity >= 0),
    INDEX idx_product_status_category (status, category),
    INDEX idx_product_name (name),
    INDEX idx_product_stock (stock_quantity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE sales_orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    status ENUM('Draft', 'Confirmed', 'Cancelled') NOT NULL DEFAULT 'Draft',
    discount_percentage DECIMAL(5,2) NOT NULL DEFAULT 0,
    subtotal DECIMAL(16,2) NOT NULL,
    discount_amount DECIMAL(16,2) NOT NULL,
    grand_total DECIMAL(16,2) NOT NULL,
    created_by INT NOT NULL,
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_order_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT ck_order_discount CHECK (discount_percentage BETWEEN 0 AND 20),
    CONSTRAINT ck_order_totals CHECK (subtotal >= 0 AND discount_amount >= 0 AND grand_total >= 0),
    INDEX idx_order_owner (created_by, id),
    INDEX idx_order_status_date (status, order_date),
    INDEX idx_order_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE sales_order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sales_order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    rate DECIMAL(16,2) NOT NULL,
    amount DECIMAL(16,2) NOT NULL,
    CONSTRAINT fk_item_order FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id) ON DELETE RESTRICT,
    CONSTRAINT fk_item_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT uq_order_product UNIQUE (sales_order_id, product_id),
    CONSTRAINT ck_item_quantity CHECK (quantity > 0),
    CONSTRAINT ck_item_money CHECK (rate >= 0 AND amount >= 0),
    INDEX idx_item_product (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE stock_movements (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    movement_type ENUM('Opening', 'Adjustment', 'Sale', 'Cancellation') NOT NULL,
    quantity_change INT NOT NULL,
    related_order_id INT NULL,
    reason VARCHAR(255) NOT NULL,
    created_by INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movement_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT fk_movement_order FOREIGN KEY (related_order_id) REFERENCES sales_orders(id) ON DELETE RESTRICT,
    CONSTRAINT fk_movement_creator FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT ck_movement_nonzero CHECK (quantity_change <> 0),
    CONSTRAINT ck_movement_direction CHECK (
        (movement_type = 'Sale' AND quantity_change < 0 AND related_order_id IS NOT NULL) OR
        (movement_type = 'Cancellation' AND quantity_change > 0 AND related_order_id IS NOT NULL) OR
        (movement_type = 'Opening' AND quantity_change > 0 AND related_order_id IS NULL) OR
        (movement_type = 'Adjustment' AND related_order_id IS NULL)
    ),
    CONSTRAINT uq_order_stock_event UNIQUE (related_order_id, product_id, movement_type),
    INDEX idx_movement_product_time (product_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
