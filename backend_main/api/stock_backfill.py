import importlib.util
import json
import os
import platform
import re
import threading
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

from django.db import connections
import requests


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
STATE_FILE = RUNTIME_DIR / "stock_backfill_state.json"
LOCK_FILE = RUNTIME_DIR / "stock_backfill.lock"
BACKFILL_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "xtquant_backfill.py"
BACKFILL_MODULE_NAME = "daoquant_xtquant_backfill"
HOST_BACKFILL_SERVICE_URL = (os.getenv("BACKFILL_HOST_SERVICE_URL") or "http://host.docker.internal:8765").rstrip("/")
HOST_BACKFILL_SERVICE_TOKEN = (os.getenv("BACKFILL_HOST_SERVICE_TOKEN") or "").strip()

try:
    HOST_BACKFILL_SERVICE_TIMEOUT = max(5, int(os.getenv("BACKFILL_HOST_SERVICE_TIMEOUT") or "15"))
except ValueError:
    HOST_BACKFILL_SERVICE_TIMEOUT = 15

_STATE_LOCK = threading.Lock()
_MODULE_CACHE = None


def _should_proxy_to_host_service():
    forced = os.getenv("BACKFILL_USE_HOST_SERVICE")
    if forced is not None:
        return forced.strip().lower() in {"1", "true", "yes", "on"}
    return platform.system().lower() != "windows"


def _execution_mode():
    return "windows_host_service" if _should_proxy_to_host_service() else "local_backend"


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _to_iso_date(value):
    if value is None:
        return None
    if isinstance(value, str):
        if re.fullmatch(r"\d{8}", value):
            return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
        return value
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _validate_table_name(table_name):
    if not re.fullmatch(r"[A-Za-z0-9_]+", table_name or ""):
        raise ValueError(f"非法表名: {table_name}")
    return table_name


def _default_state():
    today = date.today().isoformat()
    using_host_service = _should_proxy_to_host_service()
    return {
        "status": "idle",
        "phase": "idle",
        "message": "等待开始补全。",
        "target_table": "stock_1d",
        "execution_mode": _execution_mode(),
        "service_url": HOST_BACKFILL_SERVICE_URL if using_host_service else None,
        "service_status": "configured" if using_host_service else "local",
        "service_message": (
            "等待连接 Windows xtquant 补数服务。"
            if using_host_service
            else "当前由后端本地执行补数任务。"
        ),
        "today_date": today,
        "database_latest_date": None,
        "database_latest_date_live": None,
        "suggested_start_date": None,
        "suggested_end_date": today,
        "start_date": None,
        "end_date": today,
        "reason": None,
        "progress_percent": 0.0,
        "total_stocks": 0,
        "processed_stocks": 0,
        "total_batches": 0,
        "processed_batches": 0,
        "saved_rows": 0,
        "last_batch_rows": 0,
        "failed_batches": 0,
        "current_stock": None,
        "started_at": None,
        "finished_at": None,
        "updated_at": None,
        "elapsed_seconds": 0,
        "last_error": None,
    }


def _ensure_runtime_dir():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _read_state_unlocked():
    state = _default_state()
    if not STATE_FILE.exists():
        return state

    try:
        loaded = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return state

    state.update(loaded)
    return state


def _read_state():
    _ensure_runtime_dir()
    with _STATE_LOCK:
        return _read_state_unlocked()


def _write_state(updates):
    _ensure_runtime_dir()
    with _STATE_LOCK:
        state = _read_state_unlocked()
        state.update(updates)
        state["updated_at"] = _now_iso()

        started_at = _parse_iso_datetime(state.get("started_at"))
        finished_at = _parse_iso_datetime(state.get("finished_at"))
        reference_time = finished_at or datetime.now()
        if started_at is not None:
            state["elapsed_seconds"] = max(0, int((reference_time - started_at).total_seconds()))
        else:
            state["elapsed_seconds"] = 0

        STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return state


def _is_locked():
    return LOCK_FILE.exists()


def _acquire_lock():
    _ensure_runtime_dir()
    try:
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(str(os.getpid()))
        return True
    except FileExistsError:
        return False


def _release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _load_backfill_module():
    global _MODULE_CACHE

    if _MODULE_CACHE is not None:
        return _MODULE_CACHE

    if not BACKFILL_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"未找到补数脚本: {BACKFILL_SCRIPT_PATH}")

    spec = importlib.util.spec_from_file_location(BACKFILL_MODULE_NAME, BACKFILL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载补数脚本: {BACKFILL_SCRIPT_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _MODULE_CACHE = module
    return module


def _get_live_latest_trade_date(table_name):
    table_name = _validate_table_name(table_name)
    with connections["default"].cursor() as cursor:
        cursor.execute(f"SELECT MAX(trade_date) FROM `{table_name}`")
        row = cursor.fetchone()
    return row[0] if row else None


def _get_suggested_start_date(latest_trade_date):
    if latest_trade_date is None:
        return None
    return _to_iso_date(latest_trade_date + timedelta(days=1))


def _decorate_state(state, service_status=None, service_message=None):
    decorated = _default_state()
    decorated.update(state or {})
    decorated["execution_mode"] = _execution_mode()

    if _should_proxy_to_host_service():
        decorated["service_url"] = HOST_BACKFILL_SERVICE_URL
        decorated["service_status"] = service_status or decorated.get("service_status") or "configured"
        decorated["service_message"] = (
            service_message
            or decorated.get("service_message")
            or "通过 Windows xtquant 补数服务执行任务。"
        )
    else:
        decorated["service_url"] = None
        decorated["service_status"] = service_status or "local"
        decorated["service_message"] = service_message or "当前由后端本地执行补数任务。"

    return decorated


def _build_proxy_headers():
    headers = {"Accept": "application/json"}
    if HOST_BACKFILL_SERVICE_TOKEN:
        headers["X-Backfill-Token"] = HOST_BACKFILL_SERVICE_TOKEN
    return headers


def _proxy_request(method, path):
    response = requests.request(
        method,
        f"{HOST_BACKFILL_SERVICE_URL}{path}",
        headers=_build_proxy_headers(),
        timeout=HOST_BACKFILL_SERVICE_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {"error": response.text}
    return response.status_code, payload


def _build_proxy_error_state(message, last_error=None, service_status="unreachable"):
    state = _default_state()
    state.update(
        {
            "status": "failed",
            "phase": "failed",
            "message": message,
            "today_date": date.today().isoformat(),
            "suggested_end_date": date.today().isoformat(),
            "last_error": last_error,
            "updated_at": _now_iso(),
        }
    )
    hydrated = _hydrate_state(state)
    return _decorate_state(hydrated, service_status=service_status, service_message=message)


def _summarize_proxy_payload(payload):
    if isinstance(payload, dict):
        try:
            return json.dumps(payload, ensure_ascii=False)
        except TypeError:
            return str(payload)
    return str(payload)


def _get_proxy_service_status(status_code):
    if status_code in {401, 403}:
        return "auth_failed"
    if status_code == 404:
        return "invalid_endpoint"
    if status_code >= 500:
        return "connected"
    return "connected"


def _get_proxy_failure_message(status_code, payload):
    detail = None
    if isinstance(payload, dict):
        detail = payload.get("message") or payload.get("error")

    if status_code in {401, 403}:
        return detail or "Windows 补数服务鉴权失败，请检查 BACKFILL_HOST_SERVICE_TOKEN 配置。"
    if status_code == 404:
        return detail or "Windows 补数服务接口不存在，请确认服务版本与脚本已更新。"
    if status_code >= 500:
        return detail or "Windows 补数服务内部错误，请检查服务日志。"
    return detail or f"Windows 补数服务返回异常状态：HTTP {status_code}"


def _hydrate_state(state):
    hydrated = _default_state()
    hydrated.update(state or {})

    table_name = hydrated.get("target_table") or "stock_1d"
    live_latest_date = None
    should_refresh_live_date = hydrated.get("status") in {"idle", "completed", "failed"} or not hydrated.get("database_latest_date_live")

    if should_refresh_live_date:
        try:
            live_latest_date = _get_live_latest_trade_date(table_name)
            hydrated["database_latest_date_live"] = _to_iso_date(live_latest_date)
            hydrated["suggested_start_date"] = _get_suggested_start_date(live_latest_date)
        except Exception as exc:
            hydrated["database_latest_date_live"] = hydrated.get("database_latest_date_live")
            if hydrated.get("status") in {"idle", "completed"}:
                hydrated["message"] = hydrated.get("message") or f"读取数据库最晚日期失败: {exc}"

    if not hydrated.get("database_latest_date"):
        hydrated["database_latest_date"] = hydrated.get("database_latest_date_live")

    hydrated["today_date"] = date.today().isoformat()
    hydrated["suggested_end_date"] = hydrated["today_date"]

    started_at = _parse_iso_datetime(hydrated.get("started_at"))
    finished_at = _parse_iso_datetime(hydrated.get("finished_at"))
    reference_time = finished_at or datetime.now()
    if started_at is not None:
        hydrated["elapsed_seconds"] = max(0, int((reference_time - started_at).total_seconds()))
    else:
        hydrated["elapsed_seconds"] = 0

    return hydrated


def get_stock_backfill_status():
    if _should_proxy_to_host_service():
        try:
            status_code, payload = _proxy_request("GET", "/stock-backfill/status")
            if status_code == 200 and isinstance(payload, dict):
                return _decorate_state(
                    payload,
                    service_status="connected",
                    service_message="xtquant 补数任务由 Windows worker 执行。",
                )
            return _build_proxy_error_state(
                _get_proxy_failure_message(status_code, payload),
                last_error=_summarize_proxy_payload(payload),
                service_status=_get_proxy_service_status(status_code),
            )
        except Exception as exc:
            return _build_proxy_error_state(
                f"无法连接 Windows 主机补数服务：{exc}",
                last_error=traceback.format_exc(),
            )
    return _decorate_state(
        _hydrate_state(_read_state()),
        service_status="local",
        service_message="当前由后端本地执行补数任务。",
    )


def _build_progress_message(payload):
    event = payload.get("event")
    current_stock = payload.get("current_stock") or "-"
    batch_number = payload.get("batch_number") or 0
    total_batches = payload.get("total_batches") or 0

    if event == "prepared":
        return "已获取股票列表，准备开始补数。"
    if event == "batch_started":
        return f"正在处理第 {batch_number}/{total_batches} 批，起始股票 {current_stock}。"
    if event == "batch_completed":
        rows = payload.get("batch_rows", 0)
        return f"第 {batch_number}/{total_batches} 批完成，本批入库 {rows} 条。"
    if event == "batch_failed":
        return f"第 {batch_number}/{total_batches} 批失败：{payload.get('error', '未知错误')}"
    if event == "finished":
        return "股票数据补全完成。"
    return "补数任务运行中。"


def _write_running_state(base_state, payload):
    event = payload.get("event") or "running"
    updates = {
        "status": "running",
        "phase": event,
        "message": _build_progress_message(payload),
        "start_date": _to_iso_date(payload.get("start_date")) or base_state.get("start_date"),
        "end_date": _to_iso_date(payload.get("end_date")) or base_state.get("end_date"),
        "target_table": base_state.get("target_table", "stock_1d"),
        "progress_percent": round(float(payload.get("progress_percent", 0.0)), 2),
        "total_stocks": int(payload.get("total_stocks") or 0),
        "processed_stocks": int(payload.get("processed_stocks") or 0),
        "total_batches": int(payload.get("total_batches") or 0),
        "processed_batches": int(payload.get("processed_batches") or 0),
        "saved_rows": int(payload.get("total_saved_rows") or 0),
        "last_batch_rows": int(payload.get("batch_rows") or 0),
        "failed_batches": int(payload.get("failed_batches") or 0),
        "current_stock": payload.get("current_stock"),
        "last_error": payload.get("error") if event == "batch_failed" else None,
    }
    _write_state(updates)


def _run_stock_backfill(start_date_raw, end_date_raw, reason, table_name, latest_before):
    started_at = _now_iso()
    _write_state(
        {
            "status": "running",
            "phase": "initializing",
            "message": "正在初始化 xtquant 行情模块...",
            "started_at": started_at,
            "finished_at": None,
            "target_table": table_name,
            "database_latest_date": _to_iso_date(latest_before),
            "start_date": _to_iso_date(start_date_raw),
            "end_date": _to_iso_date(end_date_raw),
            "reason": reason,
            "progress_percent": 0.0,
            "total_stocks": 0,
            "processed_stocks": 0,
            "total_batches": 0,
            "processed_batches": 0,
            "saved_rows": 0,
            "last_batch_rows": 0,
            "failed_batches": 0,
            "current_stock": None,
            "last_error": None,
        }
    )

    try:
        module = _load_backfill_module()

        if start_date_raw > end_date_raw:
            latest_after = _get_live_latest_trade_date(table_name)
            _write_state(
                {
                    "status": "completed",
                    "phase": "completed",
                    "message": "当前数据库已经是最新，无需补全。",
                    "finished_at": _now_iso(),
                    "database_latest_date": _to_iso_date(latest_before),
                    "database_latest_date_live": _to_iso_date(latest_after),
                    "progress_percent": 100.0,
                    "saved_rows": 0,
                }
            )
            return

        module.init_xtquant()
        _write_state(
            {
                "status": "running",
                "phase": "initialized",
                "message": "xtquant 初始化完成，开始执行股票补全。",
                "progress_percent": 0.0,
            }
        )

        base_state = {
            "target_table": table_name,
            "start_date": _to_iso_date(start_date_raw),
            "end_date": _to_iso_date(end_date_raw),
        }

        summary = module.download_all_ashares_daily(
            start_date_raw,
            end_date_raw,
            progress_callback=lambda payload: _write_running_state(base_state, payload),
        )

        latest_after = _get_live_latest_trade_date(table_name)
        failed_batches = int(summary.get("failed_batches") or 0)
        saved_rows = int(summary.get("total_saved_rows") or 0)
        message = (
            f"补全完成，共写入 {saved_rows} 条记录。"
            if saved_rows
            else "补全完成，没有新增记录。"
        )
        if failed_batches:
            message += f" 其中 {failed_batches} 个批次失败，请检查服务日志。"

        _write_state(
            {
                "status": "completed",
                "phase": "completed",
                "message": message,
                "finished_at": _now_iso(),
                "database_latest_date": _to_iso_date(latest_before),
                "database_latest_date_live": _to_iso_date(latest_after),
                "progress_percent": 100.0,
                "total_stocks": int(summary.get("total_stocks") or 0),
                "processed_stocks": int(summary.get("processed_stocks") or 0),
                "total_batches": int(summary.get("total_batches") or 0),
                "processed_batches": int(summary.get("processed_batches") or 0),
                "saved_rows": saved_rows,
                "failed_batches": failed_batches,
                "current_stock": None,
                "last_error": None if not failed_batches else "部分批次执行失败",
            }
        )
    except Exception as exc:
        current_state = _read_state()
        _write_state(
            {
                "status": "failed",
                "phase": "failed",
                "message": f"补全失败：{exc}",
                "finished_at": _now_iso(),
                "progress_percent": current_state.get("progress_percent", 0.0),
                "last_error": traceback.format_exc(),
            }
        )
    finally:
        _release_lock()


def start_stock_backfill():
    if _should_proxy_to_host_service():
        try:
            status_code, payload = _proxy_request("POST", "/stock-backfill/start")
            state = payload.get("state") if isinstance(payload, dict) else None
            if not isinstance(state, dict):
                state = _build_proxy_error_state(
                    _get_proxy_failure_message(status_code, payload),
                    last_error=_summarize_proxy_payload(payload),
                    service_status=_get_proxy_service_status(status_code),
                )
                return False, state, 502

            state = _decorate_state(
                state,
                service_status=_get_proxy_service_status(status_code),
                service_message="xtquant 补数任务由 Windows worker 执行。",
            )
            if status_code == 202 and bool(payload.get("success")):
                return True, state, 202
            return False, state, status_code if status_code >= 400 else 502
        except Exception as exc:
            return (
                False,
                _build_proxy_error_state(
                    f"无法连接 Windows 主机补数服务：{exc}",
                    last_error=traceback.format_exc(),
                ),
                503,
            )

    current_state = get_stock_backfill_status()
    if not _is_locked() and current_state.get("status") in {"starting", "running"}:
        _write_state(
            {
                "status": "idle",
                "phase": "idle",
                "message": "检测到上一次补数任务未正常结束，状态已重置，可重新启动。",
                "finished_at": _now_iso(),
                "current_stock": None,
            }
        )
        current_state = get_stock_backfill_status()

    if _is_locked():
        return False, current_state, 409

    if not _acquire_lock():
        return False, get_stock_backfill_status(), 409

    try:
        module = _load_backfill_module()
        table_name = getattr(module, "TARGET_TABLE", "stock_1d")
        latest_before = _get_live_latest_trade_date(table_name)
        start_date_raw, end_date_raw, reason = module.get_resume_window()

        _write_state(
            {
                "status": "starting",
                "phase": "starting",
                "message": "补数任务已创建，准备启动。",
                "started_at": _now_iso(),
                "finished_at": None,
                "target_table": table_name,
                "database_latest_date": _to_iso_date(latest_before),
                "start_date": _to_iso_date(start_date_raw),
                "end_date": _to_iso_date(end_date_raw),
                "reason": reason,
                "progress_percent": 0.0,
                "total_stocks": 0,
                "processed_stocks": 0,
                "total_batches": 0,
                "processed_batches": 0,
                "saved_rows": 0,
                "last_batch_rows": 0,
                "failed_batches": 0,
                "current_stock": None,
                "last_error": None,
            }
        )

        worker = threading.Thread(
            target=_run_stock_backfill,
            args=(start_date_raw, end_date_raw, reason, table_name, latest_before),
            daemon=True,
            name="stock-backfill-worker",
        )
        worker.start()
        return True, get_stock_backfill_status(), 202
    except Exception as exc:
        _write_state(
            {
                "status": "failed",
                "phase": "failed",
                "message": f"启动补数任务失败：{exc}",
                "finished_at": _now_iso(),
                "progress_percent": 0.0,
                "last_error": traceback.format_exc(),
            }
        )
        _release_lock()
        return False, get_stock_backfill_status(), 500
