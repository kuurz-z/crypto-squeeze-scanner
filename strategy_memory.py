import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Philippine Standard Time (PHT, UTC+8 / Asia/Manila)
PHT = timezone(timedelta(hours=8))

def ph_now() -> datetime:
    """Return current timestamp in Philippine Standard Time (PHT, UTC+8)."""
    return datetime.now(timezone.utc).astimezone(PHT).replace(tzinfo=None)

SAVED_STRATEGIES_FILE = "saved_strategies.json"

def evaluate_reproducibility(
    train_metrics: Dict[str, Any], 
    test_metrics: Dict[str, Any],
    min_test_trades: int = 15,
    min_win_rate_pct: Optional[float] = None,
    min_profit_factor: float = 1.35,
    min_expectancy_r: float = 0.20
) -> Dict[str, Any]:
    """
    Screen research results; passing is not proof of a reproducible trading edge.
    min_win_rate_pct remains accepted for callers but never qualifies a strategy.
    """
    test_trades = test_metrics.get('total_trades', 0)
    win_rate = test_metrics.get('win_rate_pct')
    # Undefined or empty ratios remain nullable in reports, while this screen
    # treats a measured positive sample without losses as unbounded PF.
    measured_pf = test_metrics.get('profit_factor')
    pf = float('inf') if test_metrics.get('profit_factor_unbounded') else (measured_pf or 0.0)
    exp_r = test_metrics.get('expectancy_r') or 0.0
    target_rr = test_metrics.get('target_rr', 2.0)

    reproducible = True
    rejection_reasons = []

    if target_rr < 2.0:
        reproducible = False
        rejection_reasons.append(f"Target RR 1:{target_rr} does not meet >= 1:2 RR mandate")

    if test_trades < min_test_trades:
        reproducible = False
        rejection_reasons.append(f"Insufficient sample size ({test_trades} trades, required >= {min_test_trades})")

    if pf < min_profit_factor:
        reproducible = False
        rejection_reasons.append(f"Profit factor ({pf}) below {min_profit_factor} threshold")

    if exp_r < min_expectancy_r:
        reproducible = False
        rejection_reasons.append(f"Expectancy ({exp_r}R) below +{min_expectancy_r}R threshold")

    # Check for severe overfit (e.g. training PF 4.0 but test PF 0.8)
    train_pf = float('inf') if train_metrics.get('profit_factor_unbounded') else (train_metrics.get('profit_factor') or 0.0)
    if train_pf > 2.0 and pf < 1.0:
        reproducible = False
        rejection_reasons.append("Severe overfit: strong training performance collapsed on out-of-sample test data")

    return {
        "is_reproducible": reproducible,
        "screen_passed": reproducible,
        "validation_status": "RESEARCH_SCREEN_PASSED" if reproducible else "NOT_VALIDATED",
        "strategy": test_metrics.get('strategy', 'Unknown'),
        "target_rr": target_rr,
        "test_trades": test_trades,
        "win_rate_pct": win_rate,
        "profit_factor": measured_pf,
        "profit_factor_unbounded": bool(test_metrics.get('profit_factor_unbounded')),
        "expectancy_r": test_metrics.get('expectancy_r'),
        "rejection_reasons": rejection_reasons
    }

def save_strategy_to_catalog(
    strategy_name: str, 
    eval_result: Dict[str, Any], 
    details: Dict[str, Any],
    filepath: str = SAVED_STRATEGIES_FILE
) -> None:
    """Persist a research-screen result without authorizing live promotion."""
    catalog = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                catalog = json.load(f)
        except Exception:
            catalog = {}

    catalog[strategy_name] = {
        "strategy_name": strategy_name,
        "target_rr": eval_result.get("target_rr", 3.0),
        "validated_at": ph_now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "out_of_sample_trades": eval_result.get("test_trades"),
            "win_rate_pct": eval_result.get("win_rate_pct"),
            "profit_factor": eval_result.get("profit_factor"),
            "expectancy_r": eval_result.get("expectancy_r"),
        },
        "rules_and_description": details.get("description", ""),
        "status": "RESEARCH_SCREEN_PASSED",
        "report_only": True,
        "provenance": details.get("provenance"),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

def load_saved_strategies(filepath: str = SAVED_STRATEGIES_FILE) -> Dict[str, Any]:
    """Load previously validated strategies from catalog."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            for record in catalog.values():
                if isinstance(record, dict) and not record.get("provenance"):
                    record["validation_status"] = "UNVERIFIED_HISTORY"
            return catalog
        except Exception:
            return {}
    return {}
