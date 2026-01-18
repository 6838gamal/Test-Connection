from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import sqlite3
import hashlib
import uvicorn
from typing import List

app = FastAPI(title="Users API")

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

# ---------- Pydantic ----------
class User(BaseModel):
    email: EmailStr
    password: str

# ---------- API ROUTES ----------
@app.get("/status")
def status():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    db.close()
    return {"status": "online", "users": count}

@app.get("/users", response_model=List[User])
def list_users():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT id, email FROM users ORDER BY id DESC")
    rows = c.fetchall()
    db.close()
    return [{"email": r[1], "password": "********"} for r in rows]

@app.post("/users")
def add_user(user: User):
    db = get_db()
    c = db.cursor()
    try:
        c.execute(
            "INSERT INTO users(email,password) VALUES (?, ?)",
            (user.email, hash_pw(user.password))
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        db.close()
    return {"success": True}

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    c.connection.commit()
    db.close()
    return {"deleted": True}

# ---------- SIMPLE WEB INTERFACE ----------
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
    </head>
    <body>
        <h1>User Dashboard</h1>
        <form method="POST" action="/add">
            Email: <input type="email" name="email" required>
            Password: <input type="password" name="password" required>
            <button type="submit">Add User</button>
        </form>
        <h2>Users</h2>
        <table border="1" cellpadding="5">
            <tr><th>ID</th><th>Email</th><th>Action</th></tr>
            {user_rows}
        </table>
    </body>
    </html>
    """
    return html

@app.post("/add")
def web_add(email: str = Form(...), password: str = Form(...)):
    db = get_db()
    c = db.cursor()
    try:
        c.execute(
            "INSERT INTO users(email,password) VALUES (?, ?)",
            (email, hash_pw(password))
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        db.close()
    return dashboard()

@app.post("/delete/{user_id}")
def web_delete(user_id: int):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    db.close()
    return dashboard()

# ---------- RUN LOCAL ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
