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
            (1, "How to get a good grade in DOS in 40 minutes a day.", "distributed systems", 19.99, 8),
            (2, "RPCs for Noobs.", "distributed systems", 24.90, 12),
            (3, "Xen and the Art of Surviving Undergraduate School.", "undergraduate school", 17.50, 5),
            (4, "Cooking for the Impatient Undergrad.", "undergraduate school", 29.00, 10),
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
# ---------------------------
# Query-by-subject (يدعم الطريقتين)
# ---------------------------
# ---------------------------
# Query-by-subject (يدعم الطريقتين بنفس الوقت)
# ---------------------------
@app.get("/search")
@app.get("/search/<string:topic>")
def search(topic=None):
    con = get_db()

    # نقرأ الـ topic من الـ path أو من الـ query
    if not topic:
        topic = (request.args.get("topic") or "").strip().lower()
    else:
        topic = topic.strip().lower()

    # إذا ما تم تحديد topic، رجع كل الكتب
    if not topic:
        rows = con.execute("SELECT id, title FROM books").fetchall()
    else:
        rows = con.execute(
            "SELECT id, title FROM books WHERE lower(topic) LIKE ?",
            (f"%{topic}%",),
        ).fetchall()

    # نحول النتائج لقاموس (title → id)
    items_dict = {r["title"].strip(): r["id"] for r in rows}

    # نرجع الشكل المطلوب فقط
    return jsonify({"items": items_dict}), 200

@app.get("/info")
@app.get("/info/<int:item_id>")
def info(item_id=None):
    con = get_db()
    if not item_id:
        item_id = request.args.get("id", type=int)

    if not item_id:
        return jsonify({"error": "no_item_id_provided"}), 400

    row = con.execute(
        "SELECT id, title, price, quantity, topic FROM books WHERE id=?",
        (item_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify(dict(row)), 200


# يُستدعى من order-service لتقليل المخزون
# ---------------------------
# Decrement (supports both forms)
# ---------------------------
@app.post("/decrement")
@app.post("/decrement/<int:item_id>")
def decrement(item_id=None):
    con = get_db()
    if not item_id:
        item_id = request.args.get("id", type=int)
    if not item_id:
        return jsonify({"error": "no_item_id_provided"}), 400

    row = con.execute("SELECT quantity FROM books WHERE id=?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "not_found"}), 404
    if row["quantity"] <= 0:
        return jsonify({"error": "out_of_stock"}), 400

    con.execute("UPDATE books SET quantity = quantity - 1 WHERE id=? AND quantity > 0", (item_id,))
    con.commit()
    new_q = con.execute("SELECT quantity FROM books WHERE id=?", (item_id,)).fetchone()["quantity"]

    return jsonify({"ok": True, "item_id": item_id, "remaining": new_q}), 200



# ---------------------------
# ✅ Update Operation (new)
# يسمح بتعديل السعر أو زيادة/نقص الكمية
# ---------------------------
# ---------------------------
# Update (supports both forms)
# ---------------------------
@app.post("/update")
@app.post("/update/<int:item_id>")
def update_item(item_id=None):
    data = request.get_json(force=True)
    if not item_id:
        item_id = request.args.get("id", type=int)

    if not item_id:
        return jsonify({"error": "no_item_id_provided"}), 400

    fields, values = [], []

    if "price" in data:
        fields.append("price = ?")
        values.append(float(data["price"]))

    if "quantity" in data:
        fields.append("quantity = quantity + ?")
        values.append(int(data["quantity"]))

    if not fields:
        return jsonify({"error": "no_valid_fields"}), 400

    values.append(item_id)
    con = get_db()
    con.execute(f"UPDATE books SET {', '.join(fields)} WHERE id = ?", values)
    con.commit()

    updated_row = con.execute(
        "SELECT id, title, price, quantity FROM books WHERE id=?",
        (item_id,)
    ).fetchone()

    return jsonify({"ok": True, "item_id": item_id, "new_data": dict(updated_row)}), 200


# للتشغيل المحلي (خارج Docker/Gunicorn)
if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000)