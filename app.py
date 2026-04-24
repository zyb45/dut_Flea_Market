from __future__ import annotations

import os
import re
import sqlite3
from contextlib import closing
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'campus_market.db'
SCHEMA_PATH = BASE_DIR / 'sql' / 'schema.sql'
SEED_PATH = BASE_DIR / 'sql' / 'seed.sql'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'campus-market-demo-secret-key'
app.config['DATABASE'] = str(DB_PATH)

CATEGORY_LABELS = {
    'Book': '书籍',
    'DailyGoods': '生活用品',
    'Electronics': '电子产品',
    'Furniture': '家具',
    'Sports': '运动用品',
    'Other': '其他',
}

STATUS_LABELS = {0: '未售出', 1: '已售出'}


def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = dict_factory
        conn.execute('PRAGMA foreign_keys = ON;')
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception: Exception | None) -> None:
    db = g.pop('db', None)
    if db is not None:
        db.close()


def execute_script(conn: sqlite3.Connection, path: Path) -> None:
    conn.executescript(path.read_text(encoding='utf-8'))


def init_db(force_reset: bool = False) -> None:
    if force_reset and DB_PATH.exists():
        DB_PATH.unlink()
    if DB_PATH.exists() and not force_reset:
        return
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute('PRAGMA foreign_keys = ON;')
        execute_script(conn, SCHEMA_PATH)
        execute_script(conn, SEED_PATH)
        conn.commit()


def ensure_admin_and_columns() -> None:
    if not DB_PATH.exists():
        return
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = dict_factory
        columns = {row['name'] for row in conn.execute('PRAGMA table_info(user)').fetchall()}
        if 'password' not in columns:
            conn.execute("ALTER TABLE user ADD COLUMN password TEXT NOT NULL DEFAULT '123456'")
        if 'role' not in columns:
            conn.execute("ALTER TABLE user ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.execute(
            '''
            INSERT INTO user (user_id, user_name, phone, password, role)
            VALUES ('admin', '平台管理员', '13800000000', 'admin', 'admin')
            ON CONFLICT(user_id) DO UPDATE SET
                user_name = excluded.user_name,
                phone = excluded.phone,
                password = excluded.password,
                role = excluded.role
            '''
        )
        conn.commit()


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    return get_db().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    return get_db().execute(sql, params).fetchone()


def category_label(value: str) -> str:
    return CATEGORY_LABELS.get(value, value)


def next_prefixed_id(table: str, column: str, prefix: str, width: int = 3) -> str:
    rows = query_all(f'SELECT {column} AS value FROM {table}')
    max_number = 0
    pattern = re.compile(rf'^{re.escape(prefix)}(\d+)$')
    for row in rows:
        match = pattern.match(row['value'])
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f'{prefix}{max_number + 1:0{width}d}'


def current_user() -> dict | None:
    user_id = session.get('user_id')
    if not user_id:
        return None
    return query_one('SELECT user_id, user_name, phone, role FROM user WHERE user_id = ?', (user_id,))


@app.before_request
def load_current_user() -> None:
    init_db()
    ensure_admin_and_columns()
    g.current_user = current_user()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            flash('请先登录后再继续操作。', 'error')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            flash('请先登录管理员账号。', 'error')
            return redirect(url_for('login'))
        if g.current_user['role'] != 'admin':
            flash('当前账号没有访问管理员页面的权限。', 'error')
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    return wrapped_view


@app.context_processor
def inject_globals() -> dict:
    return {
        'category_label': category_label,
        'status_labels': STATUS_LABELS,
        'category_labels': CATEGORY_LABELS,
        'current_user': g.get('current_user'),
    }


@app.route('/')
@login_required
def index():
    item_total = query_one('SELECT COUNT(*) AS total FROM item')['total']
    sold_total = query_one('SELECT COUNT(*) AS total FROM item WHERE status = 1')['total']
    unsold_total = item_total - sold_total
    order_total = query_one('SELECT COUNT(*) AS total FROM orders')['total']
    top_seller = query_one(
        '''
        SELECT u.user_id, u.user_name, COUNT(i.item_id) AS item_count
        FROM user u
        LEFT JOIN item i ON u.user_id = i.seller_id
        GROUP BY u.user_id, u.user_name
        ORDER BY item_count DESC, u.user_id
        LIMIT 1
        '''
    )
    latest_orders = query_all(
        '''
        SELECT o.order_id, i.item_name, u.user_name AS buyer_name, o.order_date
        FROM orders o
        JOIN item i ON o.item_id = i.item_id
        JOIN user u ON o.buyer_id = u.user_id
        ORDER BY o.order_date DESC, o.order_id DESC
        LIMIT 5
        '''
    )
    own_stats = None
    if g.current_user['role'] != 'admin':
        own_stats = {
            'published': query_one('SELECT COUNT(*) AS total FROM item WHERE seller_id = ?', (g.current_user['user_id'],))['total'],
            'sold': query_one(
                'SELECT COUNT(*) AS total FROM item WHERE seller_id = ? AND status = 1',
                (g.current_user['user_id'],),
            )['total'],
            'bought': query_one('SELECT COUNT(*) AS total FROM orders WHERE buyer_id = ?', (g.current_user['user_id'],))['total'],
        }
    return render_template('index.html', item_total=item_total, sold_total=sold_total, unsold_total=unsold_total,
                           order_total=order_total, top_seller=top_seller, latest_orders=latest_orders,
                           own_stats=own_stats)


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()
        user = query_one(
            'SELECT user_id, user_name, role FROM user WHERE user_id = ? AND password = ?',
            (user_id, password),
        )
        if user:
            session.clear()
            session['user_id'] = user['user_id']
            flash(f'欢迎回来，{user["user_name"]}。', 'success')
            return redirect(url_for('index'))
        flash('登录失败：账号或密码不正确。', 'error')
    return render_template('login.html')


@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        user_name = request.form.get('user_name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        if not all([user_id, user_name, phone, password]):
            flash('注册失败：请完整填写账号、昵称、手机号和密码。', 'error')
            return redirect(url_for('register'))
        try:
            get_db().execute(
                '''
                INSERT INTO user (user_id, user_name, phone, password, role)
                VALUES (?, ?, ?, ?, 'user')
                ''',
                (user_id, user_name, phone, password),
            )
            get_db().commit()
            session.clear()
            session['user_id'] = user_id
            flash('注册成功，可以开始发布或购买商品了。', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError as exc:
            flash(f'注册失败：{exc}', 'error')
    return render_template('register.html')


@app.post('/logout')
def logout():
    session.clear()
    flash('已退出当前账号。', 'success')
    return redirect(url_for('login'))


@app.route('/users')
@admin_required
def users():
    user_rows = query_all(
        '''
        SELECT u.user_id, u.user_name, u.phone, u.role,
               COUNT(i.item_id) AS published_count,
               SUM(CASE WHEN i.status = 1 THEN 1 ELSE 0 END) AS sold_count
        FROM user u
        LEFT JOIN item i ON u.user_id = i.seller_id
        GROUP BY u.user_id, u.user_name, u.phone, u.role
        ORDER BY u.user_id
        '''
    )
    return render_template('users.html', users=user_rows)


@app.route('/items')
@login_required
def items():
    item_rows = query_all(
        '''
        SELECT i.item_id, i.item_name, i.category, i.price, i.status, i.seller_id,
               u.user_name AS seller_name,
               o.buyer_id, bu.user_name AS buyer_name,
               o.order_date
        FROM item i
        JOIN user u ON i.seller_id = u.user_id
        LEFT JOIN orders o ON i.item_id = o.item_id
        LEFT JOIN user bu ON o.buyer_id = bu.user_id
        ORDER BY i.item_id
        '''
    )
    users_all = query_all("SELECT user_id, user_name FROM user WHERE role = 'user' ORDER BY user_id")
    return render_template('items.html', items=item_rows, users=users_all)


@app.route('/orders')
@login_required
def orders():
    where = ''
    params = ()
    if g.current_user['role'] != 'admin':
        where = 'WHERE o.buyer_id = ? OR i.seller_id = ?'
        params = (g.current_user['user_id'], g.current_user['user_id'])
    order_rows = query_all(
        f'''
        SELECT o.order_id, o.order_date, o.buyer_id, bu.user_name AS buyer_name,
               o.item_id, i.item_name,
               i.seller_id, su.user_name AS seller_name,
               i.price, i.category
        FROM orders o
        JOIN item i ON o.item_id = i.item_id
        JOIN user bu ON o.buyer_id = bu.user_id
        JOIN user su ON i.seller_id = su.user_id
        {where}
        ORDER BY o.order_date DESC, o.order_id DESC
        ''',
        params,
    )
    return render_template('orders.html', orders=order_rows)


@app.route('/queries')
@admin_required
def queries_page():
    category = request.args.get('category', '').strip()
    seller_id = request.args.get('seller_id', '').strip()
    status = request.args.get('status', '').strip()
    min_price_raw = request.args.get('min_price', '30').strip()
    max_price_raw = request.args.get('max_price', '').strip()
    try:
        min_price = float(min_price_raw) if min_price_raw else None
        max_price = float(max_price_raw) if max_price_raw else None
    except ValueError:
        flash('价格筛选条件无效，已恢复默认查询。', 'error')
        min_price, max_price = 30, None

    filters = []
    params = []
    if category:
        filters.append('i.category = ?')
        params.append(category)
    if seller_id:
        filters.append('i.seller_id = ?')
        params.append(seller_id)
    if status in {'0', '1'}:
        filters.append('i.status = ?')
        params.append(int(status))
    if min_price is not None:
        filters.append('i.price >= ?')
        params.append(min_price)
    if max_price is not None:
        filters.append('i.price <= ?')
        params.append(max_price)
    where = f"WHERE {' AND '.join(filters)}" if filters else ''

    custom_items = query_all(
        f'''
        SELECT i.item_id, i.item_name, i.category, i.price, i.status,
               i.seller_id, u.user_name AS seller_name
        FROM item i
        JOIN user u ON i.seller_id = u.user_id
        {where}
        ORDER BY i.status, i.price DESC, i.item_id
        ''',
        tuple(params),
    )
    sellers = query_all("SELECT user_id, user_name FROM user WHERE role = 'user' ORDER BY user_id")
    category_counts = query_all('SELECT category, COUNT(*) AS category_count FROM item GROUP BY category ORDER BY category')
    buyer_orders = query_all(
        '''
        SELECT bu.user_name AS buyer_name, COUNT(o.order_id) AS order_count, COALESCE(SUM(i.price), 0) AS total_spent
        FROM user bu
        LEFT JOIN orders o ON bu.user_id = o.buyer_id
        LEFT JOIN item i ON o.item_id = i.item_id
        WHERE bu.role = 'user'
        GROUP BY bu.user_id, bu.user_name
        ORDER BY order_count DESC, total_spent DESC
        '''
    )

    join_sold_buyer = query_all(
        '''
        SELECT i.item_id, i.item_name, u.user_name AS buyer_name
        FROM item i
        JOIN orders o ON i.item_id = o.item_id
        JOIN user u ON o.buyer_id = u.user_id
        WHERE i.status = 1
        ORDER BY i.item_id
        '''
    )
    join_order_detail = query_all(
        '''
        SELECT o.order_id, i.item_name, u.user_name AS buyer_name, o.order_date
        FROM orders o
        JOIN item i ON o.item_id = i.item_id
        JOIN user u ON o.buyer_id = u.user_id
        ORDER BY o.order_date, o.order_id
        '''
    )
    item_purchase_status = query_all(
        '''
        SELECT i.item_id, i.item_name, su.user_name AS seller_name,
               CASE WHEN o.order_id IS NULL THEN '未购买' ELSE '已购买' END AS purchase_status,
               COALESCE(u.user_name, '-') AS buyer_name
        FROM item i
        JOIN user su ON i.seller_id = su.user_id
        LEFT JOIN orders o ON i.item_id = o.item_id
        LEFT JOIN user u ON o.buyer_id = u.user_id
        ORDER BY i.item_id
        '''
    )
    return render_template(
        'queries.html',
        custom_items=custom_items,
        sellers=sellers,
        category_counts=category_counts,
        buyer_orders=buyer_orders,
        selected_filters={
            'category': category,
            'seller_id': seller_id,
            'status': status,
            'min_price': '' if min_price is None else min_price,
            'max_price': '' if max_price is None else max_price,
        },
        join_sold_buyer=join_sold_buyer,
        join_order_detail=join_order_detail,
        item_purchase_status=item_purchase_status,
    )


@app.route('/analytics')
@admin_required
def analytics():
    total_items = query_one('SELECT COUNT(*) AS total_items FROM item')
    category_counts = query_all('SELECT category, COUNT(*) AS category_count FROM item GROUP BY category ORDER BY category')
    avg_price = query_one('SELECT ROUND(AVG(price), 2) AS avg_price FROM item')
    top_seller = query_one(
        '''
        SELECT u.user_id, u.user_name, COUNT(i.item_id) AS item_count
        FROM user u
        LEFT JOIN item i ON u.user_id = i.seller_id
        GROUP BY u.user_id, u.user_name
        ORDER BY item_count DESC, u.user_id
        LIMIT 1
        '''
    )
    sold_view = query_all('SELECT item_id, item_name, buyer_id, order_date FROM sold_item_view ORDER BY item_id')
    unsold_view = query_all('SELECT item_id, item_name, category, price, seller_id FROM unsold_item_view ORDER BY item_id')
    return render_template(
        'analytics.html',
        total_items=total_items,
        category_counts=category_counts,
        avg_price=avg_price,
        top_seller=top_seller,
        sold_view=sold_view,
        unsold_view=unsold_view,
    )


@app.post('/ops/add-item')
@login_required
def add_item():
    item_id = request.form.get('item_id', '').strip()
    item_name = request.form.get('item_name', '').strip()
    category = request.form.get('category', '').strip()
    price = request.form.get('price', '').strip()
    seller_id = request.form.get('seller_id', '').strip()
    if g.current_user['role'] != 'admin':
        seller_id = g.current_user['user_id']

    if not item_id:
        item_id = next_prefixed_id('item', 'item_id', 'i')

    if not all([item_name, category, price, seller_id]):
        flash('新增商品失败：请完整填写商品名、类别、价格和卖家。', 'error')
        return redirect(url_for('items'))

    try:
        get_db().execute(
            '''
            INSERT INTO item (item_id, item_name, category, price, status, seller_id)
            VALUES (?, ?, ?, ?, 0, ?)
            ''',
            (item_id, item_name, category, float(price), seller_id),
        )
        get_db().commit()
        flash(f'新增商品成功：{item_id} / {item_name}', 'success')
    except sqlite3.IntegrityError as exc:
        flash(f'新增商品失败：{exc}', 'error')
    return redirect(url_for('items'))


@app.post('/ops/update-price')
@login_required
def update_price():
    item_id = request.form.get('item_id', '').strip()
    new_price = request.form.get('new_price', '').strip()
    item = query_one('SELECT seller_id, status FROM item WHERE item_id = ?', (item_id,))
    if not item:
        flash(f'修改失败：未找到商品 {item_id}', 'error')
        return redirect(url_for('items'))
    if g.current_user['role'] != 'admin' and item['seller_id'] != g.current_user['user_id']:
        flash('修改失败：只能调整自己发布的商品。', 'error')
        return redirect(url_for('items'))
    if item['status'] == 1:
        flash('修改失败：已售出的商品不能再调整价格。', 'error')
        return redirect(url_for('items'))
    try:
        cur = get_db().execute('UPDATE item SET price = ? WHERE item_id = ?', (float(new_price), item_id))
        get_db().commit()
        if cur.rowcount == 0:
            flash(f'修改失败：未找到商品 {item_id}', 'error')
        else:
            flash(f'已将商品 {item_id} 的价格更新为 {new_price}', 'success')
    except (ValueError, sqlite3.IntegrityError) as exc:
        flash(f'修改失败：{exc}', 'error')
    return redirect(url_for('items'))


@app.post('/ops/delete-item')
@login_required
def delete_item():
    item_id = request.form.get('item_id', '').strip()
    item = query_one('SELECT status, item_name, seller_id FROM item WHERE item_id = ?', (item_id,))
    if not item:
        flash(f'删除失败：未找到商品 {item_id}', 'error')
        return redirect(url_for('items'))
    if item['status'] == 1:
        flash(f'删除失败：商品 {item_id} 已售出，不能删除。', 'error')
        return redirect(url_for('items'))
    if g.current_user['role'] != 'admin' and item['seller_id'] != g.current_user['user_id']:
        flash('删除失败：只能删除自己发布的未售商品。', 'error')
        return redirect(url_for('items'))

    get_db().execute('DELETE FROM item WHERE item_id = ?', (item_id,))
    get_db().commit()
    flash(f'已删除未售出商品：{item_id} / {item["item_name"]}', 'success')
    return redirect(url_for('items'))


@app.post('/ops/purchase')
@login_required
def purchase_item():
    buyer_id = request.form.get('buyer_id', '').strip()
    if g.current_user['role'] != 'admin':
        buyer_id = g.current_user['user_id']
    item_id = request.form.get('item_id', '').strip()
    order_id = next_prefixed_id('orders', 'order_id', 'o')
    item = query_one('SELECT seller_id, status FROM item WHERE item_id = ?', (item_id,))
    if not item:
        flash(f'购买失败：未找到商品 {item_id}', 'error')
        return redirect(url_for('items'))
    if item['seller_id'] == buyer_id:
        flash('购买失败：不能购买自己发布的商品。', 'error')
        return redirect(url_for('items'))
    conn = get_db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute(
            '''
            INSERT INTO orders (order_id, buyer_id, item_id, order_date)
            VALUES (?, ?, ?, date('now', 'localtime'))
            ''',
            (order_id, buyer_id, item_id),
        )
        conn.commit()
        flash(f'购买成功：订单 {order_id} 已创建，商品 {item_id} 已标记为已售出。', 'success')
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        flash(f'购买失败：{exc}', 'error')
    return redirect(url_for('items'))


@app.post('/ops/reset')
@admin_required
def reset_db():
    close_db(None)
    init_db(force_reset=True)
    flash('数据库已重置为初始数据。', 'success')
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', '5000'))
    app.run(host='0.0.0.0', port=port, debug=False)
