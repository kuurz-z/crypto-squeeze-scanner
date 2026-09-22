"""Explicit completed-history fixtures for indicator-isolated strategy tests."""
import pandas as pd

from data_loader import ANCHOR_TIMEFRAMES, interval_seconds


def _completed_fixture(frame, timeframe, decision_time, count=200):
    """Extend the supplied indicator fixture into the past, never into its future."""
    frame = frame.copy().reset_index(drop=True)
    if len(frame) < count:
        prefix = pd.concat([frame.iloc[:1]] * (count - len(frame)), ignore_index=True)
        frame = pd.concat([prefix, frame], ignore_index=True)
    duration = interval_seconds(timeframe)
    final_open = int(decision_time // duration) * duration - duration
    frame["time"] = [final_open - (len(frame) - 1 - index) * duration for index in range(len(frame))]
    frame["close_time"] = frame["time"] + duration - .001
    return frame


def anchors_for(decision_time, timeframe="15m", supplied=None):
    anchor_tf = ANCHOR_TIMEFRAMES[timeframe]
    if supplied is None:
        # Deliberately neutral: directional filtering is exercised by tests that
        # explicitly supply bullish or bearish anchors.
        supplied = {anchor_tf: pd.DataFrame({"open": [100.0], "high": [101.0],
                    "low": [99.0], "close": [100.0], "volume": [1000.0],
                    "ema50": [99.0], "ema200": [99.0], "rsi14": [45.0], "momentum": [0.0]})}
    return {tf: _completed_fixture(frame, tf, decision_time) for tf, frame in supplied.items()}


def signal_with_history(strategy, frame, idx, target_rr=3.5, params=None,
                        htf_data=None, timeframe="15m", **kwargs):
    """Keep the test's engineered indicator values, with valid causal context."""
    duration = interval_seconds(timeframe)
    decision_time = int(float(frame.iloc[idx]["time"]) // duration) * duration + duration
    prepared = _completed_fixture(frame.iloc[:idx + 1], timeframe, decision_time)
    # These tests isolate indicator predicates; omitted derived features are
    # explicit ordinary-regime fixture values rather than a recomputation that
    # would overwrite the feature under test.
    for column, value in {"hurst": .56, "bb_width_percentile": 20.0,
                          "atr_expansion": 1.2, "adx14": 28.0}.items():
        if column not in prepared:
            prepared[column] = value
    if "ema20" not in prepared:
        prepared["ema20"] = prepared["close"]
    return strategy.generate_signal(prepared, len(prepared) - 1, target_rr=target_rr,
        params=params, htf_data=anchors_for(decision_time, timeframe, htf_data),
        timeframe=timeframe, decision_time=decision_time, **kwargs)


def simulation_fixture(path, timeframe="15m"):
    """200 warmup bars followed by valid (open, high, low, close) replay bars."""
    duration = interval_seconds(timeframe)
    base = 1767225600
    rows = [(100.0, 100.5, 99.5, 100.0)] * 200 + list(path)
    result = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    result["time"] = [base + index * duration for index in range(len(result))]
    result["close_time"] = result["time"] + duration - .001
    result["volume"] = 1000.0
    for name, value in {"hurst": .56, "ema20": 100.0, "atr14": 1.0,
                        "rvol": 1.5, "bb_width_percentile": 20.0,
                        "momentum": 0.0, "rsi14": 50.0}.items():
        result[name] = value
    return result, anchors_for(base + 200 * duration, timeframe)
