PRAGMA foreign_keys = ON;

INSERT INTO user (user_id, user_name, phone, password, role) VALUES
('admin', '平台管理员', '13800000000', 'admin', 'admin'),
('u001', '张三', '13800000001', '123456', 'user'),
('u002', '李四', '13800000002', '123456', 'user'),
('u003', '王五', '13800000003', '123456', 'user'),
('u004', '赵六', '13800000004', '123456', 'user');

INSERT INTO item (item_id, item_name, category, price, status, seller_id) VALUES
('i001', '高等数学教材',   'Book',        20, 0, 'u001'),
('i002', '宿舍护眼台灯',   'DailyGoods',  35, 0, 'u002'),
('i003', '单片机开发板',   'Electronics', 80, 0, 'u001'),
('i004', '折叠椅',         'Furniture',   50, 0, 'u003'),
('i005', '运动水杯',       'DailyGoods',  15, 0, 'u004');

INSERT INTO orders (order_id, buyer_id, item_id, order_date) VALUES
('o001', 'u003', 'i002', '2024-05-01'),
('o002', 'u002', 'i004', '2024-05-03');
