import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path


CACHE_DIR = Path(__file__).resolve().parent / "report_cache"


def _clean_data_for_json(data):
    if isinstance(data, dict):
        return {k: _clean_data_for_json(v) for k, v in data.items()}
    if isinstance(data, tuple):
        return [_clean_data_for_json(item) for item in data]
    if isinstance(data, list):
        return [_clean_data_for_json(item) for item in data]
    if isinstance(data, Decimal):
        return float(data)
    if isinstance(data, float):
        return data if math.isfinite(data) else None

    item = getattr(data, "item", None)
    if callable(item):
        try:
            return _clean_data_for_json(item())
        except Exception:
            return data

    return data


def _cache_path(user_id, strategy_name):
    key = f"{user_id}::{strategy_name}".encode("utf-8")
    filename = f"{hashlib.sha256(key).hexdigest()}.json"
    return CACHE_DIR / filename


def load_backtest_cache(user_id, strategy_name):
    path = _cache_path(user_id, strategy_name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _clean_data_for_json(payload.get("backtest_result"))
    except Exception:
        return None


def save_backtest_cache(user_id, strategy_name, backtest_result):
    if not user_id or not strategy_name or backtest_result is None:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(user_id, strategy_name)
    payload = {
        "user_id": str(user_id),
        "strategy_name": strategy_name,
        "backtest_result": _clean_data_for_json(backtest_result),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def delete_backtest_cache(user_id, strategy_name):
    path = _cache_path(user_id, strategy_name)
    if path.exists():
        path.unlink()
