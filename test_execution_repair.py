"""Offline regressions for modeled execution; no production bot is imported."""
import unittest
from unittest.mock import patch

import pandas as pd

from execution import create_position, process_bar, process_price, close_position, summarize_position
from sim_engine import compile_simulation_metrics, simulate_strategy_on_dataframe


class ExecutionRepairTests(unittest.TestCase):
    def test_all_adapters_use_paper_baseline_candle_thresholds(self):
        from execution import EXIT_TIMEFRAME_PROFILES
        from live_bot import TIMEFRAME_PROFILES as paper
        from sim_engine import TIMEFRAME_PROFILES as simulation
        from backtester import TIMEFRAME_PROFILES as reference
        for timeframe, expected in EXIT_TIMEFRAME_PROFILES.items():
            for profiles in (paper, simulation, reference):
                self.assertEqual(profiles[timeframe]["stagnation_bars"], expected["stagnation_bars"])
                self.assertEqual(profiles[timeframe]["max_holding_bars"], expected["max_holding_bars"])

    def position(self, direction="LONG", target_rr=2.0, **costs):
        return create_position(direction, 100, 1, 1, target_rr, 0,
                               fee_pct=costs.get("fee_pct", 0),
                               slippage_pct=costs.get("slippage_pct", 0))

    def test_ambiguous_existing_stop_precedes_targets_both_directions(self):
        for direction in ("LONG", "SHORT"):
            with self.subTest(direction=direction):
                pos = self.position(direction)
                process_bar(pos, {"time": 1, "open": 100, "high": 101.5, "low": 98.5, "close": 100},
                            timestamp=2, completed_bars=1)
                self.assertEqual(pos["exit_reason"], "STOP_LOSS")
                self.assertFalse(pos["tp1_hit"])
                self.assertAlmostEqual(summarize_position(pos)["net_r"], -1)

    def test_opening_gap_fills_at_worse_open(self):
        for direction, opening in (("LONG", 98), ("SHORT", 102)):
            pos = self.position(direction)
            process_bar(pos, {"time": 1, "open": opening, "high": opening + .5,
                              "low": opening - .5, "close": opening}, timestamp=2)
            self.assertEqual(pos["exit_price"], opening)
            self.assertAlmostEqual(summarize_position(pos)["net_r"], -2)

    def test_standing_target_precedes_same_bar_runner_switch(self):
        pos = self.position()
        process_bar(pos, {"time": 1, "open": 100, "high": 105, "low": 99.5, "close": 104}, timestamp=2)
        self.assertEqual(pos["exit_reason"], "TAKE_PROFIT")
        self.assertFalse(pos["is_unlimited_runner"])
        self.assertAlmostEqual(summarize_position(pos)["net_r"], 1.5)
        self.assertEqual([f["kind"] for f in pos["fills"]], ["ENTRY", "TP1", "EXIT"])

    def test_target_reached_at_known_open_precedes_later_adverse_extreme(self):
        pos = self.position()
        process_bar(pos, {"time": 1, "open": 103, "high": 104, "low": 98, "close": 100}, timestamp=2)
        self.assertEqual(pos["exit_reason"], "TAKE_PROFIT")
        self.assertEqual(pos["exit_time"], 1)
        self.assertAlmostEqual(summarize_position(pos)["net_r"], 1.5)

    def test_old_wick_cannot_hit_new_stop_or_repeat_fill(self):
        pos = self.position()
        bar = {"time": 1, "open": 100, "high": 100.9, "low": 99.5, "close": 100.8}
        process_bar(pos, bar, timestamp=2, completed_bars=1)
        self.assertFalse(pos["closed"])
        self.assertEqual(pos["sl_price"], 100.15)
        self.assertEqual(process_bar(pos, bar, timestamp=2)["fills"], [])
        process_price(pos, 100.7, 3)
        self.assertFalse(pos["closed"])
        process_price(pos, 100.1, 4)
        self.assertTrue(pos["closed"])
        self.assertEqual(pos["exit_price"], 100.1)
        self.assertEqual(process_price(pos, 99, 5)["fills"], [])

    def test_costs_quantity_and_cash_reconcile_for_partial_and_final(self):
        pos = create_position("LONG", 100, 2, 3, 2, 0)
        self.assertAlmostEqual(pos["initial_qty"], 1.5)
        entry_cash = pos["entry_cash_delta_usd"]
        partial = process_price(pos, pos["tp1_price"], 1)
        self.assertEqual(len(partial["fills"]), 1)
        self.assertAlmostEqual(pos["position_qty"], .75)
        final = close_position(pos, 102, 2)
        summary = summarize_position(pos)
        self.assertAlmostEqual(entry_cash + partial["cash_delta_usd"] + final["cash_delta_usd"], summary["pnl_usd"])
        self.assertAlmostEqual(sum(f["quantity"] for f in pos["fills"][1:]), pos["initial_qty"])
        self.assertAlmostEqual(summary["pnl_usd"], summary["gross_pnl_usd"] - summary["fees_usd"])
        self.assertGreater(summary["slippage_usd"], 0)
        self.assertEqual(summary["remaining_qty"], 0)
        self.assertEqual(close_position(pos, 500, 3)["cash_delta_usd"], 0)

    def test_newly_marketable_stop_waits_for_next_observation(self):
        for direction, high, low, next_price in (("LONG", 100.9, 99.5, 99.8),
                                                 ("SHORT", 100.5, 99.1, 100.2)):
            with self.subTest(direction=direction):
                pos = self.position(direction)
                process_bar(pos, {"time": 1, "open": 100, "high": high, "low": low, "close": 100}, timestamp=2)
                self.assertFalse(pos["closed"])
                self.assertTrue(pos["is_breakeven_protected"])
                process_price(pos, next_price, 3)
                self.assertEqual(pos["exit_price"], next_price)
                self.assertEqual(pos["exit_time"], 3)
                self.assertEqual(pos["exit_reason"], "PROTECTED_STOP")

    def test_protected_stop_can_be_net_loss_after_costs(self):
        pos = create_position("LONG", 100, .1, 1, 2, 0)
        process_price(pos, pos["entry_price"] + .085, 1)
        process_price(pos, pos["sl_price"], 2)
        summary = summarize_position(pos)
        self.assertEqual(summary["exit_reason"], "PROTECTED_STOP")
        self.assertLess(summary["net_r"], 0)
        self.assertEqual(summary["outcome"], "LOSS")

    def test_stop_ratchets_do_not_change_original_risk(self):
        pos = self.position(target_rr=5)
        process_price(pos, 101.1, 1)
        process_price(pos, 102.3, 2, atr=.2)
        self.assertEqual(pos["original_risk_distance"], 1)
        self.assertEqual(pos["initial_sl_price"], 99)
        self.assertEqual(pos["initial_qty"], 1)
        self.assertGreater(pos["sl_price"], 99)

    def test_initial_losses_and_unsorted_cash_flow_drawdown(self):
        trades = [{"net_r": -1, "exit_time": 2, "bars_held": 1},
                  {"net_r": -1, "exit_time": 1, "bars_held": 1}]
        self.assertEqual(compile_simulation_metrics(trades, "test", 2)["max_drawdown_r"], 2)
        for order in (trades, list(reversed(trades))):
            self.assertEqual(compile_simulation_metrics(order, "test", 2)["max_drawdown_r"], 2)

    def test_unmeasured_and_unbounded_metrics_are_not_fabricated(self):
        empty = compile_simulation_metrics([], "test", 2)
        self.assertIsNone(empty["win_rate_pct"])
        self.assertIsNone(empty["expectancy_r"])
        self.assertIsNone(empty["profit_factor"])
        wins = compile_simulation_metrics([{"net_r": 1, "exit_time": 1}], "test", 2)
        self.assertIsNone(wins["profit_factor"])
        self.assertTrue(wins["profit_factor_unbounded"])

    def test_drawdown_includes_entry_fee_before_profitable_exit(self):
        pos = self.position(fee_pct=.05)
        close_position(pos, 101, 2)
        metrics = compile_simulation_metrics([summarize_position(pos)], "test", 2)
        self.assertAlmostEqual(metrics["max_drawdown_r"], .05)


class SimulationRepairTests(unittest.TestCase):
    class Signal:
        name = "AuditFixture"

        @staticmethod
        def generate_signal(df, idx, **kwargs):
            if idx != 199:
                return None
            return {"direction": "LONG", "risk_distance": 2, "target_rr": 2,
                    "pre_trade_context": {"decision_time": kwargs["decision_time"]}}

    def frames(self):
        frame = pd.DataFrame({"time": [n * 900 for n in range(203)],
                              "open": [100.] * 200 + [103.] * 3,
                              "high": [100.2] * 200 + [103.2] * 3,
                              "low": [99.8] * 200 + [102.8] * 3,
                              "close": [100.] * 200 + [103.] * 3,
                              "volume": [1000.] * 203})
        anchor = pd.DataFrame({"time": [(n - 250) * 3600 + 180000 for n in range(250)],
                               "open": [100.] * 250, "high": [100.2] * 250,
                               "low": [99.8] * 250, "close": [100.] * 250,
                               "volume": [1000.] * 250})
        return frame, {"1h": anchor}

    def test_next_open_entry_and_explicit_window_close(self):
        frame, anchors = self.frames()
        result = simulate_strategy_on_dataframe(frame, self.Signal, timeframe="15m", htf_data=anchors,
                                                window_start=180000, window_end=182700,
                                                fee_pct=0, slippage_pct=0)
        self.assertEqual(result["total_trades"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["entry_price"], 103)
        self.assertEqual(trade["entry_time"], 180000)
        self.assertEqual(trade["exit_reason"], "WINDOW_END")
        self.assertEqual(trade["exit_time"], 182700)
        self.assertEqual(trade["net_r"], 0)

    def test_missing_anchor_rejects_with_diagnostic(self):
        frame, _ = self.frames()
        result = simulate_strategy_on_dataframe(frame, self.Signal, timeframe="15m")
        self.assertEqual(result["total_trades"], 0)
        self.assertGreater(result["data_diagnostics"]["missing_anchor_history"], 0)

    def test_forming_final_bar_is_not_replayed_as_completed(self):
        frame, anchors = self.frames()
        frame.loc[202, ["high", "low", "close"]] = [200, 50, 150]
        with patch("data_loader.time.time", return_value=182699):
            result = simulate_strategy_on_dataframe(frame, self.Signal, timeframe="15m", htf_data=anchors,
                                                    fee_pct=0, slippage_pct=0)
        self.assertEqual(result["total_trades"], 1)
        self.assertEqual(result["trades"][0]["exit_time"], 181800)
        self.assertEqual(result["trades"][0]["exit_reason"], "WINDOW_END")
        self.assertEqual(result["trades"][0]["net_r"], 0)

    def test_future_window_bars_cannot_change_prior_replay(self):
        frame, anchors = self.frames()
        args = dict(timeframe="15m", htf_data=anchors, window_start=180000,
                    window_end=181800, fee_pct=0, slippage_pct=0)
        before = simulate_strategy_on_dataframe(frame, self.Signal, **args)
        frame.loc[202, ["open", "high", "low", "close"]] = [500, 501, 499, 500]
        after = simulate_strategy_on_dataframe(frame, self.Signal, **args)
        self.assertEqual(before["trades"], after["trades"])

    def test_reference_backtester_uses_fill_costs_and_labels_strategy_scope(self):
        from backtester import run_backtest_simulation
        frame, _ = self.frames()
        frame["signal"] = "NONE"
        frame.loc[199, "signal"] = "LONG"
        frame["atr14"] = 2 / 1.5
        with patch("backtester.compute_indicators", side_effect=lambda value: value):
            result = run_backtest_simulation(frame, timeframe="15m")
        self.assertEqual(result["total_trades"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["schema_version"], 2)
        self.assertGreater(trade["fees_usd"], 0)
        self.assertAlmostEqual(result["equity_curve"][-1], trade["net_r"], places=6)
        self.assertIn("not validation", result["strategy_scope"])


if __name__ == "__main__":
    unittest.main()
