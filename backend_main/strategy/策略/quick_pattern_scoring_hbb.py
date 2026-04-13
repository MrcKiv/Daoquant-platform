# -*- coding: utf-8 -*-
"""
quick_pattern_scoring.py
用途：加载已训练好的聚类模型，对数据库里的股票做特征构建 -> 打分 -> 筛选
支持三种模式：
  --mode full     : 输出所有股票打分
  --mode topk     : 每日TopK + 行业分散
  --mode hybrid   : 分数阈值过滤 + TopK + 行业分散（推荐）
支持簇加权模式：
  --cluster-mode add   : 基础分 + 簇分数（默认）
  --cluster-mode scale : 基础分 * (1 + 簇分数)

依赖：
  pip install pandas numpy SQLAlchemy pymysql scikit-learn
"""
from __future__ import annotations
import argparse, warnings, pickle
import os
from typing import Optional, List, Dict
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

warnings.filterwarnings("ignore")

# ========= DB 连接 =========
DB_USER="root"; DB_PASSWORD="123456"; DB_HOST="127.0.0.1"; DB_PORT="3306"; DB_NAME="jdgp"
ENGINE = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
    pool_pre_ping=True
)

# ========= 表名 =========
TBL_DAILY = "前复权日线行情_移动股池"
TBL_INDMAP = "个股行业映射"
TBL_INDFLOW = "行业流向细节"
TBL_STKFLOW = "行业个股流向细节"
TBL_LABELS  = "股票标签"
TBL_CONCEPT = "advanced_industry_tags"

# ========= 列名别名 =========
ALT_CODE = {"st_code","ts_code","code","证券代码","symbol"}
ALT_DATE = {"trade_date","date","交易日期"}
ALT_VOL  = {"vol","amount","volume","成交量"}
ALT_INDC = {"industry_code","Industry_code","industry","Industry"}

def to_dt(s: pd.Series)->pd.Series:
    if np.issubdtype(s.dtype, np.datetime64): return s.dt.normalize()
    out = pd.to_datetime(s, errors="coerce")
    mask = out.isna() & s.notna()
    if mask.any():
        out.loc[mask] = pd.to_datetime(s[mask].astype(str), errors="coerce", format="%Y%m%d")
    return out.dt.normalize()

def unify_cols(df: pd.DataFrame)->pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    code_col = next((c for c in df.columns if c in ALT_CODE), None)
    if code_col and code_col!="st_code": df.rename(columns={code_col:"st_code"}, inplace=True)
    date_col = next((c for c in df.columns if c in ALT_DATE), None)
    if date_col and date_col!="trade_date": df.rename(columns={date_col:"trade_date"}, inplace=True)
    if "trade_date" in df.columns: df["trade_date"] = to_dt(df["trade_date"])
    vol_col = next((c for c in df.columns if c in ALT_VOL), None)
    if vol_col and vol_col!="vol": df.rename(columns={vol_col:"vol"}, inplace=True)
    indc_col = next((c for c in df.columns if c in ALT_INDC), None)
    if indc_col and indc_col!="industry_code": df.rename(columns={indc_col:"industry_code"}, inplace=True)
    return df

# ========= 读取 =========
def read_df(sql: str, params: Optional[dict]=None)->pd.DataFrame:
    # 延迟导入以避免循环引用
    import strategy.mysql_connect as sc
    # safe_read_sql内部已强制转string并使用raw_conn，且不接受text()对象
    return sc.safe_read_sql(sql, params=params or {})

def load_daily(start:str, end:str)->pd.DataFrame:
    df = read_df(f"SELECT * FROM {TBL_DAILY} WHERE trade_date BETWEEN :s AND :e",
                 {"s": start.replace("-",""), "e": end.replace("-","")})
    df = unify_cols(df)
    need = ["st_code", "trade_date", "open", "high", "low", "close", "pre_close", "pct_chg", "vol",
            "cci", "pre_cci", "macd_macd", "pre_macd_macd", "macd_dif", "macd_dea"]

    for c in need:
        if c not in df.columns: df[c]=np.nan
    return df

def load_ind_map()->pd.DataFrame:
    try:
        df = read_df(f"SELECT * FROM {TBL_INDMAP}")
        df = unify_cols(df)
        if {"st_code","industry_code"}.issubset(df.columns):
            return df[["st_code","industry_code"]].dropna().drop_duplicates()
    except Exception as e:
        print(f"[WARN] 读取行业映射失败：{e}")
    return pd.DataFrame(columns=["st_code","industry_code"])

def load_industry_flow(start:str, end:str)->pd.DataFrame:
    try:
        df = read_df(f"SELECT * FROM {TBL_INDFLOW} WHERE trade_date BETWEEN :s AND :e",
                     {"s": start.replace("-",""), "e": end.replace("-","")})
        df = unify_cols(df)
        if "Main_net_amount" not in df.columns: return pd.DataFrame(columns=["trade_date","industry_code","Main_net_amount"])
        return df
    except Exception as e:
        print(f"[WARN] 读取行业流向细节失败：{e}")
        return pd.DataFrame(columns=["trade_date","industry_code","Main_net_amount"])

def load_stock_flow(start:str, end:str)->pd.DataFrame:
    try:
        df = read_df(f"SELECT * FROM {TBL_STKFLOW} WHERE trade_date BETWEEN :s AND :e",
                     {"s": start.replace("-",""), "e": end.replace("-","")})
        df = unify_cols(df)
        if {"st_code","Main_net_amount"}.issubset(df.columns):
            return df[["trade_date","st_code","industry_code","Main_net_amount"]]
    except Exception as e:
        print(f"[WARN] 读取行业个股流向细节失败：{e}")
    return pd.DataFrame(columns=["trade_date","st_code","industry_code","Main_net_amount"])

def load_labels()->pd.DataFrame:
    try:
        df = read_df(f"SELECT * FROM {TBL_LABELS}")
        df = unify_cols(df)
        if "st_code" not in df.columns: return pd.DataFrame(columns=["st_code"])
        num_cols = [c for c in df.columns if c!="st_code" and pd.api.types.is_numeric_dtype(df[c])]
        if not num_cols: return pd.DataFrame(columns=["st_code"])
        lab = df[["st_code"]+num_cols].groupby("st_code", as_index=False).mean()
        for c in num_cols:
            v = lab[c].astype(float)
            mn, mx = np.nanpercentile(v,5), np.nanpercentile(v,95)
            lab[c] = ((v-mn)/(mx-mn+1e-12)).clip(0,1)
        return lab
    except Exception as e:
        print(f"[WARN] 读取股票标签失败：{e}")
        return pd.DataFrame(columns=["st_code"])

def load_concepts()->pd.DataFrame:
    try:
        df = read_df(f"SELECT * FROM {TBL_CONCEPT}")
        if df.empty: return pd.DataFrame(columns=["st_code"])
        df = unify_cols(df)
        cand = [c for c in ["tag","concept","concept_name","标签","theme","concept_tag"] if c in df.columns]
        if "st_code" not in df.columns or not cand: return pd.DataFrame(columns=["st_code"])
        tagcol = cand[0]
        tmp = df[["st_code", tagcol]].dropna()
        tmp[tagcol] = tmp[tagcol].astype(str)
        oh = pd.get_dummies(tmp[tagcol], prefix="tag")
        oh = pd.concat([tmp["st_code"], oh], axis=1).groupby("st_code", as_index=False).max()
        return oh
    except Exception as e:
        print(f"[WARN] 读取概念表失败：{e}")
        return pd.DataFrame(columns=["st_code"])

# ========= 特征 =========
def ensure_indics(d: pd.DataFrame)->pd.DataFrame:
    d = d.sort_values(["st_code","trade_date"]).copy()
    for c in ["cci","pre_cci","macd_macd","pre_macd_macd","macd_dif","macd_dea"]:
        if c not in d.columns: d[c]=np.nan
    d["pre_cci"] = d["pre_cci"].fillna(d.groupby("st_code")["cci"].shift(1))
    d["pre_macd_macd"] = d["pre_macd_macd"].fillna(d.groupby("st_code")["macd_macd"].shift(1))
    d["ret_3"]  = d.groupby("st_code")["close"].pct_change(3)
    d["ret_5"]  = d.groupby("st_code")["close"].pct_change(5)
    d["vol_ma10"] = d.groupby("st_code")["vol"].transform(lambda x: x.rolling(10, min_periods=1).mean())
    d["vol_ratio"] = d["vol"]/(d["vol_ma10"]+1e-12)
    return d

def build_features(df_daily, ind_map, concept_oh, labels, ind_flow, stk_flow,
                   ind_trend_df=pd.DataFrame(), concept_trend_df=pd.DataFrame()):
    d = ensure_indics(df_daily)
    feat = []

    # 行业映射
    if not ind_map.empty:
        d = d.merge(ind_map, on="st_code", how="left")

    # 行业流入
    if not ind_flow.empty and "industry_code" in d.columns:
        tmp = ind_flow.rename(columns={"Main_net_amount":"ind_net_amt"})
        d = d.merge(tmp[["trade_date","industry_code","ind_net_amt"]],
                    on=["trade_date","industry_code"], how="left")
        d["ind_flow_z"] = d.groupby("trade_date")["ind_net_amt"].transform(
            lambda x: (x - x.mean())/(x.std()+1e-12)).fillna(0.0)
        feat.append("ind_flow_z")

    # === 新增：行业补全的趋势 ===
    if not ind_trend_df.empty:
        d = d.merge(ind_trend_df[["trade_date","industry_code","trend"]],
                    on=["trade_date","industry_code"], how="left")
        d.rename(columns={"trend":"ind_trend"}, inplace=True)

    # === 新增：概念补全的趋势 ===
    if not concept_trend_df.empty:
        d = d.merge(concept_trend_df[["trade_date","st_code","trend"]],
                    on=["trade_date","st_code"], how="left")
        d.rename(columns={"trend":"concept_trend"}, inplace=True)

    # 概念 one-hot
    if not concept_oh.empty:
        d = d.merge(concept_oh, on="st_code", how="left").fillna(0.0)
        feat += [c for c in concept_oh.columns if c!="st_code"]

    # 标签
    if not labels.empty:
        d = d.merge(labels, on="st_code", how="left").fillna(0.0)
        feat += [c for c in labels.columns if c!="st_code"]

    # 技术面
    tech = ["macd_dif","macd_dea","macd_macd","cci","pre_cci","ret_3","ret_5","vol_ratio"]
    for c in tech:
        if c not in d.columns: d[c]=0.0
    feat += tech

    d[feat] = d[feat].replace([np.inf,-np.inf], np.nan).fillna(0.0)
    return d, feat

# ========= 打分 =========
def base_score(df: pd.DataFrame) -> pd.Series:
    s = pd.Series(0.0, index=df.index, dtype=float)

    # 技术因子
    s += 10.0 * (df["macd_macd"] > 0).astype(float)
    s += 8.0 * (df.groupby("st_code")["macd_macd"].diff() > 0).astype(float).fillna(0)
    s += 6.0 * (df.groupby("st_code")["macd_dif"].diff() > 0).astype(float).fillna(0)
    s += 10.0 * (df["ret_3"] > 0.03).astype(float)
    s += 8.0 * (df["ret_5"] > 0.05).astype(float)
    s += 6.0 * (df["vol_ratio"] > 2.0).astype(float)

    # 行业趋势
    if "ind_trend" in df.columns:
        s += 12.0 * (df["ind_trend"] > 0).astype(float)
        s -= 8.0 * (df["ind_trend"] < 0).astype(float)

    # 概念趋势
    if "concept_trend" in df.columns:
        s += 8.0 * (df["concept_trend"] > 0).astype(float)
        s -= 5.0 * (df["concept_trend"] < 0).astype(float)

    # 标签
    tag_cols = [c for c in df.columns if c.startswith("tag_")]
    if tag_cols:
        s += 4.0 * df[tag_cols].sum(axis=1).clip(0, 3)

    # 风控：CCI 过低扣分
    s -= 5.0 * (df["cci"] < -200).astype(float)

    return s
# ========= 模型 =========
def load_trained_model(path:str):
    with open(path, "rb") as f: return pickle.load(f)

def cluster_weighted_scores(df_feat, feat_cols, base, model, mode:str="add"):
    if not model or "scaler" not in model or "kmeans" not in model or "cluster_stats" not in model:
        print("[WARN] 模型结构不完整，使用基础打分。")
        return base

    scaler = model["scaler"]; km = model["kmeans"]; stats = model["cluster_stats"]
    # 优先用模型保存的 feat_cols
    if "feat_cols" in model:
        feat_cols = model["feat_cols"]

    Xs = scaler.transform(df_feat[feat_cols])
    lab = km.predict(Xs)
    s_map = stats.set_index("cluster")["score"].to_dict()
    cluster_scores = np.array([s_map.get(int(c), 0.0) for c in lab])

    if mode == "scale":
        final = base.values * (1.0 + cluster_scores)
    else:
        final = base.values + cluster_scores
    return pd.Series(final, index=base.index)
# ========= 行业分散 =========
def pick_with_diversification(day_df, k, max_per_industry, priority_inds=None):
    if k<=0 or day_df.empty: return day_df.iloc[0:0]
    df=day_df.copy()
    if "industry_code" not in df.columns: df["industry_code"]="NA"
    if priority_inds:
        df["is_top_ind"]=df["industry_code"].astype(str).isin(priority_inds).astype(int)
        df=df.sort_values(["is_top_ind","MACD"],ascending=[False,False])
    else:
        df=df.sort_values("MACD",ascending=False)
    out=[];cnt={}
    for _,r in df.iterrows():
        ind=str(r["industry_code"])
        if cnt.get(ind,0)>=max_per_industry: continue
        out.append(r); cnt[ind]=cnt.get(ind,0)+1
        if len(out)>=k: break
    return pd.DataFrame(out)
def supervised_scores(df_feat, model_obj):
    """使用有监督 LightGBM 模型打分"""
    feat_cols = model_obj["feat_cols"]
    X = df_feat[feat_cols].to_numpy(float)
    proba = model_obj["model"].predict(X)  # 输出概率
    return pd.Series(proba, index=df_feat.index)

# ========= 主流程 =========
# ========= 主流程 =========
def main(df_external: pd.DataFrame,
         model: str = "supervised_model.pkl",
         out: str = "quick_pattern_out.csv",
         mode: str = "full",          # full / hybrid
         k: int = 30,
         sector_topk: int = 8,
         max_per_industry: int = 4,
         supervised_weight: float = 100.0):
    """
    df_external: 外部传入的日线行情 DataFrame（必须包含 st_code, trade_date, open, high, low, close, pre_close, change, vol 等列）
    model:       有监督模型文件路径 (pkl)
    supervised_weight: 有监督概率的权重系数，默认乘100，与指标分数在一个量级
    """
    print(111)
    # === 检查输入 ===
    # if model is None:
    #     current_dir = os.path.dirname(os.path.abspath(__file__))
    #     model = os.path.join(current_dir, "supervised_model.pkl")
    #
    # if not os.path.exists(model):
    #     raise FileNotFoundError(f"模型文件未找到: {model}")
    #
    # if df_external is None:
    #     raise ValueError("请传入 df_external，比如 main(sc.df_table_daily_qfq)")
    print(222)
    # === 数据加载 ===
    df_daily = df_external.copy()
    ind_map = load_ind_map()
    ind_flow = pd.DataFrame()
    stk_flow = pd.DataFrame()
    labels = load_labels()
    concept = load_concepts()

    # === 构建特征 ===
    feat_df, feat_cols = build_features(df_daily, ind_map, concept, labels, ind_flow, stk_flow)
    print(333)
    # === 指标打分 ===
    base = base_score(feat_df)
    print(444)
    # === 有监督模型打分 ===
    model_obj = load_trained_model(model)
    print(555)
    sup_score = supervised_scores(feat_df, model_obj)

    # === 最终分数（融合 + 归一化到0–100） ===
    final_scores = base + sup_score * supervised_weight
    minv, maxv = final_scores.min(), final_scores.max()
    if maxv > minv:
        final_scores = (final_scores - minv) / (maxv - minv) * 100
    else:
        final_scores = pd.Series(50.0, index=final_scores.index)
    print(666)
    feat_df["MACD"] = final_scores.astype(float)

    # === 选股逻辑 ===
    outs = []
    if mode == "full":
        outs.append(feat_df)
    else:
        for dte, day in feat_df.groupby("trade_date"):
            day = day.sort_values("MACD", ascending=False)
            picks = pick_with_diversification(day, k, max_per_industry)
            outs.append(picks)

    res = pd.concat(outs, ignore_index=True) if outs else feat_df.iloc[0:0]
    out_cols = ['st_code','trade_date','open','high','low','close','pre_close','pct_chg',
                'vol','cci','pre_cci','macd_macd','pre_macd_macd','MACD']

    for c in out_cols:
        if c not in res.columns:
            res[c] = np.nan

    res = res[out_cols].sort_values(["trade_date","MACD"], ascending=[True, False]).reset_index(drop=True)
    res = res.drop_duplicates(subset=["st_code","trade_date"], keep="first")

    # === 输出 ===
    print(f"[OK] 结果已生成，共 {len(res)} 条")
    print(res.head(12).to_string(index=False))

    return res


if __name__ == "__main__":
    import sc  # 这里假设 sc 是你项目里提供 df_table_daily_qfq 的模块
    stock2 = main(sc.df_table_daily_qfq)

