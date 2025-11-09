# catalog-service/app.py
import os
import sqlite3
from flask import Flask, jsonify, request, g

app = Flask(__name__)

# مسار قاعدة البيانات داخل الحاوية (قابل للتغيير عبر متغيّر بيئة)
DB_PATH = os.getenv("DB_PATH", "/data/catalog.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ---------------------------
# اتصال SQLite لكل طلب
# ---------------------------
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        # check_same_thread=False لأن Gunicorn قد ينشئ عدة Threads/Workers
        db = sqlite3.connect(DB_PATH, check_same_thread=False)
        db.row_factory = sqlite3.Row
        # تحسينات بسيطة للتزامن والأداء
        db.execute("PRAGMA journal_mode=WAL;")
        db.execute("PRAGMA foreign_keys=ON;")
        g._db = db
    return db

@app.teardown_appcontext
def close_db(e=None):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

# ---------------------------
# تهيئة قاعدة البيانات + Seed
# ---------------------------
def init_db():
    con = get_db()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id       INTEGER PRIMARY KEY,
            title    TEXT    NOT NULL,
            topic    TEXT    NOT NULL,
            price    REAL    NOT NULL,
            quantity INTEGER NOT NULL
        )
        """
    )
    con.executemany(
        "INSERT OR IGNORE INTO books(id, title, topic, price, quantity) VALUES(?,?,?,?,?)",
        [
            (1, "How to finish Project 3 on time", "distributed systems", 19.99, 8),
            (2, "Why theory classes are so hard.", "distributed systems", 24.90, 12),
            (3, "Spring in the Pioneer Valley", "distributed systems", 17.50, 5),
            (4, "Notes on Practical Microservices", "microservices", 29.00, 10),
        ],
    )
    con.commit()

# نهيّئ القاعدة لحظة الاستيراد (مفيد مع Gunicorn)
with app.app_context():
    init_db()

# ---------------------------
# Healthcheck
# ---------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

# ---------------------------
# REST Endpoints
# ---------------------------
@app.get("/search")
def search():
    topic = (request.args.get("topic") or "").strip().lower()
    con = get_db()
    if topic:
        rows = con.execute(
            "SELECT id, title FROM books WHERE lower(topic) LIKE ?",
            (f"%{topic}%",),
        ).fetchall()
    else:
        rows = con.execute("SELECT id, title FROM books").fetchall()
    return jsonify({"items": [dict(r) for r in rows]}), 200

@app.get("/info/<int:item_id>")
def info(item_id: int):
    con = get_db()
    row = con.execute(
        "SELECT id, title, price, quantity, topic FROM books WHERE id=?",
        (item_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify(dict(row)), 200

# يُستدعى من order-service لتقليل المخزون
@app.post("/decrement/<int:item_id>")
def decrement(item_id: int):
    con = get_db()

    # نتأكد موجود ومش صفر
    row = con.execute("SELECT quantity FROM books WHERE id=?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "not_found"}), 404
    if row["quantity"] <= 0:
        return jsonify({"error": "out_of_stock"}), 400

    # إنقاص ذري + حماية من السباق (WHERE quantity > 0)
    cur = con.execute(
        "UPDATE books SET quantity = quantity - 1 WHERE id=? AND quantity > 0",
        (item_id,),
    )
    con.commit()

    if cur.rowcount == 0:
        # صار صفر بين القراءة والتحديث
        return jsonify({"error": "out_of_stock"}), 400

    new_q = con.execute(
        "SELECT quantity FROM books WHERE id=?", (item_id,)
    ).fetchone()["quantity"]

    return jsonify({"ok": True, "item_id": item_id, "remaining": new_q}), 200

# للتشغيل المحلي (خارج Docker/Gunicorn)
if __name__ == "_main_":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000)