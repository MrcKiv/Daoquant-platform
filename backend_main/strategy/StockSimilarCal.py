import pymysql as mdb
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import warnings

warnings.filterwarnings('ignore')

import strategy.mysql_connect as sc

# engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8")


def get_Target_Stock(st_code):
    sql1 = f"SELECT st_code, trade_date, close FROM partition_table where st_code = '{st_code}' order by trade_date asc"
    df1 = sc.safe_read_sql(sql1)
    target_stock = df1[['st_code', 'trade_date', 'close']]
    return target_stock


def get_All_Stocks():
    sql2 = "SELECT st_code, trade_date,close FROM partition_table order by trade_date asc"
    df2 = sc.safe_read_sql(sql2)
    all_stocks = df2[['st_code', 'trade_date', 'close']]
    return all_stocks


def normalize_series(series):
    """归一化时间序列"""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return np.zeros_like(series)
    return (series - mean) / std


def calculate_derivative(series):
    """计算时间序列的一阶导数"""
    if len(series) < 2:
        return np.zeros_like(series)
    derivative = np.diff(series)
    # 为了保持维度一致，在开头补零
    return np.concatenate([[0], derivative])


def custom_dtw_v3(x, y, dist=None):
    """
    自定义动态时间规整，支持多种距离函数。
    参数：
        x (list or np.array): 时间序列 x
        y (list or np.array): 时间序列 y
        dist (function): 距离度量函数，默认使用欧几里得距离
    返回：
        total_cost (float): 总匹配成本
        path (list of tuples): 最优对齐路径
    """
    # 长度检查
    if len(x) == 0 or len(y) == 0:
        return 0.01, []

    n, m = len(x), len(y)

    # 默认使用欧几里得距离
    def default_dist(a, b):
        return (a - b) ** 2

    dist = dist or default_dist

    # 初始化 DP 表 (内存优化版本)
    prev_row = np.full(m + 1, float('inf'))
    curr_row = np.full(m + 1, float('inf'))
    prev_row[0] = 0

    # 填充 DP 表 (仅保留必要信息)
    for i in range(1, n + 1):
        curr_row[0] = float('inf')
        for j in range(1, m + 1):
            cost = dist(x[i - 1], y[j - 1])
            curr_row[j] = cost + min(
                prev_row[j - 1],  # 对角线
                curr_row[j - 1],  # 左侧
                prev_row[j]  # 上方
            )
        # 交换行
        prev_row, curr_row = curr_row, prev_row

    # 最优路径和距离
    total_cost = prev_row[m]

    if total_cost == 0:
        similarity_percentage = 1.0  # 完全匹配
    else:
        # 使用指数衰减函数，对小距离更敏感
        similarity_percentage = np.exp(-total_cost * 0.1)
        # 或者使用更温和的倒数函数
        # similarity_percentage = 1.0 / (1.0 + total_cost * 0.01)

        # 确保范围在合理区间
    similarity_percentage = min(max(similarity_percentage, 0.01), 1.0)

    return similarity_percentage, []


def ddtw_distance(x, y):
    """DDTW距离计算：先求导再使用DTW"""
    x_derivative = calculate_derivative(x)
    y_derivative = calculate_derivative(y)
    return custom_dtw_v3(x_derivative, y_derivative)


def process_stock_chunk(args):
    """处理股票数据块的函数"""
    stock_chunk, target_resized, dates_dict, min_window, max_window, use_ddtw = args
    results = []

    for stock_code, stock_data in stock_chunk:
        stock_close = stock_data['close'].values
        dates = stock_data['trade_date'].values

        # 尝试不同窗口大小
        for window_size in range(min_window, max_window + 1):
            if len(stock_close) < window_size:
                continue

            # 滑动窗口提取子区间并计算相似度
            for i in range(len(stock_close) - window_size + 1):
                if i + window_size - 1 < len(dates):
                    try:
                        window_close = normalize_series(stock_close[i:i + window_size])
                        # 确保序列长度一致
                        if len(window_close) == len(target_resized):
                            if use_ddtw:
                                similarity, _ = ddtw_distance(target_resized, window_close)
                            else:
                                similarity, _ = custom_dtw_v3(target_resized, window_close)
                            results.append({
                                '股票代码': stock_code,
                                '起始日期': dates[i],
                                '终止日期': dates[i + window_size - 1],
                                '相似度': similarity,
                                '窗口大小': window_size
                            })
                    except Exception:
                        # 忽略计算异常
                        continue
    return results


def find_similar_stocks_adaptive(target_stock, all_stocks, start_date, end_date,
                                 window_size_range=(0.8, 1.2), max_workers=None, use_ddtw=False):
    """
    在所有股票中寻找与目标股票走势相似的股票，支持动态窗口大小
    参数：
        target_stock (pd.DataFrame): 单个股票的数据（含日期、收盘价等）
        all_stocks (pd.DataFrame): 所有股票的数据
        start_date (str): 目标窗口的开始日期
        end_date (str): 目标窗口的结束日期
        window_size_range (tuple): 窗口大小调整范围（比例，例如(0.8, 1.2)表示80%-120%）
        max_workers (int): 最大工作进程数，默认为CPU核心数
        use_ddtw (bool): 是否使用DDTW算法，默认False使用标准DTW
    返回：
        pd.DataFrame: 包含匹配结果的DataFrame（股票代码、起始日期、终止日期、相似度、窗口大小）
    """
    # 提取目标走势
    start_date = start_date.strftime('%Y%m%d')
    end_date = end_date.strftime('%Y%m%d')
    target_window = target_stock[(target_stock['trade_date'] >= start_date) &
                                 (target_stock['trade_date'] <= end_date)]
    target_close = target_window['close'].values
    target_len = len(target_close)

    if target_len == 0:
        return pd.DataFrame(columns=['股票代码', '起始日期', '终止日期', '相似度', '窗口大小'])

    # 窗口大小范围
    min_window = max(1, int(target_len * window_size_range[0]))
    max_window = max(min_window, int(target_len * window_size_range[1]))

    # 归一化目标序列
    target_normalized = normalize_series(target_close)

    # 将所有股票数据分组
    stock_groups = list(all_stocks.groupby('st_code'))

    # 如果股票数量很少，直接串行处理
    if len(stock_groups) < 5:
        results = []
        for stock_code, stock_data in stock_groups:
            stock_close = stock_data['close'].values
            dates = stock_data['trade_date'].values

            # 尝试不同窗口大小
            for window_size in range(min_window, max_window + 1):
                if len(stock_close) < window_size:
                    continue
                # 滑动窗口提取子区间并计算相似度
                for i in range(len(stock_close) - window_size + 1):
                    if i + window_size - 1 < len(dates):
                        try:
                            window_close = normalize_series(stock_close[i:i + window_size])
                            if len(window_close) == len(target_normalized):
                                if use_ddtw:
                                    similarity, _ = ddtw_distance(target_normalized, window_close)
                                else:
                                    similarity, _ = custom_dtw_v3(target_normalized, window_close)
                                results.append({
                                    '股票代码': stock_code,
                                    '起始日期': dates[i],
                                    '终止日期': dates[i + window_size - 1],
                                    '相似度': similarity,
                                    '窗口大小': window_size
                                })
                        except Exception:
                            continue
        results_df = pd.DataFrame(results)
        return results_df.sort_values(by='相似度', ascending=False) if not results_df.empty else results_df

    # 并行处理大量股票数据
    # 分割股票数据为多个块
    num_workers = max_workers or min(mp.cpu_count(), len(stock_groups))
    chunk_size = max(1, len(stock_groups) // num_workers)

    chunks = []
    for i in range(0, len(stock_groups), chunk_size):
        chunks.append(stock_groups[i:i + chunk_size])

    # 准备并行处理参数
    tasks = [(chunk, target_normalized, {}, min_window, max_window, use_ddtw) for chunk in chunks]

    results = []
    try:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            chunk_results = list(executor.map(process_stock_chunk, tasks))
            for chunk_result in chunk_results:
                results.extend(chunk_result)
    except Exception as e:
        # 如果并行处理失败，回退到串行处理
        print(f"并行处理失败，回退到串行处理: {e}")
        results = []
        for stock_code, stock_data in stock_groups:
            stock_close = stock_data['close'].values
            dates = stock_data['trade_date'].values

            for window_size in range(min_window, max_window + 1):
                if len(stock_close) < window_size:
                    continue
                for i in range(len(stock_close) - window_size + 1):
                    if i + window_size - 1 < len(dates):
                        try:
                            window_close = normalize_series(stock_close[i:i + window_size])
                            if len(window_close) == len(target_normalized):
                                if use_ddtw:
                                    similarity, _ = ddtw_distance(target_normalized, window_close)
                                else:
                                    similarity, _ = custom_dtw_v3(target_normalized, window_close)
                                results.append({
                                    '股票代码': stock_code,
                                    '起始日期': dates[i],
                                    '终止日期': dates[i + window_size - 1],
                                    '相似度': similarity,
                                    '窗口大小': window_size
                                })
                        except Exception:
                            continue

    # 按相似度排序并返回
    results_df = pd.DataFrame(results)
    return results_df.sort_values(by='相似度', ascending=False) if not results_df.empty else results_df


# 定义不同距离函数
def manhattan_dist(a, b):
    return abs(a - b)


def weighted_dist(a, b):
    weight = 0.5  # 假设权重
    return weight * abs(a - b)

# 测试代码示例（取消注释以运行）
# if __name__ == "__main__":
#     # 示例用法
#     # target_stock = get_Target_Stock('000001.SZ')
#     # all_stocks = get_All_Stocks()
#     # results = find_similar_stocks_adaptive(
#     #     target_stock,
#     #     all_stocks,
#     #     datetime.strptime('2022-01-04', '%Y-%m-%d').date(),
#     #     datetime.strptime('2022-02-09', '%Y-%m-%d').date(),
#     #     window_size_range=(0.8, 1.2),
#     #     use_ddtw=True  # 使用DDTW算法
#     # )
#     # print(results.head())
