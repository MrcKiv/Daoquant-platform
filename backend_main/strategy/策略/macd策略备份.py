import logging

import numpy as np


# 打分函数
def calculate_score_macd(dif, dif_min, dif_max):
    """
    根据dif值和dif的最大值、最小值计算打分（0-100分）。
    """
    if dif >= 0:
        # 对于正DIF值，值越接近0分数越高
        score = 100 * (1 - dif / dif_max)
    else:
        # 对于负DIF值，值越远离0分数越高
        score = 100 * (1 - (dif_min - dif) / (dif_min + 0.01))

    # 确保打分在[0, 100]区间内
    return np.clip(score, 0, 100)

def calculate_score(dif, dif_min, dif_max):
    """
    根据dif值和dif的最大值、最小值计算打分（0-100分）。
    """
    # 计算标准化后的dif值
    norm_dif = (dif - dif_min) / (dif_max - dif_min)

    # 转换为打分，dif值越小分数越高
    score = 100 * (1 - norm_dif)

    # 确保打分在[0, 100]区间内
    return np.clip(score, 0, 100)


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 提取常量到配置
WEEK_MACD_MOMENTUM1 = 1.2
WEEK_MACD_MOMENTUM2 = 1.5
CCI_THRESHOLD = -150
MAX_SCORE_DECREASE = -200
MIN_SCORE_DECREASE = -300

def calculate_macd_composite_score(row, max_macd_dif, min_macd_dif, max_macd, min_macd, volatility_factor=1.0):
    score = 0.0
    macd_dif_temp = 0.0
    macd_temp = 0.0


    try:
        if row['st_code'] in max_macd_dif.index:
            max_macd_dif_value = max_macd_dif.at[row['st_code'], 'macd_dif']
            min_macd_dif_value = min_macd_dif.at[row['st_code'], 'macd_dif']
        else:
            max_macd_dif_value = -999
            min_macd_dif_value = 0
    except Exception as e:
        max_macd_dif_value = -999
        min_macd_dif_value = 0

    # 获取 max_macd 和 min_macd (使用索引访问)
    try:
        if row['st_code'] in max_macd.index:
            max_macd_value = max_macd.at[row['st_code'], 'macd_macd']
            min_macd_value = min_macd.at[row['st_code'], 'macd_macd']
        else:
            max_macd_value = -999
            min_macd_value = 0
    except Exception as e:
        max_macd_value = -999
        min_macd_value = 0
    # 计算 macd_temp 和 macd_dif_temp
    try:
        macd_temp = calculate_score_macd(row['macd_macd'], min_macd_value, max_macd_value)
        macd_dif_temp = calculate_score(row['macd_dif'], min_macd_dif_value, max_macd_dif_value)
        if max_macd_dif_value == -999:
            macd_dif_temp = -999
    except ZeroDivisionError:
        # logging.warning("Zero division encountered in score calculation. Setting default values.")
        macd_temp = 0.0
        macd_dif_temp = -999

    # 日线金叉条件
    if (row['cci'] > row['pre_cci'] and row['pre_cci'] < CCI_THRESHOLD and
        row['macd_macd'] - row['pre_macd_macd'] > 0 and row['pre_macd_macd'] < 0) or \
       (row['macd_macd'] > 0 and row['pre_macd_macd'] < 0):

        # 周线动量条件
        if ((row['week_macd_dif'] > row['lastweek_macd_dif'] and
             row['lastlastweek_macd_dif'] > row['lastweek_macd_dif'] and
             row['week_macd_dif'] - row['lastweek_macd_dif'] > WEEK_MACD_MOMENTUM1 * (row['lastlastweek_macd_dif'] - row['lastweek_macd_dif'])) or
            (row['week_macd_dif'] - row['lastweek_macd_dif'] > 0 and
             row['lastweek_macd_dif'] - row['lastlastweek_macd_dif'] > 0 and
             (row['week_macd_dif'] - row['lastweek_macd_dif']) - WEEK_MACD_MOMENTUM2 * (row['lastweek_macd_dif'] - row['lastlastweek_macd_dif']) > 0)) and \
           (row['lastweek_macd_macd'] < 0):

            # CCI 条件
            # if row['cci'] < 90 and row['cci'] - row['pre_cci'] > 3:
                # logging.info(f"Adding score for st_code {row['st_code']} on {row['trade_date']}")
                score += macd_dif_temp * volatility_factor
            # else:
            #     score += MAX_SCORE_DECREASE + macd_dif_temp * volatility_factor
        else:
            score += MAX_SCORE_DECREASE + macd_dif_temp * volatility_factor
    else:
        score += MIN_SCORE_DECREASE + macd_dif_temp * volatility_factor

    return score