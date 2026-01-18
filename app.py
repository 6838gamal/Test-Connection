from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = "users.db"
request_count = 0

# ---------- DB ----------
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE
        )
        """)
        cur.execute(
            "INSERT OR IGNORE INTO users (email) VALUES (?)",
            ("test@example.com",)
        )
        conn.commit()
        conn.close()

def get_db():
    return sqlite3.connect(DB_PATH)

init_db()

# ---------- API ----------
@app.route("/check-user", methods=["POST"])
def check_user():
    global request_count
    request_count += 1

    data = request.get_json(silent=True)
    if not data or "email" not in data:
        return jsonify({"error": "Email is required"}), 400

    email = data["email"].strip().lower()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    return jsonify({
        "exists": bool(user)
    })

# ---------- DASHBOARD ----------
@app.route("/")
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]
    conn.close()

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>System Dashboard</title>
    <style>
        body {{
            background: #0f172a;
            color: #e5e7eb;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .card {{
            background: #020617;
            padding: 30px;
            border-radius: 12px;
            width: 320px;
            box-shadow: 0 0 25px rgba(0,0,0,.5);
        }}
        h1 {{
            margin-bottom: 20px;
            font-size: 20px;
        }}
        .row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        .online {{
            color: #22c55e;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>📊 System Status</h1>

        <div class="row">
            <span>Server</span>
            <span class="online">Online</span>
        </div>

        <div class="row">
            <span>Total Users</span>
            <span>{user_count}</span>
        </div>

        <div class="row">
            <span>API Requests</span>
            <span>{request_count}</span>
        </div>
    </div>
</body>
</html>
"""
    return Response(html, mimetype="text/html")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
