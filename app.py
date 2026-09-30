from flask import Flask, render_template, jsonify, request, redirect, url_for
from datetime import datetime, timedelta
import sqlite3, os, random

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, 'fulfillment.db')
app = Flask(__name__)

STATUSES = ['Processing', 'Picking', 'Packing', 'Staged', 'Shipped', 'Blocked']


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        customer TEXT NOT NULL,
        channel TEXT NOT NULL,
        priority TEXT NOT NULL,
        deadline TEXT NOT NULL,
        status TEXT NOT NULL,
        courier TEXT,
        pickup TEXT,
        created_at TEXT NOT NULL,
        box_id TEXT,
        issue TEXT
    );

    CREATE TABLE IF NOT EXISTS products (
        sku TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        variant TEXT NOT NULL,
        main_stock INTEGER NOT NULL,
        secondary_stock INTEGER NOT NULL,
        reserved INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        sku TEXT,
        qty INTEGER,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(sku) REFERENCES products(sku)
    );

    CREATE TABLE IF NOT EXISTS pick_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        sku TEXT NOT NULL,
        verified_qty INTEGER NOT NULL,
        verified_variant TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        UNIQUE(order_id, sku),
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(sku) REFERENCES products(sku)
    );

    CREATE TABLE IF NOT EXISTS stock_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        sku TEXT NOT NULL,
        qty INTEGER NOT NULL,
        from_warehouse TEXT NOT NULL,
        to_warehouse TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(sku) REFERENCES products(sku)
    );

    CREATE TABLE IF NOT EXISTS exceptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        severity TEXT,
        type TEXT,
        message TEXT,
        status TEXT,
        created_at TEXT,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );
    ''')

    if con.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0:
        now = datetime.now()

        orders = [
            (1042, 'Rahul Mehta', 'Website', 'Priority',
             (now + timedelta(hours=2)).isoformat(timespec='minutes'),
             'Picking', 'BlueDart', '17:00',
             (now - timedelta(hours=2)).isoformat(timespec='minutes'),
             None, None),

            (1043, 'Anil Kumar', 'Amazon', 'Normal',
             (now + timedelta(hours=7)).isoformat(timespec='minutes'),
             'Packing', 'Delhivery', '19:00',
             (now - timedelta(hours=1)).isoformat(timespec='minutes'),
             'BX-0183', None),

            (1044, 'Priya Shah', 'Website', 'Priority',
             (now + timedelta(hours=1)).isoformat(timespec='minutes'),
             'Blocked', 'DTDC', '16:30',
             (now - timedelta(hours=3)).isoformat(timespec='minutes'),
             None, 'Main warehouse stock unavailable'),

            (1045, 'Kiran Rao', 'Flipkart', 'Normal',
             (now + timedelta(hours=5)).isoformat(timespec='minutes'),
             'Staged', 'BlueDart', '17:00',
             (now - timedelta(hours=2)).isoformat(timespec='minutes'),
             'BX-0184', None),

            (1046, 'Sneha Reddy', 'Website', 'Priority',
             (now + timedelta(hours=3)).isoformat(timespec='minutes'),
             'Processing', 'Delhivery', '18:00',
             (now - timedelta(minutes=40)).isoformat(timespec='minutes'),
             None, None),

            (1047, 'Arjun Nair', 'Amazon', 'Normal',
             (now + timedelta(hours=8)).isoformat(timespec='minutes'),
             'Picking', 'DTDC', '20:00',
             (now - timedelta(minutes=30)).isoformat(timespec='minutes'),
             None, None),

            (1048, 'Meera Iyer', 'Website', 'Normal',
             (now + timedelta(hours=6)).isoformat(timespec='minutes'),
             'Packing', 'BlueDart', '19:00',
             (now - timedelta(hours=2)).isoformat(timespec='minutes'),
             'BX-0188', None),

            (1049, 'Vikram Singh', 'Flipkart', 'Priority',
             (now + timedelta(hours=2)).isoformat(timespec='minutes'),
             'Staged', 'Delhivery', '17:30',
             (now - timedelta(hours=3)).isoformat(timespec='minutes'),
             'BX-0189', 'Courier pickup pending')
        ]

        con.executemany(
            'INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            orders
        )

        products = [
            ('SKU-101', 'Classic T-Shirt', 'Blue / M', 2, 10, 1),
            ('SKU-102', 'Running Shoes', 'Black / 9', 8, 4, 3),
            ('SKU-103', 'Everyday Cap', 'Black / Free Size', 16, 8, 2),
            ('SKU-104', 'Hoodie', 'Grey / L', 5, 7, 4),
            ('SKU-105', 'Sports Socks', 'White / M', 24, 20, 6)
        ]

        con.executemany(
            'INSERT INTO products VALUES (?,?,?,?,?,?)',
            products
        )

        items = [
            (1042, 'SKU-101', 1),
            (1042, 'SKU-102', 1),
            (1042, 'SKU-103', 1),
            (1043, 'SKU-104', 1),
            (1043, 'SKU-105', 2),
            (1044, 'SKU-101', 4),
            (1045, 'SKU-103', 1),
            (1046, 'SKU-102', 1),
            (1047, 'SKU-104', 1),
            (1048, 'SKU-105', 2),
            (1049, 'SKU-103', 2)
        ]

        con.executemany(
            'INSERT INTO order_items(order_id,sku,qty) VALUES (?,?,?)',
            items
        )

        exc = [
            (
                1044, 'HIGH', 'Inventory',
                'Priority order blocked: 4 units required, only 2 available in main warehouse.',
                'Open', now.isoformat(timespec='minutes')
            ),
            (
                1049, 'MEDIUM', 'Courier',
                'Packed box is staged but courier pickup is still pending.',
                'Open', now.isoformat(timespec='minutes')
            ),
            (
                1042, 'HIGH', 'Deadline',
                'Priority order is within the same-day dispatch window.',
                'Open', now.isoformat(timespec='minutes')
            )
        ]

        con.executemany(
            'INSERT INTO exceptions(order_id,severity,type,message,status,created_at) VALUES (?,?,?,?,?,?)',
            exc
        )

    # Keep the demo's inventory story consistent even when an older V1 database already exists.
    con.execute("UPDATE products SET reserved=0 WHERE sku='SKU-101'")
    con.execute(
        "UPDATE exceptions SET message='Priority order blocked: 4 units required, only 2 available in main warehouse.' WHERE order_id=1044 AND type='Inventory'"
    )

    con.commit()
    con.close()


def metrics():
    con = db()

    counts = {
        r['status']: r['n']
        for r in con.execute(
            'SELECT status,COUNT(*) n FROM orders GROUP BY status'
        )
    }

    priority = con.execute(
        "SELECT COUNT(*) FROM orders WHERE priority='Priority'"
    ).fetchone()[0]

    blocked = con.execute(
        "SELECT COUNT(*) FROM orders WHERE status='Blocked'"
    ).fetchone()[0]

    open_exc = con.execute(
        "SELECT COUNT(*) FROM exceptions WHERE status='Open'"
    ).fetchone()[0]

    con.close()

    return dict(
        total=sum(counts.values()),
        priority=priority,
        blocked=blocked,
        open_exceptions=open_exc,
        **counts
    )


@app.route('/')
def dashboard():
    con = db()
    m = metrics()

    at_risk = con.execute(
        "SELECT * FROM orders WHERE priority='Priority' AND status NOT IN ('Shipped') ORDER BY deadline LIMIT 5"
    ).fetchall()

    exceptions = con.execute(
        "SELECT e.*,o.customer FROM exceptions e LEFT JOIN orders o ON e.order_id=o.id WHERE e.status='Open' ORDER BY CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, e.id DESC LIMIT 6"
    ).fetchall()

    con.close()

    return render_template(
        'dashboard.html',
        metrics=m,
        at_risk=at_risk,
        exceptions=exceptions
    )


@app.route('/orders')
def orders():
    status = request.args.get('status', 'All')
    priority = request.args.get('priority', 'All')
    q = request.args.get('q', '').strip()

    con = db()
    sql = 'SELECT * FROM orders WHERE 1=1'
    args = []

    if status != 'All':
        sql += ' AND status=?'
        args.append(status)

    if priority != 'All':
        sql += ' AND priority=?'
        args.append(priority)

    if q:
        sql += ' AND (CAST(id AS TEXT) LIKE ? OR customer LIKE ? OR channel LIKE ?)'
        args += [f'%{q}%'] * 3

    sql += ' ORDER BY CASE priority WHEN "Priority" THEN 1 ELSE 2 END, deadline'

    rows = con.execute(sql, args).fetchall()
    con.close()

    return render_template(
        'orders.html',
        orders=rows,
        status=status,
        priority=priority,
        q=q
    )


@app.route('/orders/<int:order_id>')
def order_detail(order_id):
    con = db()

    order = con.execute(
        'SELECT * FROM orders WHERE id=?',
        (order_id,)
    ).fetchone()

    items = con.execute(
        'SELECT oi.*,p.name,p.variant,p.main_stock,p.secondary_stock FROM order_items oi JOIN products p ON p.sku=oi.sku WHERE order_id=?',
        (order_id,)
    ).fetchall()

    transfers = con.execute(
        'SELECT st.*,p.name,p.variant FROM stock_transfers st JOIN products p ON p.sku=st.sku WHERE st.order_id=? ORDER BY st.id DESC',
        (order_id,)
    ).fetchall()

    con.close()

    return render_template(
        'order_detail.html',
        order=order,
        items=items,
        transfers=transfers
    )


@app.route('/picking')
def picking():
    con = db()

    rows = con.execute(
        "SELECT * FROM orders WHERE status IN ('Processing','Picking') ORDER BY CASE priority WHEN 'Priority' THEN 1 ELSE 2 END, deadline"
    ).fetchall()

    con.close()

    return render_template('picking.html', orders=rows)


@app.route('/inventory')
def inventory():
    con = db()

    rows = con.execute(
        'SELECT *, main_stock-reserved available FROM products ORDER BY available'
    ).fetchall()

    con.close()

    return render_template('inventory.html', products=rows)


@app.route('/packing')
def packing():
    con = db()

    rows = con.execute(
        "SELECT * FROM orders WHERE status IN ('Packing','Staged') ORDER BY pickup, priority"
    ).fetchall()

    con.close()

    return render_template('packing.html', orders=rows)


@app.route('/exceptions')
def exception_page():
    con = db()

    rows = con.execute(
        "SELECT e.*,o.customer,o.priority,o.status order_status FROM exceptions e LEFT JOIN orders o ON e.order_id=o.id ORDER BY CASE e.status WHEN 'Open' THEN 1 ELSE 2 END, CASE e.severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END"
    ).fetchall()

    con.close()

    return render_template('exceptions.html', exceptions=rows)


@app.route('/analytics')
def analytics():
    con = db()

    status_rows = con.execute(
        'SELECT status,COUNT(*) AS n FROM orders GROUP BY status'
    ).fetchall()

    status_counts = {r['status']: r['n'] for r in status_rows}
    total = sum(status_counts.values())
    shipped = status_counts.get('Shipped', 0)

    priority_total = con.execute(
        "SELECT COUNT(*) FROM orders WHERE priority='Priority'"
    ).fetchone()[0]

    priority_shipped = con.execute(
        "SELECT COUNT(*) FROM orders WHERE priority='Priority' AND status='Shipped'"
    ).fetchone()[0]

    open_count = con.execute(
        "SELECT COUNT(*) FROM exceptions WHERE status='Open'"
    ).fetchone()[0]

    severity_rows = con.execute(
        "SELECT severity,COUNT(*) n FROM exceptions WHERE status='Open' GROUP BY severity"
    ).fetchall()

    severity_counts = {r['severity']: r['n'] for r in severity_rows}

    con.close()

    return render_template(
        'analytics.html',
        status_counts=status_counts,
        total=total,
        shipped=shipped,
        priority_total=priority_total,
        priority_shipped=priority_shipped,
        open_count=open_count,
        severity_counts=severity_counts
    )


@app.route('/reports')
def reports():
    conn = db()

    orders = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC"
    ).fetchall()

    total = conn.execute(
        "SELECT COUNT(*) FROM orders"
    ).fetchone()[0]

    shipped = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status='Shipped'"
    ).fetchone()[0]

    open_orders = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status != 'Shipped'"
    ).fetchone()[0]

    # Corrected: database uses 'Priority', not 'High'
    high_priority = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE priority='Priority'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        'reports.html',
        orders=orders,
        total=total,
        shipped=shipped,
        open_orders=open_orders,
        high_priority=high_priority
    )


@app.post('/api/orders/<int:order_id>/status')
def update_status(order_id):
    data = request.get_json() or {}
    status = data.get('status')

    if status not in STATUSES:
        return jsonify(error='Invalid status'), 400

    con = db()

    order = con.execute(
        'SELECT status FROM orders WHERE id=?',
        (order_id,)
    ).fetchone()

    if not order:
        con.close()
        return jsonify(error='Order not found'), 404

    if order['status'] == 'Picking' and status == 'Packing':
        con.close()
        return jsonify(
            error='Complete item verification before moving this order to Packing.'
        ), 409

    if order['status'] == 'Packing' and status == 'Staged':
        con.close()
        return jsonify(
            error='Assign a box ID and confirm packing from the Packing & Staging screen.'
        ), 409

    if order['status'] == 'Staged' and status == 'Shipped':
        con.close()
        return jsonify(
            error='Confirm courier handoff from the Packing & Staging screen.'
        ), 409

    con.execute(
        'UPDATE orders SET status=? WHERE id=?',
        (status, order_id)
    )

    con.commit()
    con.close()

    return jsonify(ok=True, status=status)


@app.post('/api/orders/<int:order_id>/verify-picking')
def verify_picking(order_id):
    data = request.get_json() or {}
    submitted = data.get('items', [])
    con = db()

    try:
        order = con.execute(
            'SELECT status FROM orders WHERE id=?',
            (order_id,)
        ).fetchone()

        if not order:
            return jsonify(error='Order not found'), 404

        if order['status'] != 'Picking':
            return jsonify(
                error='Only orders currently in Picking can be verified.'
            ), 409

        expected = con.execute(
            'SELECT oi.sku,oi.qty,p.variant FROM order_items oi JOIN products p ON p.sku=oi.sku WHERE oi.order_id=? ORDER BY oi.sku',
            (order_id,)
        ).fetchall()

        supplied = {
            str(x.get('sku', '')).strip().upper(): x
            for x in submitted
        }

        if len(supplied) != len(expected) or set(supplied) != set(
            x['sku'].upper() for x in expected
        ):
            return jsonify(
                error='Scan or enter every expected SKU exactly once.'
            ), 400

        for item in expected:
            row = supplied[item['sku'].upper()]

            try:
                qty = int(row.get('qty', 0))
            except (TypeError, ValueError):
                qty = 0

            variant = str(row.get('variant', '')).strip()

            if variant.casefold() != item['variant'].strip().casefold():
                return jsonify(
                    error=f"Variant mismatch for {item['sku']}. Expected: {item['variant']}"
                ), 400

            if qty != item['qty']:
                return jsonify(
                    error=f"Quantity mismatch for {item['sku']}. Expected {item['qty']}, entered {qty}."
                ), 400

        now = datetime.now().isoformat(timespec='minutes')

        for item in expected:
            con.execute(
                'INSERT OR REPLACE INTO pick_verifications(order_id,sku,verified_qty,verified_variant,verified_at) VALUES (?,?,?,?,?)',
                (
                    order_id,
                    item['sku'],
                    item['qty'],
                    item['variant'],
                    now
                )
            )

        con.execute(
            "UPDATE orders SET status='Packing' WHERE id=?",
            (order_id,)
        )

        con.commit()

        return jsonify(
            ok=True,
            status='Packing',
            message='All items verified. Order moved to Packing.'
        )

    except Exception as exc:
        con.rollback()
        return jsonify(error=str(exc)), 500

    finally:
        con.close()


@app.post('/api/orders/<int:order_id>/pack')
def pack_order(order_id):
    data = request.get_json() or {}
    box_id = (data.get('box_id') or '').strip().upper()

    if not box_id:
        return jsonify(
            error='Enter a box ID before confirming packing.'
        ), 400

    con = db()

    try:
        order = con.execute(
            'SELECT status FROM orders WHERE id=?',
            (order_id,)
        ).fetchone()

        if not order:
            return jsonify(error='Order not found'), 404

        if order['status'] != 'Packing':
            return jsonify(
                error='Only verified orders in Packing can be packed.'
            ), 409

        expected = con.execute(
            'SELECT COUNT(*) FROM order_items WHERE order_id=?',
            (order_id,)
        ).fetchone()[0]

        verified = con.execute(
            'SELECT COUNT(*) FROM pick_verifications WHERE order_id=?',
            (order_id,)
        ).fetchone()[0]

        if expected == 0 or verified != expected:
            return jsonify(
                error='Complete picking verification for every item before packing.'
            ), 409

        duplicate = con.execute(
            'SELECT id FROM orders WHERE box_id=? AND id<>?',
            (box_id, order_id)
        ).fetchone()

        if duplicate:
            return jsonify(
                error='That box ID is already assigned to another order.'
            ), 409

        con.execute(
            "UPDATE orders SET box_id=?,status='Staged' WHERE id=?",
            (box_id, order_id)
        )

        con.commit()

        return jsonify(
            ok=True,
            status='Staged',
            box_id=box_id,
            message='Packing confirmed. Box moved to staging.'
        )

    except Exception as exc:
        con.rollback()
        return jsonify(error=str(exc)), 500

    finally:
        con.close()


@app.post('/api/orders/<int:order_id>/handoff')
def handoff_order(order_id):
    con = db()

    try:
        order = con.execute(
            'SELECT status,box_id,courier FROM orders WHERE id=?',
            (order_id,)
        ).fetchone()

        if not order:
            return jsonify(error='Order not found'), 404

        if order['status'] != 'Staged':
            return jsonify(
                error='Only staged boxes can be handed to a courier.'
            ), 409

        if not order['box_id']:
            return jsonify(
                error='This order has no box ID. Complete packing first.'
            ), 409

        con.execute(
            "UPDATE orders SET status='Shipped' WHERE id=?",
            (order_id,)
        )

        con.execute(
            "UPDATE exceptions SET status='Resolved' WHERE order_id=? AND type='Courier' AND status='Open'",
            (order_id,)
        )

        con.commit()

        return jsonify(
            ok=True,
            status='Shipped',
            message=f"Handoff to {order['courier']} confirmed."
        )

    except Exception as exc:
        con.rollback()
        return jsonify(error=str(exc)), 500

    finally:
        con.close()


@app.post('/api/orders/<int:order_id>/transfer')
def transfer(order_id):
    con = db()

    try:
        order = con.execute(
            "SELECT * FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()

        if not order:
            return jsonify(error='Order not found'), 404

        if order['status'] != 'Blocked':
            return jsonify(error='This order is not blocked'), 400

        items = con.execute(
            "SELECT oi.sku, oi.qty, p.main_stock, p.secondary_stock, p.reserved FROM order_items oi JOIN products p ON p.sku=oi.sku WHERE oi.order_id=?",
            (order_id,)
        ).fetchall()

        transfers = []

        for item in items:
            available = max(0, item['main_stock'] - item['reserved'])
            shortage = max(0, item['qty'] - available)

            if shortage:
                if item['secondary_stock'] < shortage:
                    return jsonify(
                        error=f"Insufficient secondary stock for {item['sku']}"
                    ), 409

                transfers.append((item['sku'], shortage))

        if not transfers:
            con.execute(
                "UPDATE orders SET status='Picking', issue=NULL WHERE id=?",
                (order_id,)
            )

        else:
            now = datetime.now().isoformat(timespec='minutes')

            for sku, qty in transfers:
                con.execute(
                    "UPDATE products SET main_stock=main_stock+?, secondary_stock=secondary_stock-? WHERE sku=?",
                    (qty, qty, sku)
                )

                con.execute(
                    "INSERT INTO stock_transfers(order_id,sku,qty,from_warehouse,to_warehouse,status,created_at) VALUES (?,?,?,?,?,?,?)",
                    (
                        order_id,
                        sku,
                        qty,
                        'Secondary Warehouse',
                        'Main Warehouse',
                        'Completed',
                        now
                    )
                )

            con.execute(
                "UPDATE orders SET status='Picking', issue=NULL WHERE id=?",
                (order_id,)
            )

        con.execute(
            "UPDATE exceptions SET status='Resolved' WHERE order_id=? AND type='Inventory' AND status='Open'",
            (order_id,)
        )

        con.commit()

        return jsonify(
            ok=True,
            transfers=[
                {'sku': sku, 'qty': qty}
                for sku, qty in transfers
            ]
        )

    except Exception as exc:
        con.rollback()
        return jsonify(error=str(exc)), 500

    finally:
        con.close()


@app.post('/api/exceptions/<int:exception_id>/resolve')
def resolve(exception_id):
    con = db()

    con.execute(
        "UPDATE exceptions SET status='Resolved' WHERE id=?",
        (exception_id,)
    )

    con.commit()
    con.close()

    return jsonify(ok=True)


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)