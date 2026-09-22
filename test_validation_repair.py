"""Isolated repair regression tests. No production bot, files, or HTTP requests."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import data_loader
from data_loader import completed_candles, fetch_symbol_klines
from strategies import (AVAILABLE_STRATEGIES, TrendPullbackConfluence,
                        compute_crypto_indicators, evaluate_mtf_alignment)
from strategy_memory import evaluate_reproducibility
import validation


def frame(start, end, seconds=900):
    times = np.arange(start, end, seconds, dtype=np.int64)
    n = len(times)
    return pd.DataFrame({"time": times, "close_time": times + seconds - 0.001,
        "open": np.full(n, 101.0), "high": np.full(n, 103.0), "low": np.full(n, 101.5),
        "close": np.full(n, 102.0), "volume": np.full(n, 1000.0),
        "ema20": np.full(n, 102.0), "ema50": np.full(n, 100.0), "ema200": np.full(n, 95.0),
        "atr14": np.full(n, 1.0), "rsi14": np.full(n, 50.0), "rvol": np.full(n, 2.0),
        "adx14": np.full(n, 30.0), "hurst": np.full(n, 0.6), "buyer_ratio": np.full(n, 60.0),
        "momentum": np.full(n, 1.0), "bb_width_percentile": np.full(n, 20.0),
        "squeeze_on": np.full(n, False), "swing_low_5": np.full(n, 99.0),
        "swing_high_5": np.full(n, 102.0), "swing_low_20": np.full(n, 98.0),
        "swing_high_20": np.full(n, 104.0)})


class ClosedAnchorTests(unittest.TestCase):
    def setUp(self):
        self.now = 20000 * 86400
        self.base = frame(self.now - 200 * 900, self.now)
        self.anchor = frame(self.now - 200 * 3600, self.now, 3600)

    def test_completed_filter_keeps_close_timestamp_and_excludes_forming_bar(self):
        data = frame(self.now - 900, self.now + 900)
        clean = completed_candles(data, "15m", self.now)
        self.assertEqual(list(clean.time), [self.now - 900])
        self.assertAlmostEqual(clean.iloc[0].close_time, self.now - 0.001)

    def test_missing_stale_opposing_and_warmup_anchors_block(self):
        for anchor, reason in ((None, "MISSING_OR_INSUFFICIENT_ANCHOR"),
                               (self.anchor.iloc[:199], "MISSING_OR_INSUFFICIENT_ANCHOR")):
            aligned, ctx = evaluate_mtf_alignment(anchor, decision_time=self.now)
            self.assertFalse(aligned)
            self.assertIn(reason, ctx["reasons"])
        stale = frame(self.now - 201 * 3600, self.now - 3600, 3600)
        self.assertEqual(evaluate_mtf_alignment(stale, decision_time=self.now)[1]["reasons"], ["STALE_ANCHOR"])
        bearish = self.anchor.copy()
        bearish["ema50"], bearish["rsi14"] = 110.0, 35.0
        self.assertEqual(evaluate_mtf_alignment(bearish, decision_time=self.now)[1]["reasons"], ["OPPOSING_ANCHOR"])

    def test_neutral_allowed_and_actual_anchor_timestamp_recorded(self):
        self.anchor["rsi14"] = 45.0
        aligned, ctx = evaluate_mtf_alignment(self.anchor, decision_time=self.now)
        self.assertTrue(aligned)
        self.assertEqual(ctx["anchor_regime"], "NEUTRAL")
        self.assertEqual(ctx["anchor_time"], self.now - 3600)
        self.assertAlmostEqual(ctx["anchor_close_time"], self.now - 0.001)

    def test_every_strategy_requires_anchor_and_completed_signal(self):
        for strategy in AVAILABLE_STRATEGIES:
            self.assertIsNone(strategy.generate_signal(self.base, 199, htf_data={}, decision_time=self.now))
            self.assertIsNone(strategy.generate_signal(self.base, 199, htf_data={"1h": self.anchor},
                                                       decision_time=self.now - 900))
        good = TrendPullbackConfluence.generate_signal(self.base, 199, htf_data={"1h": self.anchor}, decision_time=self.now)
        self.assertIsNotNone(good)
        self.assertEqual(good["pre_trade_context"]["mtf_alignment"]["anchor_time"], self.now - 3600)

    def test_future_anchor_cannot_change_earlier_signal(self):
        signal = TrendPullbackConfluence.generate_signal(self.base, 199, htf_data={"1h": self.anchor}, decision_time=self.now)
        future = frame(self.now, self.now + 10 * 3600, 3600)
        future["close"], future["rsi14"] = 1.0, 1.0
        with_future = pd.concat([self.anchor, future], ignore_index=True)
        other = TrendPullbackConfluence.generate_signal(self.base, 199, htf_data={"1h": with_future}, decision_time=self.now)
        self.assertEqual(signal, other)

    def test_indicators_have_no_future_backfill(self):
        original = self.base[["time", "open", "high", "low", "close", "volume"]].copy()
        modified = original.copy()
        modified.loc[100:, "close"] = 200.0
        earlier = compute_crypto_indicators(original)
        later = compute_crypto_indicators(modified)
        pd.testing.assert_frame_equal(earlier.iloc[:100], later.iloc[:100])
        self.assertTrue(earlier.atr14.iloc[:13].isna().all())


class _Response:
    status = 200
    headers = {}

    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return self.rows


class _Session:
    def __init__(self, count=1500):
        self.rows = [[i * 900000, "100", "102", "99", "101", "20", (i + 1) * 900000 - 1,
                      "0", 1, "10", "0", "0"] for i in range(count)]
        self.calls = []

    def get(self, url, params, **kwargs):
        self.calls.append(copy.deepcopy(params))
        matching = [row for row in self.rows if row[0] <= params["endTime"]
                    and row[0] >= params.get("startTime", 0)]
        rows = matching[:params["limit"]] if "startTime" in params else matching[-params["limit"]:]
        return _Response(rows)


class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_scanner_adapter_preserves_exchange_close_timestamps(self):
        from scanner import fetch_klines
        session = _Session(count=200)
        source = await fetch_symbol_klines(session, "CLOSETEST", limit=200, start_time=0, end_time=200*900)
        with patch("scanner.fetch_symbol_klines", return_value=source):
            result = await fetch_klines(session, "CLOSETEST", interval="15m", limit=200)
        self.assertEqual(list(result.close_time), list(source.close_time))

    async def asyncSetUp(self):
        self.cache = patch.dict(data_loader._shared_kline_cache, {}, clear=True)
        self.cache.start()

    async def asyncTearDown(self):
        self.cache.stop()

    async def test_forward_pagination_and_range_cache_identity(self):
        session = _Session()
        result = await fetch_symbol_klines(session, "PAGETEST", limit=1500, start_time=0, end_time=1500 * 900)
        self.assertEqual(len(result), 1500)
        self.assertEqual([c["limit"] for c in session.calls], [1000, 500])
        self.assertEqual(session.calls[1]["startTime"], 1000 * 900000)
        self.assertEqual(result.iloc[0].close_time, 899.999)
        second = await fetch_symbol_klines(session, "PAGETEST", limit=1500, start_time=0, end_time=1500 * 900)
        self.assertEqual(len(session.calls), 2)
        second.loc[0, "close"] = 1
        self.assertEqual(result.loc[0, "close"], 101)
        await fetch_symbol_klines(session, "PAGETEST", limit=1500, start_time=900, end_time=1500 * 900)
        self.assertGreater(len(session.calls), 2)

    async def test_backwards_pagination_fetches_latest_unique_bars(self):
        session = _Session()
        result = await fetch_symbol_klines(session, "BACKTEST", limit=1500, end_time=1500 * 900)
        self.assertEqual(len(result), 1500)
        self.assertEqual(len(result.time.unique()), 1500)
        self.assertEqual(session.calls[1]["endTime"], 500 * 900000 - 1)
        self.assertEqual(list(result.time), sorted(result.time))


class ResearchValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 20000 * 86400
        self.start = self.now - 1500 * 1800
        self.datasets = {"15m": {"TEST": frame(self.start - 200 * 900, self.now)}}
        self.anchors = {"TEST": {"1h": frame(self.start - 200 * 3600, self.now, 3600)}}
        self.kwargs = dict(mode="micro", report_dir=self.temp.name, symbols=["TEST"],
                           now=self.now, datasets=self.datasets, htf_datasets=self.anchors)

    def metrics(self, candidate, window, datasets, anchors, symbols):
        # Validation favors wider stops; equal expectancy favors smaller drawdown.
        return {"strategy": candidate["strategy"], "target_rr": 2.0, "total_trades": 20,
                "profit_factor": 1.5, "expectancy_r": candidate["params"].get("atr_sl_mult", 2.2) / 10,
                "max_drawdown_r": candidate["params"].get("rvol_min", 1.25),
                "win_rate_pct": 10.0, "total_net_r": 5.0}

    async def test_final_data_changes_never_affect_validation_selection(self):
        boundary = self.start + int(1500 * 0.8) * 1800
        calls = []
        def evaluate(*args):
            calls.append((args[0]["candidate_id"], args[1]))
            result = self.metrics(*args)
            if args[1][0] == boundary:
                result["expectancy_r"] = float(args[2]["15m"]["TEST"].iloc[-1]["close"])
            return result
        with patch.object(validation, "_evaluate", side_effect=evaluate):
            first = await validation.run_report_only_evaluation(**self.kwargs)
            self.datasets["15m"]["TEST"].loc[self.datasets["15m"]["TEST"].time >= boundary, "close"] = 0.001
            with tempfile.TemporaryDirectory() as fresh:
                second = await validation.run_report_only_evaluation(**{**self.kwargs, "report_dir": fresh})
        self.assertEqual(first["selected_candidate"], second["selected_candidate"])
        self.assertNotEqual(first["final_results"][0]["metrics"]["expectancy_r"], second["final_results"][0]["metrics"]["expectancy_r"])
        self.assertEqual(first["selected_candidate"]["params"]["atr_sl_mult"], 2.6)
        self.assertEqual(first["selected_candidate"]["params"]["rvol_min"], 1.25)
        self.assertLessEqual(len(first["final_results"]), 2)
        self.assertTrue(first["report_only"])

    async def test_final_window_is_consumed_across_modes_and_configurations(self):
        with patch.object(validation, "_evaluate", side_effect=self.metrics) as mock:
            first = await validation.run_report_only_evaluation(**self.kwargs)
            count = mock.call_count
            second = await validation.run_report_only_evaluation(**{**self.kwargs, "mode": "monthly", "timeframes": ["15m"],
                "incumbent": {"params": {"atr_sl_mult": 5.0}}})
            self.assertEqual(mock.call_count, count)
        self.assertTrue(second["cached"])
        self.assertEqual(first["selected_candidate"], second["selected_candidate"])
        ledger = json.loads((Path(self.temp.name) / "validation_evaluations.json").read_text())
        self.assertEqual(len(ledger["evaluations"]), 1)

    async def test_failure_cannot_release_consumed_holdout(self):
        with patch.object(validation, "_evaluate", side_effect=RuntimeError("interrupted")) as mock:
            failed = await validation.run_report_only_evaluation(**self.kwargs)
            count = mock.call_count
            cached = await validation.run_report_only_evaluation(**self.kwargs)
            self.assertEqual(mock.call_count, count)
        self.assertEqual(failed["status"], "EVALUATION_FAILED")
        self.assertTrue(cached["cached"])

    async def test_empty_tournament_has_no_fabricated_metrics(self):
        result = await validation.run_report_only_evaluation(**{**self.kwargs, "datasets": {}})
        self.assertEqual(result["status"], "NOT_VALIDATED")
        self.assertIsNone(result["selected_candidate"])
        self.assertEqual(result["final_results"], [])
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_common_windows_use_timestamps_and_preserve_warmup(self):
        splits = validation.common_boundaries(self.datasets, self.anchors, ["TEST"], ["15m"], self.start, self.now)
        self.assertEqual(splits["train"], [self.start, self.start + 900 * 1800])
        self.assertEqual(splits["validation"], [self.start + 900 * 1800, self.start + 1200 * 1800])
        self.assertEqual(splits["final_test"], [self.start + 1200 * 1800, self.now])
        self.assertLess(self.datasets["15m"]["TEST"].iloc[0].time, splits["train"][0])

    def test_win_rate_is_not_a_research_qualification_gate(self):
        result = evaluate_reproducibility({}, {"total_trades": 20, "win_rate_pct": 10,
            "profit_factor": 1.5, "expectancy_r": 0.3, "target_rr": 2}, min_win_rate_pct=80)
        self.assertTrue(result["screen_passed"])

    def test_configured_costs_reach_simulator_and_report(self):
        incumbent = {**validation.DEFAULT_INCUMBENT, "fee_pct": 0.1, "slippage_pct": 0.05}
        candidates = validation.freeze_candidates("micro", incumbent)
        self.assertTrue(all(c["fee_pct"] == 0.1 and c["slippage_pct"] == 0.05 for c in candidates))
        with patch.object(validation, "simulate_strategy_on_dataframe", return_value={"trades": []}) as simulate:
            validation._evaluate(candidates[0], [self.start, self.now], self.datasets, self.anchors, ["TEST"])
        self.assertEqual(simulate.call_args.kwargs["fee_pct"], 0.1)
        self.assertEqual(simulate.call_args.kwargs["slippage_pct"], 0.05)
        cost_model = validation._base_report("micro", incumbent)["cost_model"]
        self.assertEqual(cost_model["fee_rate"], 0.001)
        self.assertEqual(cost_model["slippage_rate"], 0.0005)


if __name__ == "__main__":
    unittest.main()
