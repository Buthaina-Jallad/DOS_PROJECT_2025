# order-service/app.py
import os
import sqlite3
import requests
from flask import Flask, jsonify, g

# مسار قاعدة الطلبات
DB_PATH = os.environ.get("DB_PATH", "/data/orders.db")

# عنوان خدمة الكتالوج داخل شبكة الـ Docker
CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog:5000")

app = Flask(__name__)

# ---------- DB helpers ----------
def get_db():
    if "db" not in g:
        # check_same_thread=False للسماح بالاستعمال داخل gunicorn workers
        con = sqlite3.connect(DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        # تحسينات أمان/أداء اختيارية
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        g.db = con
    return g.db

def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id   INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    con.commit()

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ---------- Routes ----------
@app.get("/health")
def health():
    return jsonify({"ok": True, "db_exists": os.path.exists(DB_PATH)}), 200

@app.post("/purchase/<int:item_id>")
def purchase(item_id: int):
    """
    1) يطلب من الكتالوج حجز/تنقيص الكمية عبر /decrement/<id>
    2) إذا نجح، يسجل الطلب في orders.db
    3) يرجّع JSON واضح دائماً
    """
    # (1) حجز من الكتالوج
    try:
        r = requests.post(f"{CATALOG_URL}/decrement/{item_id}", timeout=5)
    except requests.RequestException as e:
        return jsonify({
            "ok": False,
            "error": "catalog_unreachable",
            "detail": str(e)
        }), 502

    if r.status_code != 200:
        # مرّر رسالة الكتالوج كما هي قدر الإمكان
        try:
            upstream = r.json()
        except ValueError:
            upstream = {"status": r.status_code, "body": (r.text or "")[:400]}
        return jsonify({"ok": False, "from": "catalog", **upstream}), r.status_code

    # (2) سجّل الطلب محلياً بعد نجاح الحجز
    try:
        con = get_db()
        con.execute("INSERT INTO orders(item_id) VALUES (?)", (item_id,))
        con.commit()
    except Exception as e:
        # فشل التسجيل بعد الحجز — بإمكانك لاحقاً تعمل “تعويض” (compensation) إذا بدك
        return jsonify({"ok": False, "error": "db_insert_failed", "detail": str(e)}), 500

    # (3) نجاح
    return jsonify({"ok": True, "item_id": item_id}), 200

# اجبر التهيئة تحت Gunicorn أيضاً
with app.app_context():
    init_db()

if __name__ == "_main_":
    # تشغيل محلي (خارج Docker)
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5001)