import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

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
    
    df['swing_high_20'] = df['high'].rolling(window=20).max().shift(1)
    df['swing_low_20'] = df['low'].rolling(window=20).min().shift(1)

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
    **kwargs
) -> tuple[bool, Dict[str, Any]]:
    """
    Evaluate intermediate 1h and macro 4h alignment for a proposed trade direction (required for 15m/30m trades).
    
    For LONG:
      - 1h must NOT be BEARISH (should be BULLISH or NEUTRAL)
      - 4h must NOT be BEARISH (should be BULLISH or NEUTRAL)
    For SHORT:
      - 1h must NOT be BULLISH (should be BEARISH or NEUTRAL)
      - 4h must NOT be BULLISH (should be BEARISH or NEUTRAL)
    """
    if df_1h is None and "df_30m" in kwargs:
        df_1h = kwargs["df_30m"]
        
    t_1h = evaluate_tf_trend(df_1h)
    t_4h = evaluate_tf_trend(df_4h)
    
    context = {
        "tf_1h": t_1h,
        "tf_4h": t_4h,
        "aligned": True,
        "reasons": []
    }
    
    if direction == "LONG":
        if t_1h["is_valid"] and t_1h["regime"] == "BEARISH":
            context["aligned"] = False
            context["reasons"].append(f"1h is BEARISH (Close ${t_1h['close']:.4f} < EMA50 ${t_1h['ema50']:.4f}, RSI {t_1h['rsi']})")
        if t_4h["is_valid"] and t_4h["regime"] == "BEARISH":
            context["aligned"] = False
            context["reasons"].append(f"4h Macro is BEARISH (Close ${t_4h['close']:.4f} < EMA50 ${t_4h['ema50']:.4f}, RSI {t_4h['rsi']})")
    elif direction == "SHORT":
        if t_1h["is_valid"] and t_1h["regime"] == "BULLISH":
            context["aligned"] = False
            context["reasons"].append(f"1h is BULLISH (Close ${t_1h['close']:.4f} > EMA50 ${t_1h['ema50']:.4f}, RSI {t_1h['rsi']})")
        if t_4h["is_valid"] and t_4h["regime"] == "BULLISH":
            context["aligned"] = False
            context["reasons"].append(f"4h Macro is BULLISH (Close ${t_4h['close']:.4f} > EMA50 ${t_4h['ema50']:.4f}, RSI {t_4h['rsi']})")
            
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
        htf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a candle and return a trade order dict if triggered."""
        raise NotImplementedError

class SqueezeMomentumBreakout(StrategyBase):
    name = "Squeeze_Momentum_Breakout"
    description = "Trades volatility expansion out of compressed Bollinger Bands inside Keltner Channels with volume confirmation, RSI corridor protection, and 1h/4h MTF alignment."

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.0,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

        p = params or {}
        rvol_min = p.get("rvol_min", 1.15)
        atr_sl_mult = p.get("atr_sl_mult", 1.40)
        rsi_min_long = p.get("rsi_min_long", 50.0)
        rsi_max_long = p.get("rsi_max_long", 68.0)
        rsi_min_short = p.get("rsi_min_short", 32.0)
        rsi_max_short = p.get("rsi_max_short", 50.0)
        min_body_ratio = p.get("min_body_ratio", 0.25)
        max_wick_ratio = p.get("max_wick_ratio", 0.50)
        min_risk_dist_pct = p.get("min_risk_dist_pct", 0.008)

        curr = df.iloc[idx]
        
        # Check if squeeze was active recently and just fired off
        recent_squeezes = df['squeeze_on'].iloc[max(0, idx - 5):idx].sum()
        squeeze_fired = (recent_squeezes >= 2) and (not curr['squeeze_on'])
        
        if not squeeze_fired:
            return None

        close = float(curr['close'])
        open_p = float(curr['open'])
        high = float(curr['high'])
        low = float(curr['low'])
        atr = float(curr['atr14'])
        ema50 = float(curr['ema50'])
        rvol = float(curr['rvol'])
        rsi = float(curr['rsi14'])
        mom = float(curr['momentum'])
        
        if atr <= 0:
            return None

        total_range = max(high - low, 1e-6)
        risk_dist = max(atr_sl_mult * atr, close * min_risk_dist_pct)

        # Long Setup: Squeeze release + Bullish Breakout + Volume expansion + Bullish Regime + Safe RSI Corridor + Solid Body
        if close > curr['bb_upper'] and mom > 0 and rvol >= rvol_min and close > ema50 and (rsi_min_long <= rsi <= rsi_max_long):
            # Check 1h & 4h Multi-Timeframe Alignment
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            body = close - open_p
            upper_wick = high - close
            
            # Reject wick traps and dojis (ensure strong directional body closing near highs)
            if body > 0 and (body / total_range) >= min_body_ratio and (upper_wick / total_range) <= max_wick_ratio:
                entry_price = close
                sl_price = entry_price - risk_dist
                tp_price = entry_price + (target_rr * risk_dist)
                
                return {
                    "strategy": "Squeeze_Momentum_Breakout",
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "sl_price": sl_price,
                    "tp_price": tp_price,
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Bullish Trend & Volatility Expansion",
                        "reason": "Squeeze fired bullishly above BB upper band with volume surge and strong candle body",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "momentum": round(mom, 4),
                        "ema_alignment": "Close > EMA50",
                        "body_ratio": round(body / total_range, 2),
                        "volatility_atr": round(atr, 4),
                        "mtf_alignment": mtf_summary
                    }
                }

        # Short Setup: Squeeze release + Bearish Breakdown + Volume expansion + Bearish Regime + Safe RSI Corridor + Solid Body
        if close < curr['bb_lower'] and mom < 0 and rvol >= rvol_min and close < ema50 and (rsi_min_short <= rsi <= rsi_max_short):
            # Check 1h & 4h Multi-Timeframe Alignment
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            body = open_p - close
            lower_wick = close - low
            
            # Reject wick traps and dojis (ensure strong directional body closing near lows)
            if body > 0 and (body / total_range) >= min_body_ratio and (lower_wick / total_range) <= max_wick_ratio:
                entry_price = close
                sl_price = entry_price + risk_dist
                tp_price = entry_price - (target_rr * risk_dist)
                
                return {
                    "strategy": "Squeeze_Momentum_Breakout",
                    "direction": "SHORT",
                    "entry_price": entry_price,
                    "sl_price": sl_price,
                    "tp_price": tp_price,
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Bearish Trend & Volatility Breakdown",
                        "reason": "Squeeze fired bearishly below BB lower band with volume surge and strong candle body",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "momentum": round(mom, 4),
                        "ema_alignment": "Close < EMA50",
                        "body_ratio": round(body / total_range, 2),
                        "volatility_atr": round(atr, 4),
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
        htf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[Dict[str, Any]]:
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
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            lower_wick = min(open_p, close) - low
            body = abs(close - open_p)
            if lower_wick >= 1.0 * body and rvol >= rvol_min:  # Valid rejection wick
                risk_dist = max(atr * 1.2, (close - low) * 1.15, close * min_risk_dist_pct)
                entry_price = close
                sl_price = entry_price - risk_dist
                tp_price = entry_price + (target_rr * risk_dist)
                
                return {
                    "strategy": "Liquidity_Sweep_Reversal",
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "sl_price": sl_price,
                    "tp_price": tp_price,
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Liquidity Hunt Reversal (Bull Trap Clearance)",
                        "reason": f"Price pierced 20-bar swing low ({round(swing_low, 4)}) and rejected aggressively with lower wick",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "lower_wick_ratio": round(lower_wick / (body + 1e-6), 2),
                        "volatility_atr": round(atr, 4),
                        "mtf_alignment": mtf_summary
                    }
                }

        # Short: Sweep of swing high, closing with bearish rejection wick and non-oversold RSI
        if high > swing_high and close < swing_high and close < open_p and rsi >= 45.0:
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            upper_wick = high - max(open_p, close)
            body = abs(close - open_p)
            if upper_wick >= 1.0 * body and rvol >= rvol_min:  # Valid rejection wick
                risk_dist = max(atr * 1.2, (high - close) * 1.15, close * min_risk_dist_pct)
                entry_price = close
                sl_price = entry_price + risk_dist
                tp_price = entry_price - (target_rr * risk_dist)
                
                return {
                    "strategy": "Liquidity_Sweep_Reversal",
                    "direction": "SHORT",
                    "entry_price": entry_price,
                    "sl_price": sl_price,
                    "tp_price": tp_price,
                    "risk_distance": risk_dist,
                    "target_rr": target_rr,
                    "pre_trade_context": {
                        "regime": "Liquidity Hunt Reversal (Bear Trap Clearance)",
                        "reason": f"Price swept 20-bar swing high ({round(swing_high, 4)}) and rejected aggressively with upper wick",
                        "rvol": round(rvol, 2),
                        "rsi": round(rsi, 1),
                        "upper_wick_ratio": round(upper_wick / (body + 1e-6), 2),
                        "volatility_atr": round(atr, 4),
                        "mtf_alignment": mtf_summary
                    }
                }

        return None

class TrendPullbackConfluence(StrategyBase):
    name = "Trend_Pullback_Confluence"
    description = "Enters on high-probability pullbacks to EMA20/EMA50 value zones within established higher-timeframe trends."

    @staticmethod
    def generate_signal(
        df: pd.DataFrame, 
        idx: int, 
        target_rr: float = 2.0,
        params: Optional[Dict[str, Any]] = None,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

        p = params or {}
        min_risk_dist_pct = p.get("min_risk_dist_pct", 0.008)

        curr = df.iloc[idx]
        
        close = float(curr['close'])
        open_p = float(curr['open'])
        low = float(curr['low'])
        high = float(curr['high'])
        ema20 = float(curr['ema20'])
        ema50 = float(curr['ema50'])
        ema200 = float(curr['ema200'])
        atr = float(curr['atr14'])
        rsi = float(curr['rsi14'])
        rvol = float(curr['rvol'])

        if atr <= 0:
            return None

        # Uptrend Condition: EMA20 > EMA50 > EMA200
        uptrend = (ema20 > ema50) and (ema50 > ema200) and (close > ema200)
        # Downtrend Condition: EMA20 < EMA50 < EMA200
        downtrend = (ema20 < ema50) and (ema50 < ema200) and (close < ema200)

        # Long: In strong uptrend, price pulled back into EMA20/EMA50 zone, RSI cooled off (38-55), bullish trigger candle
        if uptrend and (low <= ema20 or low <= ema50) and (close > open_p) and (38.0 <= rsi <= 55.0):
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "LONG")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            risk_dist = max(1.4 * atr, close * min_risk_dist_pct)
            entry_price = close
            sl_price = entry_price - risk_dist
            tp_price = entry_price + (target_rr * risk_dist)
            
            return {
                "strategy": "Trend_Pullback_Confluence",
                "direction": "LONG",
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Structured Bullish Trend Pullback",
                    "reason": "Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation",
                    "rsi": round(rsi, 1),
                    "rvol": round(rvol, 2),
                    "trend_structure": "EMA20 > EMA50 > EMA200",
                    "volatility_atr": round(atr, 4),
                    "mtf_alignment": mtf_summary
                }
            }

        # Short: In strong downtrend, price pulled back into EMA20/EMA50 zone, RSI bounced (45-62), bearish trigger candle
        if downtrend and (high >= ema20 or high >= ema50) and (close < open_p) and (45.0 <= rsi <= 62.0):
            mtf_summary = {"aligned": True, "1h": "N/A", "4h": "N/A"}
            if htf_data:
                df_1h = htf_data.get("1h", htf_data.get("1hr", htf_data.get("30m")))
                df_4h = htf_data.get("4h", htf_data.get("4hr"))
                aligned, mtf_ctx = evaluate_mtf_alignment(df_1h, df_4h, "SHORT")
                if not aligned:
                    return None
                mtf_summary = {
                    "aligned": True,
                    "1h": mtf_ctx["tf_1h"]["regime"],
                    "4h": mtf_ctx["tf_4h"]["regime"]
                }

            risk_dist = max(1.4 * atr, close * min_risk_dist_pct)
            entry_price = close
            sl_price = entry_price + risk_dist
            tp_price = entry_price - (target_rr * risk_dist)
            
            return {
                "strategy": "Trend_Pullback_Confluence",
                "direction": "SHORT",
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Structured Bearish Trend Pullback",
                    "reason": "Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation",
                    "rsi": round(rsi, 1),
                    "rvol": round(rvol, 2),
                    "trend_structure": "EMA20 < EMA50 < EMA200",
                    "volatility_atr": round(atr, 4),
                    "mtf_alignment": mtf_summary
                }
            }

        return None

AVAILABLE_STRATEGIES = [
    SqueezeMomentumBreakout,
    LiquiditySweepReversal,
    TrendPullbackConfluence
]
