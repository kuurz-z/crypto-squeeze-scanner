import asyncio
import aiohttp
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from data_loader import rate_limit_manager, fetch_symbol_klines

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

# Shared persistent session and connection pooling
_session: Optional[aiohttp.ClientSession] = None
_top_pairs_cache: Dict[str, Any] = {"timestamp": 0.0, "pairs": []}
_scan_cache: Dict[str, Any] = {}
SCAN_CACHE_TTL = 15.0  # 15 seconds cache for scan results
TOP_PAIRS_CACHE_TTL = 300.0  # 5 minutes cache for 24h ticker ranking

async def get_http_session() -> aiohttp.ClientSession:
    """Get or initialize a high-throughput persistent aiohttp ClientSession."""
    global _session
    if _session is None or _session.closed:
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50, keepalive_timeout=60, ttl_dns_cache=300)
        _session = aiohttp.ClientSession(connector=connector)
    return _session

async def close_http_session():
    """Cleanly close persistent http session."""
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
        _session = None


# Excluded symbols (stablecoins, wrapped tokens, leveraged tokens)
EXCLUDED_KEYWORDS = [
    'UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT', 'USDCUSDT', 'FDUSDUSDT', 
    'TUSDUSDT', 'EURUSDT', 'DAIUSDT', 'USD1USDT', 'USDEUSDT', 'EURIUSDT', 
    'AEURUSDT', 'USDPUSDT', 'PYUSDUSDT', 'USDDUSDT', 'WBTCUSDT', 'WETHUSDT'
]

# Default fallback list of liquid USDT trading pairs
DEFAULT_TOP_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "SUIUSDT", "NEARUSDT", "DOTUSDT", "APTUSDT", "LTCUSDT", 
    "UNIUSDT", "ICPUSDT", "RENDERUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT", "ARBUSDT", 
    "OPUSDT", "PEPEUSDT", "WIFUSDT", "SHIBUSDT", "BONKUSDT", "GALAUSDT", "FTMUSDT", 
    "STXUSDT", "OMUSDT", "JUPUSDT", "PYTHUSDT", "ONDOUSDT", "AAVEUSDT", "PENDLEUSDT",
    "FETUSDT", "KASUSDT", "TAOUSDT", "CRVUSDT", "MKRUSDT", "RUNEUSDT", "FILUSDT"
]

async def fetch_top_usdt_pairs(limit: int = 60) -> List[str]:
    """Fetch top USDT pairs by 24h quote volume from Binance with 5-min caching."""
    now = time.time()
    if _top_pairs_cache["pairs"] and (now - _top_pairs_cache["timestamp"] < TOP_PAIRS_CACHE_TTL):
        return _top_pairs_cache["pairs"][:limit]

    session = await get_http_session()
    try:
        async with session.get(BINANCE_TICKER_24HR_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                usdt_pairs = [
                    item for item in data 
                    if item['symbol'].endswith('USDT') 
                    and not any(x == item['symbol'] or x in item['symbol'] for x in EXCLUDED_KEYWORDS)
                ]
                usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                top_symbols = [item['symbol'] for item in usdt_pairs[:100]]
                if top_symbols:
                    _top_pairs_cache["timestamp"] = now
                    _top_pairs_cache["pairs"] = top_symbols
                    return top_symbols[:limit]
    except Exception as e:
        print(f"Error fetching 24hr tickers: {e}, falling back to default list.")
    return DEFAULT_TOP_COINS[:limit]

async def fetch_klines(session: aiohttp.ClientSession, symbol: str, interval: str = "1h", limit: int = 300) -> Optional[pd.DataFrame]:
    """Fetch historical kline data for a symbol using the shared global cache and rate-limit tracking."""
    df = await fetch_symbol_klines(session, symbol, interval=interval, limit=limit)
    if df is not None and len(df) >= 50:
        return df[['time', 'open', 'high', 'low', 'close', 'volume']]
    return None

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mathematical indicators: EMA200, EMA50, Bollinger Bands, Keltner Channels, ATR, Squeeze."""
    if len(df) < 50:
        return df

    # EMAs
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # 20 SMA & Bollinger Bands (20, 2.0)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (2.0 * df['std20'])
    df['bb_lower'] = df['sma20'] - (2.0 * df['std20'])
    
    # ATR (14) & Keltner Channels (20 SMA, 1.5 ATR)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(window=14).mean()
    df['atr14'] = df['atr14'].bfill()
    
    df['kc_upper'] = df['sma20'] + (1.5 * df['atr14'])
    df['kc_lower'] = df['sma20'] - (1.5 * df['atr14'])
    
    # Squeeze Condition: True if BB is inside KC
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    
    # Volume SMA 20 & Volume Surge
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    df['vol_surge'] = df['volume'] > (1.3 * df['vol_sma20'])
    
    # Momentum (Linear regression/Momentum oscillator)
    highest_20 = df['high'].rolling(window=20).max()
    lowest_20 = df['low'].rolling(window=20).min()
    midpoint = (highest_20 + lowest_20) / 2.0
    avg_val = (midpoint + df['sma20']) / 2.0
    df['momentum'] = df['close'] - avg_val
    
    # Squeeze Consecutive Duration & Release
    squeeze_blocks = (~df['squeeze_on']).cumsum()
    df['squeeze_bars'] = df.groupby(squeeze_blocks).cumcount()
    df['squeeze_bars'] = np.where(df['squeeze_on'], df['squeeze_bars'] + 1, 0)
    df['squeeze_released'] = (~df['squeeze_on']) & (df['squeeze_on'].shift(1) == True)
    
    # Relative Strength Index (RSI 14)
    change = df['close'].diff()
    gain = (change.where(change > 0, 0)).rolling(window=14).mean()
    loss = (-change.where(change < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    df['rsi14'] = df['rsi14'].fillna(50.0)

    # Candle body & wick quality ratios
    total_range = (df['high'] - df['low']).replace(0, 1e-6)
    long_body = (df['close'] - df['open']) / total_range
    short_body = (df['open'] - df['close']) / total_range
    long_wick = (df['high'] - df['close']) / total_range
    short_wick = (df['close'] - df['low']) / total_range
    
    # Signal classification
    df['signal'] = 'NONE'
    
    # Long condition with safe RSI corridor (50-68) and solid body close
    long_cond = (
        df['squeeze_released'] & 
        (df['close'] > df['ema50']) & 
        (df['momentum'] > 0) & 
        df['vol_surge'] &
        (df['rsi14'] >= 50.0) & (df['rsi14'] <= 68.0) &
        (long_body >= 0.35) & (long_wick <= 0.45)
    )
    # Short condition with safe RSI corridor (32-50) and solid body close
    short_cond = (
        df['squeeze_released'] & 
        (df['close'] < df['ema50']) & 
        (df['momentum'] < 0) & 
        df['vol_surge'] &
        (df['rsi14'] >= 32.0) & (df['rsi14'] <= 50.0) &
        (short_body >= 0.35) & (short_wick <= 0.45)
    )
    
    df.loc[long_cond, 'signal'] = 'LONG'
    df.loc[short_cond, 'signal'] = 'SHORT'
    
    return df

def calculate_rr_levels(price: float, atr: float, direction: str) -> Dict[str, float]:
    """Calculate exact mathematical 1:1, 1:2, 1:3, and 1:4 Risk-to-Reward levels using ATR."""
    risk = 1.5 * atr
    if direction == "LONG":
        sl = price - risk
        tp1 = price + (1.0 * risk)
        tp2 = price + (2.0 * risk)
        tp3 = price + (3.0 * risk)
        tp4 = price + (4.0 * risk)
    elif direction == "SHORT":
        sl = price + risk
        tp1 = price - (1.0 * risk)
        tp2 = price - (2.0 * risk)
        tp3 = price - (3.0 * risk)
        tp4 = price - (4.0 * risk)
    else:
        sl = price - risk
        tp1 = price + (1.0 * risk)
        tp2 = price + (2.0 * risk)
        tp3 = price + (3.0 * risk)
        tp4 = price + (4.0 * risk)
        
    return {
        "entry": round(price, 6 if price < 1 else 2),
        "stop_loss": round(sl, 6 if sl < 1 else 2),
        "risk_distance": round(risk, 6 if risk < 1 else 2),
        "tp1_1rr": round(tp1, 6 if tp1 < 1 else 2),
        "tp2_2rr": round(tp2, 6 if tp2 < 1 else 2),
        "tp3_3rr": round(tp3, 6 if tp3 < 1 else 2),
        "tp4_4rr": round(tp4, 6 if tp4 < 1 else 2),
    }

async def scan_single_symbol(session: aiohttp.ClientSession, symbol: str, interval: str = "1h") -> Optional[Dict[str, Any]]:
    """Scan and compute real-time metrics for a single symbol."""
    df = await fetch_klines(session, symbol, interval=interval, limit=250)
    if df is None or len(df) < 50:
        return None
    
    df = compute_indicators(df)
    last_row = df.iloc[-1]
    
    is_squeeze = bool(last_row['squeeze_on'])
    squeeze_bars = int(last_row['squeeze_bars'])
    signal = str(last_row['signal'])
    
    recent_signal = "NONE"
    for i in range(1, min(4, len(df))):
        sig = df.iloc[-i]['signal']
        if sig in ['LONG', 'SHORT']:
            recent_signal = f"{sig} ({i} bar{'s' if i > 1 else ''} ago)"
            break
            
    trend = "BULLISH" if last_row['close'] > last_row['ema200'] else "BEARISH"
    pct_from_ema200 = ((last_row['close'] - last_row['ema200']) / last_row['ema200']) * 100.0
    
    # MTF Trend Estimation
    close_val = float(last_row['close'])
    ema50_val = float(last_row['ema50'])
    rsi_val = float(last_row['rsi14'])
    mtf_1h = "BULLISH" if (close_val > ema50_val and rsi_val >= 48) else ("BEARISH" if (close_val < ema50_val and rsi_val <= 52) else "NEUTRAL")
    mtf_30m = mtf_1h
    mtf_4h = "BULLISH" if (close_val > float(last_row['ema200']) and rsi_val >= 46) else ("BEARISH" if (close_val < float(last_row['ema200']) and rsi_val <= 54) else "NEUTRAL")

    target_dir = "LONG" if (signal == "LONG" or (signal == "NONE" and trend == "BULLISH")) else "SHORT"
    rr_targets = calculate_rr_levels(float(last_row['close']), float(last_row['atr14']), target_dir)
    
    return {
        "symbol": symbol,
        "price": float(last_row['close']),
        "volume": float(last_row['volume']),
        "change_pct": round(((last_row['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close'] * 100.0) if len(df) >= 24 else 0.0, 2),
        "is_squeeze": is_squeeze,
        "squeeze_bars": squeeze_bars,
        "signal": signal,
        "recent_signal": recent_signal,
        "trend": trend,
        "mtf_1h": mtf_1h,
        "mtf_30m": mtf_30m,
        "mtf_4h": mtf_4h,
        "pct_from_ema200": round(pct_from_ema200, 2),
        "momentum": round(float(last_row['momentum']), 4),
        "atr": round(float(last_row['atr14']), 6 if last_row['atr14'] < 1 else 2),
        "rr_targets": rr_targets
    }

async def scan_market(interval: str = "1h", limit_pairs: int = 50, force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Scan all top market pairs concurrently using aiohttp with fast in-memory caching and safe rate limits."""
    safe_limit = max(10, min(100, int(limit_pairs)))
    cache_key = f"{interval}_{safe_limit}"
    now = time.time()
    if not force_refresh and cache_key in _scan_cache:
        cached = _scan_cache[cache_key]
        if now - cached["timestamp"] < SCAN_CACHE_TTL:
            return cached["data"]

    symbols = await fetch_top_usdt_pairs(limit=safe_limit)
    session = await get_http_session()
    tasks = [scan_single_symbol(session, sym, interval=interval) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if isinstance(r, dict) and r is not None]
    
    def sort_priority(item):
        sig_score = 100 if item.get('signal') in ['LONG', 'SHORT'] else (50 if item.get('recent_signal') != 'NONE' else 0)
        sqz_score = (item.get('squeeze_bars', 0) * 2) if item.get('is_squeeze') else 0
        return sig_score + sqz_score
        
    valid_results.sort(key=sort_priority, reverse=True)
    _scan_cache[cache_key] = {"timestamp": now, "data": valid_results}
    return valid_results

