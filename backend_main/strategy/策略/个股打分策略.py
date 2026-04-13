#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资金流股池 + 60m/日线 MACD 否决 + 排序选出每日 TopK（默认20只）
特点：MACD 只做“否决”，不做“触发”，以保证产出数量稳定并契合“盘中兑现”的池子特征。
"""

from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

# =========================
# 配置
# =========================
DB_URI = "mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8"

POOL_TABLE = "当日入选个股_资金容量版"
TABLE_60M = "stock_60m_all"
TABLE_1D = "partition_table"

# 输出表（你可以改名）
OUT_TABLE = "当日入选个股_资金容量版_MACD否决Top20"

# 选股数量
TOP_K = 20

# 取 60m 尾盘两根K（你原逻辑：14/15点）
TAIL_HOURS = (14, 15)

today = datetime.now().strftime("%Y%m%d")

# 时间范围（None=全量；建议你先用近半年验证）
# START_DATE = today  # "20250101"
# END_DATE = today    # "20251217"

START_DATE = None  # "20250101"
END_DATE = None    # "20251217"

# =========================
# 工具：rank-based 综合分
# =========================
def rank01(s: pd.Series) -> pd.Series:
    """把数值转成(0,1]分位分数，越大越好；NaN会保持NaN"""
    r = s.rank(pct=True, method="average")
    return r

def safe_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# =========================
# 读取数据
# =========================
def load_pool(engine):
    where = []
    if START_DATE:
        where.append(f"trade_date>='{START_DATE}'")
    if END_DATE:
        where.append(f"trade_date<='{END_DATE}'")
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT * FROM `{POOL_TABLE}`{wsql}"
    pool = pd.read_sql(sql, engine)
    if pool.empty:
        raise ValueError(f"{POOL_TABLE} 为空")

    pool["trade_date"] = pool["trade_date"].astype(str)
    pool["st_code"] = pool["st_code"].astype(str)

    # 常见列（没有也不报错）
    pool = safe_numeric(pool, ["score", "inflow_ratio", "capacity", "totalNetInflow", "SuperLargeNetInflow"])
    return pool


def load_60m_tail(engine, dates):
    """
    只取每日尾盘(14/15点)的60m记录，然后每只股票每天取最后一条（更贴近收盘前状态）
    字段参考你代码：macd/pre_macd/dif/dea/pre_dif 等
    """
    date_min, date_max = min(dates), max(dates)
    sql = f"""
    SELECT stock_code,
           DATE(time) as trade_date,
           time,
           close,
           macd, pre_macd,
           dif, dea,
           pre_dif, pre_dea
    FROM `{TABLE_60M}`
    WHERE DATE(time) >= '{date_min[:4]}-{date_min[4:6]}-{date_min[6:8]}'
      AND DATE(time) <= '{date_max[:4]}-{date_max[4:6]}-{date_max[6:8]}'
      AND (HOUR(time) = {TAIL_HOURS[0]} OR HOUR(time) = {TAIL_HOURS[1]})
    """
    df = pd.read_sql(sql, engine)
    if df.empty:
        return df

    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
    df["stock_code"] = df["stock_code"].astype(str)
    df["time"] = pd.to_datetime(df["time"])

    df = safe_numeric(df, ["macd", "pre_macd", "dif", "dea", "pre_dif", "pre_dea"])

    # 每股每天取“最后一条”（更接近收盘）
    df = (df.sort_values(["stock_code", "trade_date", "time"])
            .groupby(["stock_code", "trade_date"], as_index=False)
            .tail(1))
    return df


def load_daily(engine, dates):
    date_min, date_max = min(dates), max(dates)
    sql = f"""
    SELECT st_code,
           trade_date,
           open, high, low, close,
           pre_close, pct_chg, vol, cci, pre_cci,
           macd_macd, pre_macd_macd,
           macd_dif, last_dif
    FROM `{TABLE_1D}`
    WHERE trade_date >= '{date_min}'
      AND trade_date <= '{date_max}'
    """
    df = pd.read_sql(sql, engine)
    if df.empty:
        return df
    df["trade_date"] = df["trade_date"].astype(str)
    df["st_code"] = df["st_code"].astype(str)
    # 确保所有数值列都被正确转换
    numeric_cols = ["open", "high", "low", "close", "pre_close", "pct_chg", "vol",
                   "cci", "pre_cci", "macd_macd", "pre_macd_macd", "macd_dif", "last_dif"]
    df = safe_numeric(df, numeric_cols)
    return df


# =========================
# MACD 否决逻辑（轻约束）
# =========================
def apply_macd_veto(m: pd.DataFrame) -> pd.DataFrame:
    """
    返回通过否决后的子集，并附加一些动能特征用于排序。
    """
    # 60m 动能
    m["macd_delta_60m"] = m["macd"] - m["pre_macd"]
    m["dif_delta_60m"] = m["dif"] - m["pre_dif"]

    # 日线动能
    m["macd_delta_1d"] = m["macd_macd"] - m["pre_macd_macd"]
    m["dif_delta_1d"] = m["macd_dif"] - m["last_dif"]

    # --- 60m 否决：明显弱势/走坏 ---
    veto_60m = (
        ((m["macd"] < 0) & (m["pre_macd"] < 0) & (m["dif"] < m["dea"])) |
        ((m["macd_delta_60m"] < 0) & (m["dif_delta_60m"] < 0))
    )

    # --- 日线 否决：日线动能同步走弱 ---
    veto_1d = (
        (m["macd_delta_1d"] < 0) & (m["dif_delta_1d"] < 0)
    )

    passed = m[~(veto_60m | veto_1d)].copy()
    return passed


# =========================
# 排序选 TopK（不足则回退补齐）
# =========================
def pick_topk_per_day(pool_day: pd.DataFrame, passed_day: pd.DataFrame, topk=20) -> pd.DataFrame:
    """
    先从 passed_day 里按综合分取 topk；若 passed_day 不足 topk，则从 pool_day 里按资金流分补齐。
    """
    # 资金流主因子：score（若缺失则用 inflow_ratio 替代）
    if "score" in pool_day.columns and pool_day["score"].notna().any():
        base_score = pool_day["score"]
    else:
        base_score = pool_day.get("inflow_ratio", pd.Series(index=pool_day.index, dtype=float))

    pool_day = pool_day.copy()
    pool_day["base_rank"] = rank01(base_score)

    # passed_day 若为空，直接用 pool_day topk
    if passed_day.empty:
        return pool_day.sort_values("base_rank", ascending=False).head(topk)

    passed_day = passed_day.copy()

    # 综合分：资金流为主，动能为辅（rank-based，避免尺度问题）
    passed_day["r_score"] = rank01(passed_day.get("score", np.nan))
    passed_day["r_inflow"] = rank01(passed_day.get("inflow_ratio", np.nan))
    passed_day["r_m60"] = rank01(passed_day.get("macd_delta_60m", np.nan)) * 0.5 + rank01(passed_day.get("dif_delta_60m", np.nan)) * 0.5
    passed_day["r_d1"] = rank01(passed_day.get("macd_delta_1d", np.nan)) * 0.5 + rank01(passed_day.get("dif_delta_1d", np.nan)) * 0.5

    # 权重（你可以微调）
    # 资金流占大头：0.70；技术动能合计 0.30（60m偏盘中，日线偏趋势）
    passed_day["final_score"] = (
        0.55 * passed_day["r_score"].fillna(0) +
        0.15 * passed_day["r_inflow"].fillna(0) +
        0.20 * passed_day["r_m60"].fillna(0) +
        0.10 * passed_day["r_d1"].fillna(0)
    )

    picked = passed_day.sort_values("final_score", ascending=False).head(topk)

    # 不足 topk：回退补齐（用资金流 base_rank 补）
    if len(picked) < topk:
        need = topk - len(picked)
        picked_codes = set(picked["st_code"].astype(str))
        supplement = (pool_day[~pool_day["st_code"].astype(str).isin(picked_codes)]
                      .sort_values("base_rank", ascending=False)
                      .head(need))
        picked = pd.concat([picked, supplement], ignore_index=True)

    return picked


def main():
    engine = create_engine(DB_URI)

    pool = load_pool(engine)
    dates = sorted(pool["trade_date"].unique().tolist())

    df60 = load_60m_tail(engine, dates)
    dfd = load_daily(engine, dates)

    # 合并到一个大表
    m = pool.merge(
        df60,
        left_on=["st_code", "trade_date"],
        right_on=["stock_code", "trade_date"],
        how="left"
    ).drop(columns=["stock_code"], errors="ignore")

    m = m.merge(
        dfd,
        left_on=["st_code", "trade_date"],
        right_on=["st_code", "trade_date"],
        how="left",
        suffixes=("", "_1d")
    )

    # 应用否决
    passed = apply_macd_veto(m)

    # 每日取 TopK（不足补齐）
    out_list = []
    for td, pool_day in pool.groupby("trade_date"):
        passed_day = passed[passed["trade_date"] == td]
        picked = pick_topk_per_day(pool_day, passed_day, topk=TOP_K).copy()
        picked["pick_date"] = td
        out_list.append(picked)

    out = pd.concat(out_list, ignore_index=True)

    # 直接从已有的合并数据中获取完整字段，无需再次查询数据库
    if not out.empty:
        # 确保所有需要的列都存在
        required_cols = [
            'st_code', 'trade_date', 'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci',
            'macd_macd', 'pre_macd_macd'
        ]

        # 从合并后的数据中提取这些字段
        final_out = out[required_cols].copy()

        # 添加 MACD 分数列（使用 final_score）
        final_out['MACD'] = out.get('final_score', np.nan)

        # 确保列的顺序正确
        column_order = [
            'st_code', 'trade_date', 'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci',
            'macd_macd', 'pre_macd_macd', 'MACD'
        ]
        final_out = final_out[column_order]

    else:
        # 如果没有数据，创建空的DataFrame结构
        final_out = pd.DataFrame(columns=[
            'st_code', 'trade_date', 'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci',
            'macd_macd', 'pre_macd_macd', 'MACD'
        ])

    # 输出表（覆盖写入）
    final_out.to_sql(OUT_TABLE, engine, if_exists="append", index=False)
    print(f"Done. 输出到表：{OUT_TABLE}")
    print("每日选股数量（前10天）:")
    if not final_out.empty:
        print(final_out.groupby("trade_date").size().head(10))


if __name__ == "__main__":
    main()
