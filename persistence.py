"""Atomic, versioned portfolio snapshots without application import side effects."""

import json
import math
import os
import tempfile
from typing import Any, Dict, Optional


def validate_portfolio_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Reject incomplete snapshots instead of combining unrelated ledger versions."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 2:
        raise ValueError("Unsupported portfolio snapshot schema")
    revision = snapshot.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ValueError("Portfolio snapshot revision must be a positive integer")
    state = snapshot.get("state")
    if not isinstance(state, dict):
        raise ValueError("Portfolio snapshot is missing state")
    # A missing balance must never be replaced with the constructor's default
    # while positions/fills come from the snapshot. Other state keys remain
    # optional for compatibility with legitimate earlier snapshot producers.
    balance = state.get("current_balance")
    if isinstance(balance, bool) or not isinstance(balance, (int, float)) or not math.isfinite(balance):
        raise ValueError("Portfolio snapshot requires a finite numeric current_balance")
    positions = snapshot.get("open_positions")
    trades = snapshot.get("closed_trades")
    if not isinstance(positions, dict) or any(not isinstance(p, dict) for p in positions.values()):
        raise ValueError("Portfolio snapshot has invalid open positions")
    if not isinstance(trades, list) or any(not isinstance(t, dict) for t in trades):
        raise ValueError("Portfolio snapshot has invalid closed trades")
    json.dumps(snapshot, allow_nan=False)
    return snapshot


def atomic_write_json(path: str, payload: Any) -> None:
    """Replace one JSON file only after its complete contents have been flushed."""
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    target = os.path.abspath(os.fspath(path))
    directory = os.path.dirname(target)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory,
            prefix="." + os.path.basename(target) + ".", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = handle.name
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


def load_portfolio_snapshot(path: str) -> Optional[Dict[str, Any]]:
    """Missing is distinct from corrupt: corruption is surfaced to the caller."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except FileNotFoundError:
        return None
    return validate_portfolio_snapshot(snapshot)
