"""Pure paper execution rules and fill accounting shared by live and replay.

Prices are modeled fills, not exchange executions. Slippage is applied to each
fill price once; its separately reported amount must not be deducted again.
"""
from math import isfinite
from typing import Any, Dict, Optional


SCHEMA_VERSION = 2
COST_MODEL_VERSION = "fills_v1"

# Paper-bot baseline. All execution adapters use the same candle thresholds.
EXIT_TIMEFRAME_PROFILES = {
    "5m": {"stagnation_bars": 18, "max_holding_bars": 64},
    "15m": {"stagnation_bars": 16, "max_holding_bars": 64},
    "30m": {"stagnation_bars": 16, "max_holding_bars": 64},
}


def _positive(value: float, name: str) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def _event(pos: Dict[str, Any], start: int) -> Dict[str, Any]:
    fills = pos["fills"][start:]
    return {
        "fills": fills,
        "cash_delta_usd": sum(f["cash_delta_usd"] for f in fills),
        "closed": pos["closed"],
        "exit_reason": pos.get("exit_reason"),
    }


def _fill(pos, reference_price, quantity, timestamp, kind, reason):
    reference_price = _positive(reference_price, "reference_price")
    quantity = min(float(quantity), pos["position_qty"]) if kind != "ENTRY" else float(quantity)
    if quantity <= 0:
        return
    sign = 1.0 if pos["direction"] == "LONG" else -1.0
    buy = (sign > 0) if kind == "ENTRY" else (sign < 0)
    price = reference_price * (1.0 + (1.0 if buy else -1.0) * pos["slippage_pct"] / 100.0)
    fee = quantity * price * pos["fee_pct"] / 100.0
    gross = 0.0 if kind == "ENTRY" else sign * (price - pos["entry_price"]) * quantity
    fill = {
        "fill_id": len(pos["fills"]) + 1,
        "kind": kind, "reason": reason, "timestamp": float(timestamp),
        "reference_price": reference_price, "price": price,
        "quantity": quantity, "side": "BUY" if buy else "SELL",
        "notional_usd": quantity * price, "gross_pnl_usd": gross,
        "fee_usd": fee, "slippage_usd": quantity * abs(price - reference_price),
        "cash_delta_usd": gross - fee,
    }
    pos["fills"].append(fill)
    pos["realized_gross_usd"] += gross
    pos["fees_usd"] += fee
    pos["slippage_usd"] += fill["slippage_usd"]
    pos["cash_pnl_usd"] += fill["cash_delta_usd"]
    if kind == "ENTRY":
        pos["entry_price"] = price
        pos["entry_cash_delta_usd"] = -fee
    else:
        pos["position_qty"] = max(0.0, pos["position_qty"] - quantity)
        pos["realized_partial_r"] = pos["realized_gross_usd"] / pos["risk_amount_usd"]
        if pos["position_qty"] <= pos["initial_qty"] * 1e-12:
            pos["position_qty"] = 0.0
            pos["closed"] = True
            pos["exit_reason"] = reason
            pos["exit_price"] = price
            pos["exit_time"] = float(timestamp)


def create_position(direction, reference_price, risk_distance, risk_amount_usd,
                    target_rr, timestamp, fee_pct=0.05, slippage_pct=0.02) -> Dict[str, Any]:
    direction = str(direction).upper()
    if direction not in ("LONG", "SHORT"):
        raise ValueError("direction must be LONG or SHORT")
    reference_price = _positive(reference_price, "reference_price")
    risk_distance = _positive(risk_distance, "risk_distance")
    risk_amount_usd = _positive(risk_amount_usd, "risk_amount_usd")
    target_rr = _positive(target_rr, "target_rr")
    for name, value in (("fee_pct", fee_pct), ("slippage_pct", slippage_pct)):
        if not isfinite(float(value)) or float(value) < 0 or float(value) >= 100:
            raise ValueError(f"{name} must be between 0 and 100 percent")
    qty = risk_amount_usd / risk_distance
    pos = {
        "schema_version": SCHEMA_VERSION, "cost_model_version": COST_MODEL_VERSION,
        "direction": direction, "reference_entry_price": reference_price,
        "entry_price": reference_price, "entry_time": float(timestamp),
        "original_risk_distance": risk_distance, "risk_distance": risk_distance,
        "risk_amount_usd": risk_amount_usd, "initial_qty": qty, "position_qty": qty,
        "fee_pct": float(fee_pct), "slippage_pct": float(slippage_pct),
        "target_rr": target_rr, "tp1_rr": 1.0 if target_rr <= 2.0 else 1.5,
        "fills": [], "realized_gross_usd": 0.0, "fees_usd": 0.0,
        "slippage_usd": 0.0, "cash_pnl_usd": 0.0, "closed": False,
        "tp1_hit": False, "is_breakeven_protected": False, "is_breakeven": False,
        "is_profit_locked": False, "is_trailing": False, "is_unlimited_runner": False,
        "realized_partial_r": 0.0, "mfe_r": 0.0, "mae_r": 0.0, "bars_held": 0,
        "last_observation_time": float(timestamp), "last_observation_price": reference_price,
        "last_processed_bar_time": None,
    }
    _fill(pos, reference_price, qty, timestamp, "ENTRY", "ENTRY")
    entry = pos["entry_price"]
    sign = 1.0 if direction == "LONG" else -1.0
    pos.update({
        "initial_sl_price": entry - sign * risk_distance,
        "sl_price": entry - sign * risk_distance,
        "tp1_price": entry + sign * pos["tp1_rr"] * risk_distance,
        "tp_price": entry + sign * target_rr * risk_distance,
        "highest_since_entry": entry, "lowest_since_entry": entry,
        "current_price": reference_price, "stop_activated_at": float(timestamp),
    })
    if min(pos["sl_price"], pos["tp1_price"], pos["tp_price"]) <= 0:
        raise ValueError("stop and target prices must be positive")
    return pos


def close_position(pos, reference_price, timestamp, reason="MANUAL_CLOSE") -> Dict[str, Any]:
    start = len(pos["fills"])
    if not pos["closed"]:
        _fill(pos, reference_price, pos["position_qty"], timestamp, "EXIT", reason)
    return _event(pos, start)


def _excursion(pos, high, low):
    pos["highest_since_entry"] = max(pos["highest_since_entry"], float(high))
    pos["lowest_since_entry"] = min(pos["lowest_since_entry"], float(low))
    entry, risk = pos["entry_price"], pos["original_risk_distance"]
    if pos["direction"] == "LONG":
        fav, adv = pos["highest_since_entry"] - entry, entry - pos["lowest_since_entry"]
    else:
        fav, adv = entry - pos["lowest_since_entry"], pos["highest_since_entry"] - entry
    pos["mfe_r"] = max(pos["mfe_r"], fav / risk, 0.0)
    pos["mae_r"] = max(pos["mae_r"], adv / risk, 0.0)


def _stop_hit(pos, price):
    return price <= pos["sl_price"] if pos["direction"] == "LONG" else price >= pos["sl_price"]


def _stop_reason(pos):
    return "PROTECTED_STOP" if pos["sl_price"] != pos["initial_sl_price"] else "STOP_LOSS"


def _targets(pos, favorable_price, timestamp):
    is_long = pos["direction"] == "LONG"
    reached = lambda target: favorable_price >= target if is_long else favorable_price <= target
    if not pos["tp1_hit"] and reached(pos["tp1_price"]):
        _fill(pos, pos["tp1_price"], pos["initial_qty"] * 0.5, timestamp, "TP1", "TP1")
        pos["tp1_hit"] = True
    # Standing targets take precedence over a runner mode inferred from this observation.
    if not pos["is_unlimited_runner"] and reached(pos["tp_price"]):
        close_position(pos, pos["tp_price"], timestamp, "TAKE_PROFIT")


def _protect_and_time_exit(pos, price, timestamp, atr, momentum, rsi,
                           stagnation_bars, max_holding_bars):
    if pos["closed"]:
        return
    sign = 1.0 if pos["direction"] == "LONG" else -1.0
    entry, risk, mfe = pos["entry_price"], pos["original_risk_distance"], pos["mfe_r"]
    atr = risk if atr is None or not isfinite(float(atr)) or float(atr) <= 0 else float(atr)
    stop = pos["sl_price"]
    candidate = stop
    improve = max if sign > 0 else min
    if mfe >= (0.8 if pos["target_rr"] <= 2.0 else 1.0):
        pos["is_breakeven_protected"] = pos["is_breakeven"] = True
        candidate = improve(candidate, entry + sign * 0.15 * risk)
    if pos["tp1_hit"]:
        pos["is_profit_locked"] = True
        candidate = improve(candidate, entry + sign * 0.5 * risk)
    if 2.2 <= mfe < 3.5:
        pos["is_trailing"] = True
        candidate = improve(candidate, entry + sign * 1.5 * risk, price - sign * atr)
    if mfe >= 3.5:
        pos["is_unlimited_runner"] = True
        candidate = improve(candidate, entry + sign * 2.5 * risk, price - sign * 0.8 * atr)
    if candidate != stop:
        pos["sl_price"] = candidate
        pos["stop_activated_at"] = float(timestamp)
        # Activation is not an execution observation. Even if this candle's
        # close is beyond the new stop, wait for the next observed price/open.
    if mfe >= 1.0 and ((sign > 0 and momentum < 0 and rsi >= 72.0) or
                       (sign < 0 and momentum > 0 and rsi <= 28.0)):
        close_position(pos, price, timestamp, "MOMENTUM_EXIT")
        return
    unrealized_r = sign * (price - entry) / risk
    if (pos["bars_held"] >= stagnation_bars and abs(unrealized_r) < 0.25
            and mfe < 0.8 and not pos["tp1_hit"] and sign * momentum < 0):
        close_position(pos, price, timestamp, "TIME_EXIT")
    elif (pos["bars_held"] >= max_holding_bars and not pos["is_unlimited_runner"]
          and not (pos["is_profit_locked"] and mfe >= 1.5)):
        close_position(pos, price, timestamp, "MAX_HOLD")


def process_price(pos, price, timestamp, atr=None, momentum=0.0, rsi=50.0,
                  completed_bars=0, stagnation_bars=16, max_holding_bars=64) -> Dict[str, Any]:
    """Consume a chronological observed price; completed_bars is an absolute count."""
    start = len(pos["fills"])
    price = _positive(price, "price")
    timestamp = float(timestamp)
    if pos["closed"] or timestamp < pos["last_observation_time"]:
        return _event(pos, start)
    if (timestamp == pos["last_observation_time"] and price == pos["last_observation_price"]
            and completed_bars <= pos["bars_held"]):
        return _event(pos, start)
    pos["bars_held"] = max(pos["bars_held"], int(completed_bars))
    pos["last_observation_time"], pos["last_observation_price"] = timestamp, price
    pos["current_price"] = price
    _excursion(pos, price, price)
    if _stop_hit(pos, price):
        close_position(pos, price, timestamp, _stop_reason(pos))
    else:
        _targets(pos, price, timestamp)
        _protect_and_time_exit(pos, price, timestamp, atr, float(momentum), float(rsi),
                               stagnation_bars, max_holding_bars)
    return _event(pos, start)


def process_bar(pos, bar, timestamp=None, completed_bars=0,
                stagnation_bars=16, max_holding_bars=64) -> Dict[str, Any]:
    """Replay a completed OHLC bar, with existing stop priority when ambiguous.

Only call for bars whose entire interval follows the last consumed observation.
Trailing changes based on this bar apply only to subsequent observations.
"""
    start = len(pos["fills"])
    bar_time = float(bar.get("time", timestamp if timestamp is not None else 0))
    timestamp = float(timestamp if timestamp is not None else bar.get("close_time", bar_time))
    previous_bar = pos.get("last_processed_bar_time")
    if (pos["closed"] or (previous_bar is not None and bar_time <= previous_bar)
            or bar_time < pos["last_observation_time"]):
        return _event(pos, start)
    opening, high, low, close = [_positive(bar[k], k) for k in ("open", "high", "low", "close")]
    if low > min(opening, close) or high < max(opening, close) or high < low:
        raise ValueError("invalid OHLC bar")
    pos["bars_held"] = max(pos["bars_held"], int(completed_bars))
    pos["last_processed_bar_time"] = bar_time
    pos["last_observation_time"], pos["last_observation_price"] = timestamp, close
    pos["current_price"] = close
    adverse = low if pos["direction"] == "LONG" else high
    if _stop_hit(pos, opening):
        _excursion(pos, opening, opening)
        close_position(pos, opening, bar_time, _stop_reason(pos))
    else:
        # The open is known to precede both extremes; a gap through a standing
        # target cannot be retroactively beaten by a later low/high.
        _excursion(pos, opening, opening)
        _targets(pos, opening, bar_time)
        if not pos["closed"]:
            if _stop_hit(pos, adverse):
                stop = pos["sl_price"]
                _excursion(pos, max(opening, stop), min(opening, stop))
                close_position(pos, stop, timestamp, _stop_reason(pos))
            else:
                _excursion(pos, high, low)
                favorable = high if pos["direction"] == "LONG" else low
                _targets(pos, favorable, timestamp)
                _protect_and_time_exit(pos, close, timestamp, bar.get("atr14"),
                                       float(bar.get("momentum", 0.0)), float(bar.get("rsi14", 50.0)),
                                       stagnation_bars, max_holding_bars)
    return _event(pos, start)


def summarize_position(pos) -> Dict[str, Any]:
    gross = float(pos["realized_gross_usd"])
    net = float(pos["cash_pnl_usd"])
    risk = pos["risk_amount_usd"]
    result = dict(pos)
    result.update({
        "gross_pnl_usd": gross, "pnl_usd": net, "raw_r": gross / risk,
        "net_r": net / risk, "remaining_qty": pos["position_qty"],
        "outcome": "WIN" if net > 1e-9 else ("LOSS" if net < -1e-9 else "BE_EXIT"),
        "friction_breakdown": f"Gross: {gross / risk:+.4f}R | Fees: -{pos['fees_usd'] / risk:.4f}R | Net: {net / risk:+.4f}R",
    })
    return result
