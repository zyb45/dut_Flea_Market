PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS sold_item_view;
DROP VIEW IF EXISTS unsold_item_view;
DROP TRIGGER IF EXISTS trg_orders_before_insert_check;
DROP TRIGGER IF EXISTS trg_orders_after_insert_update_item;
DROP TRIGGER IF EXISTS trg_items_before_update_status_check;
DROP TRIGGER IF EXISTS trg_orders_before_delete_restore_status;
DROP TRIGGER IF EXISTS trg_orders_after_delete_restore_status;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS item;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id   TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    phone     TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,
    role      TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user'))
);

CREATE TABLE item (
    item_id    TEXT PRIMARY KEY,
    item_name  TEXT NOT NULL,
    category   TEXT NOT NULL,
    price      REAL NOT NULL CHECK (price >= 0),
    status     INTEGER NOT NULL CHECK (status IN (0, 1)),
    seller_id  TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (seller_id) REFERENCES user(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE orders (
    order_id    TEXT PRIMARY KEY,
    buyer_id    TEXT NOT NULL,
    item_id     TEXT NOT NULL UNIQUE,
    order_date  TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (buyer_id) REFERENCES user(user_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (item_id) REFERENCES item(item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TRIGGER trg_orders_before_insert_check
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (SELECT 1 FROM item WHERE item_id = NEW.item_id) THEN
            RAISE(ABORT, '商品不存在')
        WHEN EXISTS (SELECT 1 FROM orders WHERE item_id = NEW.item_id) THEN
            RAISE(ABORT, '该商品已经有订单记录，不能重复购买')
        WHEN (SELECT status FROM item WHERE item_id = NEW.item_id) = 1 THEN
            RAISE(ABORT, '该商品已售出，不能重复购买')
    END;
END;

CREATE TRIGGER trg_orders_after_insert_update_item
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    UPDATE item
       SET status = 1
     WHERE item_id = NEW.item_id;
END;

CREATE TRIGGER trg_items_before_update_status_check
BEFORE UPDATE OF status ON item
FOR EACH ROW
WHEN NEW.status = 0 AND EXISTS (SELECT 1 FROM orders WHERE item_id = NEW.item_id)
BEGIN
    SELECT RAISE(ABORT, '已产生订单的商品不能重新设置为未售出');
END;

CREATE TRIGGER trg_orders_after_delete_restore_status
AFTER DELETE ON orders
FOR EACH ROW
BEGIN
    UPDATE item
       SET status = 0
     WHERE item_id = OLD.item_id;
END;

CREATE VIEW sold_item_view AS
SELECT i.item_id,
       i.item_name,
       o.buyer_id,
       o.order_date
  FROM item i
  JOIN orders o ON i.item_id = o.item_id;

CREATE VIEW unsold_item_view AS
SELECT item_id,
       item_name,
       category,
       price,
       seller_id
  FROM item
 WHERE status = 0;
