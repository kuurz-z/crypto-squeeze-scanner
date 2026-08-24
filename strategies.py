import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

def calculate_hurst_exponent(
    price_series: np.ndarray, 
    min_window: int = 6, 
    max_window: Optional[int] = None,
    max_lags: Optional[int] = None,
    **kwargs
) -> float:
    """
    Calculate the Hurst Exponent (H) via Rescaled Range (R/S) analysis:
      - H > 0.52: Persistent Trending Regime (Directional breakout/trend trades approved)
      - 0.48 <= H <= 0.52: Random Walk / Brownian Motion
      - H < 0.48: Mean-Reverting / Anti-Persistent Chop (Breakout trades blocked)
    """
    try:
        series = np.asarray(price_series, dtype=float)
        if len(series) < 30:
            return 0.5
        returns = np.diff(series)
        if len(returns) < 20 or np.all(returns == 0):
            return 0.5

        N = len(returns)
        if max_window is None:
            max_window = max_lags if max_lags is not None else N // 2

        windows = []
        rs_vals = []

        for w in range(min_window, min(max_window + 1, N)):
            k = N // w
            if k < 1:
                continue
            rs_sub = []
            for i in range(k):
                sub = returns[i*w : (i+1)*w]
                std = np.std(sub)
                if std < 1e-8:
                    continue
                mean = np.mean(sub)
                dev = np.cumsum(sub - mean)
                r = np.max(dev) - np.min(dev)
                rs_sub.append(r / std)
            if rs_sub:
                windows.append(w)
                rs_vals.append(np.mean(rs_sub))

        if len(windows) < 3:
            return 0.5

        poly = np.polyfit(np.log(windows), np.log(rs_vals), 1)
        return float(np.clip(poly[0], 0.0, 1.0))
    except Exception:
        return 0.5

def compute_crypto_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate comprehensive technical indicators for crypto strategy analysis."""
    df = df.copy()
    if len(df) < 50:
        return df

    # EMAs for Trend Regime
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # Bollinger Bands (20, 2.0)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['sma20'] + (2.0 * df['std20'])
    df['bb_lower'] = df['sma20'] - (2.0 * df['std20'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['sma20']

    # ATR (14)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr14'] = tr.rolling(window=14).mean().bfill()

    # Keltner Channels (20 SMA, 1.5 ATR)
    df['kc_upper'] = df['sma20'] + (1.5 * df['atr14'])
    df['kc_lower'] = df['sma20'] - (1.5 * df['atr14'])

    # Squeeze Indicator (BB inside KC)
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']

    # Squeeze Compression Depth Ratio
    bb_w = (df['bb_upper'] - df['bb_lower']).replace(0, np.nan)
    kc_w = (df['kc_upper'] - df['kc_lower']).replace(0, np.nan)
    df['compression_ratio'] = (bb_w / kc_w).fillna(1.0)

    # Momentum Oscillator (Linear Regression of price minus midline)
    midline = (df['sma20'] + (df['high'].rolling(20).max() + df['low'].rolling(20).min()) / 2) / 2
    delta = df['close'] - midline
    df['momentum'] = delta.rolling(window=12).mean()

    # Relative Strength Index (RSI 14)
    change = df['close'].diff()
    gain = (change.where(change > 0, 0)).rolling(window=14).mean()
    loss = (-change.where(change < 0, 0)).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi14'] = 100 - (100 / (1 + rs))
    df['rsi14'] = df['rsi14'].fillna(50.0)

    # Relative Volume & Swing Highs/Lows
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    df['rvol'] = df['volume'] / df['vol_sma20'].replace(0, np.nan)
    df['rvol'] = df['rvol'].fillna(1.0)
    
    # Order Flow: Taker Buy Volume Ratio
    if 'taker_buy_base' in df.columns:
        df['buyer_ratio'] = (df['taker_buy_base'] / df['volume'].replace(0, np.nan) * 100.0).fillna(50.0)
    else:
        tot_r = (df['high'] - df['low']).replace(0, 1e-6)
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / tot_r
        df['buyer_ratio'] = ((clv + 1.0) / 2.0 * 100.0).fillna(50.0)
    
    df['swing_high_5'] = df['high'].rolling(window=5).max().shift(1)
    df['swing_low_5'] = df['low'].rolling(window=5).min().shift(1)
    df['swing_high_20'] = df['high'].rolling(window=20).max().shift(1)
    df['swing_low_20'] = df['low'].rolling(window=20).min().shift(1)

    # Rolling Hurst Exponent (Window: 40 bars)
    hurst_vals = [0.5] * len(df)
    closes = df['close'].values
    for i in range(40, len(df)):
        hurst_vals[i] = calculate_hurst_exponent(closes[i-39:i+1], max_lags=15)
    df['hurst'] = hurst_vals

    return df

def evaluate_tf_trend(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    """
    Evaluate trend direction, EMA alignment, and momentum state on any timeframe dataframe (e.g. 30m, 4h).
    Returns regime (BULLISH, BEARISH, NEUTRAL), key EMAs, RSI, and momentum.
    """
    if df is None or len(df) < 30:
        return {
            "regime": "NEUTRAL",
            "close": 0.0,
            "ema50": 0.0,
            "ema200": 0.0,
            "rsi": 50.0,
            "momentum": 0.0,
            "is_valid": False
        }
    
    if 'ema50' not in df.columns:
        df = compute_crypto_indicators(df)
        
    last = df.iloc[-1]
    close = float(last['close'])
    ema50 = float(last.get('ema50', close))
    ema200 = float(last.get('ema200', ema50))
    rsi = float(last.get('rsi14', 50.0))
    mom = float(last.get('momentum', 0.0))
    
    # 3-bar flash change check
    three_ago = float(df.iloc[-4]['close']) if len(df) >= 4 else close
    pct_3b = ((close - three_ago) / three_ago) * 100.0 if three_ago > 0 else 0.0
    
    is_bullish = (close >= ema50) and (rsi >= 46.0) and (pct_3b > -2.0)
    is_bearish = (close <= ema50) and (rsi <= 54.0)
    
    if pct_3b <= -2.0 or (close < ema50 and rsi < 42.0):
        regime = "BEARISH"
    elif is_bullish:
        regime = "BULLISH"
    elif is_bearish:
        regime = "BEARISH"
    else:
        regime = "NEUTRAL"
        
    return {
        "regime": regime,
        "close": close,
        "ema50": ema50,
        "ema200": ema200,
        "rsi": round(rsi, 1),
        "momentum": round(mom, 4),
        "pct_change_3b": round(pct_3b, 2),
        "is_valid": True
    }

def evaluate_mtf_alignment(
    df_1h: Optional[pd.DataFrame] = None, 
    df_4h: Optional[pd.DataFrame] = None, 
    direction: str = "LONG",
    entry_tf: str = "15m",
    df_30m: Optional[pd.DataFrame] = None,
    **kwargs
) -> tuple[bool, Dict[str, Any]]:
    """
    Strict Multi-Timeframe Alignment:
      - 5m entries MUST align with 30m higher-timeframe trend.
      - 15m entries MUST align with 1h higher-timeframe trend.
      - 30m entries MUST align with 4h higher-timeframe macro trend.
      - 1h, 4h, 1d entries are strictly BLOCKED.
      
    For LONG:
      - Anchor TF must NOT be BEARISH (should be BULLISH or NEUTRAL)
    For SHORT:
      - Anchor TF must NOT be BULLISH (should be BEARISH or NEUTRAL)
    """
    # STRICT RULE: Only 5m, 15m, and 30m timeframes can generate trade entries
    if entry_tf not in ["5m", "15m", "30m"]:
        return False, {
            "entry_tf": entry_tf,
            "anchor_tf": "N/A",
            "anchor_regime": "N/A",
            "30m": "N/A",
            "1h": "N/A",
            "4h": "N/A",
            "aligned": False,
            "reasons": [f"Entries on timeframe '{entry_tf}' are blocked. Entries are strictly restricted to 5m, 15m, and 30m."]
        }

    t_30m = evaluate_tf_trend(df_30m) if df_30m is not None else {"is_valid": False, "regime": "N/A"}
    t_1h = evaluate_tf_trend(df_1h) if df_1h is not None else {"is_valid": False, "regime": "N/A"}
    t_4h = evaluate_tf_trend(df_4h) if df_4h is not None else {"is_valid": False, "regime": "N/A"}

    if entry_tf == "5m":
        t_anchor = t_30m
        anchor_tf = "30m"
    elif entry_tf == "15m":
        t_anchor = t_1h
        anchor_tf = "1h"
    else:  # 30m
        t_anchor = t_4h
        anchor_tf = "4h"

    context = {
        "entry_tf": entry_tf,
        "anchor_tf": anchor_tf,
        "anchor_regime": t_anchor.get("regime", "N/A"),
        "30m": t_30m.get("regime", "N/A"),
        "1h": t_1h.get("regime", "N/A"),
        "4h": t_4h.get("regime", "N/A"),
        "aligned": True,
        "reasons": []
    }

    if direction == "LONG":
        if t_anchor.get("is_valid") and t_anchor.get("regime") == "BEARISH":
            context["aligned"] = False
            context["reasons"].append(
                f"{anchor_tf} Anchor Trend is BEARISH (Close ${t_anchor.get('close', 0):.4f} < EMA50 ${t_anchor.get('ema50', 0):.4f}, RSI {t_anchor.get('rsi', 0)})"
            )
    elif direction == "SHORT":
        if t_anchor.get("is_valid") and t_anchor.get("regime") == "BULLISH":
            context["aligned"] = False
            context["reasons"].append(
                f"{anchor_tf} Anchor Trend is BULLISH (Close ${t_anchor.get('close', 0):.4f} > EMA50 ${t_anchor.get('ema50', 0):.4f}, RSI {t_anchor.get('rsi', 0)})"
            )

    return context["aligned"], context

class StrategyBase:
    name: str = "BaseStrategy"
    description: str = ""

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.0,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None,
        timeframe: str = "15m"
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a candle and return a trade order dict if triggered."""
        raise NotImplementedError

class SqueezeMomentumBreakout(StrategyBase):
    name = "Squeeze_Momentum_Breakout"
    description = "Trades high-probability volatility expansion out of compressed Bollinger Bands/Keltner Channels with pullback/retest precision, volume surge, Hurst regime gating, and MTF alignment."

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.2,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None,
        timeframe: str = "15m"
    ) -> Optional[Dict[str, Any]]:
        # STRICT RULE: Trading entries are allowed on 5m, 15m, and 30m
        if timeframe not in ["5m", "15m", "30m"]:
            return None
        if idx < 50:
            return None

        p = params or {}
        rvol_min = p.get("rvol_min", 1.10)
        atr_sl_mult = p.get("atr_sl_mult", 1.60)
        rsi_min_long = p.get("rsi_min_long", 44.0)
        rsi_max_long = p.get("rsi_max_long", 64.0)
        rsi_min_short = p.get("rsi_min_short", 36.0)
        rsi_max_short = p.get("rsi_max_short", 56.0)
        min_body_ratio = p.get("min_body_ratio", 0.25)
        max_wick_ratio = p.get("max_wick_ratio", 0.40)
        min_risk_dist_pct = p.get("min_risk_dist_pct", 0.008)

        curr = df.iloc[idx]
        
        # Check if squeeze was active recently (at least 2 squeeze bars in the last 6 bars)
        recent_squeezes = df['squeeze_on'].iloc[max(0, idx - 6):idx].sum()
        squeeze_fired = (recent_squeezes >= 2) and (not curr['squeeze_on'])
        
        if not squeeze_fired:
            return None

        close = float(curr['close'])
        open_p = float(curr['open'])
        high = float(curr['high'])
        low = float(curr['low'])
        atr = float(curr['atr14'])
        ema20 = float(curr.get('ema20', close))
        ema50 = float(curr.get('ema50', close))
        rvol = float(curr.get('rvol', 1.0))
        rsi = float(curr.get('rsi14', 50.0))
        mom = float(curr.get('momentum', 0.0))
        hurst = float(curr.get('hurst', 0.5))
        
        if atr <= 0:
            return None

        # Regime Gating: Reject trades in strongly mean-reverting chop (H < 0.45)
        if hurst < 0.45:
            return None

        total_range = max(high - low, 1e-6)
        risk_dist = max(atr_sl_mult * atr, close * min_risk_dist_pct)

        # Long Setup: Squeeze release + Bullish Momentum + Safe RSI Corridor (44-64) + Retest / Breakout Confirmation
        swing_h5 = float(curr.get('swing_high_5', close)) if 'swing_high_5' in curr and not pd.isna(curr['swing_high_5']) else close
        buyer_r = float(curr.get('buyer_ratio', 50.0)) if 'buyer_ratio' in curr and not pd.isna(curr['buyer_ratio']) else 50.0

        # Bullish conditions: Momentum positive, price > EMA50, healthy RSI corridor, strong buyer participation
        is_bullish_expansion = (mom > 0) and (close > ema50) and (rsi_min_long <= rsi <= rsi_max_long) and (rvol >= rvol_min) and (buyer_r >= 44.0)
        # Entry triggered on breakout confirmation OR healthy pullback retest touching EMA20
        pullback_retest = (low <= ema20 * 1.004) and (close >= ema20 * 0.996)
        breakout_trigger = (close > curr['bb_upper'] or pullback_retest) and (close >= swing_h5 * 0.998)

        if is_bullish_expansion and breakout_trigger:
            # Check 5m(30m) / 15m(1h) / 30m(4h) Multi-Timeframe Alignment
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            body = close - open_p
            upper_wick = high - close
            
            # Reject wick traps and dojis (ensure strong directional body closing near highs)
            if body > 0 and (body / total_range) >= min_body_ratio and (upper_wick / total_range) <= max_wick_ratio:
                # Structural Stop Loss: Below recent swing low or ATR buffer
                recent_low = float(df['low'].iloc[max(0, idx-5):idx].min()) if idx >= 5 else low
                sl_price = min(recent_low * 0.998, close - risk_dist)
                risk_dist = close - sl_price
                tp_price = close + (target_rr * risk_dist)
                
                return {
                    "strategy": "Squeeze_Momentum_Breakout",
                    "direction": "LONG",
                    "timeframe": timeframe,
                    "entry_price": close,
                    "sl_price": round(sl_price, 6 if close < 1 else 2),
                    "tp_price": round(tp_price, 6 if close < 1 else 2),
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Bullish Trend & Volatility Expansion",
                        "reason": f"Squeeze expansion on {timeframe} with volume confirmation & Hurst persistence (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "momentum": round(mom, 4),
                        "hurst": round(hurst, 3),
                        "buyer_ratio": round(buyer_r, 1),
                        "ema_alignment": "Close > EMA50",
                        "body_ratio": round(body / total_range, 2),
                        "volatility_atr": round(atr, 4),
                        "timeframe": timeframe,
                        "mtf_alignment": mtf_summary
                    }
                }

        # Short Setup: Squeeze release + Bearish Momentum + Safe RSI Corridor (36-56) + Retest / Breakdown Confirmation
        swing_l5 = float(curr.get('swing_low_5', close)) if 'swing_low_5' in curr and not pd.isna(curr['swing_low_5']) else close

        is_bearish_expansion = (mom < 0) and (close < ema50) and (rsi_min_short <= rsi <= rsi_max_short) and (rvol >= rvol_min) and (buyer_r <= 56.0)
        pullback_retest_short = (high >= ema20 * 0.996) and (close <= ema20 * 1.004)
        breakdown_trigger = (close < curr['bb_lower'] or pullback_retest_short) and (close <= swing_l5 * 1.002)

        if is_bearish_expansion and breakdown_trigger:
            # Check 5m(30m) / 15m(1h) / 30m(4h) Multi-Timeframe Alignment
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            body = open_p - close
            lower_wick = close - low
            
            # Reject wick traps and dojis (ensure strong directional body closing near lows)
            if body > 0 and (body / total_range) >= min_body_ratio and (lower_wick / total_range) <= max_wick_ratio:
                recent_high = float(df['high'].iloc[max(0, idx-5):idx].max()) if idx >= 5 else high
                sl_price = max(recent_high * 1.002, close + risk_dist)
                risk_dist = sl_price - close
                tp_price = close - (target_rr * risk_dist)
                
                return {
                    "strategy": "Squeeze_Momentum_Breakout",
                    "direction": "SHORT",
                    "timeframe": timeframe,
                    "entry_price": close,
                    "sl_price": round(sl_price, 6 if close < 1 else 2),
                    "tp_price": round(tp_price, 6 if close < 1 else 2),
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Bearish Trend & Volatility Breakdown",
                        "reason": f"Squeeze breakdown on {timeframe} with volume confirmation & Hurst persistence (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "momentum": round(mom, 4),
                        "hurst": round(hurst, 3),
                        "buyer_ratio": round(buyer_r, 1),
                        "ema_alignment": "Close < EMA50",
                        "body_ratio": round(body / total_range, 2),
                        "volatility_atr": round(atr, 4),
                        "timeframe": timeframe,
                        "mtf_alignment": mtf_summary
                    }
                }

        return None

class LiquiditySweepReversal(StrategyBase):
    name = "Liquidity_Sweep_Reversal"
    description = "Captures false breakout traps where price sweeps previous 20-bar swing highs/lows and aggressively rejects."

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.0,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None,
        timeframe: str = "15m"
    ) -> Optional[Dict[str, Any]]:
        # STRICT RULE: Trading entries are allowed on 5m, 15m, and 30m
        if timeframe not in ["5m", "15m", "30m"]:
            return None
        if idx < 50:
            return None

        p = params or {}
        rvol_min = p.get("rvol_min", 1.05)
        min_risk_dist_pct = p.get("min_risk_dist_pct", 0.008)

        curr = df.iloc[idx]
        close = float(curr['close'])
        open_p = float(curr['open'])
        high = float(curr['high'])
        low = float(curr['low'])
        atr = float(curr['atr14'])
        swing_high = float(curr['swing_high_20'])
        swing_low = float(curr['swing_low_20'])
        rvol = float(curr['rvol'])
        rsi = float(curr['rsi14'])

        if atr <= 0 or np.isnan(swing_high) or np.isnan(swing_low):
            return None

        # Long: Sweep of swing low, closing with bullish rejection wick and non-overbought RSI
        if low < swing_low and close > swing_low and close > open_p and rsi <= 55.0:
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            lower_wick = min(open_p, close) - low
            body = abs(close - open_p)
            if lower_wick >= 0.8 * (body + 1e-6) and rvol >= rvol_min:  # Valid rejection wick
                risk_dist = max(atr * 1.2, (close - low) * 1.15, close * min_risk_dist_pct)
                entry_price = close
                sl_price = entry_price - risk_dist
                tp_price = entry_price + (target_rr * risk_dist)
                
                return {
                    "strategy": "Liquidity_Sweep_Reversal",
                    "direction": "LONG",
                    "timeframe": timeframe,
                    "entry_price": entry_price,
                    "sl_price": round(sl_price, 6 if close < 1 else 2),
                    "tp_price": round(tp_price, 6 if close < 1 else 2),
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Liquidity Hunt Reversal (Bull Trap Clearance)",
                        "reason": f"Price pierced 20-bar swing low ({round(swing_low, 4)}) on {timeframe} and rejected aggressively with lower wick (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "lower_wick_ratio": round(lower_wick / (body + 1e-6), 2),
                        "volatility_atr": round(atr, 4),
                        "timeframe": timeframe,
                        "mtf_alignment": mtf_summary
                    }
                }

        # Short: Sweep of swing high, closing with bearish rejection wick and non-oversold RSI
        if high > swing_high and close < swing_high and close < open_p and rsi >= 45.0:
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            upper_wick = high - max(open_p, close)
            body = abs(close - open_p)
            if upper_wick >= 0.8 * (body + 1e-6) and rvol >= rvol_min:  # Valid rejection wick
                risk_dist = max(atr * 1.2, (high - close) * 1.15, close * min_risk_dist_pct)
                entry_price = close
                sl_price = entry_price + risk_dist
                tp_price = entry_price - (target_rr * risk_dist)
                
                return {
                    "strategy": "Liquidity_Sweep_Reversal",
                    "direction": "SHORT",
                    "timeframe": timeframe,
                    "entry_price": entry_price,
                    "sl_price": round(sl_price, 6 if close < 1 else 2),
                    "tp_price": round(tp_price, 6 if close < 1 else 2),
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Liquidity Hunt Reversal (Bear Trap Clearance)",
                        "reason": f"Price swept 20-bar swing high ({round(swing_high, 4)}) on {timeframe} and rejected aggressively with upper wick (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "upper_wick_ratio": round(upper_wick / (body + 1e-6), 2),
                        "volatility_atr": round(atr, 4),
                        "timeframe": timeframe,
                        "mtf_alignment": mtf_summary
                    }
                }

        return None

class TrendPullbackConfluence(StrategyBase):
    name = "Trend_Pullback_Confluence"
    description = "Enters on high-probability pullbacks to EMA20/EMA50 value zones within established higher-timeframe trends with 1:2.5+ RR and 1.8x ATR protection."

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.5,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None,
        timeframe: str = "15m"
    ) -> Optional[Dict[str, Any]]:
        # STRICT RULE: Trading entries are allowed on 5m, 15m, and 30m
        if timeframe not in ["5m", "15m", "30m"]:
            return None
        if idx < 50:
            return None

        p = params or {}
        min_risk_dist_pct = p.get("min_risk_dist_pct", 0.008)
        atr_sl_mult = p.get("atr_sl_mult", 1.80)
        rvol_min = p.get("rvol_min", 1.0)
        rsi_min_long = p.get("rsi_min_long", 38.0)
        rsi_max_long = p.get("rsi_max_long", 56.0)
        rsi_min_short = p.get("rsi_min_short", 44.0)
        rsi_max_short = p.get("rsi_max_short", 62.0)

        if 'ema20' not in df.columns:
            df = compute_crypto_indicators(df)

        curr = df.iloc[idx]
        
        close = float(curr['close'])
        open_p = float(curr['open'])
        low = float(curr['low'])
        high = float(curr['high'])
        ema20 = float(curr.get('ema20', close))
        ema50 = float(curr.get('ema50', close))
        ema200 = float(curr.get('ema200', ema50))
        atr = float(curr.get('atr14', 0.0))
        rsi = float(curr.get('rsi14', 50.0))
        rvol = float(curr.get('rvol', 1.0))
        hurst = float(curr.get('hurst', 0.5))

        if atr <= 0:
            return None

        # Regime Gating: Filter out dead chop / anti-persistent regimes
        if hurst < 0.45:
            return None

        # Uptrend Condition: EMA20 > EMA50 > EMA200 and Close > EMA200
        uptrend = (ema20 > ema50) and (ema50 > ema200) and (close > ema200)
        # Downtrend Condition: EMA20 < EMA50 < EMA200 and Close < EMA200
        downtrend = (ema20 < ema50) and (ema50 < ema200) and (close < ema200)

        # Long: In strong uptrend, price pulled back into EMA20/EMA50 zone, RSI reset (38-56), bullish trigger candle reclaiming EMA20
        if uptrend and (low <= ema20 * 1.002 or low <= ema50 * 1.002) and (close > open_p) and (close >= ema20 * 0.998) and (rsi_min_long <= rsi <= rsi_max_long) and (rvol >= rvol_min):
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            risk_dist = max(atr_sl_mult * atr, close * min_risk_dist_pct)
            entry_price = close
            sl_price = entry_price - risk_dist
            tp_price = entry_price + (target_rr * risk_dist)
            
            return {
                "strategy": "Trend_Pullback_Confluence",
                "direction": "LONG",
                "timeframe": timeframe,
                "entry_price": entry_price,
                "sl_price": round(sl_price, 6 if close < 1 else 2),
                "tp_price": round(tp_price, 6 if close < 1 else 2),
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Structured Bullish Trend Pullback",
                    "reason": f"Retracement into EMA20/50 support band on {timeframe} with RSI reset & Hurst persistence (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                    "rsi": round(rsi, 1),
                    "rvol": round(rvol, 2),
                    "hurst": round(hurst, 3),
                    "trend_structure": "EMA20 > EMA50 > EMA200",
                    "volatility_atr": round(atr, 4),
                    "timeframe": timeframe,
                    "mtf_alignment": mtf_summary
                }
            }

        # Short: In strong downtrend, price pulled back into EMA20/EMA50 zone, RSI reset (44-62), bearish trigger candle reclaiming below EMA20
        if downtrend and (high >= ema20 * 0.998 or high >= ema50 * 0.998) and (close < open_p) and (close <= ema20 * 1.002) and (rsi_min_short <= rsi <= rsi_max_short) and (rvol >= rvol_min):
            anchor_name = "30m" if timeframe == "5m" else ("1h" if timeframe == "15m" else "4h")
            mtf_summary = {"aligned": True, "entry_tf": timeframe, "anchor_tf": anchor_name, "30m": "N/A", "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_30m = htf_data.get("30m")
                df_1h = htf_data.get("1h", htf_data.get("1hr"))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT", entry_tf=timeframe, df_30m=df_30m)
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "entry_tf": timeframe,
                    "anchor_tf": mtf_ctx["anchor_tf"],
                    "anchor_regime": mtf_ctx["anchor_regime"],
                    "30m": mtf_ctx["30m"],
                    "1h": mtf_ctx["1h"],
                    "4h": mtf_ctx["4h"]
                }

            risk_dist = max(atr_sl_mult * atr, close * min_risk_dist_pct)
            entry_price = close
            sl_price = entry_price + risk_dist
            tp_price = entry_price - (target_rr * risk_dist)
            
            return {
                "strategy": "Trend_Pullback_Confluence",
                "direction": "SHORT",
                "timeframe": timeframe,
                "entry_price": entry_price,
                "sl_price": round(sl_price, 6 if close < 1 else 2),
                "tp_price": round(tp_price, 6 if close < 1 else 2),
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Structured Bearish Trend Pullback",
                    "reason": f"Retracement into EMA20/50 resistance band on {timeframe} with RSI overbought reset (Anchored to {mtf_summary.get('anchor_tf', 'HTF')})",
                    "rsi": round(rsi, 1),
                    "rvol": round(rvol, 2),
                    "hurst": round(hurst, 3),
                    "trend_structure": "EMA20 < EMA50 < EMA200",
                    "volatility_atr": round(atr, 4),
                    "timeframe": timeframe,
                    "mtf_alignment": mtf_summary
                }
            }

        return None

AVAILABLE_STRATEGIES = [
    TrendPullbackConfluence,
    SqueezeMomentumBreakout,
    LiquiditySweepReversal
]
