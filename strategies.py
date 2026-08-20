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

class StrategyBase:
    name: str = "BaseStrategy"
    description: str = ""

    @staticmethod
    def generate_signal(df: pd.DataFrame, idx: int, target_rr: float = 2.0) -> Optional[Dict[str, Any]]:
        """Evaluate a candle and return a trade order dict with strict 1:3 RR if triggered."""
        raise NotImplementedError

class SqueezeMomentumBreakout(StrategyBase):
    name = "Squeeze_Momentum_Breakout"
    description = "Trades volatility expansion out of compressed Bollinger Bands inside Keltner Channels with volume confirmation."

    @staticmethod
    def generate_signal(df: pd.DataFrame, idx: int, target_rr: float = 2.0) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # Check if squeeze was active recently and just fired off
        recent_squeezes = df['squeeze_on'].iloc[max(0, idx - 5):idx].sum()
        squeeze_fired = (recent_squeezes >= 2) and (not curr['squeeze_on'])
        
        if not squeeze_fired:
            return None

        close = float(curr['close'])
        open_p = float(curr['open'])
        atr = float(curr['atr14'])
        ema50 = float(curr['ema50'])
        ema200 = float(curr['ema200'])
        rvol = float(curr['rvol'])
        rsi = float(curr['rsi14'])
        mom = float(curr['momentum'])
        
        if atr <= 0:
            return None

        # Long Setup: Squeeze release + Bullish Breakout + Volume expansion + Bullish Regime
        if close > curr['bb_upper'] and mom > 0 and rvol >= 1.1 and close > ema50 and rsi > 50:
            risk_dist = 1.3 * atr
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
                    "reason": "Squeeze fired bullishly above BB upper band with volume surge",
                    "rvol": round(rvol, 2),
                    "rsi": round(rsi, 1),
                    "momentum": round(mom, 4),
                    "ema_alignment": "Close > EMA50" if close > ema50 else "Counter-EMA50",
                    "volatility_atr": round(atr, 4)
                }
            }

        # Short Setup: Squeeze release + Bearish Breakdown + Volume expansion + Bearish Regime
        if close < curr['bb_lower'] and mom < 0 and rvol >= 1.1 and close < ema50 and rsi < 50:
            risk_dist = 1.3 * atr
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
                    "reason": "Squeeze fired bearishly below BB lower band with volume surge",
                    "rvol": round(rvol, 2),
                    "rsi": round(rsi, 1),
                    "momentum": round(mom, 4),
                    "ema_alignment": "Close < EMA50" if close < ema50 else "Counter-EMA50",
                    "volatility_atr": round(atr, 4)
                }
            }

        return None

class LiquiditySweepReversal(StrategyBase):
    name = "Liquidity_Sweep_Reversal"
    description = "Captures false breakout traps where price sweeps previous 20-bar swing highs/lows and aggressively rejects."

    @staticmethod
    def generate_signal(df: pd.DataFrame, idx: int, target_rr: float = 2.0) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

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

        # Long: Sweep of swing low, closing with bullish rejection wick
        if low < swing_low and close > swing_low and close > open_p:
            lower_wick = min(open_p, close) - low
            body = abs(close - open_p)
            if lower_wick >= 1.0 * body and rvol >= 1.05:  # Valid rejection wick
                risk_dist = max(atr * 1.0, (close - low) * 1.1)
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
                        "volatility_atr": round(atr, 4)
                    }
                }

        # Short: Sweep of swing high, closing with bearish rejection wick
        if high > swing_high and close < swing_high and close < open_p:
            upper_wick = high - max(open_p, close)
            body = abs(close - open_p)
            if upper_wick >= 1.0 * body and rvol >= 1.05:  # Valid rejection wick
                risk_dist = max(atr * 1.0, (high - close) * 1.1)
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
                        "volatility_atr": round(atr, 4)
                    }
                }

        return None

class TrendPullbackConfluence(StrategyBase):
    name = "Trend_Pullback_Confluence"
    description = "Enters on high-probability pullbacks to EMA20/EMA50 value zones within established higher-timeframe trends."

    @staticmethod
    def generate_signal(df: pd.DataFrame, idx: int, target_rr: float = 2.0) -> Optional[Dict[str, Any]]:
        if idx < 50:
            return None

        curr = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
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

        # Long: In strong uptrend, price pulled back into EMA20/EMA50 zone, RSI cooled off (35-50), bullish trigger candle
        if uptrend and (low <= ema20 or low <= ema50) and (close > open_p) and (35 <= rsi <= 52):
            risk_dist = 1.4 * atr
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
                    "volatility_atr": round(atr, 4)
                }
            }

        # Short: In strong downtrend, price pulled back into EMA20/EMA50 zone, RSI bounced (48-65), bearish trigger candle
        if downtrend and (high >= ema20 or high >= ema50) and (close < open_p) and (48 <= rsi <= 65):
            risk_dist = 1.4 * atr
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
                    "volatility_atr": round(atr, 4)
                }
            }

        return None

AVAILABLE_STRATEGIES = [
    SqueezeMomentumBreakout,
    LiquiditySweepReversal,
    TrendPullbackConfluence
]
