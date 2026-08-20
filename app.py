import os
import aiohttp
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from scanner import scan_market, fetch_klines, compute_indicators, calculate_rr_levels, fetch_top_usdt_pairs
from backtester import backtest_symbol, backtest_portfolio
from live_bot import bot_instance
from strategy_memory import load_saved_strategies

app = FastAPI(title="Quant Squeeze & Pattern Scanner", version="1.0.0")

# Enable CORS for local cross-origin development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def serve_index():
    """Serve the single-page dashboard."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return {"message": "Scanner API is running. index.html not found in static folder."}

@app.get("/api/scan")
async def get_market_scan(
    interval: str = Query("1h", description="Candle interval: 15m, 1h, 4h, 1d"),
    limit: int = Query(50, description="Number of top liquid pairs to scan")
):
    """Scan top crypto pairs and return squeeze states, momentum, and active breakout triggers."""
    valid_intervals = ["15m", "1h", "4h", "1d"]
    if interval not in valid_intervals:
        raise HTTPException(status_code=400, detail=f"Interval must be one of {valid_intervals}")
    
    results = await scan_market(interval=interval, limit_pairs=min(limit, 100))
    return {
        "interval": interval,
        "total_scanned": len(results),
        "data": results
    }

@app.get("/api/candles/{symbol}")
async def get_symbol_candles(
    symbol: str,
    interval: str = Query("1h", description="Candle interval"),
    limit: int = Query(300, description="Number of bars")
):
    """Return OHLCV candles, technical indicators, squeeze status, and RR levels for chart rendering."""
    clean_sym = symbol.upper().replace("/", "").replace("-", "")
    async with aiohttp.ClientSession() as session:
        df = await fetch_klines(session, clean_sym, interval=interval, limit=min(limit, 1000))
        if df is None or len(df) < 50:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {clean_sym}")
        
        df = compute_indicators(df)
        
        # Prepare TradingView Lightweight Charts compatible data arrays
        candles = []
        ema200_line = []
        ema50_line = []
        bb_upper_line = []
        bb_lower_line = []
        kc_upper_line = []
        kc_lower_line = []
        squeeze_dots = []
        momentum_bars = []
        
        for _, row in df.iterrows():
            t = int(row['time'])
            candles.append({
                "time": t,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
            })
            
            if not row.isna()['ema200']:
                ema200_line.append({"time": t, "value": round(float(row['ema200']), 6 if row['ema200'] < 1 else 2)})
            if not row.isna()['ema50']:
                ema50_line.append({"time": t, "value": round(float(row['ema50']), 6 if row['ema50'] < 1 else 2)})
            if not row.isna()['bb_upper']:
                bb_upper_line.append({"time": t, "value": round(float(row['bb_upper']), 6 if row['bb_upper'] < 1 else 2)})
            if not row.isna()['bb_lower']:
                bb_lower_line.append({"time": t, "value": round(float(row['bb_lower']), 6 if row['bb_lower'] < 1 else 2)})
            if not row.isna()['kc_upper']:
                kc_upper_line.append({"time": t, "value": round(float(row['kc_upper']), 6 if row['kc_upper'] < 1 else 2)})
            if not row.isna()['kc_lower']:
                kc_lower_line.append({"time": t, "value": round(float(row['kc_lower']), 6 if row['kc_lower'] < 1 else 2)})
                
            # Squeeze dots color
            squeeze_dots.append({
                "time": t,
                "value": 0,
                "color": "#ef4444" if row['squeeze_on'] else "#10b981"
            })
            
            # Momentum histogram bar color
            mom_val = float(row['momentum']) if not row.isna()['momentum'] else 0.0
            momentum_bars.append({
                "time": t,
                "value": round(mom_val, 6 if abs(mom_val) < 1 else 2),
                "color": "#10b981" if mom_val >= 0 else "#ef4444"
            })
            
        last_row = df.iloc[-1]
        last_price = float(last_row['close'])
        last_atr = float(last_row['atr14'])
        trend_state = "BULLISH" if last_price > last_row['ema200'] else "BEARISH"
        
        rr_levels = calculate_rr_levels(
            price=last_price, 
            atr=last_atr, 
            direction="LONG" if trend_state == "BULLISH" else "SHORT"
        )
        
        return {
            "symbol": clean_sym,
            "interval": interval,
            "candles": candles,
            "ema200": ema200_line,
            "ema50": ema50_line,
            "bb_upper": bb_upper_line,
            "bb_lower": bb_lower_line,
            "kc_upper": kc_upper_line,
            "kc_lower": kc_lower_line,
            "squeeze_dots": squeeze_dots,
            "momentum_bars": momentum_bars,
            "current_metrics": {
                "price": round(last_price, 6 if last_price < 1 else 2),
                "is_squeeze": bool(last_row['squeeze_on']),
                "squeeze_bars": int(last_row['squeeze_bars']),
                "signal": str(last_row['signal']),
                "trend": trend_state,
                "atr": round(last_atr, 6 if last_atr < 1 else 2),
                "rr_levels": rr_levels
            }
        }

@app.get("/api/backtest")
async def run_backtest(
    symbol: str = Query("BTCUSDT", description="Symbol to backtest or ALL"),
    interval: str = Query("1h", description="Candle timeframe"),
    bars: int = Query(1000, description="Historical candles count"),
    target_rr: float = Query(2.0, description="Target Risk-to-Reward multiple (1.0 to 4.0)")
):
    """Run full historical backtest and calculate win rate, profit factor, and equity curve."""
    clean_sym = symbol.upper().replace("/", "").replace("-", "")
    if clean_sym in ["ALL", "PORTFOLIO", "ALLPAIRS", "ALL COINS"]:
        top_symbols = await fetch_top_usdt_pairs(limit=25)
        return await backtest_portfolio(top_symbols, interval=interval, limit=min(bars, 500), target_rr=target_rr)
    return await backtest_symbol(clean_sym, interval=interval, limit=bars, target_rr=target_rr)

@app.on_event("startup")
async def startup_event():
    """Automatically start the live trading bot background engine when the web server runs."""
    await bot_instance.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully stop the live trading bot worker."""
    await bot_instance.stop()

@app.get("/api/bot/status")
async def get_bot_status():
    """Return real-time bot status, live positions, R-returns, win rate, and diagnostic logs."""
    return bot_instance.get_telemetry()

@app.post("/api/bot/toggle")
async def toggle_bot():
    """Toggle automated bot running / paused state."""
    if bot_instance.is_running:
        await bot_instance.stop()
        return {"status": "PAUSED", "message": "Live automated bot paused."}
    else:
        await bot_instance.start()
        return {"status": "RUNNING", "message": "Live automated bot started."}

@app.post("/api/bot/optimize_now")
async def trigger_optimization():
    """Manually trigger an immediate strategy self-perfection & parameter walk-forward test."""
    opt_result = await bot_instance.run_self_optimization()
    return {"message": "Optimization completed.", "result": opt_result}

@app.get("/api/bot/saved_strategies")
async def get_saved_strategies_api():
    """Return catalog of saved reproducible strategies."""
    return load_saved_strategies()

@app.post("/api/bot/reset")
async def reset_bot_wallet():
    """Reset the live bot wallet balance to $100.00 USD."""
    bot_instance.reset_account(100.0)
    return {"message": "Account wallet reset to $100.00 USD.", "balance": 100.0}

@app.get("/api/bot/depletion_report")
async def get_depletion_report():
    """Return the final markdown summary report if capital was depleted."""
    if bot_instance.depletion_report_file and os.path.exists(bot_instance.depletion_report_file):
        with open(bot_instance.depletion_report_file, "r", encoding="utf-8") as f:
            return {"status": "DEPLETED", "content": f.read(), "file": bot_instance.depletion_report_file}
    return {"status": "ACTIVE", "message": "Capital is not depleted."}

from pydantic import BaseModel

class RestartBotRequest(BaseModel):
    capital: float = 100.0
    fixed_risk_usd: float = 1.0

@app.post("/api/bot/restart_with_capital")
async def restart_bot_with_capital(payload: RestartBotRequest):
    """Re-fund the bot with user-defined capital and fixed risk, then immediately resume scanning."""
    cap = max(1.0, payload.capital)
    risk = max(0.1, payload.fixed_risk_usd)
    await bot_instance.restart_with_capital(capital=cap, fixed_risk_usd=risk)
    return {
        "status": "RUNNING",
        "message": f"Bot re-funded with ${cap:.2f} USD (${risk:.2f}/trade) and scanning started.",
        "capital": cap,
        "fixed_risk_usd": risk
    }

if __name__ == "__main__":
    import uvicorn
    print("[*] Starting Quant Squeeze & Pattern Scanner on http://127.0.0.1:8000 ...")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
