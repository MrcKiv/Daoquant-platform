import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import warnings
import multiprocessing as mp
from multiprocessing import Pool, Manager
import functools
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings('ignore')

# ====== MySQL 数据库连接信息 ======
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'stock prediction'

# ====== SQLAlchemy 引擎 ======
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)


def load_stock_data_from_db(engine, table_name='partition_table', limit=None):
    """
    从数据库加载股票数据
    """
    try:
        sql = f"SELECT * FROM {table_name}"
        if limit:
            sql += f" LIMIT {limit}"

        print(f"正在从数据库加载数据...")
        df = pd.read_sql(sql, engine)
        print(f"成功加载 {len(df)} 行数据")

        required_columns = ['st_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"缺少必要的列: {missing_columns}")

        return df

    except Exception as e:
        print(f"加载数据时出错: {e}")
        raise


def calculate_technical_indicators_for_single_stock(stock_data):
    """
    为单只股票计算技术指标（用于多进程处理）
    """
    st_code, group = stock_data
    g = group.copy()

    # 计算均线
    ma5_values = g['close'].rolling(window=5, min_periods=1).mean()
    ma10_values = g['close'].rolling(window=10, min_periods=1).mean()
    ma60_values = g['close'].rolling(window=60, min_periods=1).mean()

    # 计算MACD指标
    exp1 = g['close'].ewm(span=12, adjust=False).mean()
    exp2 = g['close'].ewm(span=26, adjust=False).mean()
    macd_dif = exp1 - exp2
    macd_dea = macd_dif.ewm(span=9, adjust=False).mean()

    # 添加技术指标列
    g['ma5'] = ma5_values.values
    g['ma10'] = ma10_values.values
    g['ma60'] = ma60_values.values
    g['macd_dif'] = macd_dif.values
    g['macd_dea'] = macd_dea.values

    return st_code, g


def calculate_technical_indicators(df, num_processes=None):
    """
    计算技术指标（支持多进程处理）
    """
    df = df.copy()
    df = df.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 初始化技术指标列
    if 'ma5' not in df.columns:
        df['ma5'] = np.nan
    if 'ma10' not in df.columns:
        df['ma10'] = np.nan
    if 'ma60' not in df.columns:
        df['ma60'] = np.nan
    if 'macd_dif' not in df.columns:
        df['macd_dif'] = np.nan
    if 'macd_dea' not in df.columns:
        df['macd_dea'] = np.nan

    # 按股票分组
    stock_groups = list(df.groupby('st_code', sort=False))

    if num_processes is None:
        num_processes = min(mp.cpu_count(), len(stock_groups))

    print(f"使用 {num_processes} 个进程计算技术指标...")

    # 使用多进程处理
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        results = list(executor.map(calculate_technical_indicators_for_single_stock, stock_groups))

    # 合并结果
    for st_code, stock_data in results:
        mask = df['st_code'] == st_code
        stock_indices = df[mask].index
        df.loc[stock_indices, 'ma5'] = stock_data['ma5'].values
        df.loc[stock_indices, 'ma10'] = stock_data['ma10'].values
        df.loc[stock_indices, 'ma60'] = stock_data['ma60'].values
        df.loc[stock_indices, 'macd_dif'] = stock_data['macd_dif'].values
        df.loc[stock_indices, 'macd_dea'] = stock_data['macd_dea'].values

    return df


def find_ma_cross_up(ma5, ma10, ma60, left, right):
    """找到5日和10日均线上穿60日均线的位置"""
    for i in range(left, right + 1):
        if i == 0:
            continue
        # 当前5日和10日均线都在60日均线上方
        if ma5[i] > ma60[i] and ma10[i] > ma60[i]:
            # 前一天至少有一条均线在60日均线下方或等于
            if (ma5[i - 1] <= ma60[i - 1]) or (ma10[i - 1] <= ma60[i - 1]):
                return i
    return None


def find_price_peak(close, start_pos, end_pos, exclude_pos=None):
    """
    在指定范围内找到股价峰值
    exclude_pos: 要排除的位置（零上金叉这一天）
    """
    peak_pos = start_pos
    peak_price = close[start_pos]

    for i in range(start_pos, end_pos + 1):
        if exclude_pos is not None and i == exclude_pos:
            continue  # 排除指定位置

        if close[i] > peak_price:
            peak_price = close[i]
            peak_pos = i

    return peak_pos, peak_price


def find_ma5_cross_down_ma10(ma5, ma10, start_pos, end_pos):
    """
    在指定范围内检测5日线下穿10日线
    """
    for i in range(start_pos, end_pos + 1):
        if i == 0:
            continue
        # 当前5日线 <= 10日线
        if ma5[i] <= ma10[i]:
            # 前一天5日线 > 10日线
            if ma5[i - 1] > ma10[i - 1]:
                return i  # 找到下穿点
    return None


def check_volume_trend(vol, start_pos, end_pos, window_size=3):
    """
    检测成交量趋势：先放大再缩小（整体趋势判断）
    使用3日滑动窗口检测成交量趋势
    """
    if end_pos - start_pos + 1 < 6:
        return False  # 数据不足，无法检测趋势

    # 计算每个3日窗口的平均成交量
    window_volumes = []
    for i in range(start_pos, end_pos - window_size + 2):
        window_avg_vol = np.mean(vol[i:i + window_size])
        window_volumes.append(window_avg_vol)

    if len(window_volumes) < 3:
        return False  # 窗口数量不足，无法检测趋势

    # 找到成交量峰值的位置
    peak_idx = np.argmax(window_volumes)

    # 检查峰值是否在边界
    if peak_idx == 0 or peak_idx == len(window_volumes) - 1:
        return False  # 峰值在边界，无法形成完整趋势

    # 使用线性回归判断整体趋势
    # 峰值前的整体趋势（应该上升）
    before_peak = window_volumes[:peak_idx + 1]
    if len(before_peak) >= 3:
        before_slope = np.polyfit(range(len(before_peak)), before_peak, 1)[0]
        before_trend = before_slope > 0
    else:
        before_trend = True  # 数据太少，默认为上升

    # 峰值后的整体趋势（应该下降）
    after_peak = window_volumes[peak_idx:]
    if len(after_peak) >= 3:
        after_slope = np.polyfit(range(len(after_peak)), after_peak, 1)[0]
        after_trend = after_slope < 0
    else:
        after_trend = True  # 数据太少，默认为下降

    # 额外的检查：确保峰值足够突出
    peak_value = window_volumes[peak_idx]
    before_avg = np.mean(before_peak[:-1]) if len(before_peak) > 1 else peak_value
    after_avg = np.mean(after_peak[1:]) if len(after_peak) > 1 else peak_value

    # 峰值应该比前后平均值都高
    peak_prominent = (peak_value > before_avg * 1.1) and (peak_value > after_avg * 1.1)

    # 返回结果：整体趋势正确且峰值突出
    return before_trend and after_trend and peak_prominent


def step1_macd_zero_up_cross_for_single_stock(stock_data, window_days=60):
    """
    为单只股票检测MACD零上金叉（用于多进程处理）
    """
    stock, group = stock_data
    g = group.copy()
    L = len(g)

    # 转换为numpy数组
    try:
        macd_dif = g['macd_dif'].to_numpy()
        macd_dea = g['macd_dea'].to_numpy()
    except Exception as e:
        return []

    # 检测MACD零上金叉
    macd_cross_positions = []
    for i in range(1, L):
        if (macd_dif[i] > 0 and macd_dea[i] > 0 and  # 都在零轴上方
                macd_dif[i - 1] <= macd_dea[i - 1] and  # 前一天DIF <= DEA
                macd_dif[i] > macd_dea[i]):  # 今天DIF > DEA
            macd_cross_positions.append(i)

    if not macd_cross_positions:
        return []

    # 记录每个金叉位置的信息
    macd_cross_details = []
    for cp in macd_cross_positions:
        # 计算左边界：如果前面数据不足60天，则使用所有前面的数据
        left = max(0, cp - window_days + 1)  # 尝试往前推60天，但不小于0
        right = cp

        start_date = g.iloc[left]['trade_date']
        end_date = g.iloc[right]['trade_date']
        actual_window_size = right - left + 1

        # 记录结果，不管窗口大小是否为60天
        macd_cross_details.append({
            'stock': stock,
            'cross_date': g.iloc[cp]['trade_date'],
            'start_date': start_date,
            'end_date': end_date,
            'cross_position': cp,
            'left_position': left,
            'right_position': right,
            'window_size': actual_window_size,
            'expected_window': window_days,
            'is_full_window': (actual_window_size == window_days),
            'note': f'实际窗口{actual_window_size}天' if actual_window_size != window_days else '完整60天窗口'
        })

    return macd_cross_details


def step1_macd_zero_up_cross_strict_60(df, window_days=60, num_processes=None):
    """
    步骤1：找出所有MACD零上金叉，每个金叉日期严格往前推60天（支持多进程处理）
    如果前面数据不足60天，则使用所有前面的数据
    滑动窗口严格是60天（或可用数据）
    """
    print("=== 步骤1：检测MACD零上金叉（严格60天窗口）===")

    required = ['st_code', 'trade_date', 'macd_dif', 'macd_dea']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 按股票分组
    groups = list(df_work.groupby('st_code', sort=False))
    total_stocks = len(groups)

    if num_processes is None:
        num_processes = min(mp.cpu_count(), total_stocks)

    print(f"总共需要处理 {total_stocks} 只股票，使用 {num_processes} 个进程")

    # 使用多进程处理
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        # 创建偏函数，固定window_days参数
        process_func = functools.partial(step1_macd_zero_up_cross_for_single_stock, window_days=window_days)
        results = list(executor.map(process_func, groups))

    # 合并结果
    macd_cross_details = []
    for result in results:
        macd_cross_details.extend(result)

    macd_cross_count = len(macd_cross_details)

    # 输出统计信息
    print(f"\n步骤1统计结果:")
    print(f"总股票数量: {total_stocks}")
    print(f"MACD零上金叉总数: {macd_cross_count}")

    return macd_cross_details


def process_window_batch(args):
    """
    处理一批窗口数据（用于多进程处理）
    """
    window_batch, df_work, step_name, process_func = args

    results = []
    for window_info in window_batch:
        try:
            result = process_func(window_info, df_work)
            if result is not None:
                results.append(result)
        except Exception as e:
            print(f"处理窗口时出错: {e}")
            continue

    return results


def parallel_process_windows(df, window_results, process_func, step_name, num_processes=None, batch_size=50):
    """
    并行处理窗口数据的通用函数
    """
    if num_processes is None:
        num_processes = min(mp.cpu_count(), len(window_results))

    print(f"使用 {num_processes} 个进程处理 {len(window_results)} 个窗口")

    # 将窗口结果分批
    batches = []
    for i in range(0, len(window_results), batch_size):
        batch = window_results[i:i + batch_size]
        batches.append((batch, df, step_name, process_func))

    # 使用多进程处理
    all_results = []
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        results = list(executor.map(process_window_batch, batches))

    # 合并结果
    for batch_results in results:
        all_results.extend(batch_results)

    return all_results


def step2_process_single_window(window_info, df_work):
    """
    处理单个窗口的均线条件检测
    """
    stock = window_info['stock']
    left_pos = window_info['left_position']
    right_pos = window_info['right_position']
    cross_pos = window_info['cross_position']

    # 获取该股票的数据
    stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

    if len(stock_data) == 0:
        return None

    # 转换为numpy数组
    try:
        ma5 = stock_data['ma5'].to_numpy()
        ma10 = stock_data['ma10'].to_numpy()
        ma60 = stock_data['ma60'].to_numpy()
    except Exception as e:
        return None

    # 检查条件A：这60天内是否所有日期都满足均线在60日线上方
    condition_a_satisfied = True
    for j in range(left_pos, right_pos + 1):
        if ma5[j] <= ma60[j] or ma10[j] <= ma60[j]:
            condition_a_satisfied = False
            break

    # 检查条件B：这60天内是否有均线上穿
    condition_b_satisfied = False
    cross_up_pos = find_ma_cross_up(ma5, ma10, ma60, left_pos, right_pos)
    if cross_up_pos is not None:
        condition_b_satisfied = True

    # 满足条件A或条件B任意一个即可
    if condition_a_satisfied or condition_b_satisfied:
        return {
            'stock': stock,
            'start_date': window_info['start_date'],
            'end_date': window_info['end_date'],
            'cross_date': window_info['cross_date'],
            'left_position': left_pos,
            'right_position': right_pos,
            'cross_position': cross_pos,
            'window_size': window_info['window_size'],
            'condition_a': condition_a_satisfied,
            'condition_b': condition_b_satisfied,
            'cross_up_pos': cross_up_pos if condition_b_satisfied else None,
            'note': window_info['note']
        }

    return None


def step2_ma_conditions_for_filtered_windows(df, step1_results, window_days=60, num_processes=None):
    """
    步骤2：在步骤1筛选出的60天窗口中检测均线条件（支持多进程处理）
    条件A：均线在60日线上方（5日线和10日线都在60日线上方）
    条件B：5日和10日均线上穿60日均线
    满足条件A或条件B任意一个即可
    """
    print("\n=== 步骤2：在筛选出的60天窗口中检测均线条件 ===")

    required = ['st_code', 'trade_date', 'ma5', 'ma10', 'ma60']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step1_results)
    print(f"需要检测 {total_windows} 个60天窗口")

    # 使用并行处理
    ma_condition_details = parallel_process_windows(
        df_work, step1_results, step2_process_single_window, "步骤2", num_processes
    )

    ma_condition_count = len(ma_condition_details)

    # 输出统计信息
    print(f"\n步骤2统计结果:")
    print(f"检测窗口数量: {total_windows}")
    print(f"均线条件满足总数: {ma_condition_count}")

    return ma_condition_details


def step3_peak_detection_for_filtered_windows(df, step2_results, window_days=60):
    """
    步骤3：在步骤2筛选出的60天窗口中进行股价峰值检测和5日线下穿10日线检测
    """
    print("\n=== 步骤3：在筛选出的60天窗口中进行峰值检测 ===")

    required = ['st_code', 'trade_date', 'ma5', 'ma10', 'ma60', 'close']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step2_results)
    peak_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个60天窗口")

    for window_idx, window_info in enumerate(step2_results):
        if window_idx % 100 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个窗口: {window_info['stock']}")

        stock = window_info['stock']
        left_pos = window_info['left_position']
        right_pos = window_info['right_position']
        cross_pos = window_info['cross_position']
        cross_up_pos = window_info['cross_up_pos']
        condition_b_satisfied = window_info['condition_b']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            ma5 = stock_data['ma5'].to_numpy()
            ma10 = stock_data['ma10'].to_numpy()
            ma60 = stock_data['ma60'].to_numpy()
            close = stock_data['close'].to_numpy()
        except Exception as e:
            continue

        peak_detection_count += 1

        # 开始股价峰值检测
        # 确定峰值检测的起始位置
        if condition_b_satisfied and cross_up_pos is not None:
            # 有上穿：从上穿日之后开始检测峰值
            peak_start_pos = cross_up_pos + 1
            if peak_start_pos >= len(stock_data):
                continue  # 上穿日在最后一天，无法检测峰值
        else:
            # 没有上穿：从序列第一天开始检测峰值
            peak_start_pos = left_pos

        # 检测股价峰值（排除零上金叉这一天）
        peak_pos, peak_price = find_price_peak(close, peak_start_pos, right_pos, exclude_pos=cross_pos)
        peak_date = stock_data.iloc[peak_pos]['trade_date']

        # 在峰值之后检测5日线下穿10日线
        cross_down_pos = find_ma5_cross_down_ma10(ma5, ma10, peak_pos + 1, right_pos)

        if cross_down_pos is not None:
            cross_down_date = stock_data.iloc[cross_down_pos]['trade_date']

            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': stock_data.iloc[cross_pos]['trade_date'],
                'window_size': window_info['window_size'],
                'condition_a': window_info['condition_a'],
                'condition_b': condition_b_satisfied,
                'cross_up_date': stock_data.iloc[cross_up_pos]['trade_date'] if cross_up_pos is not None else None,
                'peak_date': peak_date,
                'peak_price': peak_price,
                'cross_down_date': cross_down_date,
                'peak_detection_start': stock_data.iloc[peak_start_pos]['trade_date'],
                'note': '满足所有条件'
            })

    # 输出统计信息
    print(f"\n步骤3统计结果:")
    print(f"检测窗口数量: {total_windows}")
    print(f"进行峰值检测总数: {peak_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def step4_volume_trend_for_filtered_windows(df, step3_results):
    """
    步骤4：在步骤3筛选出的股票中检测成交量趋势
    检测区间：从5日均线和10日均线上穿60日均线到5日线下穿10日线的这段区间
    检测方法：以3日为滑动窗口，找到成交量呈现先放大再缩小的整体趋势
    """
    print("\n=== 步骤4：在筛选出的股票中检测成交量趋势 ===")

    required = ['st_code', 'trade_date', 'ma5', 'ma10', 'ma60', 'vol']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step3_results)
    volume_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个股票")

    for window_idx, window_info in enumerate(step3_results):
        if window_idx % 50 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个股票: {window_info['stock']}")

        stock = window_info['stock']
        cross_up_date = window_info['cross_up_date']
        cross_down_date = window_info['cross_down_date']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            ma5 = stock_data['ma5'].to_numpy()
            ma10 = stock_data['ma10'].to_numpy()
            ma60 = stock_data['ma60'].to_numpy()
            vol = stock_data['vol'].to_numpy()
        except Exception as e:
            continue

        volume_detection_count += 1

        # 确定检测区间：从上穿日期到下穿日期
        if cross_up_date is None:
            # 如果没有上穿，使用窗口的起始日期
            start_date = window_info['start_date']
        else:
            start_date = cross_up_date

        end_date = cross_down_date

        # 找到对应的位置
        start_mask = stock_data['trade_date'] == start_date
        end_mask = stock_data['trade_date'] == end_date

        if not start_mask.any() or not end_mask.any():
            continue

        start_pos = start_mask.idxmax()
        end_pos = end_mask.idxmax()

        # 确保位置顺序正确
        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos

        # 检测成交量趋势
        volume_trend_satisfied = check_volume_trend(vol, start_pos, end_pos, window_size=3)

        if volume_trend_satisfied:
            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': window_info['cross_date'],
                'window_size': window_info['window_size'],  # 添加这个字段
                'condition_a': window_info['condition_a'],  # 添加这个字段
                'condition_b': window_info['condition_b'],  # 添加这个字段
                'cross_up_date': cross_up_date,
                'cross_down_date': cross_down_date,
                'peak_date': window_info['peak_date'],
                'peak_price': window_info['peak_price'],
                'peak_detection_start': window_info['peak_detection_start'],  # 添加这个字段
                'volume_detection_start': start_date,
                'volume_detection_end': end_date,
                'note': '满足所有条件包括成交量趋势'
            })

    # 输出统计信息
    print(f"\n步骤4统计结果:")
    print(f"检测股票数量: {total_windows}")
    print(f"进行成交量检测总数: {volume_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def check_volume_price_peak_alignment(vol, close, peak_pos, start_pos, end_pos, tolerance_days=3):
    """
    检测成交量峰值与股价峰值在时间上是否对齐
    参数：
    - vol: 成交量数组
    - close: 收盘价数组
    - peak_pos: 股价峰值位置
    - start_pos: 检测区间起始位置
    - end_pos: 检测区间结束位置
    - tolerance_days: 允许的时间偏差天数（默认3天）

    返回：True表示对齐，False表示不对齐
    """
    if end_pos - start_pos + 1 < 3:
        return False  # 数据不足

    # 在检测区间内找到成交量峰值
    volume_peak_pos = start_pos
    volume_peak_value = vol[start_pos]

    for i in range(start_pos, end_pos + 1):
        if vol[i] > volume_peak_value:
            volume_peak_value = vol[i]
            volume_peak_pos = i

    # 计算股价峰值与成交量峰值的时间差
    time_diff = abs(peak_pos - volume_peak_pos)

    # 如果时间差在允许范围内，则认为对齐
    return time_diff <= tolerance_days


def step5_volume_price_peak_alignment_for_filtered_windows(df, step4_results, tolerance_days=3):
    """
    步骤5：在步骤4筛选出的股票中检测量价峰值对齐条件
    条件：成交量峰值与股价峰值在时间上相近（默认允许3天偏差）
    """
    print("\n=== 步骤5：在筛选出的股票中检测量价峰值对齐条件 ===")

    required = ['st_code', 'trade_date', 'vol', 'close']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step4_results)
    alignment_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个股票")

    for window_idx, window_info in enumerate(step4_results):
        if window_idx % 50 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个股票: {window_info['stock']}")

        stock = window_info['stock']
        volume_detection_start = window_info['volume_detection_start']
        volume_detection_end = window_info['volume_detection_end']
        peak_date = window_info['peak_date']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            vol = stock_data['vol'].to_numpy()
            close = stock_data['close'].to_numpy()
        except Exception as e:
            continue

        alignment_detection_count += 1

        # 找到成交量检测区间对应的位置
        start_mask = stock_data['trade_date'] == volume_detection_start
        end_mask = stock_data['trade_date'] == volume_detection_end
        peak_mask = stock_data['trade_date'] == peak_date

        if not start_mask.any() or not end_mask.any() or not peak_mask.any():
            continue

        start_pos = start_mask.idxmax()
        end_pos = end_mask.idxmax()
        peak_pos = peak_mask.idxmax()

        # 确保位置顺序正确
        if start_pos > end_pos:
            start_pos, end_pos = end_pos, start_pos

        # 检测量价峰值对齐
        alignment_satisfied = check_volume_price_peak_alignment(
            vol, close, peak_pos, start_pos, end_pos, tolerance_days=tolerance_days
        )

        if alignment_satisfied:
            # 找到成交量峰值位置和值
            volume_peak_pos = start_pos
            volume_peak_value = vol[start_pos]

            for i in range(start_pos, end_pos + 1):
                if vol[i] > volume_peak_value:
                    volume_peak_value = vol[i]
                    volume_peak_pos = i

            volume_peak_date = stock_data.iloc[volume_peak_pos]['trade_date']
            time_diff = abs(peak_pos - volume_peak_pos)

            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': window_info['cross_date'],
                'window_size': window_info['window_size'],
                'condition_a': window_info['condition_a'],
                'condition_b': window_info['condition_b'],
                'cross_up_date': window_info['cross_up_date'],
                'cross_down_date': window_info['cross_down_date'],
                'peak_date': peak_date,
                'peak_price': window_info['peak_price'],
                'peak_detection_start': window_info['peak_detection_start'],
                'volume_detection_start': volume_detection_start,
                'volume_detection_end': volume_detection_end,
                'volume_peak_date': volume_peak_date,
                'volume_peak_value': volume_peak_value,
                'time_difference_days': time_diff,
                'note': '满足所有条件包括量价峰值对齐'
            })

    # 输出统计信息
    print(f"\n步骤5统计结果:")
    print(f"检测股票数量: {total_windows}")
    print(f"进行量价对齐检测总数: {alignment_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def find_ma5_cross_up_ma10_after_cross_down(ma5, ma10, cross_down_pos, end_pos):
    """
    在5日线下穿10日线之后检测5日线上穿10日线
    参数：
    - ma5: 5日均线数组
    - ma10: 10日均线数组
    - cross_down_pos: 5日线下穿10日线的位置
    - end_pos: 检测的结束位置

    返回：上穿位置，如果没有找到则返回None
    """
    for i in range(cross_down_pos + 1, end_pos + 1):
        if i == 0:
            continue
        # 当前5日线 > 10日线
        if ma5[i] > ma10[i]:
            # 前一天5日线 <= 10日线
            if ma5[i - 1] <= ma10[i - 1]:
                return i  # 找到上穿点
    return None


def step6_ma5_cross_up_after_cross_down_for_filtered_windows(df, step5_results):
    """
    步骤6：在步骤5筛选出的股票中检测5日线下穿10日线后的上穿条件
    条件：在5日线下穿10日线之后，必须出现5日线上穿10日线
    """
    print("\n=== 步骤6：在筛选出的股票中检测5日线下穿10日线后的上穿条件 ===")

    required = ['st_code', 'trade_date', 'ma5', 'ma10']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step5_results)
    cross_up_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个股票")

    for window_idx, window_info in enumerate(step5_results):
        if window_idx % 50 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个股票: {window_info['stock']}")

        stock = window_info['stock']
        cross_down_date = window_info['cross_down_date']
        end_date = window_info['end_date']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            ma5 = stock_data['ma5'].to_numpy()
            ma10 = stock_data['ma10'].to_numpy()
        except Exception as e:
            continue

        cross_up_detection_count += 1

        # 找到5日线下穿10日线的位置
        cross_down_mask = stock_data['trade_date'] == cross_down_date
        end_mask = stock_data['trade_date'] == end_date

        if not cross_down_mask.any() or not end_mask.any():
            continue

        cross_down_pos = cross_down_mask.idxmax()
        end_pos = end_mask.idxmax()

        # 确保位置顺序正确
        if cross_down_pos > end_pos:
            continue  # 下穿位置在结束位置之后，无法检测后续上穿

        # 检测5日线下穿10日线后的上穿
        cross_up_pos = find_ma5_cross_up_ma10_after_cross_down(ma5, ma10, cross_down_pos, end_pos)

        if cross_up_pos is not None:
            cross_up_date = stock_data.iloc[cross_up_pos]['trade_date']

            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': window_info['cross_date'],
                'window_size': window_info['window_size'],
                'condition_a': window_info['condition_a'],
                'condition_b': window_info['condition_b'],
                'cross_up_date': window_info['cross_up_date'],
                'cross_down_date': cross_down_date,
                'cross_up_after_cross_down_date': cross_up_date,
                'peak_date': window_info['peak_date'],
                'peak_price': window_info['peak_price'],
                'peak_detection_start': window_info['peak_detection_start'],
                'volume_detection_start': window_info['volume_detection_start'],
                'volume_detection_end': window_info['volume_detection_end'],
                'volume_peak_date': window_info['volume_peak_date'],
                'volume_peak_value': window_info['volume_peak_value'],
                'time_difference_days': window_info['time_difference_days'],
                'note': '满足所有条件包括5日线下穿10日线后的上穿'
            })

    # 输出统计信息
    print(f"\n步骤6统计结果:")
    print(f"检测股票数量: {total_windows}")
    print(f"进行上穿检测总数: {cross_up_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def check_price_above_ma60_during_period(close, ma60, start_pos, end_pos):
    """
    检查在指定时间段内股价是否始终高于60日均线
    参数：
    - close: 收盘价数组
    - ma60: 60日均线数组
    - start_pos: 检测区间起始位置
    - end_pos: 检测区间结束位置

    返回：True表示始终高于60日均线，False表示有低于60日均线的情况
    """
    if start_pos >= end_pos:
        return False  # 无效区间

    # 检查区间内每一天的股价是否都高于60日均线
    for i in range(start_pos, end_pos + 1):
        if close[i] <= ma60[i]:
            return False  # 发现股价低于或等于60日均线

    return True  # 所有天都满足条件


def step7_price_above_ma60_during_cross_period_for_filtered_windows(df, step6_results):
    """
    步骤7：在步骤6筛选出的股票中检测下穿到上穿期间股价始终高于60日均线
    条件：在"5日线下穿10日线"到"5日线上穿10日线"这段时间内，股价始终高于60日均线
    """
    print("\n=== 步骤7：在筛选出的股票中检测下穿到上穿期间股价始终高于60日均线 ===")

    required = ['st_code', 'trade_date', 'close', 'ma60']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step6_results)
    price_above_ma60_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个股票")

    for window_idx, window_info in enumerate(step6_results):
        if window_idx % 50 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个股票: {window_info['stock']}")

        stock = window_info['stock']
        cross_down_date = window_info['cross_down_date']
        cross_up_after_cross_down_date = window_info['cross_up_after_cross_down_date']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            close = stock_data['close'].to_numpy()
            ma60 = stock_data['ma60'].to_numpy()
        except Exception as e:
            continue

        price_above_ma60_detection_count += 1

        # 找到下穿和上穿的日期位置
        cross_down_mask = stock_data['trade_date'] == cross_down_date
        cross_up_mask = stock_data['trade_date'] == cross_up_after_cross_down_date

        if not cross_down_mask.any() or not cross_up_mask.any():
            continue

        cross_down_pos = cross_down_mask.idxmax()
        cross_up_pos = cross_up_mask.idxmax()

        # 确保位置顺序正确
        if cross_down_pos >= cross_up_pos:
            continue  # 下穿位置不在上穿位置之前，无法检测

        # 检测在下穿到上穿期间股价是否始终高于60日均线
        price_above_ma60_satisfied = check_price_above_ma60_during_period(
            close, ma60, cross_down_pos, cross_up_pos
        )

        if price_above_ma60_satisfied:
            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': window_info['cross_date'],
                'window_size': window_info['window_size'],
                'condition_a': window_info['condition_a'],
                'condition_b': window_info['condition_b'],
                'cross_up_date': window_info['cross_up_date'],
                'cross_down_date': cross_down_date,
                'cross_up_after_cross_down_date': cross_up_after_cross_down_date,
                'price_above_ma60_period_start': cross_down_date,
                'price_above_ma60_period_end': cross_up_after_cross_down_date,
                'peak_date': window_info['peak_date'],
                'peak_price': window_info['peak_price'],
                'peak_detection_start': window_info['peak_detection_start'],
                'volume_detection_start': window_info['volume_detection_start'],
                'volume_detection_end': window_info['volume_detection_end'],
                'volume_peak_date': window_info['volume_peak_date'],
                'volume_peak_value': window_info['volume_peak_value'],
                'time_difference_days': window_info['time_difference_days'],
                'note': '满足所有条件包括下穿到上穿期间股价始终高于60日均线'
            })

    # 输出统计信息
    print(f"\n步骤7统计结果:")
    print(f"检测股票数量: {total_windows}")
    print(f"进行股价高于60日均线检测总数: {price_above_ma60_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def check_volume_ratio_condition(vol, close, cross_down_pos, cross_up_pos, peak_pos, drop_factor=0.6):
    """
    检查下穿到上穿期间的成交量均价是否远低于股价最大值所对应的成交量
    使用更宽松的逻辑：直接比较成交量均价与峰值成交量的倍数关系

    参数：
    - vol: 成交量数组
    - close: 收盘价数组
    - cross_down_pos: 下穿位置
    - cross_up_pos: 上穿位置
    - peak_pos: 股价峰值位置
    - drop_factor: 下降因子（默认0.6，即下穿到上穿期间成交量均价应低于峰值成交量的60%）

    返回：True表示满足条件，False表示不满足
    """
    if cross_down_pos >= cross_up_pos or peak_pos < cross_down_pos or peak_pos > cross_up_pos:
        return False  # 无效区间或峰值不在检测区间内

    # 计算下穿到上穿期间的成交量均价
    cross_period_volumes = vol[cross_down_pos:cross_up_pos + 1]
    cross_period_avg_volume = np.mean(cross_period_volumes)

    # 股价最大值对应的成交量（单点，更精确）
    price_max_volume = vol[peak_pos]

    # 检查数据有效性
    if np.isnan(cross_period_avg_volume) or np.isnan(price_max_volume) or price_max_volume == 0:
        return False

    # 要求下穿到上穿期间的成交量均价显著低于峰值成交量
    # 使用乘法因子方式，相对变化更明显
    return cross_period_avg_volume < price_max_volume * drop_factor


def step8_volume_ratio_condition_for_filtered_windows(df, step7_results, drop_factor=0.6):
    """
    步骤8：在步骤7筛选出的股票中检测成交量比例条件
    条件：在"5日线下穿10日线"到"5日线上穿10日线"这段时间内的成交量均价远低于股价最大值所对应的成交量
    使用更宽松的逻辑：直接比较成交量均价与峰值成交量的倍数关系
    """
    print("\n=== 步骤8：在筛选出的股票中检测成交量比例条件 ===")

    required = ['st_code', 'trade_date', 'vol', 'close']
    for c in required:
        if c not in df.columns:
            raise ValueError(f"缺少必要的列: {c}")

    # 准备数据
    df_work = df.copy()
    df_work = df_work.sort_values(['st_code', 'trade_date']).reset_index(drop=True)

    # 统计信息
    total_windows = len(step7_results)
    volume_ratio_detection_count = 0
    final_satisfied_count = 0

    # 记录满足条件的详细信息
    final_satisfied_details = []

    print(f"需要检测 {total_windows} 个股票")
    print(f"成交量下降因子: {drop_factor} (下穿到上穿期间成交量均价应低于峰值成交量的{drop_factor * 100}%)")

    for window_idx, window_info in enumerate(step7_results):
        if window_idx % 50 == 0:
            print(f"正在处理第 {window_idx}/{total_windows} 个股票: {window_info['stock']}")

        stock = window_info['stock']
        cross_down_date = window_info['cross_down_date']
        cross_up_after_cross_down_date = window_info['cross_up_after_cross_down_date']
        peak_date = window_info['peak_date']

        # 获取该股票的数据
        stock_data = df_work[df_work['st_code'] == stock].sort_values('trade_date').reset_index(drop=True)

        if len(stock_data) == 0:
            continue

        # 转换为numpy数组
        try:
            vol = stock_data['vol'].to_numpy()
            close = stock_data['close'].to_numpy()
        except Exception as e:
            continue

        volume_ratio_detection_count += 1

        # 找到下穿、上穿和峰值的日期位置
        cross_down_mask = stock_data['trade_date'] == cross_down_date
        cross_up_mask = stock_data['trade_date'] == cross_up_after_cross_down_date
        peak_mask = stock_data['trade_date'] == peak_date

        if not cross_down_mask.any() or not cross_up_mask.any() or not peak_mask.any():
            continue

        cross_down_pos = cross_down_mask.idxmax()
        cross_up_pos = cross_up_mask.idxmax()
        peak_pos = peak_mask.idxmax()

        # 确保位置顺序正确
        if cross_down_pos >= cross_up_pos:
            continue  # 下穿位置不在上穿位置之前，无法检测

        # 检测成交量比例条件
        volume_ratio_satisfied = check_volume_ratio_condition(
            vol, close, cross_down_pos, cross_up_pos, peak_pos, drop_factor
        )

        if volume_ratio_satisfied:
            # 计算具体的成交量数据用于记录
            cross_period_volumes = vol[cross_down_pos:cross_up_pos + 1]
            cross_period_avg_volume = np.mean(cross_period_volumes)

            # 股价最大值对应的成交量（单点）
            price_max_volume = vol[peak_pos]

            # 计算实际比例用于记录
            volume_ratio = cross_period_avg_volume / price_max_volume if price_max_volume > 0 else 0

            # 满足所有条件
            final_satisfied_count += 1
            final_satisfied_details.append({
                'stock': stock,
                'start_date': window_info['start_date'],
                'end_date': window_info['end_date'],
                'cross_date': window_info['cross_date'],
                'window_size': window_info['window_size'],
                'condition_a': window_info['condition_a'],
                'condition_b': window_info['condition_b'],
                'cross_up_date': window_info['cross_up_date'],
                'cross_down_date': cross_down_date,
                'cross_up_after_cross_down_date': cross_up_after_cross_down_date,
                'price_above_ma60_period_start': window_info['price_above_ma60_period_start'],
                'price_above_ma60_period_end': window_info['price_above_ma60_period_end'],
                'volume_ratio_period_start': cross_down_date,
                'volume_ratio_period_end': cross_up_after_cross_down_date,
                'cross_period_avg_volume': cross_period_avg_volume,
                'price_max_volume': price_max_volume,
                'volume_ratio': volume_ratio,
                'peak_date': peak_date,
                'peak_price': window_info['peak_price'],
                'peak_detection_start': window_info['peak_detection_start'],
                'volume_detection_start': window_info['volume_detection_start'],
                'volume_detection_end': window_info['volume_detection_end'],
                'volume_peak_date': window_info['volume_peak_date'],
                'volume_peak_value': window_info['volume_peak_value'],
                'time_difference_days': window_info['time_difference_days'],
                'note': '满足所有条件包括成交量比例条件'
            })

    # 输出统计信息
    print(f"\n步骤8统计结果:")
    print(f"检测股票数量: {total_windows}")
    print(f"进行成交量比例检测总数: {volume_ratio_detection_count}")
    print(f"最终满足所有条件总数: {final_satisfied_count}")

    return final_satisfied_details


def save_results_to_database(final_results, table_name='laoyatou_results'):
    """
    将满足条件的股票结果保存到数据库
    """
    if not final_results:
        print("没有满足条件的股票，无需保存到数据库")
        return

    try:
        # 准备数据
        data_to_save = []
        for detail in final_results:
            data_to_save.append({
                'st_code': detail['stock'],
                'cross_date': detail['cross_date'],  # 金叉日期作为时间点
                'start_date': detail['start_date'],
                'end_date': detail['end_date'],
                'window_size': detail['window_size'],
                'condition_a': detail['condition_a'],
                'condition_b': detail['condition_b'],
                'cross_up_date': detail['cross_up_date'],
                'cross_down_date': detail['cross_down_date'],
                'cross_up_after_cross_down_date': detail.get('cross_up_after_cross_down_date', None),  # 步骤6新增字段
                'price_above_ma60_period_start': detail.get('price_above_ma60_period_start', None),  # 步骤7新增字段
                'price_above_ma60_period_end': detail.get('price_above_ma60_period_end', None),  # 步骤7新增字段
                'volume_ratio_period_start': None,  # 步骤8已注释
                'volume_ratio_period_end': None,  # 步骤8已注释
                'cross_period_avg_volume': None,  # 步骤8已注释
                'price_max_volume': None,  # 步骤8已注释
                'volume_ratio': None,  # 步骤8已注释
                'peak_date': detail['peak_date'],
                'peak_price': detail['peak_price'],
                'peak_detection_start': detail['peak_detection_start'],
                'volume_detection_start': detail['volume_detection_start'],
                'volume_detection_end': detail['volume_detection_end'],
                'volume_peak_date': detail['volume_peak_date'],
                'volume_peak_value': detail['volume_peak_value'],
                'time_difference_days': detail['time_difference_days'],
                'note': detail['note'],
                'created_time': pd.Timestamp.now()
            })

        # 创建DataFrame
        df_to_save = pd.DataFrame(data_to_save)

        # 保存到数据库
        print(f"正在保存 {len(df_to_save)} 条记录到数据库表 {table_name}...")
        df_to_save.to_sql(table_name, engine, if_exists='replace', index=False, method='multi')
        print(f"成功保存到数据库表 {table_name}")

        # 显示保存的数据摘要
        print(f"\n保存的数据摘要:")
        print(f"股票数量: {df_to_save['st_code'].nunique()}")
        print(f"记录总数: {len(df_to_save)}")
        print(f"日期范围: {df_to_save['cross_date'].min()} 到 {df_to_save['cross_date'].max()}")

    except Exception as e:
        print(f"保存到数据库时出错: {e}")
        raise


def main(num_processes=None):
    """
    主函数：执行七个步骤的递进筛选（支持多进程处理）
    注意：步骤8已被注释，只使用前7个步骤

    参数：
    - num_processes: 使用的进程数，默认为CPU核心数
    """
    try:
        start_time = time.time()

        # 设置进程数
        if num_processes is None:
            num_processes = mp.cpu_count()

        print(f"=== 开始七步骤递进筛选（使用 {num_processes} 个进程）===")
        print(f"注意：步骤8已被注释，只使用前7个步骤")
        print(f"系统CPU核心数: {mp.cpu_count()}")

        # 1. 从数据库加载数据
        print("\n1. 从数据库加载数据...")
        df = load_stock_data_from_db(engine, 'partition_table')
        print(f"加载了 {len(df)} 行数据，包含 {df['st_code'].nunique()} 只股票")

        # 2. 计算技术指标（如果不存在）
        print("\n2. 计算技术指标...")
        df = calculate_technical_indicators(df, num_processes=num_processes)

        # 3. 执行步骤1：检测MACD零上金叉
        print("\n3. 执行步骤1：检测MACD零上金叉...")
        step1_start = time.time()
        step1_results = step1_macd_zero_up_cross_strict_60(df, window_days=60, num_processes=num_processes)
        step1_time = time.time() - step1_start
        print(f"步骤1完成，耗时: {step1_time:.2f}秒")

        # 4. 执行步骤2：在步骤1筛选的60天窗口中检测均线条件
        print("\n4. 执行步骤2：检测均线条件...")
        step2_start = time.time()
        step2_results = step2_ma_conditions_for_filtered_windows(df, step1_results, window_days=60,
                                                                 num_processes=num_processes)
        step2_time = time.time() - step2_start
        print(f"步骤2完成，耗时: {step2_time:.2f}秒")

        # 5. 执行步骤3：在步骤2筛选的60天窗口中进行峰值检测
        print("\n5. 执行步骤3：峰值检测...")
        step3_start = time.time()
        step3_results = step3_peak_detection_for_filtered_windows(df, step2_results, window_days=60)
        step3_time = time.time() - step3_start
        print(f"步骤3完成，耗时: {step3_time:.2f}秒")

        # 6. 执行步骤4：在步骤3筛选的股票中检测成交量趋势
        print("\n6. 执行步骤4：检测成交量趋势...")
        step4_start = time.time()
        step4_results = step4_volume_trend_for_filtered_windows(df, step3_results)
        step4_time = time.time() - step4_start
        print(f"步骤4完成，耗时: {step4_time:.2f}秒")

        # 7. 执行步骤5：在步骤4筛选的股票中检测量价峰值对齐
        print("\n7. 执行步骤5：检测量价峰值对齐...")
        step5_start = time.time()
        step5_results = step5_volume_price_peak_alignment_for_filtered_windows(df, step4_results, tolerance_days=3)
        step5_time = time.time() - step5_start
        print(f"步骤5完成，耗时: {step5_time:.2f}秒")

        # 8. 执行步骤6：在步骤5筛选的股票中检测5日线下穿10日线后的上穿条件
        print("\n8. 执行步骤6：检测5日线下穿10日线后的上穿条件...")
        step6_start = time.time()
        step6_results = step6_ma5_cross_up_after_cross_down_for_filtered_windows(df, step5_results)
        step6_time = time.time() - step6_start
        print(f"步骤6完成，耗时: {step6_time:.2f}秒")

        # 9. 执行步骤7：在步骤6筛选的股票中检测下穿到上穿期间股价始终高于60日均线
        print("\n9. 执行步骤7：检测下穿到上穿期间股价始终高于60日均线...")
        step7_start = time.time()
        step7_results = step7_price_above_ma60_during_cross_period_for_filtered_windows(df, step6_results)
        step7_time = time.time() - step7_start
        print(f"步骤7完成，耗时: {step7_time:.2f}秒")

        # 10. 执行步骤8：在步骤7筛选的股票中检测成交量比例条件（已注释）
        # print("\n10. 执行步骤8：检测成交量比例条件...")
        # step8_start = time.time()
        # final_results = step8_volume_ratio_condition_for_filtered_windows(df, step7_results, drop_factor=0.6)
        # step8_time = time.time() - step8_start
        # print(f"步骤8完成，耗时: {step8_time:.2f}秒")

        # 直接使用步骤7的结果作为最终结果
        final_results = step7_results
        step8_time = 0  # 步骤8被跳过，时间为0

        total_time = time.time() - start_time

        # 11. 最终统计
        print(f"\n=== 最终统计结果 ===")
        print(f"步骤1 - MACD零上金叉: {len(step1_results)} 个 (耗时: {step1_time:.2f}秒)")
        print(f"步骤2 - 均线条件满足: {len(step2_results)} 个 (耗时: {step2_time:.2f}秒)")
        print(f"步骤3 - 峰值检测满足: {len(step3_results)} 个 (耗时: {step3_time:.2f}秒)")
        print(f"步骤4 - 成交量趋势满足: {len(step4_results)} 个 (耗时: {step4_time:.2f}秒)")
        print(f"步骤5 - 量价峰值对齐: {len(step5_results)} 个 (耗时: {step5_time:.2f}秒)")
        print(f"步骤6 - 5日线下穿10日线后的上穿: {len(step6_results)} 个 (耗时: {step6_time:.2f}秒)")
        print(f"步骤7 - 下穿到上穿期间股价始终高于60日均线: {len(step7_results)} 个 (耗时: {step7_time:.2f}秒)")
        print(f"步骤8 - 成交量比例条件: 已跳过 (耗时: {step8_time:.2f}秒)")
        print(f"\n总耗时: {total_time:.2f}秒")

        # 12. 输出最终满足条件的详细信息
        print(f"\n=== 最终满足所有条件的股票 ===")
        print("=" * 80)
        for detail in final_results:
            print(f"股票代码: {detail['stock']}")
            print(f"窗口日期范围: {detail['start_date']} 到 {detail['end_date']}")
            print(f"金叉日期: {detail['cross_date']}")
            print(f"窗口大小: {detail['window_size']} 天")
            print(f"条件A满足: {'是' if detail['condition_a'] else '否'}")
            print(f"条件B满足: {'是' if detail['condition_b'] else '否'}")
            if detail['condition_b']:
                print(f"上穿日期: {detail['cross_up_date']}")
            print(f"峰值检测起始: {detail['peak_detection_start']}")
            print(f"股价峰值日期: {detail['peak_date']}")
            print(f"股价峰值价格: {detail['peak_price']:.2f}")
            print(f"5日线下穿10日线日期: {detail['cross_down_date']}")
            print(f"5日线下穿10日线后上穿日期: {detail['cross_up_after_cross_down_date']}")
            print(
                f"股价高于60日均线期间: {detail['price_above_ma60_period_start']} 到 {detail['price_above_ma60_period_end']}")
            # 步骤8相关字段已注释，不再显示
            # print(f"成交量比例检测期间: {detail['volume_ratio_period_start']} 到 {detail['volume_ratio_period_end']}")
            # print(f"下穿到上穿期间成交量均价: {detail['cross_period_avg_volume']:.0f}")
            # print(f"股价峰值对应成交量: {detail['price_max_volume']:.0f}")
            # print(f"成交量比例: {detail['volume_ratio']:.3f}")
            print(f"成交量检测区间: {detail['volume_detection_start']} 到 {detail['volume_detection_end']}")
            print(f"成交量峰值日期: {detail['volume_peak_date']}")
            print(f"成交量峰值: {detail['volume_peak_value']:.0f}")
            print(f"量价峰值时间差: {detail['time_difference_days']} 天")
            print(f"备注: {detail['note']}")
            print("-" * 50)

        # 13. 保存结果到数据库
        print("\n13. 保存结果到数据库...")
        save_results_to_database(final_results, 'laoyatou_results')

        return step1_results, step2_results, step3_results, step4_results, step5_results, step6_results, step7_results, final_results

    except Exception as e:
        print(f"处理过程中出错: {e}")
        raise


if __name__ == "__main__":
    # 运行主程序
    # 可以通过修改num_processes参数来控制使用的进程数
    # num_processes=None 表示使用所有CPU核心
    # num_processes=4 表示使用4个进程
    # num_processes=1 表示使用单进程（用于调试）
    # 注意：步骤8已被注释，只使用前7个步骤

    num_processes = 5  # 使用所有CPU核心，可以根据需要修改
    step1_results, step2_results, step3_results, step4_results, step5_results, step6_results, step7_results, final_results = main(
        num_processes=num_processes)