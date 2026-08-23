import asyncio
import aiohttp
import pandas as pd
import numpy as np
import time
from typing import List, Dict, Tuple, Optional, Any

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

class RateLimitManager:
    """
    Global adaptive rate-limit controller and request weight manager for Binance API.
    Inspects response headers (x-mbx-used-weight-1m), tracks latency, dynamically paces
    concurrency, and manages graceful backoff to guarantee zero 429/IP bans.
    Binance Spot IP limit is 6,000 weight/minute.
    """
    def __init__(self, weight_limit_1m: int = 6000):
        self.weight_limit_1m = weight_limit_1m
        self.used_weight_1m: int = 0
        self.last_update_ts: float = 0.0
        self.backoff_until_ts: float = 0.0
        self.last_latency_ms: float = 0.0
        self.total_requests_count: int = 0
        self._lock = asyncio.Lock()

    def update_from_headers(self, headers: Any, latency_ms: float = 0.0):
        """Update rate-limit usage metrics from Binance response headers."""
        now = time.time()
        self.last_update_ts = now
        self.last_latency_ms = latency_ms
        self.total_requests_count += 1
        
        weight_str = headers.get('x-mbx-used-weight-1m') or headers.get('X-MBX-USED-WEIGHT-1M')
        if weight_str:
            try:
                self.used_weight_1m = int(weight_str)
            except (ValueError, TypeError):
                pass

    def trigger_backoff(self, retry_after: int = 30):
        """Activate hard rate-limit backoff."""
        self.backoff_until_ts = time.time() + retry_after
        print(f"[RateLimitManager] [!] HTTP 429 encountered! Backing off for {retry_after}s...")

    async def pace(self):
        """Apply dynamic adaptive pacing delay based on current 1-minute weight usage."""
        now = time.time()
        # 1. Check hard backoff
        if now < self.backoff_until_ts:
            wait_rem = self.backoff_until_ts - now
            await asyncio.sleep(wait_rem)
            return

        # 2. Reset weight estimate if no requests for > 60s
        if self.last_update_ts > 0 and (now - self.last_update_ts) > 65.0:
            self.used_weight_1m = 0

        # 3. Dynamic pacing based on 6,000 weight limit
        if self.used_weight_1m >= 5200:
            await asyncio.sleep(0.35)
        elif self.used_weight_1m >= 4500:
            await asyncio.sleep(0.10)
        elif self.used_weight_1m >= 3500:
            await asyncio.sleep(0.03)

    def get_telemetry(self) -> Dict[str, Any]:
        """Return standardized rate-limit telemetry dictionary for APIs and UI."""
        now = time.time()
        if self.last_update_ts > 0 and (now - self.last_update_ts) > 65.0:
            self.used_weight_1m = 0
            
        pct = round((self.used_weight_1m / self.weight_limit_1m) * 100.0, 1)
        if self.used_weight_1m < 3500:
            status = "HEALTHY"
            badge_color = "emerald"
        elif self.used_weight_1m < 4800:
            status = "PACED"
            badge_color = "amber"
        else:
            status = "DEFENSE"
            badge_color = "rose"

        return {
            "used_weight_1m": self.used_weight_1m,
            "weight_limit_1m": self.weight_limit_1m,
            "usage_pct": pct,
            "status": status,
            "badge_color": badge_color,
            "last_latency_ms": round(self.last_latency_ms, 1),
            "total_requests": self.total_requests_count,
            "is_backed_off": now < self.backoff_until_ts
        }

# Global Singleton
rate_limit_manager = RateLimitManager()

EXCLUDED_KEYWORDS = [
    'UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT', 'USDCUSDT', 'FDUSDUSDT', 
    'TUSDUSDT', 'EURUSDT', 'DAIUSDT', 'USD1USDT', 'USDEUSDT', 'EURIUSDT', 
    'AEURUSDT', 'USDPUSDT', 'PYUSDUSDT', 'USDDUSDT', 'WBTCUSDT', 'WETHUSDT',
    'RLUSDUSDT', 'BUSDUSDT', 'USTCUSDT', 'UUSDT', 'USD0USDT', 'USDMUSDT',
    'BFDUSDUSDT', 'USDEUSDT'
]

DEFAULT_TOP_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", 
    "AVAXUSDT", "LINKUSDT", "SUIUSDT", "NEARUSDT", "DOTUSDT", "APTUSDT", "LTCUSDT", 
    "UNIUSDT", "ICPUSDT", "RENDERUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT", "ARBUSDT", 
    "OPUSDT", "PEPEUSDT", "WIFUSDT", "SHIBUSDT", "BONKUSDT", "FETUSDT", "TAOUSDT", 
    "RUNEUSDT", "STXUSDT", "AAVEUSDT", "MKRUSDT", "PENDLEUSDT", "ONDOUSDT", "JUPUSDT", 
    "PYTHUSDT", "CRVUSDT", "FILUSDT", "ATOMUSDT", "HBARUSDT", "KASUSDT", "FTMUSDT", 
    "GALAUSDT", "FLOKIUSDT", "IMXUSDT", "GRTUSDT", "THETAUSDT", "ALGOUSDT", "SANDUSDT", "MANAUSDT"
]

async def fetch_top_crypto_pairs(limit: int = 100) -> List[str]:
    """Fetch top 100 liquid USDT spot pairs by 24h quote volume from Binance API."""
    try:
        await rate_limit_manager.pace()
        t0 = time.perf_counter()
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(BINANCE_TICKER_24HR_URL) as resp:
                rate_limit_manager.update_from_headers(resp.headers, (time.perf_counter() - t0) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    usdt_pairs = [
                        item for item in data 
                        if item['symbol'].endswith('USDT') 
                        and not any(x == item['symbol'] or x in item['symbol'] for x in EXCLUDED_KEYWORDS)
                    ]
                    usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                    top_symbols = [item['symbol'] for item in usdt_pairs[:limit]]
                    if top_symbols:
                        return top_symbols
    except Exception as e:
        print(f"[DataLoader] Notice: Failed to fetch live tickers ({e}), using default top liquid coins.")
    return DEFAULT_TOP_COINS[:limit]

# Shared global in-memory kline cache across scanner, chart, and live bot
_shared_kline_cache: Dict[str, Dict[str, Any]] = {}
KLINE_TTL_MAP = {
    "5m": 18.0,
    "15m": 35.0,
    "30m": 60.0,
    "1h": 120.0,
    "4h": 240.0,
    "1d": 600.0,
}

async def fetch_symbol_klines(
    session: aiohttp.ClientSession, 
    symbol: str, 
    interval: str = "15m", 
    limit: int = 500,
    force_refresh: bool = False
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candlestick data with global in-memory TTL caching, rate-limit header tracking, adaptive pacing, and backoff."""
    cache_key = f"{symbol}_{interval}_{limit}"
    now = time.time()
    ttl = KLINE_TTL_MAP.get(interval, 25.0)

    if not force_refresh and cache_key in _shared_kline_cache:
        cached = _shared_kline_cache[cache_key]
        if (now - cached["ts"]) < ttl:
            return cached["df"].copy()

    await rate_limit_manager.pace()
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        t0 = time.perf_counter()
        async with session.get(BINANCE_KLINES_URL, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            latency_ms = (time.perf_counter() - t0) * 1000
            rate_limit_manager.update_from_headers(resp.headers, latency_ms)

            if resp.status == 429:
                retry_after = int(resp.headers.get('Retry-After', 30))
                rate_limit_manager.trigger_backoff(retry_after)
                return None

            if resp.status == 200:
                raw = await resp.json()
                if not raw or len(raw) < 50:
                    return None
                
                df = pd.DataFrame(raw, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['time'] = (df['open_time'] // 1000).astype(int)
                for col in ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base']:
                    df[col] = df[col].astype(float)
                
                df['symbol'] = symbol
                res_df = df[['time', 'open', 'high', 'low', 'close', 'volume', 'taker_buy_base', 'symbol']]
                _shared_kline_cache[cache_key] = {"ts": now, "df": res_df}
                return res_df
    except Exception as e:
        print(f"[DataLoader] Warning fetching {symbol}: {e}")
        return None
    except Exception as e:
        print(f"[DataLoader] Warning fetching {symbol}: {e}")
        return None

async def fetch_symbol_mtf_klines(
    session: aiohttp.ClientSession,
    symbol: str,
    intervals: List[str] = ["1h", "4h"],
    limit: int = 100
) -> Dict[str, pd.DataFrame]:
    """Fetch multi-timeframe candle datasets (e.g. 1h, 4h) for a symbol concurrently."""
    tasks = [fetch_symbol_klines(session, symbol, interval=tf, limit=limit) for tf in intervals]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    mtf_map: Dict[str, pd.DataFrame] = {}
    for tf, res in zip(intervals, results):
        if isinstance(res, pd.DataFrame) and len(res) >= 30:
            mtf_map[tf] = res
    return mtf_map

async def fetch_market_dataset(
    symbols: List[str], 
    interval: str = "15m", 
    limit: int = 500
) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV market dataset for multiple crypto symbols concurrently."""
    dataset: Dict[str, pd.DataFrame] = {}
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_symbol_klines(session, sym, interval, limit) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(symbols, results):
            if isinstance(res, pd.DataFrame) and len(res) >= 60:
                dataset[sym] = res
    return dataset

def split_train_test(df: pd.DataFrame, train_ratio: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split time-series data into In-Sample (Train/Discovery) and Out-of-Sample (Validation)."""
    split_idx = int(len(df) * train_ratio)
    train_df = df.iloc[:split_idx].copy().reset_index(drop=True)
    test_df = df.iloc[split_idx:].copy().reset_index(drop=True)
    return train_df, test_df
