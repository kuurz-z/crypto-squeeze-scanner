"""Report-only chronological strategy research with a consumed holdout ledger.

The candidate grid is frozen before any scoring. Every symbol and timeframe
shares UTC boundaries. The final window is spent once, even if a later call
requests different parameters, symbols, or optimizer modes.
"""
import asyncio
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Dict, Optional

import aiohttp
import pandas as pd

from data_loader import (ANCHOR_TIMEFRAMES, INDICATOR_WARMUP, completed_candles,
                         fetch_symbol_klines, fetch_top_crypto_pairs, interval_seconds)
from strategies import AVAILABLE_STRATEGIES, compute_crypto_indicators
from strategy_memory import evaluate_reproducibility
from sim_engine import compile_simulation_metrics, simulate_strategy_on_dataframe

VALIDATION_VERSION = "chronological_60_20_20_execution_v2"
DEFAULT_INCUMBENT = {"strategy": "Trend_Pullback_Confluence", "timeframe": "15m",
                     "params": {}, "target_rr": 2.0, "fee_pct": 0.05, "slippage_pct": 0.02}
_evaluation_locks: Dict[str, asyncio.Lock] = {}


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temp_path = stream.name
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def _candidate(strategy: str, timeframe: str, params: dict, target_rr: float,
               fee_pct: float = 0.05, slippage_pct: float = 0.02) -> dict:
    config = {"strategy": strategy, "timeframe": timeframe,
              "params": copy.deepcopy(params), "target_rr": float(params.get("target_rr", target_rr)),
              "fee_pct": float(fee_pct), "slippage_pct": float(slippage_pct)}
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
    return {"candidate_id": digest, **config}


def freeze_candidates(mode: str, incumbent: dict, timeframes=None) -> list:
    """A fixed small parameter grid, never derived from holdout/live losses."""
    frames = list(timeframes or ([incumbent["timeframe"]] if mode == "micro" else ANCHOR_TIMEFRAMES))
    if incumbent["timeframe"] not in frames:
        frames.append(incumbent["timeframe"])
    if any(tf not in ANCHOR_TIMEFRAMES for tf in frames):
        raise ValueError("Research entry timeframes must be 5m, 15m, or 30m")
    names = ([s.name for s in AVAILABLE_STRATEGIES]
             if mode in ("monthly", "cli") else [incumbent["strategy"]])
    candidates = {}
    costs = {"fee_pct": incumbent.get("fee_pct", 0.05), "slippage_pct": incumbent.get("slippage_pct", 0.02)}
    base = _candidate(incumbent["strategy"], incumbent["timeframe"], incumbent.get("params", {}), incumbent["target_rr"], **costs)
    candidates[base["candidate_id"]] = base
    for name in names:
        for tf in frames:
            params = copy.deepcopy(incumbent.get("params", {})) if name == incumbent["strategy"] else {}
            for atr_delta in (0.0, 0.2, 0.4):
                for volume_delta in (0.0, 0.15):
                    candidate_params = {**params,
                        "atr_sl_mult": round(float(params.get("atr_sl_mult", 2.2)) + atr_delta, 4),
                        "rvol_min": round(float(params.get("rvol_min", 1.25 if name == "Trend_Pullback_Confluence" else 1.6)) + volume_delta, 4),
                        "target_rr": incumbent["target_rr"]}
                    item = _candidate(name, tf, candidate_params, incumbent["target_rr"], **costs)
                    candidates[item["candidate_id"]] = item
    return list(candidates.values())


def common_boundaries(datasets: dict, htf_datasets: dict, symbols: list,
                      timeframes: list, requested_start: int, requested_end: int) -> dict:
    """Intersect actual coverage after indicator warmup, then share one split."""
    start, end = float(requested_start), float(requested_end)
    for symbol in symbols:
        for tf in timeframes:
            for frame, interval in ((datasets[tf][symbol], tf),
                                    (htf_datasets[symbol][ANCHOR_TIMEFRAMES[tf]], ANCHOR_TIMEFRAMES[tf])):
                clean = completed_candles(frame, interval, requested_end)
                if len(clean) < INDICATOR_WARMUP:
                    raise ValueError(f"Insufficient warmup for {symbol} {interval}")
                start = max(start, float(clean.iloc[INDICATOR_WARMUP - 1]["close_time"]) + 0.001)
                end = min(end, float(clean.iloc[-1]["close_time"]) + 0.001)
    # Each boundary is also a 30m candle boundary for all supported entry TFs.
    duration = 1800
    start = math.ceil(start / duration) * duration
    end = math.floor(end / duration) * duration
    span = end - start
    train_end = start + math.floor(span * 0.6 / duration) * duration
    validation_end = start + math.floor(span * 0.8 / duration) * duration
    if not (start < train_end < validation_end < end):
        raise ValueError("Not enough common chronological coverage after warmup")
    return {"train": [start, train_end], "validation": [train_end, validation_end],
            "final_test": [validation_end, end], "timezone": "UTC"}


def _summary(metrics: dict) -> dict:
    result = {key: value for key, value in metrics.items() if key != "trades"}
    for key, value in list(result.items()):
        if isinstance(value, float) and not math.isfinite(value):
            result[key] = None
    return result


def _evaluate(candidate: dict, window: list, datasets: dict, htf_datasets: dict,
              symbols: list) -> dict:
    strategy = next(s for s in AVAILABLE_STRATEGIES if s.name == candidate["strategy"])
    trades = []
    for symbol in symbols:
        tf = candidate["timeframe"]
        result = simulate_strategy_on_dataframe(
            datasets[tf][symbol], strategy, target_rr=candidate["target_rr"],
            params=candidate["params"], timeframe=tf, htf_data=htf_datasets[symbol],
            window_start=window[0], window_end=window[1],
            fee_pct=candidate.get("fee_pct", 0.05), slippage_pct=candidate.get("slippage_pct", 0.02),
        )
        trades.extend(result.get("trades", []))
    metrics = compile_simulation_metrics(trades, candidate["strategy"], candidate["target_rr"])
    metrics["window_end_trades"] = sum(t.get("exit_reason", t.get("outcome")) == "WINDOW_END" for t in trades)
    metrics["window_end_net_r"] = round(sum(float(t.get("net_r", 0)) for t in trades
        if t.get("exit_reason", t.get("outcome")) == "WINDOW_END"), 8)
    return _summary(metrics)


async def _fetch_history(symbols, timeframes, start, end):
    datasets = {tf: {} for tf in timeframes}
    anchors = {symbol: {} for symbol in symbols}
    intervals = sorted(set(timeframes) | {ANCHOR_TIMEFRAMES[tf] for tf in timeframes})
    semaphore = asyncio.Semaphore(10)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        async def fetch(symbol, tf):
            duration = interval_seconds(tf)
            fetch_start = start - INDICATOR_WARMUP * duration
            count = math.ceil((end - fetch_start) / duration)
            async with semaphore:
                result = await fetch_symbol_klines(session, symbol, tf, limit=count,
                                                  start_time=fetch_start, end_time=end)
            return symbol, tf, result
        results = await asyncio.gather(*(fetch(symbol, tf) for symbol in symbols for tf in intervals),
                                       return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            continue
        symbol, tf, frame = result
        if not isinstance(frame, pd.DataFrame) or len(frame) < INDICATOR_WARMUP:
            continue
        frame = completed_candles(frame, tf, end)
        if tf in datasets:
            datasets[tf][symbol] = frame
        if tf in ANCHOR_TIMEFRAMES.values():
            anchors[symbol][tf] = frame
    return datasets, anchors


def _base_report(mode, incumbent):
    return {"mode": mode, "report_only": True, "validation_version": VALIDATION_VERSION,
            "status": "NOT_VALIDATED", "message": "Not validated", "cached": False,
            "incumbent": copy.deepcopy(incumbent), "selected_candidate": None,
            "validation_results": [], "final_results": [], "boundaries": None,
            "execution_model": "conservative_ohlc",
            "cost_model": {"fee_pct": incumbent.get("fee_pct", 0.05),
                           "slippage_pct": incumbent.get("slippage_pct", 0.02),
                           "fee_rate": incumbent.get("fee_pct", 0.05) / 100.0,
                           "slippage_rate": incumbent.get("slippage_pct", 0.02) / 100.0,
                           "description": "Model assumptions per fill; not actual exchange costs"}}


async def run_report_only_evaluation(*, mode: str, report_dir,
                                     incumbent: Optional[dict] = None, symbols=None,
                                     timeframes=None, limit: int = 1500,
                                     now: Optional[float] = None,
                                     datasets: Optional[dict] = None,
                                     htf_datasets: Optional[dict] = None) -> dict:
    """Evaluate fixed candidates without changing any live trading configuration.

    Inject datasets={timeframe: {symbol: frame}} and
    htf_datasets={symbol: {anchor_timeframe: frame}} for offline research/tests.
    The holdout ledger is shared by every optimizer using this report directory.
    """
    incumbent = {**DEFAULT_INCUMBENT, **copy.deepcopy(incumbent or {})}
    if mode not in ("micro", "macro", "monthly", "cli"):
        raise ValueError(f"Unsupported evaluation mode: {mode}")
    candidates = freeze_candidates(mode, incumbent, timeframes)
    frames = sorted({c["timeframe"] for c in candidates})
    root = Path(report_dir).resolve()
    lock = _evaluation_locks.setdefault(str(root), asyncio.Lock())
    async with lock:
        report = _base_report(mode, incumbent)
        ledger_path = root / "validation_evaluations.json"
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"evaluations": []}
            if not isinstance(ledger.get("evaluations"), list):
                raise ValueError("Invalid evaluation ledger")
        except (ValueError, OSError) as exc:
            report.update(status="CACHE_ERROR", message=f"Holdout ledger unavailable; evaluation blocked: {exc}")
            return report

        cutoff = time.time() if now is None else float(now)
        requested_end = int(cutoff // 86400) * 86400
        requested_start = requested_end - max(int(limit), 10) * 1800
        if symbols is None:
            symbols = sorted(set.intersection(*(set(datasets.get(tf, {})) for tf in frames))) if datasets else await fetch_top_crypto_pairs(limit=15)
        symbols = list(dict.fromkeys(symbols))
        if datasets is None:
            datasets, htf_datasets = await _fetch_history(symbols, frames, requested_start, requested_end)
        htf_datasets = htf_datasets or {}
        usable = [symbol for symbol in symbols if all(
            isinstance(datasets.get(tf, {}).get(symbol), pd.DataFrame)
            and len(datasets[tf][symbol]) >= INDICATOR_WARMUP
            and isinstance(htf_datasets.get(symbol, {}).get(ANCHOR_TIMEFRAMES[tf]), pd.DataFrame)
            and len(htf_datasets[symbol][ANCHOR_TIMEFRAMES[tf]]) >= INDICATOR_WARMUP
            for tf in frames)]
        report["symbols"] = usable
        report["excluded_symbols"] = [s for s in symbols if s not in usable]
        if not usable:
            report["message"] = "Not validated: no symbols have complete entry and anchor history"
            return report
        try:
            boundaries = common_boundaries(datasets, htf_datasets, usable, frames,
                                           requested_start, requested_end)
        except ValueError as exc:
            report["message"] = f"Not validated: {exc}"
            return report
        report["boundaries"] = boundaries
        final_start, final_end = boundaries["final_test"]
        for previous in ledger["evaluations"]:
            old_start, old_end = previous["boundaries"]["final_test"]
            if max(final_start, old_start) < min(final_end, old_end):
                cached = copy.deepcopy(previous)
                cached.update(cached=True, requested_mode=mode,
                              cache_reason="Final-test dates overlap a consumed evaluation; candidates cannot be retuned")
                return cached

        # Freeze and reserve the holdout before simulation. Interrupted evaluations
        # remain consumed, so a retry can never quietly choose a different winner.
        report.update(status="EVALUATING", message="Research evaluation in progress",
                      candidates=copy.deepcopy(candidates), created_at=cutoff)
        report["evaluation_id"] = hashlib.sha256(json.dumps(boundaries, sort_keys=True).encode()).hexdigest()[:16]
        ledger["evaluations"].append(copy.deepcopy(report))
        _atomic_json(ledger_path, ledger)
        try:
            prepared = {tf: {symbol: compute_crypto_indicators(completed_candles(datasets[tf][symbol], tf, requested_end))
                             for symbol in usable} for tf in frames}
            prepared_anchors = {symbol: {tf: compute_crypto_indicators(completed_candles(frame, tf, requested_end))
                                         for tf, frame in htf_datasets[symbol].items()}
                                for symbol in usable}
            rows = []
            for candidate in candidates:
                train = await asyncio.to_thread(_evaluate, candidate, boundaries["train"], prepared, prepared_anchors, usable)
                validation = await asyncio.to_thread(_evaluate, candidate, boundaries["validation"], prepared, prepared_anchors, usable)
                screen = evaluate_reproducibility(train, validation)
                rows.append({"candidate": candidate, "train_metrics": train,
                             "validation_metrics": validation, "screen": screen})
            rows.sort(key=lambda row: (-float(row["validation_metrics"].get("expectancy_r") if row["validation_metrics"].get("expectancy_r") is not None else float('-inf')),
                                     float(row["validation_metrics"].get("max_drawdown_r", 0)),
                                     row["candidate"]["candidate_id"]))
            qualified = [row for row in rows if row["screen"]["screen_passed"]]
            selected = qualified[0]["candidate"] if qualified else None
            report.update(validation_results=rows, selected_candidate=selected,
                          status="FINAL_SELECTION_FROZEN", message="Validation selection frozen before final testing")
            ledger["evaluations"][-1] = copy.deepcopy(report)
            _atomic_json(ledger_path, ledger)
            incumbent_candidate = _candidate(incumbent["strategy"], incumbent["timeframe"], incumbent.get("params", {}),
                incumbent["target_rr"], fee_pct=incumbent.get("fee_pct", 0.05), slippage_pct=incumbent.get("slippage_pct", 0.02))
            finalists = {incumbent_candidate["candidate_id"]: incumbent_candidate}
            if selected:
                finalists[selected["candidate_id"]] = selected
            for candidate in finalists.values():
                metrics = await asyncio.to_thread(_evaluate, candidate, boundaries["final_test"], prepared, prepared_anchors, usable)
                training = next(row["train_metrics"] for row in rows if row["candidate"]["candidate_id"] == candidate["candidate_id"])
                report["final_results"].append({"candidate": candidate, "metrics": metrics,
                    "screen": evaluate_reproducibility(training, metrics),
                    "is_incumbent": candidate["candidate_id"] == incumbent_candidate["candidate_id"]})
            report.update(status="RESEARCH_COMPLETE" if selected else "NOT_VALIDATED",
                          message="Report only; frozen strategy unchanged" if selected else "Not validated: no candidate passed the validation screen")
        except Exception as exc:
            report.update(status="EVALUATION_FAILED", message=f"Evaluation failed; holdout remains consumed: {exc}")
        report_path = root / f"research_{report['evaluation_id']}.json"
        report["report_path"] = str(report_path)
        ledger["evaluations"][-1] = copy.deepcopy(report)
        _atomic_json(ledger_path, ledger)
        _atomic_json(report_path, report)
        return report
