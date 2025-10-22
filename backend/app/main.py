# backend/app/main.py (extended)
import os
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Field, create_engine, Session, select
import httpx

# ===========================================================
# CONFIGURACIÓN BASE
# ===========================================================

DB_URL = "sqlite:///./hr_traders.db"
engine = create_engine(DB_URL, echo=False)

DRY_RUN = True
TRADELOCKER_REST = os.getenv("TRADELOCKER_REST", "https://public-api.tradelocker.com")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

app = FastAPI(title="HR-Traders API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_scheme = HTTPBearer(auto_error=False)

# ===========================================================
# AUTENTICACIÓN SIMPLE
# ===========================================================

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if credentials.scheme.lower() != "bearer" or credentials.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials

# ===========================================================
# MODELOS DE DATOS
# ===========================================================

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    api_key: str
    is_master: bool = False
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderMap(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    master_order_id: str
    follower_order_id: str
    follower_id: int = Field(foreign_key="account.id")
    synced: bool = True

# ===========================================================
# FUNCIONES PRINCIPALES
# ===========================================================

async def get_follower_order_status(follower_order_id: str, follower: Account) -> dict:
    if DRY_RUN:
        return {
            "id": follower_order_id,
            "filled": None,
            "status": "unknown",
            "avg_price": None
        }

    async with httpx.AsyncClient() as client:
        url = f"{TRADELOCKER_REST}/orders/{follower_order_id}"
        headers = {"Authorization": f"Bearer {follower.api_key}"}
        r = await client.get(url, headers=headers, timeout=10.0)
        r.raise_for_status()
        return r.json()

def get_maps_by_master(master_order_id: str) -> list[OrderMap]:
    with Session(engine) as s:
        return s.exec(select(OrderMap).where(OrderMap.master_order_id == master_order_id)).all()

async def notify(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}

    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=10.0)
        except Exception:
            pass

async def send_order_to_tradelocker(order: dict, follower: Account) -> str:
    if DRY_RUN:
        print(f"Simulando orden para {follower.name}: {order}")
        return "fake_order_id"

    async with httpx.AsyncClient() as client:
        url = f"{TRADELOCKER_REST}/orders"
        headers = {
            "Authorization": f"Bearer {follower.api_key}",
            "Content-Type": "application/json"
        }
        r = await client.post(url, json=order, headers=headers, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        return data.get("id", "unknown")

# ===========================================================
# EVENTOS Y ENDPOINTS
# ===========================================================

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    print("✅ Base de datos inicializada correctamente.")

@app.get("/", tags=["status"])
def root():
    return {"status": "✅ HR Traders backend activo", "dry_run": DRY_RUN}

@app.get("/accounts", tags=["accounts"])
def get_accounts():
    with Session(engine) as session:
        accounts = session.exec(select(Account)).all()
        return accounts

@app.post("/orders/sync", tags=["orders"])
async def sync_orders(request: Request, credentials: HTTPAuthorizationCredentials = Depends(require_auth)):
    payload = await request.json()
    print(f"📩 Recibida orden: {payload}")
    await notify("Nueva orden recibida desde TradeLocker")
    return {"message": "Orden procesada correctamente (modo demo)"}

# ===========================================================
# ARCHIVOS ESTÁTICOS
# ===========================================================
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")