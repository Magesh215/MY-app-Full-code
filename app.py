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
    start_algo, stop_algo, set_mode,
    request_force_exit, is_algo_running
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

def load_historical_once():
    kite = get_kite()
    end = datetime.now()
    start = end - timedelta(days=5)

    for symbol, token in SYMBOLS.items():
        candles = kite.historical_data(
            token, start, end, "minute"
        )
        for c in candles:
            save_candle(symbol, {
                "timestamp": int(c["date"].timestamp()) - (int(c["date"].timestamp()) % 60),
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
            })
        print(f"📥 Loaded historical candles: {symbol} ({len(candles)})")

@app.on_event("startup")
def startup():
    init_db()
    load_historical_once()
    bootstrap_candles()
    start_zerodha_ws()
    start_scheduler()
    print(f"🔥 Backend started | MODE={MODE}")

@app.post("/api/algo/start")
def algo_start(mode: str = Query(...)):
    set_mode(mode.upper())
    return {"status": "started" if start_algo() else "already running"}

@app.post("/api/algo/stop")
def algo_stop():
    stop_algo()
    return {"status": "stopped"}

@app.get("/api/candles")
def api_candles(symbol: str, interval: str | None = None):
    return (
        get_timeframe_candles(symbol, interval)
        if interval else get_candles(symbol)
    )

@app.get("/health")
def health():
    return {"mode": MODE, "algo_running": is_algo_running()}
