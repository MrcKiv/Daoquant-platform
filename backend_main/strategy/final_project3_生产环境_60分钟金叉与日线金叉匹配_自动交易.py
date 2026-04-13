import math
import multiprocessing
import time
import numpy as np
import pymysql as mdb
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import copy
from concurrent.futures import ThreadPoolExecutor
import sys
import requests
import warnings
from backend.env import get_pymysql_config, get_sqlalchemy_database_url
from strategy.拆单交易系统 import execute_split_orders, save_to_database
from strategy.策略.日线金叉与60分钟金叉匹配优化 import MACDGoldenCrossMatcher
# from .策略.macd策略 import calculate_macd_composite_score
from strategy.策略.macd策略 import calculate_macd_composite_score, \
    calculate_macd_composite_score_vectorized, preprocess_macd_parameters
import strategy.mysql_connect as sc
from strategy.策略.quick_pattern_scoring_hbb import main
from strategy.策略.稳定上涨策略2 import load_real_data, run_strategy_pipeline
# 稳定上涨策略
warnings.filterwarnings("ignore")
# 数据库连接
conn = mdb.connect(**get_pymysql_config(charset="utf8"))
engine = create_engine(get_sqlalchemy_database_url(charset="utf8"))
cursor = conn.cursor()


def append_row(df, row):
    """Compatibility helper for pandas 2 DataFrame row appends."""
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)

# 超参
min_hold = 0.2  # 最低持股比例
max_hold_balance = 0.5  # 最高持股比例
CHAIDAN = 0  # 是否拆单，1是，0否

# 微信提示
def vxmsgsend(str):
    data = {
        'msgtype': 'text',
        'text': {'content': str},
        "mentioned_list": '@all',
        "mentioned_mobile_list": '@all'
    }

    result = requests.post(
        'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d64b17f5-c96c-457f-a612-27ef9683f23f', json=data)
    print(result.text)


# 日期处理
# def find_last_open_date(engine, initial_date_str):
#     def query_specific_date(date_str):
#         sql = f"SELECT * FROM 股票日历_new WHERE cal_date = '{date_str}'"
#         dfa_specific = pd.read_sql(sql, engine)
#         return pd.DataFrame(dfa_specific[['cal_date', 'is_open']])
#
#     def decrease_date(date_str, days=1):
#         date_format = '%Y%m%d'
#         date_obj = datetime.strptime(date_str, date_format)
#         new_date_obj = date_obj - timedelta(days=days)
#         return new_date_obj.strftime(date_format)
#
#     date_str = initial_date_str
#
#     print(date_str)
#     result_df = query_specific_date(date_str)
#     is_open = result_df['is_open'].iloc[-1]
#
#     while is_open == '0':
#         date_str = decrease_date(date_str)
#         result_df = query_specific_date(date_str)
#         is_open = result_df['is_open'].iloc[-1]
#
#     return result_df['cal_date'].iloc[-1]
def find_next_open_date(engine, initial_date_str):
    """
    从指定日期开始，向后查找最近一个股票交易日
    """

    def query_specific_date(date_str):
        sql = f"SELECT * FROM 股票日历_new WHERE cal_date = '{date_str}'"
        dfa_specific = sc.safe_read_sql(sql)
        return pd.DataFrame(dfa_specific[['cal_date', 'is_open']])

    def increase_date(date_str, days=1):
        date_format = '%Y%m%d'
        try:
            # 直接使用 timedelta 增加日期，避免手动计算
            date_obj = datetime.strptime(date_str, date_format)
            new_date_obj = date_obj + timedelta(days=days)
            return new_date_obj.strftime(date_format)
        except ValueError:
            # 如果日期无效，使用 timedelta 来正确计算下一天
            # 先尝试解析年月部分，然后加一天
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])

            # 创建一个有效的日期然后加一天
            # 使用每月1号作为基准，避免无效日期问题
            try:
                base_date = datetime(year, month, 1)
                # 计算应该是当月的第几天
                target_date = base_date + timedelta(days=day - 1 + days)
                return target_date.strftime(date_format)
            except ValueError:
                # 如果还是无效，就从上一个月的最后一天开始计算
                if month == 1:
                    base_date = datetime(year - 1, 12, 31)
                else:
                    # 获取上一个月的最后一天
                    if month <= 10:
                        base_date = datetime(year, month - 1, 28)  # 安全起见使用28号
                    else:
                        base_date = datetime(year, month - 1, 28)

                target_date = base_date + timedelta(days=days + 3)  # 大概加几天确保到下一个月
                return target_date.strftime(date_format)

    # 从输入日期开始查找
    date_str = initial_date_str
    print("Initial date:", date_str)

    # 直接开始查找，让 increase_date 函数处理无效日期
    result_df = query_specific_date(date_str)

    # 如果输入日期在数据库中找不到，则向后查找直到找到
    while result_df.empty:
        print(f"Date {date_str} not found in database")
        date_str = increase_date(date_str)
        print(f"Trying next date: {date_str}")
        result_df = query_specific_date(date_str)

    print("Valid date found:", date_str)

    # 检查是否为交易日
    if not result_df.empty:
        is_open = result_df['is_open'].iloc[-1]
        while is_open == '0':
            date_str = increase_date(date_str)
            print(f"Date {date_str} is not a trading day, checking next")
            result_df = query_specific_date(date_str)
            # 处理可能的空结果
            while result_df.empty:
                date_str = increase_date(date_str)
                print(f"Date {date_str} not found, checking next")
                result_df = query_specific_date(date_str)
            is_open = result_df['is_open'].iloc[-1] if not result_df.empty else '0'

    final_date = result_df['cal_date'].iloc[-1] if not result_df.empty else initial_date_str
    print(f"Found next trading day: {final_date}")
    return final_date


# 然后修改这行代码：


# 根据大盘涨跌股票数目的比例决定是否买股及投资比例。
def decide_investment(balance, min_hold, max_hold_balance):
    """
    根据大盘涨跌股票数目的比例决定是否买股及投资比例。

    参数:
    balance (float): 股票上涨数目与总数的比例。

    返回:
    float: 投资比例，0 表示不投资。
    """
    if balance <= min_hold:
        return 0.0  # 不投资
    elif min_hold < balance < max_hold_balance:
        return balance  # 投资比例为 balance

    # 其他情况下，默认投资比例为 1
    return 1.0


# 多线程，打分并行化处理
def process_group(group, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed):
    # 使用预处理参数的向量化操作
    group.loc[:, 'MACD'] = calculate_macd_composite_score_vectorized(
        group, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed)
    return group


# 新的worker函数，使用预处理的参数
def worker_with_params(task_queue, result_queue):
    while True:
        try:
            chunk_data = task_queue.get(timeout=5)  # 设置超时时间
            if chunk_data is None:
                break  # 如果收到None，则退出循环

            chunk, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed = chunk_data
            result = process_group(chunk, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed,
                                   macd_min_indexed)
            result_queue.put(result)
        except multiprocessing.Queue.Empty:
            continue
        except Exception as e:
            print(f"Worker error: {e}")
            continue


# 多线程，打分并行化处理
def worker(task_queue, result_queue, max_macd_dif, min_macd_dif, max_macd, min_macd):
    while True:
        try:
            chunk = task_queue.get(timeout=5)  # 设置超时时间
            if chunk is None:
                break  # 如果收到None，则退出循环
            result = process_group(chunk, max_macd_dif, min_macd_dif, max_macd, min_macd)
            result_queue.put(result)
        except multiprocessing.Queue.Empty:
            continue
        except Exception as e:
            task_queue.put(chunk)  # 将任务重新放入队列
            continue


# 计算macd打分，并返回DataFrame
class trading_strategy():
    def __init__(self, factors):
        self.factors = factors

    # 按交易日取数据
    def get_data(self, start_date, end_date):
        df = sc.df_table_daily_qfq
        return df

    def get_macd_dif_max(self):
        query = """
            SELECT *
            FROM macd_dif_max_大表22年五月至23年五月
            """
        macd_max = sc.safe_read_sql(query)
        return macd_max

    def get_macd_dif_min(self):
        query = """
             SELECT *
             FROM macd_dif_min_大表22年五月至23年五月
            """
        macd_min = sc.safe_read_sql(query)
        return macd_min

    def get_macd_max(self):
        query = """
            SELECT *
            FROM macd_max
            """
        macd_min = sc.safe_read_sql(query)
        return macd_min

    def get_macd_min(self):
        query = """
               SELECT *
               FROM macd_min
               """
        macd_min = sc.safe_read_sql(query)
        return macd_min

    def get_industry_code(self):
        industry_code = sc.df_table_industry
        return industry_code

    # 计算所有股票MACD、WR、BOLL和KDJ指标值，并返回DataFrame
    @staticmethod
    def calc(stock_data, macd_dif_max, macd_dif_min, macd_max, macd_min, industry_code):
        # 预处理索引数据，创建高效的参数查找结构
        macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed = preprocess_macd_parameters(
            macd_dif_max, macd_dif_min, macd_max, macd_min)

        # 分割数据
        num_processes = min(8, multiprocessing.cpu_count())
        chunk_size = len(stock_data) // num_processes
        remainder = len(stock_data) % num_processes

        chunks = []
        start = 0
        for i in range(num_processes):
            end = start + chunk_size + (1 if i < remainder else 0)
            chunks.append(stock_data.iloc[start:end])
            start = end

        print('chunks', len(chunks))

        # 创建任务队列和结果队列
        task_queue = multiprocessing.Manager().Queue()
        result_queue = multiprocessing.Manager().Queue()

        # 将预处理的参数传递给工作进程
        for chunk in chunks:
            task_queue.put((chunk, macd_dif_max_indexed, macd_dif_min_indexed, macd_max_indexed, macd_min_indexed))

        # 创建进程池
        processes = []
        for _ in range(num_processes):
            p = multiprocessing.Process(target=worker_with_params,
                                        args=(task_queue, result_queue))
            p.start()
            processes.append(p)

        # 等待所有任务完成
        for _ in range(num_processes):
            task_queue.put(None)  # 发送结束信号

        for p in processes:
            p.join()

        # 合并处理结果
        try:
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())

            stock_data['MACD'] = pd.concat(results)['MACD']
        except Exception as e:
            print(f"Error merging results: {e}")
            pass

        selected_columns = ['st_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'pct_chg',
                            'vol', 'cci', 'pre_cci', 'macd_macd', 'pre_macd_macd', 'MACD']
        stock_data = stock_data[selected_columns]
        return stock_data

    # 在给定的股票数据stock_data中添加两列：position和signal，并根据技术指标WR和CCI的值生成买入信号。
    def generate_signal_buy(self, stock_data):
        # 在stock_data添加两新列'position'和'signal'
        stock_data['position'] = 0
        stock_data['signal'] = 0
        # 定义买入条件
        condition_buy = (stock_data['wr'] < -80) & (stock_data['CCI'] < -100)
        # condition_buy = (stock_data['open'] < stock_data['LOWER']) & (stock_data['close'] > stock_data['LOWER'])
        # 将符合买入条件的股票的'signal'设置为1
        stock_data.loc[condition_buy, 'signal'] = 1

        return stock_data


# 确定因子
class MachineLearning():
    def __init__(self, factors):
        self.factors = factors

    @staticmethod
    def calc(stock_data, factor):
        if '线性回归' in factor:
            stock_data['线性回归'] = (stock_data['open'] - stock_data['close']) / stock_data['open']
            # print('this 线性回归', stock_data.head(10))
        return stock_data


# 以下编写的代码是将上涨下跌等作为参数进行买和卖操作。
class SaleCondition:
    def __init__(self, stocklist, sell_policy_list, current_day):
        self.stocklist = stocklist
        self.sell_policy_list = sell_policy_list
        self.current_day = current_day

    # 筛选出符合上涨幅度条件的股票
    def up(self):
        up_ratio = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            current_close = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
            current_close = current_close.reset_index(drop=True)
            if len(list(current_close['close'])) == 0:
                continue
            old_close = sc.df_table_transaction[
                sc.df_table_transaction['st_code'] == stocklist['st_code'][i]].sort_values(
                by='trade_date', ascending=False)
            old_close = old_close.reset_index(drop=True)
            condition = ((current_close['high'][0] - old_close['trade_price'][0]) / old_close['trade_price'][
                0] >= int(self.sell_policy_list['上涨幅度']) / 100)
            if condition:
                up_ratio_selected = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
                up_ratio = pd.concat([up_ratio, up_ratio_selected], axis=0, ignore_index=True)
        up_ratio = up_ratio.reset_index(drop=True)

        return up_ratio

    def down(self):
        down_ratio = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            current_close = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
            current_close = current_close.reset_index(drop=True)
            if len(list(current_close['close'])) == 0:
                continue
            old_close = sc.df_table_transaction[
                sc.df_table_transaction['st_code'] == stocklist['st_code'][i]].sort_values(
                by='trade_date', ascending=False)
            old_close = old_close.reset_index(drop=True)
            old_close2 = stock_data[(stock_data['st_code'] == stocklist['st_code'][i]) &
                                    (stock_data['trade_date'] == self.current_day)]
            old_close2 = old_close2.reset_index(drop=True)
            condition = (current_close['low'][0] - old_close['trade_price'][0]) / old_close['trade_price'][
                0] <= -(int(self.sell_policy_list['下跌幅度']) / 100)
            if condition:
                down_ratio_selected = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
                down_ratio = pd.concat([down_ratio, down_ratio_selected], axis=0, ignore_index=True)
        down_ratio = down_ratio.reset_index(drop=True)
        return down_ratio

    # 筛选符合最大持股天数条件的股票数据
    def last(self):
        last_day = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            try:
                # 检查当前日期是否为交易日
                current_close = sc.df_table_calendar[(sc.df_table_calendar['cal_date'] == self.current_day)]
                current_close = current_close.reset_index(drop=True)

                # 检查数据是否为空
                if current_close.empty or len(current_close) == 0:
                    continue

                # 安全访问is_open列
                if len(current_close['is_open']) == 0 or current_close['is_open'].iloc[0] == '0':
                    continue

                # 获取该股票的交易记录
                data = sc.df_table_transaction[
                    sc.df_table_transaction['st_code'] == stocklist['st_code'][i]].sort_values(
                    by='trade_date', ascending=False)
                data = data.reset_index(drop=True)

                # 检查交易数据是否为空
                if data.empty or len(data) == 0 or len(data['trade_date']) == 0:
                    continue

                # 获取买入日期的交易日信息
                old_date = sc.df_table_calendar[sc.df_table_calendar['cal_date'] == data['trade_date'].iloc[0]]
                old_date = old_date.reset_index(drop=True)

                # 检查旧日期数据是否为空
                if old_date.empty or len(old_date) == 0 or len(old_date['trade_day']) == 0:
                    continue

                # 获取当前日期的交易日信息
                current_date = sc.df_table_calendar[sc.df_table_calendar['cal_date'] == self.current_day]
                current_date = current_date.reset_index(drop=True)

                # 检查当前日期数据是否为空
                if current_date.empty or len(current_date) == 0 or len(current_date['trade_day']) == 0:
                    continue

                # 计算持股天数
                condition = (current_date['trade_day'].iloc[0] - old_date['trade_day'].iloc[0] > int(
                    self.sell_policy_list['最大持股天数']))

                if condition:
                    last_day_selected = stock_data[
                        (stock_data['st_code'] == stocklist['st_code'][i]) & (
                                stock_data['trade_date'] == self.current_day)]
                    last_day = pd.concat([last_day, last_day_selected], axis=0, ignore_index=True)
            except Exception as e:
                print(
                    f"处理股票 {stocklist['st_code'][i] if i < len(stocklist) else 'unknown'} 的最大持股天数时出错: {e}")
                continue

        last_day = last_day.reset_index(drop=True)
        return last_day

    # 关于boll函数的买和卖还没定义。
    def boll_sell(self):
        Boll_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) & (
                        stock_data['trade_date'] == self.current_day)]
            current_data = current_data.reset_index(drop=True)
            if len(list(current_data['close'])) == 0:
                continue
            condition = (current_data['open'][0] > current_data['UPPER'][0]) & current_data['close'][
                0] <= current_data['UPPER'][0]
            if condition:
                Boll_sell_selected = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (
                            stock_data['trade_date'] == self.current_day)]
                Boll_sell = pd.concat([Boll_sell, Boll_sell_selected], axis=0, ignore_index=True)
        Boll_sell = Boll_sell.reset_index(drop=True)
        return Boll_sell

    def cci_sell(self):
        CCI_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            current_cci = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            if len(current_cci) == 0:
                continue
            if current_cci['cci'].item() - current_cci['pre_cci'].item() < 3:
                CCI_sell_list = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
                CCI_sell = pd.concat([CCI_sell, CCI_sell_list], axis=0, ignore_index=True)
        CCI_sell = CCI_sell.reset_index(drop=True)
        return CCI_sell

    def macd_sell(self):
        MACD_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)
        for i in range(len(stocklist)):
            current_macd = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            if len(current_macd) == 0:
                continue
            if current_macd['macd_macd'].item() < current_macd['pre_macd_macd'].item():
                MACD_sell_list = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == self.current_day)]
                MACD_sell = pd.concat([MACD_sell, MACD_sell_list], axis=0, ignore_index=True)
        MACD_sell = MACD_sell.reset_index(drop=True)
        return MACD_sell

    def macd_bias_sell(self):
        MACD_bias_sell = pd.DataFrame(columns=stock_data.columns)
        return MACD_bias_sell


# 选择收益基准
def IncomeBaseline(start_date, end_date, Baseline):
    if isinstance(start_date, str) and len(start_date) == 8:
        start_date = datetime.strptime(start_date, '%Y%m%d')
    else:
        start_date = start_date

    if isinstance(end_date, str) and len(end_date) == 8:
        end_date = datetime.strptime(end_date, '%Y%m%d')
    else:
        end_date = end_date

    if '深证' in Baseline:
        filtered_data = sc.df_table_index[(sc.df_table_index['st_code'] == '399001.SZ') &
                                              (sc.df_table_index['trade_date'] >= start_date) &
                                              (sc.df_table_index['trade_date'] <= end_date)]
        filtered_data = filtered_data.reset_index(drop=True)

    if '上证指数' in Baseline:
        print(1111)
        filtered_data = sc.df_table_index[(sc.df_table_index['st_code'] == '000001.SH') &
                                              (sc.df_table_index['trade_date'] >= start_date) &
                                              (sc.df_table_index['trade_date'] <= end_date)]
        filtered_data = filtered_data.reset_index(drop=True)
        print('filtered_data',filtered_data)

    if '创业' in Baseline:
        filtered_data = sc.df_table_index[(sc.df_table_index['st_code'] == '399006.SZ') &
                                              (sc.df_table_index['trade_date'] >= start_date) &
                                              (sc.df_table_index['trade_date'] <= end_date)]
        filtered_data = filtered_data.reset_index(drop=True)

    return filtered_data


# 检查是否存在历史回测数据
def check_existing_backtest_data(sid, uid, start_date, end_date):
    """
    检查数据库中是否存在历史回测数据，并返回最后一个已回测日期

    参数:
    sid: 策略ID
    uid: 用户ID
    start_date: 原计划开始日期
    end_date: 原计划结束日期

    返回:
    last_backtest_date: 最后一个已回测日期，如果不存在则返回None
    """
    try:
        sql = """
        SELECT MAX(trade_date) as last_date 
        FROM new_war_每日统计表 
        WHERE strategy_id = %s AND user_id = %s
        """
        # 使用 query_sql 替代 execute_sql_query，并处理返回的DataFrame
        result_df = sc.query_sql(sql, (sid, uid))
        print(result_df)
        if not result_df.empty and pd.notna(result_df.iloc[0]['last_date']):
            last_date = result_df.iloc[0]['last_date']

            if last_date >= end_date:
                print(f"策略 {sid} 已有完整回测数据，无需重复回测")
                return end_date
            elif last_date >= start_date:
                print(f"发现历史回测数据，最后回测日期: {last_date}")
                return last_date
    except Exception as e:
        print(f"检查历史回测数据时出错: {e}")

    return None


def check_start_date_consistency(sid, uid, start_date):
    """
    检查数据库中的开始日期是否与当前开始日期一致

    参数:
    sid: 策略ID
    uid: 用户ID
    start_date: 当前计划开始日期

    返回:
    bool: 如果数据库开始日期与当前开始日期一致返回True，否则返回False
    """
    try:
        sql = """
        SELECT MIN(trade_date) as start_date 
        FROM new_war_每日统计表 
        WHERE strategy_id = %s AND user_id = %s
        """
        result_df = sc.query_sql(sql, (sid, uid))
        print(sid, uid, start_date)
        print(result_df)
        if not result_df.empty and pd.notna(result_df.iloc[0]['start_date']):
            db_start_date = result_df.iloc[0]['start_date']
            # 比较日期是否一致
            if db_start_date == start_date:
                print(f"数据库开始日期({db_start_date})与当前开始日期({start_date})一致")
                return True
            else:
                print(f"数据库开始日期({db_start_date})与当前开始日期({start_date})不一致")
                return False
        else:
            # 如果没有历史数据，认为是一致的（新策略）
            print("未找到历史回测数据，视为开始日期一致")
            return True
    except Exception as e:
        print(f"检查开始日期一致性时出错: {e}")
        # 出错时保守处理，返回False避免错误的增量回测
        return False


# 回测进度日志
def log_backtest_progress(current_date, total_days, processed_days):
    progress = (processed_days / total_days) * 100
    print(f"回测进度: {progress:.2f}% (日期: {current_date})")



def buy_stock(stocklist, candidate_stock, max_stock_num, remained_money, current_day, fund_data, sid, uid):
    if isinstance(current_day, str) and len(current_day) == 8:
        current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
    elif isinstance(current_day, datetime):
        current_date_obj = current_day.date()
    else:
        current_date_obj = current_day
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
    buystocklist = pd.DataFrame(
        columns=["st_code", "trade_date", "trade_type", "trade_price", "number_of_transactions", "turnover"],
        dtype=object)

    # 单只股票最大投入资金
    min_invest_money = fund_data * 0.1
    # 设置买入最小持仓资金
    max_invest_num = remained_money // (min_invest_money)
    # 获取当天的股票数据
    invest_stock_data = stock_data[stock_data['trade_date'] == current_date_obj]
    # 计算 change 列大于 0 的行数
    positive_changes = (invest_stock_data['pct_chg'] > 0).sum()
    # 计算 change 列小于 0 的行数
    negative_changes = (invest_stock_data['pct_chg'] <= 0).sum()
    # balance1股票上涨数目与总数的比例。
    balance1 = positive_changes / (negative_changes + positive_changes)
    # invest_balance投资比例
    invest_balance = decide_investment(balance1, min_hold, max_hold_balance)
    remained_money_invest = remained_money
    count = 0

    candidate_stock = candidate_stock.sort_values(by='MACD', ascending=False).reset_index(drop=True)

    for i in range(len(candidate_stock)):
        if (candidate_stock['MACD'][i] > 0):
            count += 1
        else:
            break
    print("候选买股数目:", count)
    num = max_stock_num - len(stocklist)  # 当前还需要购买股票的数量
    num = min(num, count, max_invest_num)
    print("实际买股数目:", num)

    if num == 0:
        if current_day == today_date:
            # vxmsgsend('测试\n基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
            pass
            # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
        return stocklist, remained_money

    elif invest_balance == 0:
        if current_day == today_date:
            # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
            pass
            # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
        return stocklist, remained_money

    elif invest_balance == 1:
        # 每只股票的最大购买金额
        max_cost = min((remained_money_invest) / num, min_invest_money)  # 拿出剩余资金的投入,若股票太少，则投入最大资金
    else:
        max_cost = min((remained_money_invest) / num, min_invest_money)  # 每只股票的最大购买金额

    stocklist = stocklist.reset_index(drop=True)
    print("最终买股列表condidate_stock", candidate_stock)
    while num > 0:
        for i in range(len(candidate_stock)):
            if num == 0:
                break
            if (candidate_stock['MACD'][i] < 0):
                num = 0
                break


            print("type(sc.df_table_daily_qfq['trade_date'][0]",type(sc.df_table_daily_qfq['trade_date'][0]))
            print("sc.df_table_daily_qfq['st_code'][0]",type(sc.df_table_daily_qfq['st_code'][0]))
            print("candidate_stock['st_code'][0]",type(candidate_stock['st_code'][0]))
            print("type(current_day)",type(current_day))

            # 直接使用候选股票表，不考虑 industry_code 表
            data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == candidate_stock['st_code'][i]) & (
                    sc.df_table_daily_qfq['trade_date'] == current_date_obj)]
            data = data.reset_index(drop=True)

            if data.empty:
                num = num - 1
                print('无当天数据', candidate_stock['st_code'][i], current_day)
                continue

            if 100 * data['close'][0] >= max_cost or 100 * data['close'][0] >= remained_money or (
                    data['close'][0] - data['pre_close'][0]) / data['pre_close'][0] > 0.11:
                num = num - 1
                continue
            else:
                share = int(max_cost / (100 * data['close'][0]))  # 买入的多少手
                buystocklist.loc[0, 'st_code'] = candidate_stock['st_code'][i]
                buystocklist.loc[0, 'trade_date'] = current_day
                buystocklist.loc[0, 'turnover'] = float(share * 100 * data['close'][0])  # turnover成交额
                # 表示买入的交易量（单位：股）
                buystocklist.loc[0, 'number_of_transactions'] = share * 100
                buystocklist.loc[0, 'trade_price'] = float(data['close'][0])
                remained_money = remained_money - share * 100 * data['close'][0]
                # round(number,digits)digits>0，四舍五入到指定的小数位
                remained_money = round(remained_money, 2)
                buystocklist.loc[0, 'trade_type'] = '买入'
                stocklist.loc[len(stocklist)] = candidate_stock.loc[i]  # 将刚买入的股票添加到stocklist中
                stocklist.loc[(stocklist['trade_date'] == current_date_obj) & (
                        stocklist['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                # 实现插入操作
                add_rows = (
                    {'st_code': buystocklist.loc[0, 'st_code'], 'trade_date': buystocklist.loc[0, 'trade_date'],
                     "trade_type": '买入', "trade_price": buystocklist.loc[0, 'trade_price'],
                     "number_of_transactions": buystocklist.loc[0, 'number_of_transactions'],
                     "turnover": buystocklist.loc[0, 'turnover'], 'strategy_id': sid, 'user_id': uid})
                # global  sc.df_table_transaction
                sc.df_table_transaction = append_row(sc.df_table_transaction, add_rows)
                stock_data.loc[(stock_data['trade_date'] == current_date_obj) & (
                        stock_data['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                num = num - 1

    stocklist = stocklist.reset_index(drop=True)
    print("买入股票:", stocklist)
    return stocklist, remained_money



# 筛选卖出的候选股票
def macd_cross_sell_strategy(candidate_sell_stock, current_day, sid, uid):
    """
    基于MACD金叉匹配的卖股策略：
    1. 检查持股股票当天日线是否形成金叉，若形成则卖出
    2. 若未形成金叉：
       - 持股三天强制卖出
       - 下跌2%止损卖出
       - 上涨5%止盈卖出
    """
    if isinstance(current_day, str) and len(current_day) == 8:
        current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
    elif isinstance(current_day, datetime):
        current_date_obj = current_day.date()
    else:
        current_date_obj = current_day

    stocks_to_sell = pd.DataFrame(columns=stock_data.columns)

    for i in range(len(candidate_sell_stock)):
        stock_code = candidate_sell_stock['st_code'][i]

        # 获取该股票的买入信息
        buy_info = sc.df_table_transaction[
            (sc.df_table_transaction['st_code'] == stock_code) &
            (sc.df_table_transaction['trade_type'] == '买入')
            ].sort_values(by='trade_date', ascending=False)

        if buy_info.empty:
            continue

        buy_info = buy_info.reset_index(drop=True)
        buy_date = buy_info['trade_date'][0]
        buy_price = buy_info['trade_price'][0]

        # 获取当前股票数据
        current_data = stock_data[
            (stock_data['st_code'] == stock_code) &
            (stock_data['trade_date'] == current_date_obj)
            ]

        if current_data.empty:
            continue

        current_data = current_data.reset_index(drop=True)
        current_price = current_data['close'][0]

        # 计算涨跌幅
        price_change_ratio = (current_price - buy_price) / buy_price

        # 检查当天是否形成日线金叉（简化判断：前一天macd小于0，当天macd大于0）
        is_daily_golden_cross = (
            (current_data['pre_macd_macd'][0] < 0) &
            (current_data['macd_macd'][0] > 0)
        )
        # 如果开盘价跳空低开，且低于止损位，则以开盘价卖出
        is_open_gap_down = current_data['open'][0] < current_data['pre_close'][0] * 0.98

        # 检查持股天数
        buy_calendar = sc.df_table_calendar[sc.df_table_calendar['cal_date'] == buy_date]
        current_calendar = sc.df_table_calendar[sc.df_table_calendar['cal_date'] == current_day]

        if not buy_calendar.empty and not current_calendar.empty:
            hold_days = current_calendar['trade_day'].iloc[0] - buy_calendar['trade_day'].iloc[0]
        else:
            # 如果无法获取交易日信息，则使用自然日计算
            if isinstance(buy_date, str):
                buy_date_obj = datetime.strptime(buy_date, '%Y%m%d').date()
            else:
                buy_date_obj = buy_date
            hold_days = (current_date_obj - buy_date_obj).days

        # 判断是否需要卖出
        should_sell = False
        sell_reason = ""
        if is_open_gap_down:
            should_sell = True
            sell_reason = "开盘跳空低开止损"
        # # 条件1: 当天形成日线金叉则卖出
        # elif is_daily_golden_cross:
        #     should_sell = True
        #     sell_reason = "当天形成日线金叉"

        # 条件2: 若未形成金叉，则按以下条件判断
        elif hold_days >= 3:
            should_sell = True
            sell_reason = "持股3天强制卖出"
        elif price_change_ratio <= -0.02:
            should_sell = True
            sell_reason = "下跌2%止损"
        elif price_change_ratio >= 0.05:
            should_sell = True
            sell_reason = "上涨3%止盈"

        # 如果需要卖出，则添加到卖出列表
        if should_sell:
            print(
                f"股票 {stock_code} 触发卖出条件: {sell_reason} (持股天数: {hold_days}, 涨跌幅: {price_change_ratio:.2%})")
            stocks_to_sell = pd.concat([stocks_to_sell, candidate_sell_stock.iloc[[i]]], ignore_index=True)

    return stocks_to_sell



# 修改candidate_sell函数，添加新的卖股策略
def candidate_sell(stocklist, sell_policy_list, current_day):
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
    up_stock = pd.DataFrame(columns=stock_data.columns)
    down_stock = pd.DataFrame(columns=stock_data.columns)
    holdday_stock = pd.DataFrame(columns=stock_data.columns)
    cci_stock = pd.DataFrame(columns=stock_data.columns)

    if isinstance(current_day, str) and len(current_day) == 8:
        current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
    elif isinstance(current_day, datetime):
        current_date_obj = current_day.date()
    else:
        current_date_obj = current_day

    sale_condition = SaleCondition(stocklist, sell_policy_list, current_date_obj)

    if '上涨幅度' in sell_policy_list:
        up_stock = sale_condition.up()
        if not up_stock.empty:
            print('上涨幅度:', up_stock)

    if '下跌幅度' in sell_policy_list:
        down_stock = sale_condition.down()
        if not down_stock.empty:
            print('下跌幅度:', down_stock)

    if '最大持股天数' in sell_policy_list:
        holdday_stock = sale_condition.last()
        if not holdday_stock.empty:
            print('最大持股天数:', holdday_stock)

    if 'cci卖股' in sell_policy_list:
        cci_stock = sale_condition.cci_sell()
        if not cci_stock.empty:
            if current_day == today_date and len(cci_stock) > 0:
                cci_sell = cci_stock['st_code']
                # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{} CCI发生拐头 卖股建议如下：\n 股票代码：{} '.format(current_day,cci_sell))
                # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{} CCI发生拐头 卖股建议如下：\n 股票代码：{} '.format(current_day, cci_sell))
            print('cci卖股:', cci_stock)

    macd_stock = pd.DataFrame(columns=stock_data.columns)
    if 'macd卖股' in sell_policy_list:
        macd_stock = sale_condition.macd_sell()
        if not macd_stock.empty:
            print('macd卖股:', macd_stock)

    macd_stock_bias = pd.DataFrame(columns=stock_data.columns)
    if 'macd顶背离卖股' in sell_policy_list:
        macd_stock_bias = sale_condition.macd_bias_sell()
        if not macd_stock_bias.empty:
            print('macd卖股:', macd_stock_bias)

    # 添加新的基于MACD金叉匹配的卖股策略
    macd_cross_sell_stock = pd.DataFrame(columns=stock_data.columns)
    if 'macd金叉策略卖股' in sell_policy_list:
        # 使用新的卖股策略
        macd_cross_sell_stock = macd_cross_sell_strategy(stocklist, current_day,
                                                         sell_policy_list.get('strategy_id', 2),
                                                         sell_policy_list.get('user_id', 1))
        if not macd_cross_sell_stock.empty:
            print('macd金叉策略卖股:', macd_cross_sell_stock)

    candidate_sell_stock = pd.concat([
        up_stock, down_stock, holdday_stock, cci_stock,
        macd_stock, macd_stock_bias, macd_cross_sell_stock
    ], axis=0, ignore_index=True)

    candidate_sell_stock = candidate_sell_stock.drop_duplicates()
    candidate_sell_stock = candidate_sell_stock.reset_index(drop=True)

    return candidate_sell_stock


# def candidate_sell(stocklist, sell_policy_list, current_day):
#     today_date = pd.Timestamp.today().strftime('%Y%m%d')
#     up_stock = pd.DataFrame(columns=stock_data.columns)
#     down_stock = pd.DataFrame(columns=stock_data.columns)
#     holdday_stock = pd.DataFrame(columns=stock_data.columns)
#     cci_stock = pd.DataFrame(columns=stock_data.columns)
#     if isinstance(current_day, str) and len(current_day) == 8:
#         current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
#     elif isinstance(current_day, datetime):
#         current_date_obj = current_day.date()
#     else:
#         current_date_obj = current_day
#     sale_condition = SaleCondition(stocklist, sell_policy_list, current_date_obj)
#
#     if '上涨幅度' in sell_policy_list:
#         up_stock = sale_condition.up()
#         if not up_stock.empty:
#             print('上涨幅度:', up_stock)
#
#     if '下跌幅度' in sell_policy_list:
#         down_stock = sale_condition.down()
#         if not down_stock.empty:
#             print('下跌幅度:', down_stock)
#
#     if '最大持股天数' in sell_policy_list:
#
#         holdday_stock = sale_condition.last()
#
#         if not holdday_stock.empty:
#             print('最大持股天数:', holdday_stock)
#
#     if 'cci卖股' in sell_policy_list:
#         cci_stock = sale_condition.cci_sell()
#         if not cci_stock.empty:
#             if current_day == today_date and len(cci_stock) > 0:
#                 cci_sell = cci_stock['st_code']
#                 # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{} CCI发生拐头 卖股建议如下：\n 股票代码：{} '.format(current_day,cci_sell))
#                 # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{} CCI发生拐头 卖股建议如下：\n 股票代码：{} '.format(current_day, cci_sell))
#             print('cci卖股:', cci_stock)
#
#     macd_stock = pd.DataFrame(columns=stock_data.columns)
#     if 'macd卖股' in sell_policy_list:
#         macd_stock = sale_condition.macd_sell()
#         if not macd_stock.empty:
#             print('macd卖股:', macd_stock)
#
#     macd_stock_bias = pd.DataFrame(columns=stock_data.columns)
#     if 'macd顶背离卖股' in sell_policy_list:
#         macd_stock_bias = sale_condition.macd_bias_sell()
#         if not macd_stock_bias.empty:
#             print('macd卖股:', macd_stock_bias)
#
#     candidate_sell_stock = pd.concat([up_stock, down_stock, holdday_stock, cci_stock, macd_stock, macd_stock_bias],
#                                      axis=0, ignore_index=True)
#     candidate_sell_stock = candidate_sell_stock.drop_duplicates()
#     candidate_sell_stock = candidate_sell_stock.reset_index(drop=True)
#
#     return candidate_sell_stock


def sell_stock(stocklist, candidate_sell_stock, remained_money, current_day, sid, uid):
    if isinstance(current_day, str) and len(current_day) == 8:
        current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
    elif isinstance(current_day, datetime):
        current_date_obj = current_day.date()
    else:
        current_date_obj = current_day

    for i in range(len(candidate_sell_stock)):
        data = stock_data[
            (stock_data['st_code'] == candidate_sell_stock['st_code'][i]) & (stock_data['trade_date'] == current_date_obj)]
        data = data.reset_index(drop=True)
        data1 = sc.df_table_transaction[
            sc.df_table_transaction['st_code'] == candidate_sell_stock['st_code'][i]].sort_values(
            by=['trade_date', 'trade_type'],
            ascending=[False, True])
        data1 = data1.reset_index(drop=True)

        if data1['trade_date'][0] == current_date_obj:
            continue

        trade_type = '卖出'
        old_close = sc.df_table_transaction[
            sc.df_table_transaction['st_code'] == candidate_sell_stock['st_code'][i]].sort_values(
            by='trade_date', ascending=False)

        if data['low'][0] <= old_close.iloc[0]['trade_price'] * 0.98:
            # 如果开盘价跳空低开，且低于止损位，则以开盘价卖出
            if data['open'][0] <= old_close.iloc[0]['trade_price'] * 0.98:
                trade_price = float(data['open'][0])
            else:
                # 挂单
                trade_price = float(old_close.iloc[0]['trade_price'] * 0.98)

        else:
            trade_price = float(data['close'][0])
        # if data['low'][0] <= old_close.iloc[0]['trade_price'] * 0.98:
        #     # 如果开盘价跳空低开，且低于止损位，则以开盘价卖出
        #     if data['open'][0] <= old_close.iloc[0]['trade_price'] * 0.98:
        #         trade_price = float(data['open'][0])
        #     else:
        #         # 挂单
        #         trade_price = float(old_close.iloc[0]['trade_price'] * 0.98)
        # elif data['high'][0] >= old_close.iloc[0]['trade_price'] * 1.05:
        #     # 挂单
        #     trade_price = float(old_close.iloc[0]['trade_price'] * 1.05)
        #     print('st_code', data['st_code'][0], 'trade_price', trade_price, 'old_close',
        #           old_close.iloc[0]['trade_price'])
        # else:
        #     trade_price = float(data['close'][0])

        # 涨跌幅
        up_down_rate = (trade_price - old_close.iloc[0]['trade_price']) / old_close.iloc[0]['trade_price']
        number_of_transactions = int(data1['number_of_transactions'][0])
        turnover = number_of_transactions * trade_price
        add_rows = (
            {'st_code': candidate_sell_stock['st_code'][i], 'trade_date': current_day, "trade_type": trade_type,
             "trade_price": trade_price,
             "number_of_transactions": number_of_transactions,
             "turnover": turnover, 'strategy_id': sid, 'user_id': uid})
        sc.df_table_transaction = append_row(sc.df_table_transaction, add_rows)

        stock_data.loc[(stock_data['st_code'] == candidate_sell_stock['st_code'][i]) & (
                stock_data['trade_date'] == candidate_sell_stock['trade_date'][i]), 'position'] = 0
        stocklist = stocklist[stocklist['st_code'] != candidate_sell_stock['st_code'][i]]
        remained_money = remained_money + number_of_transactions * trade_price

    stocklist = stocklist.reset_index(drop=True)
    return stocklist, remained_money


def order(All_stock_data, totalmoney, max_stock_num, start_date, end_date, Optionfactors, factors, Baseline,
          sell_policy_list, fund_data, sid, uid, last_backtest_date=None):
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
    # All_stock_data['trade_date'] = pd.to_datetime(All_stock_data['trade_date']).dt.strftime('%Y%m%d')
    table_calendar = copy.deepcopy(sc.df_table_calendar)
    table_calendar.set_index('cal_date', inplace=True)

    # 如果有历史数据，加载历史状态
    if last_backtest_date:
        print(f"从历史数据恢复状态，最后回测日期: {last_backtest_date}")

        # 从数据库加载历史持仓数据
        sql_position = """
        SELECT * FROM new_war_当前持股信息表 
        WHERE strategy_id = %s AND user_id = %s AND trade_date = %s
        """
        try:
            stocklist = sc.safe_read_sql(sql_position, params=(sid, uid, last_backtest_date))
            print("stocklist", stocklist)
            print(f"恢复持仓 {len(stocklist)} 只股票")
        except Exception as e:
            print(f"加载历史持仓数据时出错: {e}")
            stocklist = pd.DataFrame(columns=All_stock_data.columns)

        # 从数据库加载历史资金数据
        sql_fund = """
        SELECT balance FROM new_war_每日统计表 
        WHERE strategy_id = %s AND user_id = %s AND trade_date = %s
        """
        try:
            fund_result = sc.query_sql(sql_fund, (sid, uid, last_backtest_date))
            if not fund_result.empty and pd.notna(fund_result.iloc[0]['balance']):
                remained_money = fund_result.iloc[0]['balance']
                print(f"从历史数据恢复资金: {remained_money}")
            else:
                remained_money = totalmoney
                print("无法从历史数据恢复资金，使用初始资金")
        except Exception as e:
            print(f"加载历史资金数据时出错: {e}")
            remained_money = totalmoney

        print(f"恢复持仓 {len(stocklist)} 只股票，剩余资金: {remained_money}")

        # 处理大盘资金数据 - 从历史大盘数据中恢复
        if not sc.df_table_baseline.empty and last_backtest_date:
            last_baseline = sc.df_table_baseline[sc.df_table_baseline['trade_date'] == last_backtest_date]
            if not last_baseline.empty:
                testmoney = last_baseline.iloc[0]['balance']  # 使用历史资产作为新的起始资金
                print(f"使用历史大盘资产作为起始资金: {testmoney}")
            else:
                testmoney = totalmoney
                print("未找到历史大盘资产数据，使用初始资金")
        else:
            testmoney = totalmoney
            print("没有历史大盘数据，使用初始资金")
    else:
        stocklist = pd.DataFrame(columns=All_stock_data.columns)
        remained_money = totalmoney
        testmoney = totalmoney
        print("初始资金:", remained_money)

    trade_day = table_calendar.loc[start_date, 'trade_day']
    trade_day1 = table_calendar.loc[end_date, 'trade_day']
    current_day = start_date

    print('testmoney', testmoney)
    Basedata = IncomeBaseline(start_date, end_date, Baseline)

    print("-----------当前日期：" + current_day + "--------------")
    global stock_data
    Stock_data = copy.deepcopy(All_stock_data)
    print("Stock_data",Stock_data)
    count_day = 0
    while True:
        # 每日筛
        if isinstance(current_day, str) and len(current_day) == 8:
            current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
        elif isinstance(current_day, datetime):
            current_date_obj = current_day.date()
        else:
            current_date_obj = current_day
        print('type(Stock_data[trade_date][0])',type(Stock_data['trade_date'][0]))
        print('type(current_date_obj)',type(current_date_obj))
        stock_data = Stock_data.loc[Stock_data['trade_date'] == current_date_obj]
        print("stock_data",stock_data)
        # 今日筛股排序
        stock_data = stock_data.sort_values(by=factors, ascending=False)

        # 大盘指标
        if testmoney < 100 * Basedata['open'][0]:

            add_rows = {
                'trade_date': current_day,
                'reference_market_capitalization': stocknum * 100 *
                                                   Basedata.loc[Basedata['trade_date'] == current_day, 'open'].values[
                                                       0],
                'assets': testmoney + stocknum * 100 *
                          Basedata.loc[Basedata['trade_date'] == current_day, 'open'].values[0],
                'profit_and_loss': testmoney + stocknum * 100 *
                                   Basedata.loc[Basedata['trade_date'] == current_day, 'open'].values[0] - totalmoney,
                'profit_and_loss_ratio': (testmoney + stocknum * 100 *
                                          Basedata.loc[Basedata['trade_date'] == current_day, 'open'].values[
                                              0] - totalmoney) / totalmoney,
                'strategy_id': sid, 'user_id': uid
            }
            sc.df_table_baseline = append_row(sc.df_table_baseline, add_rows)
        else:
            # print('上证指数开盘价：', Basedata['open'][0])
            stocknum = int(testmoney / (100 * Basedata['open'][0]))  # 买入的大盘股票数量
            # print('买入的大盘指标数量：', stocknum)
            testmoney = testmoney - stocknum * 100 * Basedata['open'][0]
            # print('买完大盘之后剩下多少钱：', testmoney)
            reference_market_capitalization = stocknum * 100 * \
                                              Basedata.loc[Basedata['trade_date'] == current_day, 'open'].values[0]
            # print('今天的大盘开盘价是多少', reference_market_capitalization)
            asserts = testmoney + reference_market_capitalization
            profit_and_loss = asserts - totalmoney
            profit_and_loss_ratio = profit_and_loss / totalmoney
            add_rows = {
                'trade_date': current_day,
                'reference_market_capitalization': reference_market_capitalization,
                'assets': asserts,
                'profit_and_loss': profit_and_loss,
                'profit_and_loss_ratio': profit_and_loss_ratio,
                'strategy_id': sid, 'user_id': uid
            }
            sc.df_table_baseline = append_row(sc.df_table_baseline, add_rows)

        # 卖股：出售持有的股票
        if len(stocklist) > 0:
            candidate_sell_stock = candidate_sell(stocklist, sell_policy_list, current_day)  # 获取能够出售的股票列表
            print(f"候选卖出股票数: {len(candidate_sell_stock)}")
            if len(candidate_sell_stock) > 0:
                print('候选卖出股票:', candidate_sell_stock)
                stocklist, remained_money = sell_stock(stocklist, candidate_sell_stock, remained_money, current_day,
                                                       sid, uid)

            candidate_sell_stock_copy = copy.deepcopy(candidate_sell_stock)
            if not candidate_sell_stock_copy.empty:
                selected_columns = ['st_code', 'trade_type', 'trade_date', 'trade_price', 'number_of_transactions',
                                    'turnover']
                filtered_df = sc.df_table_transaction[(sc.df_table_transaction['trade_date'] == current_day) & (
                        sc.df_table_transaction['trade_type'] == '卖出')]

                if CHAIDAN == 1:
                    filtered_df = filtered_df.reset_index(drop=True)
                    filtered_df = filtered_df[selected_columns]
                    executed_result = execute_split_orders(filtered_df)
                    # 显示结果
                    print("\n拆单执行结果:")
                    print(executed_result)

                    # 将拆单结果合并回 df_table_transaction
                    # 首先删除原始的卖出交易记录
                    sc.df_table_transaction = sc.df_table_transaction[
                        ~((sc.df_table_transaction['trade_date'] == current_day) &
                          (sc.df_table_transaction['trade_type'] == '卖出'))
                    ]

                    # 创建新的交易记录DataFrame
                    new_transactions = []
                    for _, row in executed_result.iterrows():
                        # 为每个拆单交易创建新的记录
                        split_order_record = {
                            'st_code': row['stock_code'],
                            'trade_date': row['trade_date'],
                            'trade_type': row['trade_type'],
                            'trade_price': row['avg_price'] if pd.notna(row['avg_price']) else row['target_price'],
                            'number_of_transactions': row['executed_volume'] * 100,  # 转换为股数
                            'turnover': row['executed_turnover'],
                            'strategy_id': sid,
                            'user_id': uid
                        }
                        new_transactions.append(split_order_record)

                    # 将新记录添加到交易表中
                    if new_transactions:
                        new_transactions_df = pd.DataFrame(new_transactions)
                        sc.df_table_transaction = pd.concat(
                            [sc.df_table_transaction, new_transactions_df],
                            ignore_index=True
                        )
                    save_to_database(executed_result)

        print("-----------当前日期：" + current_day + "--------------")
        # 买股：当前持股数量小于最大持股数量时买入
        if len(stocklist) < max_stock_num:
            weights = [1 / len(factors)] * len(factors)
            if isinstance(current_day, str) and len(current_day) == 8:
                current_date_obj = datetime.strptime(current_day, '%Y%m%d').date()
            elif isinstance(current_day, datetime):
                current_date_obj = current_day.date()
            else:
                current_date_obj = current_day
            selected_rows = stock_data[(stock_data['trade_date'] == current_date_obj)]
            # 计算加权求和并排序
            selected_rows.loc[:, 'sum'] = (selected_rows[factors] * weights).sum(axis=1)
            selected_stock = selected_rows.sort_values(by='sum', ascending=False).reset_index(drop=True)
            selected_stock = selected_stock.drop('sum', axis=1)
            # 区分不同板块股票的涨跌幅限制
            print("selected_stock",selected_stock)
            selected_stock = selected_stock[
                (selected_stock['st_code'].str.startswith(('688', '300')) & (selected_stock['pct_chg'] < 0.199)) |
                (~selected_stock['st_code'].str.startswith(('688', '300')) & (selected_stock['pct_chg'] < 0.099))
                ]

            if len(selected_stock) > 0:
                candidate_buy_stock = selected_stock[~selected_stock['st_code'].isin(stocklist['st_code'])]
                candidate_buy_stock = candidate_buy_stock.reset_index(drop=True)
                print(f"候选买入股票数: candidate_buy_stock",candidate_buy_stock)
                stocklist, remained_money = buy_stock(stocklist, candidate_buy_stock, max_stock_num, remained_money,
                                                      current_day, fund_data, sid, uid)

                print('当前持股：', stocklist)
                print('可用余额：', remained_money)
                stocklist_copy = copy.deepcopy(stocklist)
                if not stocklist_copy.empty:
                    selected_columns = ['st_code', 'trade_type', 'trade_date', 'trade_price', 'number_of_transactions',
                                        'turnover']
                    filtered_df = sc.df_table_transaction[(sc.df_table_transaction['trade_date'] == current_day) & (
                            sc.df_table_transaction['trade_type'] == '买入')]
                    if CHAIDAN == 1:
                        filtered_df = filtered_df.reset_index(drop=True)
                        filtered_df = filtered_df[selected_columns]
                        executed_result = execute_split_orders(filtered_df)
                        # 显示结果
                        print("\n拆单执行结果:")
                        print(executed_result)
                        print('当前持股：', stocklist)

                        # 将拆单结果合并回 df_table_transaction
                        # 首先删除原始的买入交易记录
                        sc.df_table_transaction = sc.df_table_transaction[
                            ~((sc.df_table_transaction['trade_date'] == current_day) &
                              (sc.df_table_transaction['trade_type'] == '买入'))
                        ]

                        # 创建新的交易记录DataFrame
                        new_transactions = []
                        for _, row in executed_result.iterrows():
                            # 为每个拆单交易创建新的记录
                            split_order_record = {
                                'st_code': row['stock_code'],
                                'trade_date': row['trade_date'],
                                'trade_type': row['trade_type'],
                                'trade_price': row['avg_price'] if pd.notna(row['avg_price']) else row['target_price'],
                                'number_of_transactions': row['executed_volume'] * 100,  # 转换为股数
                                'turnover': row['executed_turnover'],
                                'strategy_id': sid,
                                'user_id': uid
                            }
                            new_transactions.append(split_order_record)

                        # 将新记录添加到交易表中
                        if new_transactions:
                            new_transactions_df = pd.DataFrame(new_transactions)
                            sc.df_table_transaction = pd.concat(
                                [sc.df_table_transaction, new_transactions_df],
                                ignore_index=True
                            )
                        save_to_database(executed_result)
                    if not filtered_df.empty:
                        send = filtered_df
                        if current_day == today_date:
                            pass
                            # vxmsgsend("测试\n 基于macd(固定投资十万)的买卖股策略\n今天是{}  {}买入股票如下：\n{}".format(current_day,datetime.now().strftime('%H:%M:%S'),send))
                            # vxmsgsend(" 基于macd(固定投资十万)的买卖股策略\n今天是{}  {}买入股票如下：\n{}".format(current_day, datetime.now().strftime('%H:%M:%S'),send))
                    else:
                        if current_day == today_date:
                            pass
                            # vxmsgsend("测试\n 基于macd(固定投资十万)的买卖股策略\n今天是{}  {},当天未买入股票".format(current_day,datetime.now().strftime('%H:%M:%S')))
                            # vxmsgsend("基于macd(固定投资十万)的买卖股策略\n今天是{}  {},当天未买入股票".format(current_day, datetime.now().strftime('%H:%M:%S')))

        else:
            if current_day == today_date:
                pass
                # vxmsgsend("测试\n 基于macd(固定投资十万)的买卖股策略\n今天是{} {}达到最大持股数，未购入股票".format(current_day,datetime.now().strftime( '%H:%M:%S')))
                # vxmsgsend("基于macd(固定投资十万)的买卖股策略\n今天是{} {}达到最大持股数，未购入股票".format(current_day, datetime.now().strftime('%H:%M:%S')))

        # 记录当前持股信息表 - 确保每天都记录数据
        if len(stocklist) > 0:
            for i in range(len(stocklist)):
                hold_stock_info = sc.df_table_transaction[
                    sc.df_table_transaction['st_code'] == stocklist['st_code'][i]].sort_values(
                    by=['trade_date', 'trade_type'],
                    ascending=[False, True])
                hold_stock_info = hold_stock_info.reset_index(drop=True)

                current_close = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == current_date_obj)]
                current_close = current_close.reset_index(drop=True)

                if current_close.empty:
                    continue

                # 计算盈亏
                profit_and_loss = (
                                          current_close['close'][0] - hold_stock_info['trade_price'][0]) * \
                                  hold_stock_info['number_of_transactions'][0]
                # 计算盈亏率
                profit_and_loss_ratio = (
                                                current_close['close'][0] - hold_stock_info['trade_price'][0]) / \
                                        hold_stock_info['trade_price'][0]
                latest_value = current_close['close'][0] * \
                               hold_stock_info['number_of_transactions'][0]
                add_rows = (
                    {'trade_date': current_day, 'st_code': stocklist['st_code'][i],
                     "number_of_securities": hold_stock_info['number_of_transactions'][0],
                     "saleable_quantity": hold_stock_info['number_of_transactions'][0],
                     "cost_price": hold_stock_info['trade_price'][0],
                     "profit_and_loss": profit_and_loss, 'profit_and_loss_ratio': profit_and_loss_ratio,
                     'latest_value': latest_value, 'current_price': current_close['close'][0],
                     'strategy_id': sid, 'user_id': uid})

                sc.df_table_shareholding = append_row(sc.df_table_shareholding, add_rows)
        # 即使没有持仓也要确保当日有记录
        else:
            # 可以添加空记录或零值记录，确保数据完整性
            pass

        # 记录war_每日统计表 - 确保每天都记录数据（移到条件块外面）
        turnover_sell = 0
        turnover_buy = 0

        # 统计累计交易金额（包括当天及之前的所有交易）
        if not sc.df_table_transaction.empty:
            transaction_up_to_today = sc.df_table_transaction[
                sc.df_table_transaction['trade_date'] <= current_day
                ]
            turnover_sell = transaction_up_to_today[transaction_up_to_today['trade_type'] == '卖出'][
                'turnover'].sum()
            turnover_buy = transaction_up_to_today[transaction_up_to_today['trade_type'] == '买入'][
                'turnover'].sum()

        # 计算账户余额
        balance = float(totalmoney) + turnover_sell - turnover_buy
        available = balance

        # 计算持仓市值
        reference_market_capitalization = 0
        if not sc.df_table_shareholding.empty:
            current_holdings = sc.df_table_shareholding[
                sc.df_table_shareholding['trade_date'] == current_day
                ]
            if not current_holdings.empty:
                reference_market_capitalization = current_holdings['latest_value'].sum()

        # 计算总资产和盈亏
        assets = balance + reference_market_capitalization
        sum_profit_and_loss = assets - totalmoney
        sum_profit_and_loss_ratio = sum_profit_and_loss / totalmoney if totalmoney != 0 else 0

        # 记录每日统计数据
        add_rows = (
            {'trade_date': current_day, 'balance': balance,
             "available": available,
             "reference_market_capitalization": reference_market_capitalization,
             "assets": assets,
             'profit_and_loss': sum_profit_and_loss,
             "profit_and_loss_ratio": sum_profit_and_loss_ratio,
             'strategy_id': sid, 'user_id': uid})

        sc.df_table_statistic = append_row(sc.df_table_statistic, add_rows)
        print(
            f'每日统计数据: {current_day} - 余额: {balance:.2f}, 持仓市值: {reference_market_capitalization:.2f}, 总资产: {assets:.2f}')

        count_day = count_day + 1
        if int(trade_day) + count_day < int(trade_day1):
            next_day = int(trade_day) + count_day

            trade_day2 = table_calendar[table_calendar['trade_day'] == next_day]
            current_day = str(trade_day2.index[0])
        else:
            break

    if len(stocklist) > 0:
        tmp = 0.
        for i in range(len(stocklist)):
            data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == stocklist['st_code'][i]) & (
                    sc.df_table_daily_qfq['trade_date'] == current_date_obj)]
            data = data.reset_index(drop=True)
            try:
                # 尝试获取data中的st_code值并执行筛选和排序
                data1 = sc.df_table_transaction[sc.df_table_transaction['st_code'] == data['st_code'][0]].sort_values(
                    by='trade_date', ascending=False)
                data1 = data1.reset_index(drop=True)
            except (KeyError, IndexError, TypeError):
                # 如果data为空，或者'st_code'不存在，或者data['st_code']无法取到值，则设置data1为None或空DataFrame
                data1 = None  # 或者使用 data1 = pd.DataFrame() 来创建一个空的DataFrame
                print("data1 is None or empty")
            if data1 is not None and not data1.empty and 'number_of_transactions' in data1.columns:
                tmp = tmp + data['close'][0] * data1['number_of_transactions'][0]
        totalmoney = remained_money + tmp
    else:
        totalmoney = remained_money
    print("三张表写入数据库")
    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_shareholding)
    sc.execute_sql(sql, (sid, uid))

    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_transaction)
    sc.execute_sql(sql, (sid, uid))

    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_statistic)
    sc.execute_sql(sql, (sid, uid))

    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_baseline)
    sc.execute_sql(sql, (sid, uid))


    # 三张表写入数据库
    sc.df_table_transaction.to_sql("new_war_历史成交信息表", con=engine, schema="jdgp", index=False,
                                   index_label=False,
                                   if_exists='append', chunksize=1000, method='multi')
    sc.df_table_statistic.to_sql("new_war_每日统计表", con=engine, schema="jdgp", index=False, index_label=False,
                                 if_exists='append', chunksize=1000, method='multi')
    sc.df_table_shareholding.to_sql("new_war_当前持股信息表", con=engine, schema="jdgp", index=False,
                                    index_label=False,
                                    if_exists='append', chunksize=1000, method='multi')
    sc.df_table_baseline.to_sql("大盘盈亏表", con=engine, schema="jdgp", index=False, index_label=False,
                                if_exists='append', chunksize=1000, method='multi')

    return totalmoney


def filter_stocks_by_labels(df, strategy_id, user_id):
    """根据用户策略配置中的标签筛选股票数据"""
    if df.empty:
        print("输入数据为空，返回原始数据")
        return df

    required_columns = ['st_code', 'trade_date']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"警告：输入数据缺少必要列 {missing_columns}，跳过标签筛选")
        return df

    if not hasattr(sc, 'df_table_user_strategy_configuration'):
        print("策略配置表未加载，返回所有股票数据")
        return df

    strategy_configs = sc.df_table_user_strategy_configuration[
        (sc.df_table_user_strategy_configuration['id'] == strategy_id) &
        (sc.df_table_user_strategy_configuration['userID'] == str(user_id))
        ]

    if strategy_configs.empty:
        print(f"未找到策略配置: id={strategy_id}, userID={user_id}，返回所有股票数据")
        return df

    strategy_config = strategy_configs.iloc[0]
    labels_data = strategy_config['labels']
    labels = []

    if labels_data and str(labels_data).strip() != '':
        try:
            if isinstance(labels_data, str) and labels_data.startswith('[') and labels_data.endswith(']'):
                labels = eval(labels_data)
            else:
                labels = [label.strip() for label in str(labels_data).split(',') if label.strip()]
        except Exception as e:
            print(f"解析标签时出错: {e}")
            labels = []

    if not labels:
        print("未设置标签筛选条件，返回所有股票数据")
        return df

    if not hasattr(sc, 'df_table_labels'):
        print("标签表未加载，返回所有股票数据")
        return df

    labels_df = sc.df_table_labels.copy()
    if labels_df.empty:
        print("标签表为空，返回所有股票数据")
        return df

    if 'st_code' not in labels_df.columns:
        print("警告：标签表缺少必要列 st_code，跳过标签筛选")
        return df

    missing_labels = [label for label in labels if label not in labels_df.columns]
    if missing_labels:
        print(f"警告：以下标签在标签表中未找到: {missing_labels}")
        labels = [label for label in labels if label not in missing_labels]

    if not labels:
        print("没有有效的标签可用于筛选，返回所有股票数据")
        return df

    condition = pd.Series([False] * len(labels_df), index=labels_df.index)
    valid_labels = []

    for label in labels:
        if label in labels_df.columns:
            label_series = labels_df[label]
            if label_series.dtype == 'bool':
                label_condition = label_series == True
            elif label_series.dtype in ['int64', 'float64']:
                label_condition = label_series == 1
            else:
                try:
                    label_condition = pd.to_numeric(label_series, errors='coerce') == 1
                except:
                    label_condition = (label_series == "1") | (label_series.str.upper() == "TRUE")

            condition = condition | label_condition
            valid_labels.append(label)

    if not valid_labels:
        print("没有有效的标签可用于筛选，返回所有股票数据")
        return df

    filtered_stocks = labels_df[condition]['st_code'].tolist()
    filtered_df = df[df['st_code'].isin(filtered_stocks)]
    return filtered_df


def get_final_assets_from_db(sid, uid, end_date):
    """从数据库获取最终资产值"""
    sql = """
    SELECT assets FROM new_war_每日统计表 
    WHERE strategy_id = %s AND user_id = %s AND trade_date = %s
    ORDER BY trade_date DESC LIMIT 1
    """
    result_df = sc.query_sql(sql, (sid, uid, end_date))
    if not result_df.empty and pd.notna(result_df.iloc[0]['assets']):
        return result_df.iloc[0]['assets']
    return 0


# 网页端运行
# 修改 main1 函数中的增量回测逻辑
def daily_60m_cross_main(fund_data, InvestmentRatio, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid):
    print("开始执行主函数")
    print("fund_data", fund_data)
    start_time = time.time()
    original_start_date = start_date  # 保存原始开始日期
    start_date = find_next_open_date(conn, start_date)
    end_date = find_next_open_date(conn, end_date)
    factors = ['MACD']
    Baseline = ['上证指数']

    # sell_policy_list = {'上涨幅度': 5, '下跌幅度': 2, '最大持股天数': 5, 'cci卖股': 0, 'macd卖股': 0}
    sell_policy_list = {'macd金叉策略卖股': 1}
    # 增量回测：检查是否需要执行完整回测或增量回测
    force_full_backtest = False  # 可通过参数控制是否强制完整回测
    print('start_date', start_date)
    print('end_date', end_date)
    # 检查历史回测数据
    last_backtest_date = check_existing_backtest_data(sid, uid, start_date, end_date)
    print("last_backtest_date", last_backtest_date)

    # 如果已有完整回测数据，直接返回结果
    if last_backtest_date == end_date:
        print(f"策略 {sid} 已有完整回测数据，无需重复回测")
        # 从数据库获取最终结果
        sql = """
        SELECT assets FROM new_war_每日统计表 
        WHERE strategy_id = %s AND user_id = %s AND trade_date = %s
        ORDER BY trade_date DESC LIMIT 1
        """
        result_df = sc.query_sql(sql, (sid, uid, end_date))

        # 同时检查大盘数据是否存在
        sql_baseline = """
               SELECT assets FROM 大盘盈亏表 
               WHERE strategy_id = %s AND user_id = %s AND trade_date = %s
               ORDER BY trade_date DESC LIMIT 1
               """
        baseline_df = sc.query_sql(sql_baseline, (sid, uid, end_date))

        if not result_df.empty and pd.notna(result_df.iloc[0]['assets']):
            print(f"最终资产: {result_df.iloc[0]['assets']}")
            # 确保大盘数据也存在
            if not baseline_df.empty and pd.notna(baseline_df.iloc[0]['assets']):
                print(f"大盘数据也已存在")
                return result_df.iloc[0]['assets']
            else:
                print("大盘数据缺失，需要重新运行回测")
                # 继续执行回测以生成大盘数据
        else:
            return fund_data * (InvestmentRatio / 100)

    # 检查开始日期一致性
    is_start_date_consistent = check_start_date_consistency(sid, uid, start_date)
    print("is_start_date_consistent", is_start_date_consistent)

    # 初始化回测参数
    actual_start_date = start_date
    actual_end_date = end_date

    # 如果不是强制完整回测，则保留历史数据，只删除增量部分
    if not force_full_backtest:
        # 只有当存在历史数据、开始日期一致且未完成完整回测时，才执行增量删除
        if last_backtest_date and last_backtest_date < end_date and is_start_date_consistent:
            print("开始日期一致，执行增量回测删除操作")
            # 只删除最后回测日期之后的数据
            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s AND trade_date > %s".format(sc.table_shareholding)
            sc.execute_sql(sql, (sid, uid, last_backtest_date))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s AND trade_date > %s".format(sc.table_transaction)
            sc.execute_sql(sql, (sid, uid, last_backtest_date))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s AND trade_date > %s".format(sc.table_statistic)
            sc.execute_sql(sql, (sid, uid, last_backtest_date))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s AND trade_date > %s".format(sc.table_baseline)
            sc.execute_sql(sql, (sid, uid, last_backtest_date))
            print("已删除最后回测日期之后的数据")
            # 更新回测开始日期为最后回测日期的下一天
            actual_start_date = find_next_open_date(engine, str(int(last_backtest_date) + 1))
            print(f"增量回测范围调整为: {actual_start_date} 至 {actual_end_date}")

            # 从数据库加载历史数据用于大盘盈亏表的初始化
            sql_baseline = "SELECT * FROM {} WHERE strategy_id=%s AND user_id=%s AND trade_date <= %s".format(
                sc.table_baseline)
            try:
                existing_baseline = sc.query_sql(sql_baseline, (sid, uid, last_backtest_date))
                if not existing_baseline.empty:
                    sc.df_table_baseline = existing_baseline
                    print(f"从历史数据恢复 {len(existing_baseline)} 条大盘盈亏数据")
                else:
                    # 如果没有历史大盘数据，则初始化为空的DataFrame
                    sc.df_table_baseline = pd.DataFrame(columns=[
                        'trade_date', 'reference_market_capitalization', 'assets',
                        'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
                    ])
                    print("未找到历史大盘数据，初始化为空")
            except Exception as e:
                print(f"加载历史大盘盈亏数据时出错: {e}")
                sc.df_table_baseline = pd.DataFrame(columns=[
                    'trade_date', 'reference_market_capitalization', 'assets',
                    'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
                ])

        elif last_backtest_date and last_backtest_date < end_date and not is_start_date_consistent:
            print("开始日期不一致，执行完整回测清理")
            # 开始日期不一致，执行完整删除
            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_shareholding)
            sc.execute_sql(sql, (sid, uid))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_transaction)
            sc.execute_sql(sql, (sid, uid))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_statistic)
            sc.execute_sql(sql, (sid, uid))

            sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_baseline)
            sc.execute_sql(sql, (sid, uid))
        elif last_backtest_date == end_date:
            print("已有完整回测数据，无需重复回测")
            return get_final_assets_from_db(sid, uid, end_date)
    else:
        # 强制完整回测，删除所有历史数据
        sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_shareholding)
        sc.execute_sql(sql, (sid, uid))

        sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_transaction)
        sc.execute_sql(sql, (sid, uid))

        sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_statistic)
        sc.execute_sql(sql, (sid, uid))

        sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_baseline)
        sc.execute_sql(sql, (sid, uid))

    sector_mapping = {
        "1": "主板",
        "2": "创业板",
        "3": "中小板"
    }

    sectors2 = ['主板', '创业板', '中小板']
    print('成功1')
    print(sectors2)

    # 加载数据
    sc.database(actual_start_date, actual_end_date, sid, uid, sectors2)
    # stock = trading_strategy(factors)
    ml = MachineLearning(factors)

    start_time2 = time.time()
    matcher = MACDGoldenCrossMatcher(debug=True)
    df_daily_with_macd = matcher.add_macd_score_to_daily_data(sc.df_stock_60m, sc.df_table_daily_qfq)

    # 查看结果
    print(df_daily_with_macd[df_daily_with_macd['MACD'] > 0].head())
    stock2 = df_daily_with_macd.copy()
    if 'st_code' not in stock2.columns and 'stock_code' in stock2.columns:
        stock2 = stock2.rename(columns={'stock_code': 'st_code'})
    if 'st_code' in stock2.columns:
        stock2['st_code'] = stock2['st_code'].astype(str)

    if factors:
        stock3 = stock2.groupby('st_code', group_keys=True).apply(ml.calc, factor=factors)
        if 'st_code' not in stock3.columns:
            stock3 = stock3.reset_index()
            if 'st_code' not in stock3.columns:
                if 'level_0' in stock3.columns:
                    stock3 = stock3.rename(columns={'level_0': 'st_code'})
                elif 'st_code' in stock3.index.names:
                    stock3 = stock3.reset_index(level=0).rename(columns={'level_0': 'st_code'})
        stock3 = stock3.reset_index(drop=True)
    else:
        stock3 = stock2.copy().reset_index(drop=True)
    if 'st_code' not in stock3.columns and 'stock_code' in stock3.columns:
        stock3 = stock3.rename(columns={'stock_code': 'st_code'})
    if 'st_code' in stock3.columns:
        stock3['st_code'] = stock3['st_code'].astype(str)
    All_stock_data = stock3
    end_time2 = time.time()
    execution_time = end_time2 - start_time2
    print(f"打分时间：{execution_time:.6f} 秒")
    print("All_stock_data", All_stock_data)
    print(f"All_stock_data['trade_date']: {All_stock_data['trade_date']}, 类型: {type(All_stock_data['trade_date'])}")

    totalmoney = order(All_stock_data, fund_data * (InvestmentRatio / 100), max_hold, actual_start_date,
                       actual_end_date,
                       Optionfactors, factors, Baseline, sell_policy_list, fund_data, sid, uid,
                       last_backtest_date if (
                               last_backtest_date and last_backtest_date < end_date and is_start_date_consistent) else None)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"主函数执行时间：{execution_time:.6f} 秒")
    print('totalmoney:', totalmoney)
    return totalmoney


# 后端单独运行
if __name__ == "__main__":
    start_time = time.time()
    Baseline = ['上证指数']
    start_date = '20250226'
    end_date = '20250514'
    start_date = find_next_open_date(sc.ENGINE, start_date)
    end_date = find_next_open_date(sc.ENGINE, end_date)
    sell_policy_list = {'上涨幅度': 5, '下跌幅度': 2, '最大持股天数': 5, 'cci卖股': 0, 'macd卖股': 0}
    fund_data = 1000000
    max_hold = 100
    factors = ['MACD']
    Optionfactors = ['MACD']
    sid = 2
    uid = 1

    # 清空数据表
    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_shareholding)
    sc.execute_sql(sql, (sid, uid))
    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_transaction)
    sc.execute_sql(sql, (sid, uid))
    sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_statistic)
    sc.execute_sql(sql, (sid, uid))
    sql = "truncate table {} ".format(sc.table_baseline)
    sc.execute_sql(sql)
    conn.commit()

    sql1 = "SELECT * FROM {} WHERE cal_date between '{}' and '{}'".format(sc.table_calendar, start_date, end_date)
    sc.df_table_calendar = sc.safe_read_sql(sql1)

    sql2 = f"SELECT * FROM {sc.table_shareholding} WHERE user_id={uid} AND strategy_id={sid}"
    sc.df_table_shareholding = sc.safe_read_sql(sql2)

    sql3 = f"SELECT * FROM {sc.table_transaction} WHERE user_id={uid} AND strategy_id={sid}"
    sc.df_table_transaction = sc.safe_read_sql(sql3)

    sql4 = f"SELECT * FROM {sc.table_statistic} WHERE user_id={uid} AND strategy_id={sid}"
    sc.df_table_statistic = sc.safe_read_sql(sql4)

    # 执行回测
    daily_60m_cross_main(fund_data, 100, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid)
    end_time = time.time()
    print(f"总执行时间: {end_time - start_time:.2f}秒")
