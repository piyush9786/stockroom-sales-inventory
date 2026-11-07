-- Fictional records only. Run through `flask --app app seed-sample` after creating users.
INSERT INTO customers (name,email,mobile,city,status) VALUES
('Acme Traders','orders@acme.example','9000000001','Pune','Active'),
('Bluebird Supplies','hello@bluebird.example','9000000002','Mumbai','Active'),
('Cedar Stores','sales@cedar.example','9000000003','Nashik','Inactive');

INSERT INTO products (product_code,name,category,price,stock_quantity,status) VALUES
('PRD-001','Keyboard','Accessories',1500.00,20,'Active'),
('PRD-002','Mouse','Accessories',500.00,50,'Active'),
('PRD-003','USB-C Cable','Cables',250.00,4,'Active'),
('PRD-004','Legacy Adapter','Cables',100.00,0,'Inactive');

INSERT INTO stock_movements (product_id,movement_type,quantity_change,reason,created_by)
SELECT p.id,'Opening',p.stock_quantity,'Sample opening stock',u.id
FROM products p CROSS JOIN
(SELECT id FROM users WHERE role='Admin' ORDER BY id LIMIT 1) u
WHERE p.stock_quantity > 0;
