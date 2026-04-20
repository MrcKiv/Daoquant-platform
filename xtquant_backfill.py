import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from xtquant import xtdata
from xtquant import xtdatacenter as xtdc


def load_env_file(env_path=None):
    env_file = Path(env_path) if env_path else Path(__file__).resolve().with_name(".env")
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def normalize_db_host(host):
    if not host:
        return "127.0.0.1"
    if host == "db" and not Path("/.dockerenv").exists():
        return "127.0.0.1"
    return host


def validate_table_name(table_name):
    if not re.fullmatch(r"[A-Za-z0-9_]+", table_name):
        raise ValueError(f"非法表名: {table_name}")
    return table_name


def emit_progress(progress_callback, payload):
    if callable(progress_callback):
        progress_callback(payload)


load_env_file()

TARGET_TABLE = validate_table_name(os.getenv("BACKFILL_TABLE", "stock_1d"))
BATCH_SIZE = int(os.getenv("BACKFILL_BATCH_SIZE", "50"))
INITIAL_START_DATE = os.getenv("BACKFILL_INITIAL_START_DATE", "20200101")

DB_NAME = os.getenv("BACKFILL_DB_NAME") or os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME") or "jdgp"
DB_USER = os.getenv("BACKFILL_DB_USER") or os.getenv("MYSQL_USER") or os.getenv("DB_USER") or "daoquant"
DB_PASSWORD = os.getenv("BACKFILL_DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD") or "daoquant123"
DB_HOST = normalize_db_host(os.getenv("BACKFILL_DB_HOST") or os.getenv("MYSQL_HOST") or os.getenv("DB_HOST"))
DB_PORT = int(os.getenv("BACKFILL_DB_PORT") or os.getenv("MYSQL_PORT") or os.getenv("DB_PORT") or "3306")
DB_CHARSET = os.getenv("BACKFILL_DB_CHARSET") or os.getenv("DB_CHARSET") or "utf8mb4"
XTQUANT_TOKEN = (os.getenv("XTQUANT_TOKEN") or "").strip() or "210097f139884e84e93e28e6045b6266325b5023"
XTQUANT_OPTIMIZED_ADDRESSES = [
    item.strip()
    for item in (
        os.getenv("XTQUANT_OPTIMIZED_ADDRESSES")
        or "115.231.218.73:55310,115.231.218.79:55310,42.228.16.211:55300,42.228.16.210:55300,36.99.48.20:55300,36.99.48.21:55300"
    ).split(",")
    if item.strip()
]

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}"
)


def get_resume_window():
    start_override = os.getenv("BACKFILL_START_DATE")
    end_override = os.getenv("BACKFILL_END_DATE")
    end_date = end_override or datetime.now().strftime("%Y%m%d")

    if start_override:
        return start_override, end_date, "使用环境变量指定起始日期"

    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT MAX(trade_date) AS max_trade_date FROM `{TARGET_TABLE}`")
        ).first()

    max_trade_date = row[0] if row else None
    if max_trade_date is None:
        return INITIAL_START_DATE, end_date, "目标表为空，从初始日期开始"

    next_date = (pd.Timestamp(max_trade_date) + timedelta(days=1)).strftime("%Y%m%d")
    return next_date, end_date, f"接续 {pd.Timestamp(max_trade_date).strftime('%Y-%m-%d')} 之后的数据"


def save_chunk_to_mysql(stock_list, start_date, end_date):
    """
    处理一个小批次：下载 -> 读取 -> 存库
    """
    for stock in stock_list:
        xtdata.download_history_data(stock, period="1d", start_time=start_date, end_time=end_date)

    time.sleep(1)

    data_1d = xtdata.get_market_data_ex(
        field_list=["time", "open", "high", "low", "close", "volume"],
        stock_list=stock_list,
        period="1d",
        start_time=start_date,
        end_time=end_date,
        dividend_type="front",
        fill_data=True,
    )

    all_dfs = []
    for stock_code, df in data_1d.items():
        if df.empty:
            continue

        df_copy = df.copy()
        df_copy["stock_code"] = stock_code
        df_copy["time"] = (
            pd.to_datetime(df_copy["time"], unit="ms", utc=True)
            .dt.tz_convert("Asia/Shanghai")
            .dt.tz_localize(None)
        )
        df_copy.rename(
            columns={
                "stock_code": "st_code",
                "time": "trade_date",
                "volume": "vol",
            },
            inplace=True,
        )
        all_dfs.append(df_copy)

    if not all_dfs:
        return 0

    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df.to_sql(TARGET_TABLE, engine, if_exists="append", index=False)
    return len(combined_df)


def download_all_ashares_daily(start_date, end_date, progress_callback=None):
    print("正在获取全市场A股列表...")
    all_stocks = xtdata.get_stock_list_in_sector("沪深A股")

    if not all_stocks:
        print("[warn] '沪深A股' 板块为空，再尝试一次...")
        all_stocks = xtdata.get_stock_list_in_sector("沪深A股")

    if not all_stocks:
        raise RuntimeError("未获取到沪深A股股票列表，无法执行补数。")

    print(f"[info] 共获取到 {len(all_stocks)} 只股票，开始从 {start_date} 补到 {end_date}")

    total_stocks = len(all_stocks)
    total_saved_rows = 0
    failed_batches = 0
    total_batches = (total_stocks + BATCH_SIZE - 1) // BATCH_SIZE

    emit_progress(
        progress_callback,
        {
            "event": "prepared",
            "start_date": start_date,
            "end_date": end_date,
            "total_stocks": total_stocks,
            "total_batches": total_batches,
            "processed_stocks": 0,
            "processed_batches": 0,
            "progress_percent": 0.0,
            "total_saved_rows": 0,
            "failed_batches": 0,
        },
    )

    for batch_number, i in enumerate(range(0, total_stocks, BATCH_SIZE), start=1):
        batch_stocks = all_stocks[i:i + BATCH_SIZE]
        print(f"[progress {i}/{total_stocks}] 正在处理: {batch_stocks[0]} 等 {len(batch_stocks)} 只...")

        emit_progress(
            progress_callback,
            {
                "event": "batch_started",
                "start_date": start_date,
                "end_date": end_date,
                "total_stocks": total_stocks,
                "total_batches": total_batches,
                "processed_stocks": i,
                "processed_batches": batch_number - 1,
                "batch_number": batch_number,
                "batch_stock_count": len(batch_stocks),
                "current_stock": batch_stocks[0],
                "progress_percent": round(i * 100 / total_stocks, 2),
                "total_saved_rows": total_saved_rows,
                "failed_batches": failed_batches,
            },
        )

        try:
            rows = save_chunk_to_mysql(batch_stocks, start_date, end_date)
            total_saved_rows += rows
            processed_stocks = min(i + len(batch_stocks), total_stocks)
            print(f"   [ok] 本批次入库 {rows} 条记录")
            emit_progress(
                progress_callback,
                {
                    "event": "batch_completed",
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_stocks": total_stocks,
                    "total_batches": total_batches,
                    "processed_stocks": processed_stocks,
                    "processed_batches": batch_number,
                    "batch_number": batch_number,
                    "batch_stock_count": len(batch_stocks),
                    "current_stock": batch_stocks[0],
                    "batch_rows": rows,
                    "progress_percent": round(processed_stocks * 100 / total_stocks, 2),
                    "total_saved_rows": total_saved_rows,
                    "failed_batches": failed_batches,
                },
            )
        except Exception as exc:
            failed_batches += 1
            print(f"   [error] 本批次发生错误: {exc}")
            emit_progress(
                progress_callback,
                {
                    "event": "batch_failed",
                    "start_date": start_date,
                    "end_date": end_date,
                    "total_stocks": total_stocks,
                    "total_batches": total_batches,
                    "processed_stocks": i,
                    "processed_batches": batch_number - 1,
                    "batch_number": batch_number,
                    "batch_stock_count": len(batch_stocks),
                    "current_stock": batch_stocks[0],
                    "batch_rows": 0,
                    "progress_percent": round(i * 100 / total_stocks, 2),
                    "total_saved_rows": total_saved_rows,
                    "failed_batches": failed_batches,
                    "error": str(exc),
                },
            )

    print("=" * 30)
    print("[done] 全市场补数任务完成！")
    print(f"[rows] 总计入库数据行数: {total_saved_rows}")
    print("=" * 30)
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_stocks": total_stocks,
        "total_batches": total_batches,
        "processed_stocks": total_stocks,
        "processed_batches": total_batches,
        "total_saved_rows": total_saved_rows,
        "failed_batches": failed_batches,
        "progress_percent": 100.0,
    }
    emit_progress(progress_callback, {"event": "finished", **summary})
    return summary


def init_xtquant():
    print("正在初始化行情模块...")
    xtdc.set_token(XTQUANT_TOKEN)
    xtdc.set_allow_optmize_address(XTQUANT_OPTIMIZED_ADDRESSES)
    xtdc.init()
    print("[ok] 行情模块初始化完成")


if __name__ == "__main__":
    start_time_clock = time.time()

    print(f"[db] 目标数据库: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"[table] 目标数据表: {TARGET_TABLE}")

    start_date, end_date, reason = get_resume_window()
    print(f"[range] 本次补数区间: {start_date} 至 {end_date} ({reason})")

    if start_date > end_date:
        print("[ok] 当前数据库已是最新区间，无需补数。")
    else:
        init_xtquant()
        download_all_ashares_daily(start_date, end_date)

    print(f"[time] 总耗时: {(time.time() - start_time_clock) / 60:.2f} 分钟")
