import copy
from datetime import datetime,timedelta

import pandas as pd
from datetime import datetime, timedelta
import pandas as pd
from strategy.策略.macd策略 import calculate_macd_composite_score, \
    calculate_macd_composite_score_vectorized, preprocess_macd_parameters
import strategy.mysql_connect as sc

import requests
import pymysql as mdb
from sqlalchemy import create_engine

from strategy.拆单交易系统 import execute_split_orders, save_to_database

conn = mdb.connect(host="127.0.0.1", port=3306, user='root', passwd='123456', db='jdgp', charset='utf8')
engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8")



# 超参
min_hold = 0.2  # 最低持股比例
max_hold_balance = 0.5  # 最高持股比例
CHAIDAN = 1  # 是否拆单，1是，0否

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

# 从指定日期开始，向后查找最近一个股票交易日
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


# 买股逻辑
# def buy_stock(stocklist, candidate_stock, max_stock_num, remained_money, current_day, fund_data, sid, uid):
#     today_date = pd.Timestamp.today().strftime('%Y%m%d')
#     buystocklist = pd.DataFrame(
#         columns=["st_code", "trade_date", "trade_type", "trade_price", "number_of_transactions", "turnover"],
#         dtype=object)
#
#     # 单只股票最大投入资金
#     min_invest_money = fund_data * 0.1
#     # 设置买入最小持仓资金
#     max_invest_num = remained_money // (min_invest_money)
#     # 获取当天的股票数据
#     invest_stock_data = stock_data[stock_data['trade_date'] == current_day]
#     # 计算 change 列大于 0 的行数
#     positive_changes = (invest_stock_data['pct_chg'] > 0).sum()
#     # 计算 change 列小于 0 的行数
#     negative_changes = (invest_stock_data['pct_chg'] <= 0).sum()
#     # balance1股票上涨数目与总数的比例。
#     balance1 = positive_changes / (negative_changes + positive_changes)
#     # invest_balance投资比例
#     invest_balance = decide_investment(balance1, min_hold, max_hold_balance)
#     remained_money_invest = remained_money
#     count = 0
#
#     for i in range(len(candidate_stock)):
#         if (candidate_stock['MACD'][i] >= 0):
#             count += 1
#         else:
#             break
#
#     num = max_stock_num - len(stocklist)  # 当前还需要购买股票的数量
#     num = min(num, count, max_invest_num)
#
#     if num == 0:
#         if current_day == today_date:
#             # vxmsgsend('测试\n基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
#             pass
#             # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
#         return stocklist, remained_money
#
#     elif invest_balance == 0:
#         if current_day == today_date:
#             # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
#             pass
#             # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
#         return stocklist, remained_money
#
#     elif invest_balance == 1:
#         # 每只股票的最大购买金额
#         max_cost = min((remained_money_invest) / num, min_invest_money)  # 拿出剩余资金的投入,若股票太少，则投入最大资金
#     else:
#         max_cost = min((remained_money_invest) / num, min_invest_money)  # 每只股票的最大购买金额
#
#     stocklist = stocklist.reset_index(drop=True)
#
#     while num > 0:
#         for i in range(len(candidate_stock)):
#             if num == 0:
#                 break
#             if (candidate_stock['MACD'][i] < 0):
#                 num = 0
#                 break
#
#             # 直接使用候选股票表，不考虑 industry_code 表
#             data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == candidate_stock['st_code'][i]) & (
#                     sc.df_table_daily_qfq['trade_date'] == current_day)]
#             data = data.reset_index(drop=True)
#             if data.empty:
#                 num = num - 1
#                 continue
#
#             if 100 * data['close'][0] >= max_cost or 100 * data['close'][0] >= remained_money or (
#                     data['close'][0] - data['pre_close'][0]) / data['pre_close'][0] > 0.11:
#                 num = num - 1
#                 continue
#             else:
#                 share = int(max_cost / (100 * data['close'][0]))  # 买入的多少手
#                 buystocklist.loc[0, 'st_code'] = candidate_stock['st_code'][i]
#                 buystocklist.loc[0, 'trade_date'] = current_day
#                 buystocklist.loc[0, 'turnover'] = float(share * 100 * data['close'][0])  # turnover成交额
#                 # 表示买入的交易量（单位：股）
#                 buystocklist.loc[0, 'number_of_transactions'] = share * 100
#                 buystocklist.loc[0, 'trade_price'] = float(data['close'][0])
#                 remained_money = remained_money - share * 100 * data['close'][0]
#                 # round(number,digits)digits>0，四舍五入到指定的小数位
#                 remained_money = round(remained_money, 2)
#                 buystocklist.loc[0, 'trade_type'] = '买入'
#                 stocklist.loc[len(stocklist)] = candidate_stock.loc[i]  # 将刚买入的股票添加到stocklist中
#                 stocklist.loc[(stocklist['trade_date'] == current_day) & (
#                         stocklist['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
#                 # 实现插入操作
#                 add_rows = (
#                     {'st_code': buystocklist.loc[0, 'st_code'], 'trade_date': buystocklist.loc[0, 'trade_date'],
#                      "trade_type": '买入', "trade_price": buystocklist.loc[0, 'trade_price'],
#                      "number_of_transactions": buystocklist.loc[0, 'number_of_transactions'],
#                      "turnover": buystocklist.loc[0, 'turnover'], 'strategy_id': sid, 'user_id': uid})
#                 # global  sc.df_table_transaction
#                 sc.df_table_transaction = sc.df_table_transaction.append(add_rows,
#                                                                          ignore_index=True)  # 忽略新行的索引，会自动分配一个索引以保证索引的连续性
#                 stock_data.loc[(stock_data['trade_date'] == current_day) & (
#                         stock_data['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
#                 num = num - 1
#
#     stocklist = stocklist.reset_index(drop=True)
#     print("买入股票:", stocklist)
#     return stocklist, remained_money

# def buy_stock(stocklist, candidate_stock, max_stock_num, remained_money, current_day, fund_data, sid, uid):
#     today_date = pd.Timestamp.today().strftime('%Y%m%d')
#     buystocklist = pd.DataFrame(
#         columns=["st_code", "trade_date", "trade_type", "trade_price", "number_of_transactions", "turnover"],
#         dtype=object)
#
#     # 单只股票最大投入资金
#     min_invest_money = fund_data * 0.1
#     # 设置买入最小持仓资金
#     max_invest_num = remained_money // (min_invest_money)
#     # 获取当天的股票数据
#     invest_stock_data = stock_data[stock_data['trade_date'] == current_day]
#     # 计算 change 列大于 0 的行数
#     positive_changes = (invest_stock_data['pct_chg'] > 0).sum()
#     # 计算 change 列小于 0 的行数
#     negative_changes = (invest_stock_data['pct_chg'] <= 0).sum()
#     # balance1股票上涨数目与总数的比例。
#     balance1 = positive_changes / (negative_changes + positive_changes)
#     # invest_balance投资比例
#     invest_balance = decide_investment(balance1, min_hold, max_hold_balance)
#     remained_money_invest = remained_money
#     count = 0
#
#     for i in range(len(candidate_stock)):
#         if (candidate_stock['MACD'][i] >= 0):
#             count += 1
#         else:
#             break
#
#     num = max_stock_num - len(stocklist)  # 当前还需要购买股票的数量
#     num = min(num, count, max_invest_num)
#
#     if num == 0:
#         if current_day == today_date:
#             # vxmsgsend('测试\n基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
#             pass
#             # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
#         return stocklist, remained_money
#
#     elif invest_balance == 0:
#         if current_day == today_date:
#             # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
#             pass
#             # vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
#         return stocklist, remained_money
#
#     elif invest_balance == 1:
#         # 每只股票的最大购买金额
#         max_cost = min((remained_money_invest) / num, min_invest_money)  # 拿出剩余资金的投入,若股票太少，则投入最大资金
#     else:
#         max_cost = min((remained_money_invest) / num, min_invest_money)  # 每只股票的最大购买金额
#
#     stocklist = stocklist.reset_index(drop=True)
#
#     while num > 0:
#         for i in range(len(candidate_stock)):
#             if num == 0:
#                 break
#             if (candidate_stock['MACD'][i] < 0):
#                 num = 0
#                 break
#
#             # 检查 industry_code 表中是否有数据
#             industry_code = sc.df_table_industry[['st_code', 'trade_date']].copy()
#             st_code = candidate_stock['st_code'][i]
#
#             # 如果 industry_code 表为空或者没有当前日期的数据，则data为空
#             if industry_code.empty or industry_code[industry_code['trade_date'] == current_day].empty:
#                 # industry_code 表中没有数据或没有当前日期的数据，data设置为空
#                 data = pd.DataFrame()  # 设置为空DataFrame
#                 num = num - 1
#                 continue
#             else:
#                 # industry_code 表中有数据，按原来逻辑处理
#                 if not industry_code[(industry_code['st_code'] == st_code) & (
#                         industry_code['trade_date'] == current_day)].empty:
#                     data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == candidate_stock['st_code'][i]) & (
#                             sc.df_table_daily_qfq['trade_date'] == current_day)]
#                     data = data.reset_index(drop=True)
#                     if data.empty:
#                         num = num - 1
#                         continue
#
#                     if 100 * data['close'][0] >= max_cost or 100 * data['close'][0] >= remained_money or (
#                             data['close'][0] - data['pre_close'][0]) / data['pre_close'][0] > 0.11:
#                         num = num - 1
#                         continue
#                     else:
#                         share = int(max_cost / (100 * data['close'][0]))  # 买入的多少手
#                         buystocklist.loc[0, 'st_code'] = candidate_stock['st_code'][i]
#                         buystocklist.loc[0, 'trade_date'] = current_day
#                         buystocklist.loc[0, 'turnover'] = float(share * 100 * data['close'][0])  # turnover成交额
#                         # 表示买入的交易量（单位：股）
#                         buystocklist.loc[0, 'number_of_transactions'] = share * 100
#                         buystocklist.loc[0, 'trade_price'] = float(data['close'][0])
#                         remained_money = remained_money - share * 100 * data['close'][0]
#                         # round(number,digits)digits>0，四舍五入到指定的小数位
#                         remained_money = round(remained_money, 2)
#                         buystocklist.loc[0, 'trade_type'] = '买入'
#                         stocklist.loc[len(stocklist)] = candidate_stock.loc[i]  # 将刚买入的股票添加到stocklist中
#                         stocklist.loc[(stocklist['trade_date'] == current_day) & (
#                                 stocklist['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
#                         # 实现插入操作
#                         add_rows = (
#                             {'st_code': buystocklist.loc[0, 'st_code'], 'trade_date': buystocklist.loc[0, 'trade_date'],
#                              "trade_type": '买入', "trade_price": buystocklist.loc[0, 'trade_price'],
#                              "number_of_transactions": buystocklist.loc[0, 'number_of_transactions'],
#                              "turnover": buystocklist.loc[0, 'turnover'], 'strategy_id': sid, 'user_id': uid})
#                         # global  sc.df_table_transaction
#                         sc.df_table_transaction = sc.df_table_transaction.append(add_rows,
#                                                                                  ignore_index=True)  # 忽略新行的索引，会自动分配一个索引以保证索引的连续性
#                         stock_data.loc[(stock_data['trade_date'] == current_day) & (
#                                 stock_data['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
#                         num = num - 1
#                 else:
#                     num = num - 1
#
#     stocklist = stocklist.reset_index(drop=True)
#     print("买入股票:", stocklist)
#     return stocklist, remained_money
def buy_stock(stocklist, candidate_stock, max_stock_num, remained_money, current_day, fund_data,sid, uid):
    # print('this is candidate_stock', candidate_stock.head(10))
    # stocklist：持仓列表
    # candidate_stock：候选股票
    # sc.df_table_industry
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
    buystocklist = pd.DataFrame(
        columns=["st_code", "trade_date", "trade_type", "trade_price", "number_of_transactions", "turnover"],
        dtype=object)
    # 单只股票最大投入资金
    # 单只股票最大投入资金
    min_invest_money = fund_data * 0.1
    # # 设置买入最小持仓资金
    max_invest_num = remained_money // (min_invest_money)
    # 获取当天的股票数据
    invest_stock_data = stock_data[stock_data['trade_date'] == current_day]
    # 计算 change 列大于 0 的行数
    positive_changes = (invest_stock_data['pct_chg'] > 0).sum()
    # 计算 change 列小于 0 的行数
    negative_changes = (invest_stock_data['pct_chg'] <= 0).sum()
    # balance1股票上涨数目与总数的比例。
    balance1 = positive_changes / (negative_changes + negative_changes)
    # invest_balance投资比例
    invest_balance = decide_investment(balance1, min_hold, max_hold_balance)
    remained_money_invest = remained_money
    count = 0
    for i in range(len(candidate_stock)):
        if (candidate_stock['MACD'][i] >= 0):
            count += 1
        else:
            break
    num = max_stock_num - len(stocklist)  # 当前还需要购买股票的数量
    num = min(num, count, max_invest_num)
    if num == 0:
        # if current_day == today_date:
        #     # vxmsgsend('测试\n基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
        #     vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}尚未筛出股票'.format(current_day))
        return stocklist, remained_money

    elif invest_balance == 0:
        # if current_day == today_date:
        #     # vxmsgsend('测试\n 基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))
        #     vxmsgsend('基于macd(固定投资十万)的买卖股策略\n当日{}大盘下跌严重，不买股'.format(current_day))

        return stocklist, remained_money

    elif invest_balance == 1:
        # 每只股票的最大购买金额
        max_cost = min((remained_money_invest) / num, min_invest_money)  # 拿出剩余资金的投入,若股票太少，则投入最大资金

    else:
        max_cost = min((remained_money_invest) / num, min_invest_money)  # 每只股票的最大购买金额

    stocklist = stocklist.reset_index(drop=True)
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
            # 检查 industry_code 表中是否有数据
            industry_code = sc.df_table_industry[['st_code', 'trade_date']].copy()

            # 如果 industry_code 表为空或者没有当前日期的数据，则使用所有候选股票
            if industry_code.empty or industry_code[industry_code['trade_date'] == current_day].empty:
                # industry_code 表中没有数据，继续使用候选股票表
                st_code = candidate_stock['st_code'][i]
                data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == candidate_stock['st_code'][i]) & (
                        sc.df_table_daily_qfq['trade_date'] == current_day)]
                data = data.reset_index(drop=True)
                if data.empty:
                    num = num - 1
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
                    stocklist.loc[(stocklist['trade_date'] == current_day) & (
                            stocklist['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                    # 实现插入操作
                    add_rows = (
                    {'st_code': buystocklist.loc[0, 'st_code'], 'trade_date': buystocklist.loc[0, 'trade_date'],
                     "trade_type": '买入', "trade_price": buystocklist.loc[0, 'trade_price'],
                     "number_of_transactions": buystocklist.loc[0, 'number_of_transactions'],
                     "turnover": buystocklist.loc[0, 'turnover'], 'strategy_id': sid, 'user_id': uid})
                    # global  sc.df_table_transaction
                    sc.df_table_transaction = sc.df_table_transaction.append(add_rows,
                                                                             ignore_index=True)  # 忽略新行的索引，会自动分配一个索引以保证索引的连续性
                    stock_data.loc[(stock_data['trade_date'] == current_day) & (
                            stock_data['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                    num = num - 1
            else:
                # industry_code 表中有数据，按原来逻辑处理
                st_code = candidate_stock['st_code'][i]
                if not industry_code[(industry_code['st_code'] == st_code) & (
                        industry_code['trade_date'] == current_day)].empty:
                    data = sc.df_table_daily_qfq[(sc.df_table_daily_qfq['st_code'] == candidate_stock['st_code'][i]) & (
                            sc.df_table_daily_qfq['trade_date'] == current_day)]
                    data = data.reset_index(drop=True)
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
                        stocklist.loc[(stocklist['trade_date'] == current_day) & (
                                stocklist['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                        # 实现插入操作
                        add_rows = (
                        {'st_code': buystocklist.loc[0, 'st_code'], 'trade_date': buystocklist.loc[0, 'trade_date'],
                         "trade_type": '买入', "trade_price": buystocklist.loc[0, 'trade_price'],
                         "number_of_transactions": buystocklist.loc[0, 'number_of_transactions'],
                         "turnover": buystocklist.loc[0, 'turnover'], 'strategy_id': sid, 'user_id': uid})
                        # global  sc.df_table_transaction
                        sc.df_table_transaction = sc.df_table_transaction.append(add_rows,
                                                                                 ignore_index=True)  # 忽略新行的索引，会自动分配一个索引以保证索引的连续性
                        stock_data.loc[(stock_data['trade_date'] == current_day) & (
                                stock_data['st_code'] == candidate_stock['st_code'][i]), 'position'] = 1
                        num = num - 1
                else:
                    num = num - 1

    stocklist = stocklist.reset_index(drop=True)

    return stocklist, remained_money


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

    def dynamic_stop_loss_profit(self):
        """
        动态止盈止损策略：
        - 止盈：当股价从最高点回撤一定比例时卖出
        - 止损：当股价跌破买入价一定比例时卖出
        """
        dynamic_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取该股票的历史交易记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 获取该股票在当前持仓期间的最高价
            holding_period_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] >= buy_record.iloc[0]['trade_date']) &
                (stock_data['trade_date'] <= self.current_day)
                ]

            if holding_period_data.empty:
                continue

            highest_price_during_holding = holding_period_data['high'].max()

            # 动态止盈：从最高点回撤10%止盈
            dynamic_profit_target = highest_price_during_holding * 0.9

            # 动态止损：跌破买入价5%止损
            dynamic_loss_stop = buy_price * 0.95

            # 判断是否满足卖出条件
            if current_price <= dynamic_loss_stop or current_price <= dynamic_profit_target:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                dynamic_sell = pd.concat([dynamic_sell, sell_candidate], axis=0, ignore_index=True)

        dynamic_sell = dynamic_sell.reset_index(drop=True)
        return dynamic_sell

    def volatility_based_stop_loss_profit(self):
        """
        基于波动率的动态止盈止损策略：
        - 根据股票历史波动率调整止盈止损比例
        - 波动大的股票设置更宽的止损止盈区间
        """
        volatility_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取该股票近20个交易日的数据计算波动率
            recent_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] <= self.current_day)
                ].tail(20)

            if len(recent_data) < 10:
                continue

            # 计算收益率波动率
            returns = recent_data['pct_chg'] / 100
            volatility = returns.std()

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 根据波动率动态调整止盈止损比例
            # 波动率越大，止盈止损比例越宽
            stop_loss_ratio = max(0.02, 0.05 * (1 + volatility * 10))  # 最小2%，最大根据波动率调整
            take_profit_ratio = max(0.05, 0.1 * (1 + volatility * 10))  # 最小5%，最大根据波动率调整

            # 计算动态止盈止损价格
            stop_loss_price = buy_price * (1 - stop_loss_ratio)
            take_profit_price = buy_price * (1 + take_profit_ratio)

            # 判断是否满足卖出条件
            if current_price <= stop_loss_price or current_price >= take_profit_price:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                volatility_sell = pd.concat([volatility_sell, sell_candidate], axis=0, ignore_index=True)

        volatility_sell = volatility_sell.reset_index(drop=True)
        return volatility_sell

    def relative_strength_stop_loss(self):
        """
        基于相对强度的动态止盈策略：
        - 当股票相对大盘表现变弱时卖出
        - 计算股票相对大盘的相对强度指标
        """
        relative_strength_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_date = buy_record.iloc[0]['trade_date']
            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 获取基准指数数据（以上证指数为例）
            baseline_data = sc.df_table_index[
                (sc.df_table_index['st_code'] == '000001.SH') &
                (sc.df_table_index['trade_date'] >= buy_date) &
                (sc.df_table_index['trade_date'] <= self.current_day)
                ]

            if baseline_data.empty or len(baseline_data) < 2:
                continue

            # 计算股票和基准指数的收益率
            stock_return = (current_price - buy_price) / buy_price
            baseline_return = (baseline_data['close'].iloc[-1] - baseline_data['close'].iloc[0]) / \
                              baseline_data['close'].iloc[0]

            # 计算相对强度
            relative_strength = stock_return - baseline_return

            # 如果相对强度为负且持续下降，则考虑卖出
            if len(baseline_data) > 5:
                recent_baseline_return = (baseline_data['close'].iloc[-1] - baseline_data['close'].iloc[-5]) / \
                                         baseline_data['close'].iloc[-5]
                recent_stock_data = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] >= baseline_data['trade_date'].iloc[-5])
                    ]

                if not recent_stock_data.empty and len(recent_stock_data) >= 2:
                    recent_stock_return = (recent_stock_data['close'].iloc[-1] - recent_stock_data['close'].iloc[0]) / \
                                          recent_stock_data['close'].iloc[0]
                    recent_relative_strength = recent_stock_return - recent_baseline_return

                    # 如果近期相对强度持续下降，考虑卖出
                    if relative_strength < 0 and recent_relative_strength < 0:
                        sell_candidate = stock_data[
                            (stock_data['st_code'] == stocklist['st_code'][i]) &
                            (stock_data['trade_date'] == self.current_day)
                            ]
                        relative_strength_sell = pd.concat([relative_strength_sell, sell_candidate], axis=0,
                                                           ignore_index=True)

        relative_strength_sell = relative_strength_sell.reset_index(drop=True)
        return relative_strength_sell

    def technical_trend_stop_loss(self):
        """
        基于技术指标趋势的动态卖出策略：
        - 结合MACD、RSI、均线等多个指标判断趋势
        - 当多个指标同时发出卖出信号时卖出
        """
        technical_trend_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty or len(current_data) == 0:
                continue

            sell_signals = 0
            total_signals = 0

            # MACD信号：MACD值下降
            if 'macd_macd' in current_data.columns and 'pre_macd_macd' in current_data.columns:
                total_signals += 1
                if current_data['macd_macd'].iloc[0] < current_data['pre_macd_macd'].iloc[0]:
                    sell_signals += 1

            # RSI信号：RSI过高或过低且转向
            if 'rsi' in current_data.columns and 'pre_rsi' in current_data.columns:
                total_signals += 1
                current_rsi = current_data['rsi'].iloc[0]
                previous_rsi = current_data['pre_rsi'].iloc[0]
                # 超买区域回调或超卖区域反弹
                if (current_rsi > 70 and current_rsi < previous_rsi) or (
                        current_rsi < 30 and current_rsi > previous_rsi):
                    sell_signals += 1

            # 均线信号：价格跌破重要均线
            if all(col in current_data.columns for col in ['close', 'ma5', 'ma10', 'ma20']):
                total_signals += 1
                close_price = current_data['close'].iloc[0]
                # 跌破多条均线
                if close_price < current_data['ma5'].iloc[0] and close_price < current_data['ma10'].iloc[0]:
                    sell_signals += 1

            # 如果超过一半的技术指标发出卖出信号，则卖出
            if total_signals > 0 and sell_signals / total_signals >= 0.5:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                technical_trend_sell = pd.concat([technical_trend_sell, sell_candidate], axis=0, ignore_index=True)

        technical_trend_sell = technical_trend_sell.reset_index(drop=True)
        return technical_trend_sell

    # 在 SaleCondition 类中添加以下方法
    def trailing_stop_loss(self, trailing_percent=0.08, profit_target=None):
        """
        峰值回撤（Trailing % stop）策略
        - 从持仓以来的最高价回撤超过阈值即止损
        - 同时可设固定目标价止盈
        """
        trailing_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 获取持仓期间的最高价
            holding_period_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] >= buy_record.iloc[0]['trade_date']) &
                (stock_data['trade_date'] <= self.current_day)
                ]

            if holding_period_data.empty:
                continue

            highest_price = holding_period_data['high'].max()

            # 计算回撤比例
            retracement = (highest_price - current_price) / highest_price

            # 止盈条件：达到目标价
            should_sell = False
            if profit_target and current_price >= buy_price * (1 + profit_target):
                should_sell = True

            # 止损条件：回撤超过阈值
            if retracement >= trailing_percent:
                should_sell = True

            if should_sell:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                trailing_sell = pd.concat([trailing_sell, sell_candidate], axis=0, ignore_index=True)

        trailing_sell = trailing_sell.reset_index(drop=True)
        return trailing_sell

    def atr_based_stop_loss(self, atr_multiplier=2.0, lookback_period=14):
        """
        ATR（波动率）止损/止盈策略
        - 用 ATR 动态设定止损价（价格 - k * ATR）
        - 波动大时止损放宽
        """
        atr_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 计算ATR
            recent_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] <= self.current_day)
                ].tail(lookback_period)

            if len(recent_data) < lookback_period:
                continue

            # 计算真实波动范围
            high_low = recent_data['high'] - recent_data['low']
            high_close = abs(recent_data['high'] - recent_data['close'].shift(1))
            low_close = abs(recent_data['low'] - recent_data['close'].shift(1))

            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.mean()

            # 动态止损价
            stop_loss_price = current_price - (atr_multiplier * atr)

            # 如果当前价格跌破止损价，则卖出
            if current_price <= stop_loss_price:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                atr_sell = pd.concat([atr_sell, sell_candidate], axis=0, ignore_index=True)

        atr_sell = atr_sell.reset_index(drop=True)
        return atr_sell

    def ma_cross_exit(self, short_period=5, long_period=20):
        """
        移动平均交叉退出（MA exit）策略
        - 短期 MA 下穿长期 MA 时卖出（趋势反转）
        """
        ma_cross_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取足够的历史数据计算移动平均
            historical_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] <= self.current_day)
                ].tail(long_period + 5)  # 多取几天确保计算准确

            if len(historical_data) < long_period:
                continue

            # 计算移动平均
            historical_data = historical_data.sort_values('trade_date')
            historical_data['ma_short'] = historical_data['close'].rolling(window=short_period).mean()
            historical_data['ma_long'] = historical_data['close'].rolling(window=long_period).mean()

            # 检查是否有交叉信号
            if len(historical_data) >= 2:
                current_ma_short = historical_data['ma_short'].iloc[-1]
                current_ma_long = historical_data['ma_long'].iloc[-1]
                prev_ma_short = historical_data['ma_short'].iloc[-2]
                prev_ma_long = historical_data['ma_long'].iloc[-2]

                # 短期均线下穿长期均线（死叉）
                if (prev_ma_short > prev_ma_long) and (current_ma_short <= current_ma_long):
                    sell_candidate = stock_data[
                        (stock_data['st_code'] == stocklist['st_code'][i]) &
                        (stock_data['trade_date'] == self.current_day)
                        ]
                    ma_cross_sell = pd.concat([ma_cross_sell, sell_candidate], axis=0, ignore_index=True)

        ma_cross_sell = ma_cross_sell.reset_index(drop=True)
        return ma_cross_sell

    def time_decay_tightening(self, max_holding_days=30, initial_stop_loss=0.1, final_stop_loss=0.03):
        """
        时间衰减收紧止损（Time-decay tightening）策略
        - 随持仓日数增加，逐步收紧止损比例
        """
        time_decay_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 计算持仓天数
            buy_date = pd.to_datetime(buy_record.iloc[0]['trade_date'], format='%Y%m%d')
            current_date = pd.to_datetime(self.current_day, format='%Y%m%d')
            holding_days = (current_date - buy_date).days

            # 计算动态止损比例（线性收紧）
            if holding_days >= max_holding_days:
                stop_loss_ratio = final_stop_loss
            else:
                # 线性插值计算当前止损比例
                stop_loss_ratio = initial_stop_loss - (initial_stop_loss - final_stop_loss) * (
                            holding_days / max_holding_days)

            # 计算止损价
            stop_loss_price = buy_price * (1 - stop_loss_ratio)

            # 如果当前价格跌破动态止损价，则卖出
            if current_price <= stop_loss_price:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                time_decay_sell = pd.concat([time_decay_sell, sell_candidate], axis=0, ignore_index=True)

        time_decay_sell = time_decay_sell.reset_index(drop=True)
        return time_decay_sell

    def profit_lock_high_water_mark(self, profit_threshold=0.15, retracement_limit=0.08):
        """
        基于峰值锁仓（Profit-lock / high-water mark）策略
        - 达到一定盈利后把止损抬到峰值的一定回撤率（保护利润）
        """
        profit_lock_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 获取持仓期间的最高价
            holding_period_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] >= buy_record.iloc[0]['trade_date']) &
                (stock_data['trade_date'] <= self.current_day)
                ]

            if holding_period_data.empty:
                continue

            highest_price = holding_period_data['high'].max()
            highest_profit = (highest_price - buy_price) / buy_price

            # 如果曾经达到盈利阈值，则启动利润保护
            if highest_profit >= profit_threshold:
                # 计算保护性止损价（从最高点回撤一定比例）
                protected_stop_price = highest_price * (1 - retracement_limit)

                # 如果当前价格跌破保护性止损价，则卖出
                if current_price <= protected_stop_price:
                    sell_candidate = stock_data[
                        (stock_data['st_code'] == stocklist['st_code'][i]) &
                        (stock_data['trade_date'] == self.current_day)
                        ]
                    profit_lock_sell = pd.concat([profit_lock_sell, sell_candidate], axis=0, ignore_index=True)

        profit_lock_sell = profit_lock_sell.reset_index(drop=True)
        return profit_lock_sell

    def volatility_scaled_profit_target(self, base_profit_target=0.2, volatility_window=20,
                                        min_target=0.1, max_target=0.4):
        """
        波动率缩放目标（Volatility-scaled profit target）策略
        - 根据历史波动率调整止盈目标（波动高目标更宽；低波动目标更紧）
        """
        volatility_scaled_sell = pd.DataFrame(columns=stock_data.columns)
        stocklist = self.stocklist.reset_index(drop=True)

        for i in range(len(stocklist)):
            current_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] == self.current_day)
                ]
            current_data = current_data.reset_index(drop=True)

            if current_data.empty:
                continue

            # 获取买入记录
            buy_record = sc.df_table_transaction[
                (sc.df_table_transaction['st_code'] == stocklist['st_code'][i]) &
                (sc.df_table_transaction['trade_type'] == '买入')
                ].sort_values(by='trade_date', ascending=False)

            if buy_record.empty:
                continue

            buy_price = buy_record.iloc[0]['trade_price']
            current_price = current_data['close'].iloc[0]

            # 计算历史波动率
            recent_data = stock_data[
                (stock_data['st_code'] == stocklist['st_code'][i]) &
                (stock_data['trade_date'] <= self.current_day)
                ].tail(volatility_window)

            if len(recent_data) < volatility_window:
                continue

            # 计算收益率波动率
            returns = recent_data['pct_chg'] / 100
            volatility = returns.std()

            # 根据波动率调整止盈目标
            # 波动率越高，止盈目标越宽
            volatility_multiplier = 1 + (volatility * 5)  # 波动率放大系数
            adjusted_profit_target = base_profit_target * volatility_multiplier

            # 限制在合理范围内
            adjusted_profit_target = max(min_target, min(max_target, adjusted_profit_target))

            # 计算动态止盈价
            profit_target_price = buy_price * (1 + adjusted_profit_target)

            # 如果当前价格达到动态止盈价，则卖出
            if current_price >= profit_target_price:
                sell_candidate = stock_data[
                    (stock_data['st_code'] == stocklist['st_code'][i]) &
                    (stock_data['trade_date'] == self.current_day)
                    ]
                volatility_scaled_sell = pd.concat([volatility_scaled_sell, sell_candidate], axis=0, ignore_index=True)

        volatility_scaled_sell = volatility_scaled_sell.reset_index(drop=True)
        return volatility_scaled_sell



# 筛选卖出的候选股票
def candidate_sell(stocklist, sell_policy_list, current_day):
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
    up_stock = pd.DataFrame(columns=stock_data.columns)
    down_stock = pd.DataFrame(columns=stock_data.columns)
    holdday_stock = pd.DataFrame(columns=stock_data.columns)
    cci_stock = pd.DataFrame(columns=stock_data.columns)
    sale_condition = SaleCondition(stocklist, sell_policy_list, current_day)

    # 原有策略
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
            print('cci卖股:', cci_stock)

    macd_stock = pd.DataFrame(columns=stock_data.columns)
    if 'macd卖股' in sell_policy_list:
        macd_stock = sale_condition.macd_sell()
        if not macd_stock.empty:
            print('macd卖股:', macd_stock)

    # 新增动态策略
    dynamic_stop_loss_stock = pd.DataFrame(columns=stock_data.columns)
    if '动态止盈止损' in sell_policy_list:
        dynamic_stop_loss_stock = sale_condition.dynamic_stop_loss_profit()
        if not dynamic_stop_loss_stock.empty:
            print('动态止盈止损:', dynamic_stop_loss_stock)

    volatility_based_stock = pd.DataFrame(columns=stock_data.columns)
    if '波动率动态止盈止损' in sell_policy_list:
        volatility_based_stock = sale_condition.volatility_based_stop_loss_profit()
        if not volatility_based_stock.empty:
            print('波动率动态止盈止损:', volatility_based_stock)

    relative_strength_stock = pd.DataFrame(columns=stock_data.columns)
    if '相对强度卖出' in sell_policy_list:
        relative_strength_stock = sale_condition.relative_strength_stop_loss()
        if not relative_strength_stock.empty:
            print('相对强度卖出:', relative_strength_stock)

    technical_trend_stock = pd.DataFrame(columns=stock_data.columns)
    if '技术趋势卖出' in sell_policy_list:
        technical_trend_stock = sale_condition.technical_trend_stop_loss()
        if not technical_trend_stock.empty:
            print('技术趋势卖出:', technical_trend_stock)

    # 新增六种策略
    trailing_stop_stock = pd.DataFrame(columns=stock_data.columns)
    if '峰值回撤止损' in sell_policy_list:
        trailing_stop_stock = sale_condition.trailing_stop_loss()
        if not trailing_stop_stock.empty:
            print('峰值回撤止损:', trailing_stop_stock)

    atr_stop_stock = pd.DataFrame(columns=stock_data.columns)
    if 'ATR波动率止损' in sell_policy_list:
        atr_stop_stock = sale_condition.atr_based_stop_loss()
        if not atr_stop_stock.empty:
            print('ATR波动率止损:', atr_stop_stock)

    ma_cross_stock = pd.DataFrame(columns=stock_data.columns)
    if '均线交叉退出' in sell_policy_list:
        ma_cross_stock = sale_condition.ma_cross_exit()
        if not ma_cross_stock.empty:
            print('均线交叉退出:', ma_cross_stock)

    time_decay_stock = pd.DataFrame(columns=stock_data.columns)
    if '时间衰减收紧止损' in sell_policy_list:
        time_decay_stock = sale_condition.time_decay_tightening()
        if not time_decay_stock.empty:
            print('时间衰减收紧止损:', time_decay_stock)

    profit_lock_stock = pd.DataFrame(columns=stock_data.columns)
    if '利润锁仓保护' in sell_policy_list:
        profit_lock_stock = sale_condition.profit_lock_high_water_mark()
        if not profit_lock_stock.empty:
            print('利润锁仓保护:', profit_lock_stock)

    volatility_scaled_stock = pd.DataFrame(columns=stock_data.columns)
    if '波动率缩放止盈' in sell_policy_list:
        volatility_scaled_stock = sale_condition.volatility_scaled_profit_target()
        if not volatility_scaled_stock.empty:
            print('波动率缩放止盈:', volatility_scaled_stock)

    # 合并所有卖出候选股票
    candidate_sell_stock = pd.concat([
        up_stock, down_stock, holdday_stock, cci_stock,
        macd_stock, dynamic_stop_loss_stock, volatility_based_stock,
        relative_strength_stock, technical_trend_stock,
        trailing_stop_stock, atr_stop_stock, ma_cross_stock,
        time_decay_stock, profit_lock_stock, volatility_scaled_stock
    ], axis=0, ignore_index=True)

    candidate_sell_stock = candidate_sell_stock.drop_duplicates()
    candidate_sell_stock = candidate_sell_stock.reset_index(drop=True)

    return candidate_sell_stock

# 卖股逻辑
def sell_stock(stocklist, candidate_sell_stock, remained_money, current_day, sid, uid):
    for i in range(len(candidate_sell_stock)):
        data = stock_data[
            (stock_data['st_code'] == candidate_sell_stock['st_code'][i]) & (stock_data['trade_date'] == current_day)]
        data = data.reset_index(drop=True)
        data1 = sc.df_table_transaction[
            sc.df_table_transaction['st_code'] == candidate_sell_stock['st_code'][i]].sort_values(
            by=['trade_date', 'trade_type'],
            ascending=[False, True])
        data1 = data1.reset_index(drop=True)

        if data1['trade_date'][0] == current_day:
            continue

        trade_type = '卖出'
        old_close = sc.df_table_transaction[
            sc.df_table_transaction['st_code'] == candidate_sell_stock['st_code'][i]].sort_values(
            by='trade_date', ascending=False)
        #     if data['open'][0] <= old_close.iloc[0]['trade_price'] * 0.98:
        #         trade_price = float(data['open'][0])


        trade_price = float(data['close'][0])
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
        sc.df_table_transaction = sc.df_table_transaction.append(add_rows, ignore_index=True)

        stock_data.loc[(stock_data['st_code'] == candidate_sell_stock['st_code'][i]) & (
                stock_data['trade_date'] == candidate_sell_stock['trade_date'][i]), 'position'] = 0
        stocklist = stocklist[stocklist['st_code'] != candidate_sell_stock['st_code'][i]]
        remained_money = remained_money + number_of_transactions * trade_price

    stocklist = stocklist.reset_index(drop=True)
    return stocklist, remained_money


def order(All_stock_data, totalmoney, max_stock_num, start_date, end_date, Optionfactors, factors, Baseline,
          sell_policy_list, fund_data, sid, uid, last_backtest_date=None):
    today_date = pd.Timestamp.today().strftime('%Y%m%d')
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

    count_day = 0
    while True:
        # 每日筛股
        stock_data = Stock_data.loc[Stock_data['trade_date'] == current_day]

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
            sc.df_table_baseline = sc.df_table_baseline.append(add_rows, ignore_index=True)
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
            sc.df_table_baseline = sc.df_table_baseline.append(add_rows, ignore_index=True)

        # 卖股：出售持有的股票
        if len(stocklist) > 0:
            candidate_sell_stock = candidate_sell(stocklist, sell_policy_list, current_day)  # 获取能够出售的股票列表
            print(f"候选卖出股票数: {len(candidate_sell_stock)}")
            if len(candidate_sell_stock) > 0:
                print('候选卖出股票:', candidate_sell_stock)
                stocklist, remained_money = sell_stock(stocklist, candidate_sell_stock, remained_money, current_day,
                                                       sid, uid)

        stocklist_copy = copy.deepcopy(stocklist)
        if not stocklist_copy.empty:
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
                    sc.df_table_transaction = pd.concat([sc.df_table_transaction, new_transactions_df],
                                                        ignore_index=True)

                # 保存到数据库（示例）
                save_to_database(executed_result)
                # filtered_df.columns = ['股票代码', '交易价格', '交易笔数', '成交额']

        print("-----------当前日期：" + current_day + "--------------")
        # 买股：当前持股数量小于最大持股数量时买入
        if len(stocklist) < max_stock_num:
            weights = [1 / len(factors)] * len(factors)
            selected_rows = stock_data[(stock_data['trade_date'] == current_day)]
            # 计算加权求和并排序
            selected_rows.loc[:, 'sum'] = (selected_rows[factors] * weights).sum(axis=1)
            selected_stock = selected_rows.sort_values(by='sum', ascending=False).reset_index(drop=True)
            selected_stock = selected_stock.drop('sum', axis=1)
            # selected_stock = selected_stock[selected_stock["change"] < 0.099]
            # 区分不同板块股票的涨跌幅限制
            selected_stock = selected_stock[
                (selected_stock['st_code'].str.startswith(('688', '300')) & (selected_stock['pct_chg'] < 0.197)) |
                (~selected_stock['st_code'].str.startswith(('688', '300')) & (selected_stock['pct_chg'] < 0.097))
                ]

            if len(selected_stock) > 0:
                candidate_buy_stock = selected_stock[~selected_stock['st_code'].isin(stocklist['st_code'])]
                candidate_buy_stock = candidate_buy_stock.reset_index(drop=True)

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
                            sc.df_table_transaction = pd.concat([sc.df_table_transaction, new_transactions_df],
                                                                ignore_index=True)

                        # 保存到数据库（示例）
                        save_to_database(executed_result)
                        # filtered_df.columns = ['股票代码', '交易价格', '交易笔数', '成交额']
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
                    (stock_data['st_code'] == stocklist['st_code'][i]) & (stock_data['trade_date'] == current_day)]
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

                sc.df_table_shareholding = sc.df_table_shareholding.append(add_rows, ignore_index=True)
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

        sc.df_table_statistic = sc.df_table_statistic.append(add_rows, ignore_index=True)
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
                    sc.df_table_daily_qfq['trade_date'] == current_day)]
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

