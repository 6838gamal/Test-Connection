import sqlite3
import hashlib
import threading
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

# ================= DATABASE =================
DB = "users.db"

def get_db():
    return sqlite3.connect(DB, check_same_thread=False)

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

init_db()

def hash_pw(pw: str):
    return hashlib.sha256(pw.encode()).hexdigest()

# ================= FASTAPI =================
api = FastAPI(title="Users API")

class UserIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str

@api.get("/api/status")
def status():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return {"status": "online", "users": count}

@api.get("/api/users", response_model=List[UserOut])
def list_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "email": r[1]} for r in rows]

@api.post("/api/users")
def add_user(user: UserIn):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (user.email, hash_pw(user.password))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Email already exists")
    finally:
        conn.close()
    return {"success": True}

@api.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"deleted": True}

# ================= START API THREAD =================
def start_api():
    uvicorn.run(api, host="127.0.0.1", port=8000, log_level="warning")

api_thread = threading.Thread(target=start_api, daemon=True)
api_thread.start()

time.sleep(1)  # نضمن أن السيرفر اشتغل

# ================= STREAMLIT =================
import streamlit as st
import requests
import pandas as pd

API = "http://127.0.0.1:8000/api"

st.set_page_config("User Dashboard", layout="wide")
st.title("🧩 User Management Dashboard")

# ===== STATUS =====
status = requests.get(f"{API}/status").json()
c1, c2 = st.columns(2)
c1.metric("Server", status["status"])
c2.metric("Users", status["users"])

st.divider()

# ===== ADD USER =====
with st.form("add_user"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.form_submit_button("Add"):
        r = requests.post(f"{API}/users", json={
            "email": email,
            "password": password
        })
        if r.status_code == 200:
            st.success("User added")
            st.rerun()
        else:
            st.error(r.text)

st.divider()

# ===== USERS TABLE =====
users = requests.get(f"{API}/users").json()

if users:
    df = pd.DataFrame(users)
    st.dataframe(df, use_container_width=True)

    uid = st.selectbox("Delete user", df["id"])
    if st.button("Delete"):
        requests.delete(f"{API}/users/{uid}")
        st.warning("User deleted")
        st.rerun()
else:
    st.info("No users found")
