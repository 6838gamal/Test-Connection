from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
import hashlib

app = FastAPI(title="User Management Dashboard")

DB = "users.db"

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    db = get_db()
    c = db.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    db.commit()
    db.close()

init_db()

def hash_pw(pw: str):
    return hashlib.sha256(pw.encode()).hexdigest()

# ---------- API ----------
@app.get("/status")
def status():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    db.close()
    return {"status": "online", "users": count}

@app.get("/users")
def list_users():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, email FROM users ORDER BY id DESC")
    rows = c.fetchall()
    db.close()
    return [{"id": r[0], "email": r[1]} for r in rows]

@app.post("/users")
def add_user(email: str = Form(...), password: str = Form(...)):
    db = get_db()
    c = db.cursor()
    try:
        c.execute(
            "INSERT INTO users(email,password) VALUES (?,?)",
            (email, hash_pw(password))
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        db.close()
    return RedirectResponse("/", status_code=303)

@app.post("/delete/{user_id}")
def delete_user(user_id: int):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    return RedirectResponse("/", status_code=303)

# ---------- WEB DASHBOARD ----------
@app.get("/", response_class=HTMLResponse)
def dashboard():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, email FROM users ORDER BY id DESC")
    users = c.fetchall()
    db.close()

    user_rows = "".join(f"""
        <tr>
            <td>{u[0]}</td>
            <td>{u[1]}</td>
            <td>
                <form method="POST" action="/delete/{u[0]}" style="display:inline;">
                    <button type="submit">Delete</button>
                </form>
            </td>
        </tr>
    """ for u in users)

    html = f"""
    <html>
    <head>
        <title>User Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            button {{ padding: 5px 10px; }}
            input[type=email], input[type=password] {{ padding: 5px; margin-right: 10px; }}
        </style>
    </head>
    <body>
        <h1>User Dashboard</h1>
        <form method="POST" action="/users">
            Email: <input type="email" name="email" required>
            Password: <input type="password" name="password" required>
            <button type="submit">Add User</button>
        </form>

        <table>
            <tr><th>ID</th><th>Email</th><th>Action</th></tr>
            {user_rows}
        </table>
    </body>
    </html>
    """
    return HTMLResponse(html)

# ---------- RUN LOCAL ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
