import json
from datetime import datetime, timedelta
import time

import pandas as pd
import redis
from sqlalchemy import text

from config import (
    engine,
    TABLE_NAME,
    FIELDS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_KEY_TEMPLATE,
    SHOW_ROW_LIMIT
)


# -------------------------------
# 🔹 Redis 初始化
# -------------------------------
def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )


# -------------------------------
# 🔹 通用：从 MySQL 读取某天数据
# -------------------------------
def read_data_from_mysql(trade_date: str):
    query = text(f"""
        SELECT {', '.join(FIELDS)}
        FROM {TABLE_NAME}
        WHERE trade_date = :trade_date
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"trade_date": trade_date})
        rows = result.mappings().all()
        return [dict(row) for row in rows]


# -------------------------------
# ✅ 功能 1：缓存 n 个交易日的数据（向后找）
# -------------------------------
def cache_next_n_trade_days(start_date: str, n: int = 5, max_lookahead_days: int = 30):
    redis_client = get_redis_client()
    found_dates = []
    current_date = datetime.strptime(start_date, "%Y%m%d")
    tries = 0

    print(f"\n📦 缓存从 {start_date} 起接下来的 {n} 个交易日数据...\n")

    while len(found_dates) < n and tries < max_lookahead_days:
        date_str = current_date.strftime("%Y%m%d")
        data = read_data_from_mysql(date_str)
        if data:
            found_dates.append((date_str, data))
        current_date += timedelta(days=1)
        tries += 1

    if not found_dates:
        print("❌ 未找到任何可缓存的交易日数据。")
        return

    for trade_date, data in found_dates:
        redis_key = write_to_redis(redis_client, trade_date, data)
        print(f"✅ 已写入 Redis：{redis_key}（记录数：{len(data)}）")
        preview_from_redis(redis_client, trade_date)


# -------------------------------
# ✅ 功能 2：查询 Redis 数据并合并为 DataFrame
# -------------------------------
def query_redis_by_date_range(start_date: str, end_date: str) -> pd.DataFrame:
    redis_client = get_redis_client()
    print(f"\n🔍 查询 Redis：{start_date} ~ {end_date}")
    start_time = time.time()

    all_records = []
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    days = (end_dt - start_dt).days + 1
    date_list = [(start_dt + timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]

    for trade_date in date_list:
        redis_key = REDIS_KEY_TEMPLATE.format(date=trade_date)
        raw = redis_client.get(redis_key)
        if raw is None:
            print(f"⚠️ 缺失：{redis_key}")
            continue
        data_dict = json.loads(raw)
        all_records.extend(data_dict.values())

    if not all_records:
        print("❌ 查询结果为空。")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    print(f"\n📊 合并完成：{len(df)} 条记录, {len(df.columns)} 个字段")
    print(df.head(SHOW_ROW_LIMIT))

    elapsed = time.time() - start_time
    print(f"⏱️ 查询耗时：{elapsed:.2f} 秒")
    return df


# -------------------------------
# ✅ 功能 3：更新今日数据 + 删除最老 Redis 键（滑窗维护）
# -------------------------------
def update_latest_cache(today: str):
    redis_client = get_redis_client()
    print(f"\n🗓️ 更新缓存：模拟今天为 {today}")

    # 插入今天数据
    data = read_data_from_mysql(today)
    if not data:
        print(f"⚠️ 今天 {today} 无数据，Redis 未写入。")
        inserted = False
    else:
        redis_key, count = write_to_redis(redis_client, today, data, return_count=True)
        print(f"✅ 成功写入 Redis：{redis_key}（记录数：{count}）")
        inserted = True

    # 获取当前 Redis 中的全部日期
    keys = redis_client.keys("stock:*")
    dates = []
    for key in keys:
        try:
            date_part = key.split(":")[1]
            if len(date_part) == 8 and date_part.isdigit():
                dates.append(date_part)
        except:
            continue

    if inserted and today not in dates:
        dates.append(today)
    dates = sorted(dates)
    keep_dates = dates[-5:]

    print(f"\n📌 Redis 中共有 {len(dates)} 个日期")
    print(f"🛡️ 保留最近 5 天：{keep_dates}")

    removed = 0
    for date in dates:
        if date not in keep_dates:
            key = REDIS_KEY_TEMPLATE.format(date=date)
            redis_client.delete(key)
            print(f"🗑️ 删除：{key}")
            removed += 1

    print(f"\n✅ 删除完成，共删除 {removed} 个过期键")


# -------------------------------
# 🔹 Redis 写入 & 预览工具函数
# -------------------------------
def write_to_redis(redis_client, trade_date, data_list, return_count=False):
    data_dict = {}
    for item in data_list:
        st_code = item["st_code"]
        item["trade_date"] = trade_date
        data_dict[st_code] = item
    redis_key = REDIS_KEY_TEMPLATE.format(date=trade_date)
    redis_client.set(redis_key, json.dumps(data_dict))
    return (redis_key, len(data_dict)) if return_count else redis_key


def preview_from_redis(redis_client, trade_date):
    redis_key = REDIS_KEY_TEMPLATE.format(date=trade_date)
    raw = redis_client.get(redis_key)
    if raw is None:
        print(f"[{trade_date}] ⚠️ Redis中未找到键 {redis_key}")
        return
    data_dict = json.loads(raw)
    df = pd.DataFrame(list(data_dict.values()))
    print(f"[{trade_date}] Redis预览（前{SHOW_ROW_LIMIT}行）：")
    print(df.head(SHOW_ROW_LIMIT))
