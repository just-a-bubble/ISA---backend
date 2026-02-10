from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict, Any
import sqlite3
import base64
from passlib.hash import argon2
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware


DB_PATH = "/data/skupno.db3"  # mounted by docker-compose

app = FastAPI(
    title="Recipe Search API (FastAPI)",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: ensure DB exists and tables
def init_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS favourites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS shared_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            recipe_id INTEGER NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)
    # NOTE: recepti tabela je predhodno v tvoji bazi -> upam, da obstaja
    conn.commit()
    conn.close()

init_db()

# ---------- DB helper functions (preneseno iz Flask verzije) ----------
def get_user_id(username: str) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def search_recipes(keywords: List[str]) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if not keywords:
        conn.close()
        return []
    pogoji = " AND ".join([ f"(besede LIKE '%{kw}%' OR leme LIKE '%{kw}%')" for kw in keywords ])
    sql = f"""
        SELECT DISTINCT id, naziv_dat, slika
        FROM recepti
        WHERE {pogoji}
    """
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
    except Exception:
        results = []
    conn.close()
    recipes = []
    for id_, naziv, blob in results:
        img_data = base64.b64encode(blob).decode("utf-8") if blob else ""
        recipes.append({
            "id": id_,
            "naziv": naziv,
            "image": f"data:image/png;base64,{img_data}" if img_data else ""
        })
    return recipes

def get_recipe_by_id(recipe_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, naziv_dat, slika FROM recepti WHERE id=?", (recipe_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return None
    img_data = base64.b64encode(r[2]).decode("utf-8") if r[2] else ""
    return {"id": r[0], "naziv": r[1], "image": f"data:image/png;base64,{img_data}" if img_data else ""}

def add_to_favourites(username: str, recipe_id: int) -> bool:
    user_id = get_user_id(username)
    if not user_id:
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM favourites WHERE user_id=? AND recipe_id=?", (user_id, recipe_id))
    if c.fetchone():
        conn.close()
        return False
    c.execute("INSERT INTO favourites (user_id, recipe_id) VALUES (?, ?)", (user_id, recipe_id))
    conn.commit()
    conn.close()
    return True

def remove_favourite(username: str, recipe_id: int) -> bool:
    user_id = get_user_id(username)
    if not user_id:
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM favourites WHERE user_id=? AND recipe_id=?", (user_id, recipe_id))
    conn.commit()
    changed = c.rowcount
    conn.close()
    return bool(changed)

def get_user_favourites(username: str) -> List[Dict[str,Any]]:
    user_id = get_user_id(username)
    if not user_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.naziv_dat
        FROM recepti r
        JOIN favourites f ON f.recipe_id = r.id
        WHERE f.user_id=?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "naziv": r[1]} for r in rows]

def get_received_recipes(username: str) -> List[Dict[str,Any]]:
    user_id = get_user_id(username)
    if not user_id:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT r.id, r.naziv_dat, u.username
        FROM shared_recipes s
        JOIN recepti r ON s.recipe_id = r.id
        JOIN users u ON s.sender_id = u.id
        WHERE s.receiver_id=?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "naziv": r[1], "sender": r[2]} for r in rows]

# ---------- Auth helper ----------
def get_current_username(request: Request) -> Optional[str]:
    # Very simple cookie-based "session"
    username = request.cookies.get("username")
    return username

# ---------- Pydantic models ----------
class SearchModel(BaseModel):
    query: Optional[str] = ""

class RecipeIDModel(BaseModel):
    recipe_id: int

class ShareModel(BaseModel):
    recipe_id: int
    receiver: str

# ---------- Routes (prefixed with /api) ----------
@app.post("/api/register")
async def register(username: str = Form(...), password: str = Form(...)):
    pw_hash = argon2.hash(password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        conn.commit()
        msg = {"success": True, "message": "Registracija uspešna. Prijavi se."}
    except sqlite3.IntegrityError:
        msg = {"success": False, "message": "Uporabniško ime že obstaja."}
    finally:
        conn.close()
    return JSONResponse(content=msg)

@app.post("/api/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    if user and argon2.verify(password, user[0]):
        # set cookie
        response = JSONResponse(content={"success": True})
        response.set_cookie("username", username, httponly=True, samesite="lax")
        return response
    else:
        return JSONResponse(status_code=401, content={"success": False, "message": "Napačno uporabniško ime ali geslo."})

@app.post("/api/logout")
async def logout(response: Response, request: Request):
    response = JSONResponse(content={"success": True})
    response.delete_cookie("username")
    return response

@app.get("/api/me")
async def me(request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"error": "Ni prijave"})
    favourites = get_user_favourites(username)
    received = get_received_recipes(username)
    return {"username": username, "favourites": favourites, "received": received}

@app.post("/api/search")
async def api_search(payload: SearchModel, request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"error": "Ni prijave"})
    query = (payload.query or "").strip().lower()
    keywords = query.split()
    recipes = search_recipes(keywords)
    return recipes

@app.post("/api/add_favourite")
async def api_add_favourite(data: RecipeIDModel, request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"success": False, "error": "Ni prijave"})
    success = add_to_favourites(username, data.recipe_id)
    return {"success": success}

@app.post("/api/remove_favourite")
async def api_remove_favourite(data: RecipeIDModel, request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"success": False, "error": "Ni prijave"})
    success = remove_favourite(username, data.recipe_id)
    return {"success": success}

@app.post("/api/share_recipe")
async def api_share_recipe(data: ShareModel, request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"success": False, "error": "Ni prijave"})
    sender_id = get_user_id(username)
    receiver_id = get_user_id(data.receiver)
    if not receiver_id:
        return {"success": False, "error": "Prejemnik ne obstaja."}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO shared_recipes (sender_id, receiver_id, recipe_id) VALUES (?, ?, ?)",
              (sender_id, receiver_id, data.recipe_id))
    conn.commit()
    conn.close()
    return {"success": True}

@app.post("/api/get_recipe")
async def api_get_recipe(data: RecipeIDModel, request: Request):
    username = get_current_username(request)
    if not username:
        return JSONResponse(status_code=401, content={"error": "Ni prijave"})
    recipe = get_recipe_by_id(data.recipe_id)
    if recipe:
        return recipe
    else:
        return JSONResponse(status_code=404, content={"error": "Recept ni najden"})

# Root health check
@app.get("/api/health")
async def health():
    return {"status": "ok"}
