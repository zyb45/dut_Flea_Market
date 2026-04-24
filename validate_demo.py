"""用于本地快速验证数据库和核心查询是否可用。"""
from app import app, init_db


def main() -> None:
    init_db(force_reset=True)
    with app.app_context():
        from app import query_all, query_one

        checks = {
            '商品总数': query_one('SELECT COUNT(*) AS v FROM item')['v'],
            '用户总数': query_one('SELECT COUNT(*) AS v FROM user')['v'],
            '订单总数': query_one('SELECT COUNT(*) AS v FROM orders')['v'],
            '未售商品数': query_one('SELECT COUNT(*) AS v FROM unsold_item_view')['v'],
            '已售商品数': query_one('SELECT COUNT(*) AS v FROM sold_item_view')['v'],
        }
        for k, v in checks.items():
            print(f'{k}: {v}')

        print('\n[基本查询] 价格大于 30 的商品:')
        for row in query_all('SELECT item_id, item_name, price FROM item WHERE price > 30 ORDER BY price DESC'):
            print(row)

        print('\n[连接查询] 已售商品及其买家姓名:')
        for row in query_all(
            '''
            SELECT i.item_name, u.user_name AS buyer_name
            FROM item i
            JOIN orders o ON i.item_id = o.item_id
            JOIN user u ON o.buyer_id = u.user_id
            ORDER BY i.item_id
            '''
        ):
            print(row)

        print('\n[聚合] 发布商品数量最多的用户:')
        print(query_one(
            '''
            SELECT u.user_id, u.user_name, COUNT(i.item_id) AS item_count
            FROM user u
            LEFT JOIN item i ON u.user_id = i.seller_id
            GROUP BY u.user_id, u.user_name
            ORDER BY item_count DESC, u.user_id
            LIMIT 1
            '''
        ))


if __name__ == '__main__':
    main()
