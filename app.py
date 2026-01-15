import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from services.db import init_db, save_candle
from services.candle_store import bootstrap_candles, get_candles
from services.session_manager import get_kite
from services.zerodha_ws import start_zerodha_ws
from services.strategy_scheduler import start_scheduler
from services.timeframe_service import get_timeframe_candles
from services.pnl_engine import get_live_pnl
from services.algo_state import (
    start_algo,
    stop_algo,
    set_mode,
    request_force_exit,
    is_algo_running,
)

MODE = os.getenv("MODE", "DEMO").upper()

SYMBOLS = {
    "NIFTY": 256265,
    "BANKNIFTY": 260105,
    "SENSEX": 265
}

app = FastAPI(title="Trading Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= HISTORICAL LOADER (LOCKED) =================

def load_historical_once():
    kite = get_kite()
    end = datetime.now()
    start = end - timedelta(days=5)

    for symbol, token in SYMBOLS.items():
        candles = kite.historical_data(
            instrument_token=token,
            from_date=start,
            to_date=end,
            interval="minute"
        )

        for c in candles:
            ts = int(c["date"].timestamp())
            save_candle(symbol, {
                "timestamp": ts - (ts % 60),   # 🔒 FIXED: 1-minute precision
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
            })

        print(f"📥 Loaded historical candles: {symbol} ({len(candles)})")

# ================= STARTUP =================

@app.on_event("startup")
def startup():
    init_db()
    load_historical_once()
    bootstrap_candles()
    start_zerodha_ws()
    start_scheduler()
    print(f"🔥 Backend started | MODE={MODE}")

# ================= ALGO CONTROL =================

@app.post("/api/algo/start")
def algo_start(mode: str = Query(...)):
    set_mode(mode.upper())
    return {
        "status": "started" if start_algo() else "already running",
        "mode": mode.upper(),
    }

@app.post("/api/algo/stop")
def algo_stop():
    stop_algo()
    return {"status": "stopped"}

@app.post("/api/positions/force-exit")
def force_exit():
    request_force_exit()
    return {"status": "force exit requested"}

# ================= CANDLES =================

@app.get("/api/candles")
def api_candles(
    symbol: str = Query(...),
    interval: str | None = Query(None)
):
    if interval:
        data = get_timeframe_candles(symbol, interval)
        if data:
            return data
    return get_candles(symbol)

# ================= PNL =================

@app.get("/api/pnl/live")
def pnl():
    return get_live_pnl("NIFTY")

# ================= HEALTH =================

@app.get("/health")
def health():
    return {
        "mode": MODE,
        "algo_running": is_algo_running()
    }
