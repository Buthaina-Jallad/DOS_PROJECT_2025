import os
import requests
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)  # <-- هنا كانت الغلطة، لازم __name_ مش name

CATALOG_URL = os.getenv("CATALOG_URL", "http://catalog:5000")
ORDER_URL = os.environ.get("ORDER_URL", "http://order:5001")

@app.get("/health")
def health():
    return {"status": "ok"}, 200

@app.get("/api/search")
def api_search():
    topic = request.args.get("topic", "")
    r = requests.get(f"{CATALOG_URL}/search", params={"topic": topic}, timeout=5)
    return r.json(), r.status_code

@app.get("/api/info/<int:item_id>")
def api_info(item_id):
    r = requests.get(f"{CATALOG_URL}/info/{item_id}", timeout=5)
    return r.json(), r.status_code

@app.post("/api/buy/<int:item_id>")
def api_buy(item_id: int):
    try:
        r = requests.post(f"{ORDER_URL}/purchase/{item_id}", timeout=5)
        try:
            data = r.json()
            return jsonify(data), r.status_code
        except ValueError:
            return jsonify({
                "ok": False,
                "upstream": "order-service",
                "status": r.status_code,
                "body": (r.text or "")[:400]
            }), r.status_code
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": "order unreachable", "detail": str(e)}), 502


# ---------- واجهة بسيطة ----------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bazar.com (Flask)</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;margin:30px;}
    input,button{padding:8px 12px;margin:4px;font-size:16px;}
    .card{border:1px solid #ddd;border-radius:10px;padding:16px;margin:10px 0;}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;}
    .muted{color:#555}
  </style>
</head>
<body>
  <h1>Bazar.com</h1>
  <p class="muted">Flask + Gunicorn + Nginx + Docker Compose</p>

  <div class="card">
    <form onsubmit="event.preventDefault(); doSearch();">
      <input id="topic" placeholder="Search topic (e.g., distributed)" />
      <button type="submit">Search</button>
    </form>
    <div id="results" class="grid"></div>
  </div>

  <script>
    async function doSearch(){
      const topic = document.getElementById('topic').value;
      const r = await fetch('/api/search?topic=' + encodeURIComponent(topic));
      const data = await r.json();
      const box = document.getElementById('results');
      box.innerHTML = '';
      (data.items||[]).forEach(item => {
        const el = document.createElement('div');
        el.className = 'card';
        el.innerHTML = '<b>#'+item.id+'</b> ' + item.title +
          '<div><button onclick="info('+item.id+')">Info</button>' +
          '<button onclick="buy('+item.id+')">Buy</button></div>';
        box.appendChild(el);
      });
    }
    async function info(id){
      const r = await fetch('/api/info/' + id);
      const data = await r.json();
      alert(JSON.stringify(data, null, 2));
    }
    async function buy(id){
      const r = await fetch('/api/buy/' + id, {method:'POST'});
      const data = await r.json();
      alert(JSON.stringify(data, null, 2));
    }
  </script>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(INDEX_HTML)

if __name__ == "_main":  # <-- وهنا كمان نفس الشي، لازم __main_
    app.run(host="0.0.0.0", port=5002)