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
    min_win_rate_pct: float = 33.0,
    min_profit_factor: float = 1.35,
    min_expectancy_r: float = 0.20
) -> Dict[str, Any]:
    """
    Validate whether a strategy has a statistically reproducible edge on Out-of-Sample test data.
    """
    test_trades = test_metrics.get('total_trades', 0)
    win_rate = test_metrics.get('win_rate_pct', 0.0)
    pf = test_metrics.get('profit_factor', 0.0)
    exp_r = test_metrics.get('expectancy_r', 0.0)
    target_rr = test_metrics.get('target_rr', 3.0)

    reproducible = True
    rejection_reasons = []

    if target_rr < 3.0:
        reproducible = False
        rejection_reasons.append(f"Target RR 1:{target_rr} does not meet >= 1:3 RR mandate")

    if test_trades < min_test_trades:
        reproducible = False
        rejection_reasons.append(f"Insufficient sample size ({test_trades} trades, required >= {min_test_trades})")

    if win_rate < min_win_rate_pct:
        reproducible = False
        rejection_reasons.append(f"Out-of-sample win rate ({win_rate}%) below {min_win_rate_pct}% threshold")

    if pf < min_profit_factor:
        reproducible = False
        rejection_reasons.append(f"Profit factor ({pf}) below {min_profit_factor} threshold")

    if exp_r < min_expectancy_r:
        reproducible = False
        rejection_reasons.append(f"Expectancy ({exp_r}R) below +{min_expectancy_r}R threshold")

    # Check for severe overfit (e.g. training PF 4.0 but test PF 0.8)
    train_pf = train_metrics.get('profit_factor', 0.0)
    if train_pf > 2.0 and pf < 1.0:
        reproducible = False
        rejection_reasons.append("Severe overfit: strong training performance collapsed on out-of-sample test data")

    return {
        "is_reproducible": reproducible,
        "strategy": test_metrics.get('strategy', 'Unknown'),
        "target_rr": target_rr,
        "test_trades": test_trades,
        "win_rate_pct": win_rate,
        "profit_factor": pf,
        "expectancy_r": exp_r,
        "rejection_reasons": rejection_reasons
    }

def save_strategy_to_catalog(
    strategy_name: str, 
    eval_result: Dict[str, Any], 
    details: Dict[str, Any],
    filepath: str = SAVED_STRATEGIES_FILE
) -> None:
    """Persist a validated reproducible strategy to the local strategy catalog."""
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
        "status": "APPROVED_REPRODUCIBLE"
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)

def load_saved_strategies(filepath: str = SAVED_STRATEGIES_FILE) -> Dict[str, Any]:
    """Load previously validated strategies from catalog."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
