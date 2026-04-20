import importlib.util
import hmac
import json
import os
import re
import threading
import traceback
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
STATE_FILE = RUNTIME_DIR / "stock_backfill_host_state.json"
LOCK_FILE = RUNTIME_DIR / "stock_backfill_host.lock"
BACKFILL_SCRIPT_PATH = Path(__file__).resolve().parent / "xtquant_backfill.py"
BACKFILL_MODULE_NAME = "daoquant_xtquant_backfill_host"

HOST = os.getenv("XTQUANT_BACKFILL_HOST", "0.0.0.0")
PORT = int(os.getenv("XTQUANT_BACKFILL_PORT", "8765"))
SERVICE_TOKEN = (os.getenv("XTQUANT_BACKFILL_TOKEN") or "").strip()

_STATE_LOCK = threading.Lock()
_MODULE_CACHE = None


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


def _ensure_runtime_dir():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _service_url():
    return f"http://{HOST}:{PORT}"


def _default_state():
    today = date.today().isoformat()
    return {
        "status": "idle",
        "phase": "idle",
        "message": "等待开始补全。",
        "target_table": "stock_1d",
        "execution_mode": "windows_host_service",
        "service_url": _service_url(),
        "service_status": "connected",
        "service_message": "Windows xtquant 补数服务运行中。",
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

    spec = importlib.util.spec_from_file_location(BACKFILL_MODULE_NAME, BACKFILL_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载补数脚本: {BACKFILL_SCRIPT_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _MODULE_CACHE = module
    return module


def _get_live_latest_trade_date(table_name):
    module = _load_backfill_module()
    table_name = _validate_table_name(table_name)
    with module.engine.connect() as conn:
        row = conn.execute(text(f"SELECT MAX(trade_date) FROM `{table_name}`")).first()
    return row[0] if row else None


def _get_suggested_start_date(latest_trade_date):
    if latest_trade_date is None:
        return None
    return _to_iso_date(latest_trade_date + timedelta(days=1))


def _decorate_state(state, service_status=None, service_message=None):
    decorated = _default_state()
    decorated.update(state or {})
    decorated["execution_mode"] = "windows_host_service"
    decorated["service_url"] = _service_url()
    decorated["service_status"] = service_status or decorated.get("service_status") or "connected"
    decorated["service_message"] = (
        service_message
        or decorated.get("service_message")
        or "Windows xtquant 补数服务运行中。"
    )
    return decorated


def _hydrate_state(state):
    hydrated = _default_state()
    hydrated.update(state or {})

    table_name = hydrated.get("target_table") or "stock_1d"
    should_refresh_live_date = hydrated.get("status") in {"idle", "completed", "failed"} or not hydrated.get("database_latest_date_live")

    if should_refresh_live_date:
        try:
            live_latest_date = _get_live_latest_trade_date(table_name)
            hydrated["database_latest_date_live"] = _to_iso_date(live_latest_date)
            hydrated["suggested_start_date"] = _get_suggested_start_date(live_latest_date)
        except Exception as exc:
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
    return _decorate_state(
        _hydrate_state(_read_state()),
        service_status="connected",
        service_message="Windows xtquant 补数服务运行中。",
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
        return f"第 {batch_number}/{total_batches} 批完成，本批入库 {payload.get('batch_rows', 0)} 条。"
    if event == "batch_failed":
        return f"第 {batch_number}/{total_batches} 批失败：{payload.get('error', '未知错误')}"
    if event == "finished":
        return "股票数据补全完成。"
    return "补数任务运行中。"


def _write_running_state(base_state, payload):
    event = payload.get("event") or "running"
    _write_state(
        {
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
    )


def _run_stock_backfill(start_date_raw, end_date_raw, reason, table_name, latest_before):
    _write_state(
        {
            "status": "running",
            "phase": "initializing",
            "message": "正在初始化 xtquant 行情模块...",
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
        message = f"补全完成，共写入 {saved_rows} 条记录。" if saved_rows else "补全完成，没有新增记录。"
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
            name="xtquant-backfill-host-worker",
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


class HostServiceHandler(BaseHTTPRequestHandler):
    server_version = "XtquantBackfillHostService/1.1"

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ensure_authorized(self):
        if not SERVICE_TOKEN:
            return True

        received_token = (self.headers.get("X-Backfill-Token") or "").strip()
        if received_token and hmac.compare_digest(received_token, SERVICE_TOKEN):
            return True

        self._send_json(401, {"error": "未授权访问补数服务，请检查 token 配置。"})
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "xtquant-backfill-host",
                    "service_url": _service_url(),
                    "auth_enabled": bool(SERVICE_TOKEN),
                },
            )
            return
        if parsed.path == "/stock-backfill/status":
            if not self._ensure_authorized():
                return
            self._send_json(200, get_stock_backfill_status())
            return
        self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/stock-backfill/start":
            if not self._ensure_authorized():
                return
            started, state, status_code = start_stock_backfill()
            self._send_json(
                status_code,
                {
                    "success": started,
                    "message": "补数任务已启动" if started else state.get("message") or "补数任务启动失败",
                    "state": state,
                },
            )
            return
        self._send_json(404, {"error": "Not Found"})

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")


if __name__ == "__main__":
    _ensure_runtime_dir()
    server = ThreadingHTTPServer((HOST, PORT), HostServiceHandler)
    print(f"xtquant backfill host service listening on http://{HOST}:{PORT}")
    server.serve_forever()
