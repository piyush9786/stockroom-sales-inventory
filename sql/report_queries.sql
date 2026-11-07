-- 1. Top three customers by Confirmed order grand total.
SELECT c.id, c.name, SUM(o.grand_total) AS total_sales
FROM customers c JOIN sales_orders o ON o.customer_id = c.id
WHERE o.status = 'Confirmed'
GROUP BY c.id, c.name
ORDER BY total_sales DESC, c.id
LIMIT 3;

-- 2. Top three products by quantity sold in Confirmed orders.
SELECT p.id, p.product_code, p.name, SUM(i.quantity) AS quantity_sold
FROM products p JOIN sales_order_items i ON i.product_id = p.id
JOIN sales_orders o ON o.id = i.sales_order_id
WHERE o.status = 'Confirmed'
GROUP BY p.id, p.product_code, p.name
ORDER BY quantity_sold DESC, p.id
LIMIT 3;

-- 3. Customers who have never placed ANY order (including Draft/Cancelled).
SELECT c.id, c.name, c.email
FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM sales_orders o WHERE o.customer_id = c.id)
ORDER BY c.id;

-- 4. Month-wise Confirmed sales, grouped by BOTH year and month.
SELECT YEAR(order_date) AS sales_year, MONTH(order_date) AS sales_month,
       COUNT(*) AS confirmed_order_count, SUM(grand_total) AS total_sales
FROM sales_orders
WHERE status = 'Confirmed'
GROUP BY YEAR(order_date), MONTH(order_date)
ORDER BY sales_year, sales_month;

-- 5. Products strictly below a supplied threshold; edit this input before execution.
SET @stock_threshold = 10;
SELECT id, product_code, name, stock_quantity, status
FROM products
WHERE stock_quantity < @stock_threshold
ORDER BY stock_quantity, id;
