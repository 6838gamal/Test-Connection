from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import sqlite3, os, hashlib

app = Flask(__name__)
CORS(app)

DB_PATH = "users.db"

# ---------- DB ----------
def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

init_db()

# ---------- API ----------
@app.route("/api/users", methods=["GET"])
def list_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM users")
    rows = cur.fetchall()
    conn.close()
    return jsonify([
        {"id": r[0], "email": r[1]} for r in rows
    ])

@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing data"}), 400

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email.lower(), hash_password(password))
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400

@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    if password:
        cur.execute(
            "UPDATE users SET email=?, password=? WHERE id=?",
            (email.lower(), hash_password(password), user_id)
        )
    else:
        cur.execute(
            "UPDATE users SET email=? WHERE id=?",
            (email.lower(), user_id)
        )

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ---------- UI ----------
@app.route("/")
def dashboard():
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>User Manager</title>
<style>
body { background:#0f172a;color:#e5e7eb;font-family:Arial;padding:30px }
.card { background:#020617;padding:20px;border-radius:10px;max-width:700px;margin:auto }
input,button { padding:8px;margin:4px }
table { width:100%;margin-top:15px;border-collapse:collapse }
th,td { border-bottom:1px solid #334155;padding:8px;text-align:left }
button { cursor:pointer }
</style>
</head>
<body>

<div class="card">
<h2>👤 User Management</h2>

<input id="email" placeholder="Email">
<input id="password" placeholder="Password">
<button onclick="addUser()">Add</button>

<table>
<thead>
<tr><th>Email</th><th>Actions</th></tr>
</thead>
<tbody id="users"></tbody>
</table>
</div>

<script>
async function loadUsers() {
  let res = await fetch('/api/users');
  let data = await res.json();
  let tbody = document.getElementById('users');
  tbody.innerHTML = '';
  data.forEach(u => {
    tbody.innerHTML += `
      <tr>
        <td><input value="${u.email}" id="e${u.id}"></td>
        <td>
          <button onclick="updateUser(${u.id})">💾</button>
          <button onclick="deleteUser(${u.id})">🗑</button>
        </td>
      </tr>`;
  });
}

async function addUser() {
  await fetch('/api/users', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      email:email.value,
      password:password.value
    })
  });
  email.value=''; password.value='';
  loadUsers();
}

async function updateUser(id) {
  await fetch('/api/users/'+id, {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      email:document.getElementById('e'+id).value
    })
  });
}

async function deleteUser(id) {
  await fetch('/api/users/'+id,{method:'DELETE'});
  loadUsers();
}

loadUsers();
</script>

</body>
</html>
"""
    return Response(html, mimetype="text/html")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002)
