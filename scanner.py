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
    'AEURUSDT', 'USDPUSDT', 'PYUSDUSDT', 'USDDUSDT', 'WBTCUSDT', 'WETHUSDT',
    'RLUSDUSDT', 'BUSDUSDT', 'USTCUSDT', 'UUSDT', 'USD0USDT', 'USDMUSDT',
    'BFDUSDUSDT', 'USDEUSDT'
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

def filter_liquid_usdt_pairs(ticker_data: List[Dict[str, Any]], min_quote_volume: float = 15000000.0) -> List[str]:
    """
    Filter 24h ticker data to only keep liquid USDT trading pairs:
    - Keep only tickers ending in 'USDT'.
    - Exclude tokens matching EXCLUDED_KEYWORDS (stablecoins, leveraged tokens, wrapped assets).
    - Filter float(item.get('quoteVolume', 0)) >= min_quote_volume ($15,000,000 USD default floor).
    - Sort descending by quoteVolume and return symbol list.
    """
    if not isinstance(ticker_data, list):
        return []

    liquid_pairs = []
    for item in ticker_data:
        if not isinstance(item, dict):
            continue
        sym = item.get('symbol')
        if not isinstance(sym, str) or not sym.endswith('USDT'):
            continue
        if any(x == sym or x in sym for x in EXCLUDED_KEYWORDS):
            continue
        try:
            quote_vol = float(item.get('quoteVolume', 0.0))
        except (ValueError, TypeError):
            continue
        if quote_vol >= min_quote_volume:
            liquid_pairs.append((sym, quote_vol))

    liquid_pairs.sort(key=lambda x: x[1], reverse=True)
    return [sym for sym, _ in liquid_pairs]


async def fetch_top_usdt_pairs(limit: int = 60, min_quote_volume: float = 15000000.0) -> List[str]:
    """Fetch top USDT pairs by 24h quote volume from Binance with 5-min caching, enforcing $15M liquidity floor."""
    now = time.time()
    if _top_pairs_cache["pairs"] and (now - _top_pairs_cache["timestamp"] < TOP_PAIRS_CACHE_TTL):
        return _top_pairs_cache["pairs"][:limit]

    session = await get_http_session()
    try:
        async with session.get(BINANCE_TICKER_24HR_URL, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                top_symbols = filter_liquid_usdt_pairs(data, min_quote_volume=min_quote_volume)
                if top_symbols:
                    _top_pairs_cache["timestamp"] = now
                    _top_pairs_cache["pairs"] = top_symbols
                    return top_symbols[:limit]
    except Exception as e:
        print(f"Error fetching 24hr tickers: {e}, falling back to default list.")
    return DEFAULT_TOP_COINS[:limit]

async def fetch_klines(session: aiohttp.ClientSession, symbol: str, interval: str = "30m", limit: int = 300) -> Optional[pd.DataFrame]:
    """Fetch historical kline data for a symbol using the shared global cache and rate-limit tracking."""
    df = await fetch_symbol_klines(session, symbol, interval=interval, limit=limit)
    if df is not None and len(df) >= 50:
        cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        if 'taker_buy_base' in df.columns:
            cols.append('taker_buy_base')
        return df[cols]
    return None

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute mathematical indicators: EMA200, EMA50, Bollinger Bands, Keltner Channels, ATR, Squeeze, Compression Ratio, and Order Flow."""
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
    
    # Squeeze Compression Depth Ratio (< 1.0 when in squeeze; lower = tighter spring)
    bb_width = (df['bb_upper'] - df['bb_lower']).replace(0, np.nan)
    kc_width = (df['kc_upper'] - df['kc_lower']).replace(0, np.nan)
    df['compression_ratio'] = (bb_width / kc_width).fillna(1.0)
    
    # Volume SMA 20 & Volume Surge
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    df['vol_surge'] = df['volume'] > (1.3 * df['vol_sma20'])
    
    # Order Flow: Taker Buy Volume Ratio (Dominance %)
    if 'taker_buy_base' in df.columns:
        df['buyer_ratio'] = (df['taker_buy_base'] / df['volume'].replace(0, np.nan) * 100.0).fillna(50.0)
    else:
        # Fallback Close Location Value (CLV)
        total_r = (df['high'] - df['low']).replace(0, 1e-6)
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / total_r
        df['buyer_ratio'] = ((clv + 1.0) / 2.0 * 100.0).fillna(50.0)
    
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
    
    # Squeeze Tension Score
    df['tension_score'] = np.where(
        df['squeeze_on'], 
        df['squeeze_bars'] * np.maximum(0.0, 1.0 - df['compression_ratio']) * 100.0, 
        0.0
    )
    
    # 5-bar swing high/low for breakout clearance
    df['swing_high_5'] = df['high'].rolling(window=5).max().shift(1)
    df['swing_low_5'] = df['low'].rolling(window=5).min().shift(1)
    
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
    
    # Signal classification with Anti-Fakeout and Order Flow confirmation
    df['signal'] = 'NONE'
    
    # Long condition: Squeeze release + Above EMA50 + Break above 5-bar swing high + Positive Momentum + Buyer dominance + Safe RSI + Solid Body
    long_cond = (
        df['squeeze_released'] & 
        (df['close'] > df['ema50']) & 
        (df['close'] > df['swing_high_5'].fillna(0)) &
        (df['momentum'] > 0) & 
        df['vol_surge'] &
        (df['buyer_ratio'] >= 48.0) &
        (df['rsi14'] >= 50.0) & (df['rsi14'] <= 68.0) &
        (long_body >= 0.35) & (long_wick <= 0.45)
    )
    # Short condition: Squeeze release + Below EMA50 + Break below 5-bar swing low + Negative Momentum + Seller dominance + Safe RSI + Solid Body
    short_cond = (
        df['squeeze_released'] & 
        (df['close'] < df['ema50']) & 
        (df['close'] < df['swing_low_5'].fillna(1e9)) &
        (df['momentum'] < 0) & 
        df['vol_surge'] &
        (df['buyer_ratio'] <= 52.0) &
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

async def scan_single_symbol(session: aiohttp.ClientSession, symbol: str, interval: str = "30m") -> Optional[Dict[str, Any]]:
    """Scan and compute real-time metrics for a single symbol."""
    df = await fetch_klines(session, symbol, interval=interval, limit=250)
    if df is None or len(df) < 50:
        return None
    
    df = compute_indicators(df)
    last_row = df.iloc[-1]
    
    # Dynamic Peg / Stablecoin / Dead Token Filter
    close_val = float(last_row['close'])
    if close_val <= 0:
        return None
    recent_range_pct = (df['high'].iloc[-24:].max() - df['low'].iloc[-24:].min()) / close_val if len(df) >= 24 else 1.0
    std_ratio = float(last_row['std20']) / close_val if 'std20' in last_row else 1.0
    if recent_range_pct < 0.003 or std_ratio < 0.0006:
        # Asset has virtually no volatility (<0.3% range over 24 bars) -> Pegged/Flat coin
        return None
    
    is_squeeze = bool(last_row['squeeze_on'])
    squeeze_bars = int(last_row['squeeze_bars'])
    comp_ratio = round(float(last_row.get('compression_ratio', 1.0)), 2)
    tension_score = round(float(last_row.get('tension_score', 0.0)), 1)
    buyer_ratio = round(float(last_row.get('buyer_ratio', 50.0)), 1)
    signal = str(last_row['signal'])
    
    # Squeeze Lifecycle Stage Classification (Traffic Light)
    if is_squeeze:
        if squeeze_bars >= 6 or comp_ratio <= 0.75:
            squeeze_stage = "HIGH_TENSION"  # 🟠 High energy / tight spring
        else:
            squeeze_stage = "COILING"       # 🟡 Building up / early squeeze
    elif bool(last_row.get('squeeze_released', False)) or signal in ['LONG', 'SHORT']:
        squeeze_stage = "FIRED"             # 🟢 Breakout active
    else:
        squeeze_stage = "NONE"              # ⚪ Normal
    
    recent_signal = "NONE"
    for i in range(1, min(4, len(df))):
        sig = df.iloc[-i]['signal']
        if sig in ['LONG', 'SHORT']:
            recent_signal = f"{sig} ({i} bar{'s' if i > 1 else ''} ago)"
            break
            
    trend = "BULLISH" if last_row['close'] > last_row['ema200'] else "BEARISH"
    pct_from_ema200 = ((last_row['close'] - last_row['ema200']) / last_row['ema200']) * 100.0
    
    # MTF Trend Estimation
    ema50_val = float(last_row['ema50'])
    rsi_val = float(last_row['rsi14'])
    mtf_1h = "BULLISH" if (close_val > ema50_val and rsi_val >= 48) else ("BEARISH" if (close_val < ema50_val and rsi_val <= 52) else "NEUTRAL")
    mtf_30m = mtf_1h
    mtf_4h = "BULLISH" if (close_val > float(last_row['ema200']) and rsi_val >= 46) else ("BEARISH" if (close_val < float(last_row['ema200']) and rsi_val <= 54) else "NEUTRAL")

    target_dir = "LONG" if (signal == "LONG" or (signal == "NONE" and trend == "BULLISH")) else "SHORT"
    rr_targets = calculate_rr_levels(float(last_row['close']), float(last_row['atr14']), target_dir)
    
    return {
        "symbol": symbol,
        "price": close_val,
        "volume": float(last_row['volume']),
        "change_pct": round(((last_row['close'] - df.iloc[-24]['close']) / df.iloc[-24]['close'] * 100.0) if len(df) >= 24 else 0.0, 2),
        "is_squeeze": is_squeeze,
        "squeeze_bars": squeeze_bars,
        "squeeze_stage": squeeze_stage,
        "compression_ratio": comp_ratio,
        "tension_score": tension_score,
        "buyer_ratio": buyer_ratio,
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

async def scan_market(interval: str = "30m", limit_pairs: int = 50, force_refresh: bool = False) -> List[Dict[str, Any]]:
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
        stage = item.get('squeeze_stage', 'NONE')
        stage_score = 40 if stage == 'HIGH_TENSION' else (20 if stage == 'COILING' else (60 if stage == 'FIRED' else 0))
        tension = float(item.get('tension_score', 0))
        return sig_score + stage_score + min(tension, 30.0)
        
    valid_results.sort(key=sort_priority, reverse=True)
    _scan_cache[cache_key] = {"timestamp": now, "data": valid_results}
    return valid_results


async def fetch_symbol_htf_data(
    session: aiohttp.ClientSession,
    symbol: str,
    intervals: List[str] = ["30m", "1h", "4h"],
    limit: int = 120
) -> Dict[str, pd.DataFrame]:
    """
    Fetch and pre-compute indicators for multiple higher timeframes for a given symbol.
    Guarantees returning a dictionary mapping timeframe -> indicator-enriched DataFrame:
    e.g. {"30m": df_30m, "1h": df_1h, "4h": df_4h}
    """
    tasks = [fetch_klines(session, symbol, interval=tf, limit=limit) for tf in intervals]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    htf_map: Dict[str, pd.DataFrame] = {}
    for tf, res in zip(intervals, results):
        if isinstance(res, pd.DataFrame) and len(res) >= 30:
            htf_map[tf] = compute_indicators(res)
    return htf_map


async def scan_market_multi_tf(
    intervals: List[str] = ["30m", "1h", "4h"],
    primary_interval: str = "15m",
    limit_pairs: int = 50,
    min_quote_volume: float = 15000000.0,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Scan top liquid market pairs with guaranteed multi-timeframe HTF data pipeline (30m, 1h, 4h).
    Returns list of analyzed symbols with htf_data={"30m": df_30m, "1h": df_1h, "4h": df_4h}
    and multi-timeframe trend alignment.
    """
    safe_limit = max(10, min(100, int(limit_pairs)))
    symbols = await fetch_top_usdt_pairs(limit=safe_limit, min_quote_volume=min_quote_volume)
    session = await get_http_session()

    async def _scan_single(sym: str) -> Optional[Dict[str, Any]]:
        # Fetch base scan metrics
        base_res = await scan_single_symbol(session, sym, interval=primary_interval)
        if not base_res:
            return None

        # Guarantee 30m, 1h, 4h HTF data pipeline
        htf_data = await fetch_symbol_htf_data(session, sym, intervals=intervals)
        base_res["htf_data"] = htf_data

        # Determine true multi-timeframe trends if HTF data present
        for htf_tf in ["30m", "1h", "4h"]:
            df_htf = htf_data.get(htf_tf)
            if df_htf is not None and len(df_htf) >= 20:
                htf_last = df_htf.iloc[-1]
                h_c = float(htf_last['close'])
                h_ema = float(htf_last.get('ema50', htf_last.get('sma20', h_c)))
                h_rsi = float(htf_last.get('rsi14', 50.0))
                if h_c > h_ema and h_rsi >= 48.0:
                    base_res[f"mtf_{htf_tf}"] = "BULLISH"
                elif h_c < h_ema and h_rsi <= 52.0:
                    base_res[f"mtf_{htf_tf}"] = "BEARISH"
                else:
                    base_res[f"mtf_{htf_tf}"] = "NEUTRAL"

        return base_res

    tasks = [_scan_single(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid_results = [r for r in results if isinstance(r, dict) and r is not None]

    def sort_priority(item):
        sig_score = 100 if item.get('signal') in ['LONG', 'SHORT'] else (50 if item.get('recent_signal') != 'NONE' else 0)
        stage = item.get('squeeze_stage', 'NONE')
        stage_score = 40 if stage == 'HIGH_TENSION' else (20 if stage == 'COILING' else (60 if stage == 'FIRED' else 0))
        tension = float(item.get('tension_score', 0))
        return sig_score + stage_score + min(tension, 30.0)

    valid_results.sort(key=sort_priority, reverse=True)
    return valid_results


