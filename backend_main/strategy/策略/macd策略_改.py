import logging
import numpy as np
import pandas as pd

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 提取常量到配置
WEEK_MACD_MOMENTUM1 = 1.2
WEEK_MACD_MOMENTUM2 = 1.5
CCI_THRESHOLD = -150
MAX_SCORE_DECREASE = -200
MIN_SCORE_DECREASE = -300


def calculate_score_macd(dif, dif_min, dif_max):
    """
    根据dif值和dif的最大值、最小值计算打分（0-100分）。
    """
    # 处理数组形式的输入
    if isinstance(dif, (pd.Series, np.ndarray)):
        # 确保dif_min和dif_max也是Series且具有相同的索引
        if not isinstance(dif_min, pd.Series):
            dif_min = pd.Series(dif_min, index=dif.index)
        if not isinstance(dif_max, pd.Series):
            dif_max = pd.Series(dif_max, index=dif.index)

        score = pd.Series(np.zeros(len(dif)), index=dif.index)

        # 对于正DIF值，值越接近0分数越高
        positive_mask = dif >= 0
        score.loc[positive_mask] = 100 * (1 - dif.loc[positive_mask] / dif_max.loc[positive_mask])

        # 对于负DIF值，值越远离0分数越高
        negative_mask = dif < 0
        score.loc[negative_mask] = 100 * (
                    1 - (dif_min.loc[negative_mask] - dif.loc[negative_mask]) / (dif_min.loc[negative_mask] + 0.01))

        # 确保打分在[0, 100]区间内
        return np.clip(score, 0, 100)
    else:
        # 原始单值处理逻辑
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
    # 处理数组形式的输入
    if isinstance(dif, (pd.Series, np.ndarray)):
        # 确保dif_min和dif_max也是Series且具有相同的索引
        if not isinstance(dif_min, pd.Series):
            dif_min = pd.Series(dif_min, index=dif.index)
        if not isinstance(dif_max, pd.Series):
            dif_max = pd.Series(dif_max, index=dif.index)

        # 计算标准化后的dif值
        norm_dif = (dif - dif_min) / (dif_max - dif_min)
        # 转换为打分，dif值越小分数越高
        score = 100 * (1 - norm_dif)
        # 确保打分在[0, 100]区间内
        return np.clip(score, 0, 100)
    else:
        # 原始单值处理逻辑
        # 计算标准化后的dif值
        norm_dif = (dif - dif_min) / (dif_max - dif_min)
        # 转换为打分，dif值越小分数越高
        score = 100 * (1 - norm_dif)
        # 确保打分在[0, 100]区间内
        return np.clip(score, 0, 100)


def preprocess_macd_parameters(macd_dif_max, macd_dif_min, macd_max, macd_min):
    """
    预处理MACD参数，创建高效的查找结构
    """
    # 设置索引以提高查找效率
    macd_dif_max_indexed = macd_dif_max.set_index('st_code')
    macd_dif_min_indexed = macd_dif_min.set_index('st_code')
    macd_max_indexed = macd_max.set_index('st_code')
    macd_min_indexed = macd_min.set_index('st_code')

    return macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed


def calculate_macd_composite_score_vectorized(df, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed,
                                              macd_min_indexed):
    """
    向量化版本的MACD综合打分函数，保持与原始逻辑一致
    """
    # 初始化结果序列
    scores = pd.Series(0.0, index=df.index)

    # 获取股票代码列表
    st_codes = df['st_code']

    # 为每只股票获取对应的参数值
    max_macd_dif_values = pd.Series(index=df.index, dtype=float)
    min_macd_dif_values = pd.Series(index=df.index, dtype=float)
    max_macd_values = pd.Series(index=df.index, dtype=float)
    min_macd_values = pd.Series(index=df.index, dtype=float)

    # 使用循环设置参数值，避免.map()可能的索引问题
    for i, st_code in enumerate(st_codes):
        if st_code in macd_dif_max_indexed.index:
            max_macd_dif_values.iloc[i] = macd_dif_max_indexed.at[st_code, 'macd_dif']
        else:
            max_macd_dif_values.iloc[i] = -999

        if st_code in macd_dif_min_indexed.index:
            min_macd_dif_values.iloc[i] = macd_dif_min_indexed.at[st_code, 'macd_dif']
        else:
            min_macd_dif_values.iloc[i] = 0

        if st_code in macd_max_indexed.index:
            max_macd_values.iloc[i] = macd_max_indexed.at[st_code, 'macd_macd']
        else:
            max_macd_values.iloc[i] = -999

        if st_code in macd_min_indexed.index:
            min_macd_values.iloc[i] = macd_min_indexed.at[st_code, 'macd_macd']
        else:
            min_macd_values.iloc[i] = 0

    # 计算 macd_dif_temp
    macd_dif_temp = pd.Series(0.0, index=df.index)

    # 处理有效值
    valid_dif_mask = (max_macd_dif_values != -999) & (max_macd_dif_values != min_macd_dif_values)

    # 对有效值计算分数
    for i in range(len(df)):
        if valid_dif_mask.iloc[i]:
            try:
                macd_dif_temp.iloc[i] = calculate_score(
                    df['macd_dif'].iloc[i],
                    min_macd_dif_values.iloc[i],
                    max_macd_dif_values.iloc[i]
                )
            except:
                macd_dif_temp.iloc[i] = 0.0

    # 对于无效值设置为-999
    macd_dif_temp.loc[max_macd_dif_values == -999] = -999

    # 日线金叉条件
    daily_cross_condition1 = (
            (df['cci'] > df['pre_cci']) &
            (df['pre_cci'] < CCI_THRESHOLD) &
            ((df['macd_macd'] - df['pre_macd_macd']) > 0) &
            (df['pre_macd_macd'] < 0)
    )

    daily_cross_condition2 = (df['macd_macd'] > 0) & (df['pre_macd_macd'] < 0)
    daily_cross = daily_cross_condition1 | daily_cross_condition2

    # 周线动量条件
    weekly_momentum_condition1 = (
            (df['week_macd_dif'] > df['lastweek_macd_dif']) &
            (df['lastlastweek_macd_dif'] > df['lastweek_macd_dif']) &
            ((df['week_macd_dif'] - df['lastweek_macd_dif']) >
             WEEK_MACD_MOMENTUM1 * (df['lastlastweek_macd_dif'] - df['lastweek_macd_dif']))
    )

    weekly_momentum_condition2 = (
            ((df['week_macd_dif'] - df['lastweek_macd_dif']) > 0) &
            ((df['lastweek_macd_dif'] - df['lastlastweek_macd_dif']) > 0) &
            ((df['week_macd_dif'] - df['lastweek_macd_dif']) -
             WEEK_MACD_MOMENTUM2 * (df['lastweek_macd_dif'] - df['lastlastweek_macd_dif']) > 0)
    )

    weekly_momentum = (weekly_momentum_condition1 | weekly_momentum_condition2) & (df['lastweek_macd_macd'] < 0)

    # 组合条件计算最终得分
    # 满足日线金叉且满足周线动量条件
    full_condition = daily_cross & weekly_momentum
    scores.loc[full_condition] = macd_dif_temp.loc[full_condition]

    # 满足日线金叉但不满足周线动量条件
    partial_condition = daily_cross & ~weekly_momentum
    scores.loc[partial_condition] = MAX_SCORE_DECREASE + macd_dif_temp.loc[partial_condition]

    # 不满足日线金叉条件
    no_condition = ~daily_cross
    scores.loc[no_condition] = MIN_SCORE_DECREASE + macd_dif_temp.loc[no_condition]

    return scores


def calculate_macd_composite_score(row, max_macd_dif, min_macd_dif, max_macd, min_macd, volatility_factor=1.0):
    """
    原始逐行处理版本（保持完全一致）
    """
    score = 0.0
    macd_dif_temp = 0.0
    macd_temp = 0.0

    # 获取 max_macd_dif 和 min_macd_dif (使用索引访问)
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
        macd_temp = 0.0
        macd_dif_temp = -999

    # 日线金叉条件
    if (row['cci'] > row['pre_cci'] and row['pre_cci'] < CCI_THRESHOLD and
        row['macd_macd'] - row['pre_macd_macd'] > 0 and row['pre_macd_macd'] < 0) or \
            (row['macd_macd'] > 0 and row['pre_macd_macd'] < 0):

        # 周线动量条件
        if ((row['week_macd_dif'] > row['lastweek_macd_dif'] and
             row['lastlastweek_macd_dif'] > row['lastweek_macd_dif'] and
             row['week_macd_dif'] - row['lastweek_macd_dif'] > WEEK_MACD_MOMENTUM1 * (
                     row['lastlastweek_macd_dif'] - row['lastweek_macd_dif'])) or
            (row['week_macd_dif'] - row['lastweek_macd_dif'] > 0 and
             row['lastweek_macd_dif'] - row['lastlastweek_macd_dif'] > 0 and
             (row['week_macd_dif'] - row['lastweek_macd_dif']) - WEEK_MACD_MOMENTUM2 * (
                     row['lastweek_macd_dif'] - row['lastlastweek_macd_dif']) > 0)) and \
                (row['lastweek_macd_macd'] < 0):

            score += macd_dif_temp * volatility_factor
        else:
            score += MAX_SCORE_DECREASE + macd_dif_temp * volatility_factor
    else:
        score += MIN_SCORE_DECREASE + macd_dif_temp * volatility_factor

    return score
