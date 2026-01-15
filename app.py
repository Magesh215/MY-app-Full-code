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
from services.orders import get_orders
from services.algo_state import (
    start_algo,
    stop_algo,
    set_mode,
    request_force_exit,
    is_algo_running,
    get_mode,
)

MODE = os.getenv("MODE", "DEMO").upper()

SYMBOLS = {
    "NIFTY": 256265,
    "BANKNIFTY": 260105,
    "SENSEX": 265,
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
            interval="minute",
        )

        for c in candles:
            ts = int(c["date"].timestamp())
            save_candle(
                symbol,
                {
                    "timestamp": ts - (ts % 60),
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                },
            )

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

# ================= ALGO CONTROL (SAFE, NON-BLOCKING) =================

@app.post("/api/algo/start")
def api_algo_start(mode: str = Query(...)):
    """
    Starts algo via services.algo_state
    Must return immediately (no blocking)
    """
    set_mode(mode.upper())
    started = start_algo()

    return {
        "status": "started" if started else "already running",
        "mode": mode.upper(),
    }

@app.post("/api/algo/stop")
def api_algo_stop():
    stop_algo()
    return {"status": "stopped"}

@app.post("/api/positions/force-exit")
def api_force_exit():
    request_force_exit()
    return {"status": "force exit requested"}

# ================= CANDLES =================

@app.get("/api/candles")
def api_candles(symbol: str = Query(...), interval: str | None = None):
    if interval:
        data = get_timeframe_candles(symbol, interval)
        if data:
            return data
    return get_candles(symbol)

# ================= ORDERS =================

@app.get("/api/orders")
def api_orders():
    return get_orders()

# ================= FUNDS =================

@app.get("/api/funds")
def api_funds():
    mode = get_mode()

    if mode == "DEMO":
        return {"available_cash": 100000}

    kite = get_kite()
    margins = kite.margins()
    return margins.get("equity", {})

# ================= PNL =================

@app.get("/api/pnl/live")
def api_pnl():
    return get_live_pnl("NIFTY")

# ================= HEALTH =================

@app.get("/health")
def health():
    return {
        "mode": get_mode(),
        "algo_running": is_algo_running(),
    }
