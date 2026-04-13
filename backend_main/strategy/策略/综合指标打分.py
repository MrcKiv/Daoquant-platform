import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
"""
核心信号：

沿用你的 日线金叉 + 周线动量 逻辑；

分数主要由 macd_dif_temp 决定。

风险修正：

如果近 20 日涨幅过大（比如 >25%），扣分；

如果日内波动过大（振幅 >10%），扣分；

如果 KDJ 超买区（J > 100）或 WR 超买（<20），扣分；

如果股价突破 BOLL 上轨过远（>10%），扣分。

结果分数：

依旧输出一个 0~100 的综合分；

符合金叉+动量 → 高分；

涨幅过大或超买 → 高分被压低，避免追高。
"""
# 参数配置
CCI_THRESHOLD = -150
KDJ_J_THRESHOLD = 100
WR_OVERBOUGHT = 20
WR_OVERSOLD = 80
BOLL_BREAKOUT_FACTOR = 1.1  # 超过上轨过多，视为风险
MAX_RISE_DAYS = 20  # 观察的涨幅周期
MAX_ALLOWED_RISE = 0.25  # 20日涨幅超过25%开始惩罚


def normalize_score(value, min_val, max_val, reverse=False):
    """将指标值标准化到0-100之间"""
    if max_val == min_val:
        return 50
    score = (value - min_val) / (max_val - min_val)
    if reverse:  # 越大分数越低
        score = 1 - score
    return float(np.clip(score * 100, 0, 100))


def score_macd(row):
    """MACD 打分：金叉、底背离等"""
    score = 0
    if (row['macd_macd'] > 0 and row['pre_macd_macd'] < 0):   # 金叉
        score += 70
    elif (row['macd_macd'] > row['pre_macd_macd']):
        score += 50
    else:
        score += 20
    # DIF 越接近0越好
    score += normalize_score(abs(row['macd_dif']), 0, abs(row['macd_dif']) + 1, reverse=True)
    return np.clip(score, 0, 100)


def score_cci(row):
    """CCI 打分"""
    if row['cci'] < CCI_THRESHOLD:
        return 80
    elif row['cci'] > 100:
        return 20
    else:
        return normalize_score(row['cci'], -200, 200, reverse=False)


def score_kdj(row):
    """KDJ 打分"""
    if row['kdj_j'] < 20:  # 超卖区
        return 80
    elif row['kdj_j'] > KDJ_J_THRESHOLD:  # 超买区
        return 20
    else:
        return normalize_score(row['kdj_j'], 0, 120, reverse=True)


def score_wr(row):
    """WR 打分"""
    if row['wr_wr1'] > WR_OVERSOLD:  # 超卖
        return 80
    elif row['wr_wr1'] < WR_OVERBOUGHT:  # 超买
        return 20
    else:
        return normalize_score(row['wr_wr1'], 0, 100, reverse=True)


def score_boll(row):
    """BOLL 打分"""
    if row['close'] < row['boll_lb']:
        return 80
    elif row['close'] > row['boll_ub'] * BOLL_BREAKOUT_FACTOR:  # 风险
        return 20
    else:
        return normalize_score(row['close'], row['boll_lb'], row['boll_ub'], reverse=True)


def risk_penalty(row):
    """风险缓释：近20日涨幅过大 / 波动率过大 扣分"""
    penalty = 0
    # 20日涨幅
    if row['close_max__20'] and row['pre_close']:
        rise = (row['close_max__20'] - row['pre_close']) / row['pre_close']
        if rise > MAX_ALLOWED_RISE:
            penalty += (rise - MAX_ALLOWED_RISE) * 200  # 超过越多，惩罚越重
    # 振幅因子（高低价差）
    amplitude = (row['high'] - row['low']) / row['close'] if row['close'] else 0
    if amplitude > 0.1:  # 日内波动超过10% → 风险
        penalty += amplitude * 100
    return penalty


def calculate_composite_score(row):
    """
    计算单行数据的综合分数
    返回 dict，包括各子指标分数、惩罚项和最终总分
    """
    macd_score = score_macd(row)
    cci_score = score_cci(row)
    kdj_score = score_kdj(row)
    wr_score = score_wr(row)
    boll_score = score_boll(row)

    # 权重加权
    base_score = (macd_score * 0.4 +
                  cci_score * 0.2 +
                  kdj_score * 0.15 +
                  wr_score * 0.15 +
                  boll_score * 0.1)

    penalty = risk_penalty(row)
    final_score = np.clip(base_score - penalty, 0, 100)

    return  final_score

