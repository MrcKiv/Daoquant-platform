import gc
import random
from decimal import Decimal

import requests
import numpy as np
import pandas as pd
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
import json
from collections import defaultdict
from datetime import datetime, timedelta
import time

from scipy.constants import hour, minute
from sqlalchemy import create_engine

from user.models import User
from .decorators import permission_required
from .final_project3_生产环境_macd策略 import macd_main
from .final_project3_生产环境_macd纯 import macd_you_main
from .final_project3_生产环境_macd_行业 import macd_industry_main
from .final_project3_生产环境_增量回测概念 import macd_concept_main
from .final_project3_生产环境_sby import sby_main
from .final_project3_生产环境_韩冰冰 import hbb_main
from .final_project3_生产环境_cmy import cmy_main
from .final_project3_生产环境_60分钟金叉与日线金叉匹配_自动交易 import daily_60m_cross_main
from .final_project3_生产环境 import main1
from .models import Current_shareholding_information, Historical_transaction_information, \
    Daily_statistics, Baseline_Profit_Loss, User_Strategy_Configuration, Strategy, SaveState
import strategy.mysql_connect as sc
from scipy.signal import find_peaks
from django.contrib.sessions.models import Session
from django.middleware.csrf import get_token

# < option > macd策略 < / option >
# < option > macd优化策略 < / option >
# < option > macd行业策略 < / option >
# < option > macd概念策略 < / option >
# < option > sby策略 < / option >
# < option > hbb策略 < / option >
# < option > cmy策略 < / option >
STRATEGY_MAIN_MAP = {
    'default': macd_main,
    'macd策略': macd_main,
    'macd优化策略': macd_you_main,
    'macd行业策略': macd_industry_main,
    'macd概念策略': macd_concept_main,
    'sby策略': sby_main,
    'hbb策略': hbb_main,
    'cmy策略': cmy_main,
    '日线与60分钟金叉匹配策略': daily_60m_cross_main,
    # 可以继续添加其他策略
}


def csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})
def process_group(group):
    # 如果第一行是“买入”，删除
    if group.iloc[0]['trade_type'] == '买入':
        group = group.iloc[1:]
    return group

# # 胜率
# def win_rate(df):
#     # 1. 按股票代码分组，并按买卖标志降序排列，移除开始为“买入”的第一行
#     df = df.sort_values(by=['st_code', 'trade_date', 'trade_type'], ascending=[True, False, True])
#     # 应用函数处理分组
#     df = df.groupby('st_code', group_keys=False).apply(process_group)
#
#     # 2. 构建交易对
#     results = []
#     win = 0
#     lose = 0
#     for stock, group in df.groupby('st_code'):
#         buys = 0.0
#         sells = 0.0
#         for index, row in group.iterrows():
#             if row['trade_type'] == '买入':
#                 buys = buys + row['trade_price'] * row['number_of_transactions']
#             else:
#                 sells = sells + row['trade_price'] * row['number_of_transactions']
#         if buys < sells:
#             win = win + 1
#         else:
#             lose = lose + 1
#     win_rate = (win + 0.0001) / (win + lose + 0.0001)
#     return win_rate
#
# 最大回撤
def maxback(time_series):
    maxdiff = 0
    peaks, _ = find_peaks(time_series)
    valleys, _ = find_peaks(-time_series)

    if len(peaks) == 0 and len(valleys) == 0:
        if time_series[-1] > time_series[0]:
            return maxdiff
        else:
            if time_series[0] == 0:
                maxdiff = time_series[0] - time_series[-1]
            else:
                # 计算最大差值
                maxdiff = (time_series[0] - time_series[-1]) / (time_series[0])
            return maxdiff

    if len(peaks) == 0:
        peaks = [0]
    if len(valleys) == 0:
        valleys = [len(time_series) - 1]

    # Convert to numpy arrays for easier indexing
    peaks = np.array(peaks)
    valleys = np.array(valleys)

    # Ensure peaks and valleys have the same length by appending the end of the series if necessary
    if len(peaks) > len(valleys):
        valleys = np.append(valleys, len(time_series) - 1)
    elif len(peaks) < len(valleys):
        peaks = np.insert(peaks, 0, 0)

    # Calculate the maximum drawdown
    drawdowns = (time_series[peaks] - time_series[valleys]) / time_series[peaks]
    maxdiff = drawdowns.max()

    return round(maxdiff, 3)
#
# # 夏普比率
# def sharpe_ratio(time_series, risk_free_rate, trading_days_per_year):
#     # 计算每日收益率
#     daily_returns = (time_series[1:] - time_series[:-1]) / time_series[:-1]
#
#     # 计算投资组合的年化回报率
#     annualized_return = np.mean(daily_returns) * trading_days_per_year
#
#     # 计算投资组合的年化标准差（波动性）
#     annualized_std_deviation = np.std(daily_returns) * np.sqrt(trading_days_per_year)
#
#     # 计算夏普比率
#     ratio = (annualized_return - risk_free_rate) / (annualized_std_deviation + 0.0001)
#
#     return ratio
#
# 年化收益率
def annualized_return(time_series, trading_days_per_year):
    return (time_series[-1] - time_series[0]) / time_series[0] / len(time_series) * trading_days_per_year
    # return (time_series[-1] - time_series[0]) / time_series[0]
#
# # 索提诺比率
# def sortino_ratio(time_series, risk_free_rate, trading_days_per_year):
#     # 计算每日收益率
#     daily_returns = (time_series[1:] - time_series[:-1]) / time_series[:-1]
#
#     # 计算投资组合的目标回报率
#     target_return = np.mean(daily_returns) * trading_days_per_year
#
#     # 计算下行风险的回报率
#     downside_returns = daily_returns - target_return
#
#     # 计算下行风险的标准差
#     downside_std_deviation = np.std(downside_returns)
#
#     # 计算年化下行标准差
#     annualized_downside_std_deviation = downside_std_deviation * np.sqrt(trading_days_per_year)
#
#     # 计算索提诺比率
#     ratio = (target_return - risk_free_rate) / annualized_downside_std_deviation
#
#     # 打印结果
#     print("索提诺比率：", sortino_ratio)
#     return ratio
# 胜率 - 优化版本
def win_rate(df):
    # print("计算胜率的交易数据：", df)
    """
    计算交易胜率：盈利交易次数 / 总交易次数
    采用配对交易方式：每次买入后必须有对应的卖出
    """
    if df.empty:
        return 0.0

    # 按股票代码分组，并按时间排序
    df = df.sort_values(by=['st_code', 'trade_date'])

    win = 0  # 盈利交易对数
    total = 0  # 总交易对数

    for stock, group in df.groupby('st_code'):
        # 使用队列匹配买入和卖出
        buy_queue = []
        for _, row in group.iterrows():
            if row['trade_type'] == '买入':
                buy_queue.append({
                    'price': row['trade_price'],
                    'amount': row['number_of_transactions']
                })
            elif row['trade_type'] == '卖出' and buy_queue:
                # 取出最早的买入记录进行匹配
                buy_record = buy_queue.pop(0)
                buy_value = buy_record['price'] * buy_record['amount']
                sell_value = row['trade_price'] * row['number_of_transactions']

                # 计算该笔交易的盈亏
                if sell_value > buy_value:
                    win += 1
                total += 1

    # 避免除零错误
    return win / total if total > 0 else 0.0




# 夏普比率 - 优化版本
def sharpe_ratio(time_series, risk_free_rate=0.0175, trading_days_per_year=250):
    """
    计算夏普比率
    """
    if len(time_series) < 2:
        return 0.0

    # 计算每日收益率
    returns = np.diff(time_series) / (time_series[:-1] + 1e-8)

    if np.std(returns) == 0:
        return 0.0

    # 年化收益率
    annual_return = np.mean(returns) * trading_days_per_year

    # 年化标准差
    annual_std = np.std(returns) * np.sqrt(trading_days_per_year)

    # 夏普比率
    return (annual_return - risk_free_rate) / (annual_std + 1e-8)


# 年化收益率 - 优化版本 复合增长率计算
# def annualized_return(time_series, trading_days_per_year=250):
#     """
#     计算年化收益率
#     """
#     if len(time_series) < 2:
#         return 0.0
#
#     # 总收益率
#     total_return = (time_series[-1] - time_series[0]) / (time_series[0] + 1e-8)
#
#     # 计算期间的交易日数
#     num_periods = len(time_series) - 1
#
#     # 年化收益率 = (1 + 总收益率)^(年交易日数/期间交易日数) - 1
#     if num_periods > 0:
#         annual_return = (1 + total_return) ** (trading_days_per_year / num_periods) - 1
#         return annual_return
#     else:
#         return 0.0


# 索提诺比率 - 优化版本
def sortino_ratio(time_series, risk_free_rate=0.0175, trading_days_per_year=250):
    """
    计算索提诺比率
    """
    if len(time_series) < 2:
        return 0.0

    # 计算每日收益率
    returns = np.diff(time_series) / (time_series[:-1] + 1e-8)

    # 计算超额收益
    excess_returns = returns - risk_free_rate / trading_days_per_year

    # 计算下行标准差（只考虑负收益）
    negative_returns = excess_returns[excess_returns < 0]

    if len(negative_returns) == 0:
        downside_risk = 0
    else:
        downside_risk = np.std(negative_returns) * np.sqrt(trading_days_per_year)

    # 年化超额收益
    annual_excess_return = np.mean(excess_returns) * trading_days_per_year

    # 避免除零
    if downside_risk == 0:
        return 0.0

    return annual_excess_return / downside_risk


@csrf_exempt
def getStrategyConfig(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # print("接收到的数据为：", data)

            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')
            print(" strategy_name：", strategy_name)
            print(" user_id：", user_id)
            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # ✅ 使用 update_or_create 更新或创建记录
            obj, created = User_Strategy_Configuration.objects.update_or_create(
                userID=user_id,
                strategyName=strategy_name,
                defaults={
                    'init_fund': data.get('capital'),
                    'max_hold_num': data.get('hold'),
                    'start_date': data.get('start_date'),
                    'end_date': data.get('end_date'),
                    'income_base': data.get('benchmark'),
                    'labels': data.get('labels'),
                    'source_user_id': user_id,
                    # 可以继续添加其他字段
                }
            )

            if created:
                msg = '策略配置已创建'
            else:
                msg = '策略配置已更新'

            return JsonResponse({
                "success": True,
                "message": msg,
                "received_data": data
            }, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


@csrf_exempt
def getUserStrategies(request):
    """
    获取当前用户的所有策略列表，包括自建策略和已公开的策略
    """
    if request.method == 'GET':
        try:
            user_id = request.session.get('user_id')

            # 查询当前用户自建的所有策略
            user_strategies = User_Strategy_Configuration.objects.filter(userID=user_id)

            # 查询所有已公开的策略
            public_strategies = User_Strategy_Configuration.objects.filter(is_public=True)

            # 合并两个查询结果，并去重（基于 id 和 strategyName）
            all_strategies = list(user_strategies) + list(public_strategies)
            unique_strategies = []
            seen = set()

            for strategy in all_strategies:
                key = (strategy.id, strategy.strategyName)
                if key not in seen:
                    seen.add(key)
                    unique_strategies.append(strategy)

            # 将数据转换为前端可用格式
            strategies_list = []
            for strategy in unique_strategies:
                strategies_list.append({
                    "id": strategy.id,
                    "userID": strategy.userID,
                    "strategyName": strategy.strategyName,
                    "start_date": strategy.start_date,
                    "end_date": strategy.end_date,
                    "init_fund": float(strategy.init_fund) if strategy.init_fund else 0,
                    "max_hold_num": strategy.max_hold_num,
                    "income_base": strategy.income_base,
                    "remove_st_stock": strategy.remove_st_stock,
                    "remove_suspended_stok": strategy.remove_suspended_stok,
                    # 订阅相关字段
                    "isSubscribed": strategy.is_subscribed,
                    "subscriptionDate": strategy.subscription_date.strftime('%Y-%m-%d %H:%M:%S') if strategy.subscription_date else None,
                    # 公开相关字段
                    "isPublic": strategy.is_public
                })

            return JsonResponse({
                "success": True,
                "strategies": strategies_list
            }, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "error": "只支持 GET 请求"}, status=405)

class DecimalJSONEncoder(DjangoJSONEncoder):
    """自定义JSON编码器，处理Decimal类型、inf、NaN等特殊值"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def clean_data_for_json(data):
    """递归清理数据，将inf、NaN等特殊值转换为None"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif isinstance(data, float):
        if data == float('inf') or data == float('-inf') or data != data:  # inf, -inf, or NaN
            return None
        return data
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data
# 加载回测数据
@csrf_exempt
@permission_required('free')  # 确保用户有基本权限才能访问
def loadStrategyConfig(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')
            # author = request.session.get('name')
            print(" user_id：", user_id)
            print(" strategy_name：", strategy_name)

            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # 从数据库中查询策略配置
            user_config = User_Strategy_Configuration.objects.filter(
                userID=user_id,
                strategyName=strategy_name
            ).first()

            public_config = User_Strategy_Configuration.objects.filter(
                is_public=True
            ).exclude(userID=user_id).first()
            # print(" public_config：", public_config)
            config = user_config or public_config

            if not config:
                return JsonResponse({'success': False, 'message': '未找到该策略配置'}, status=404)
            # print("查询到的数据为：", config)

            # 基础策略配置数据
            strategy_config = {
                "capital": config.init_fund,
                "ratio": 100,  # 示例默认值
                "hold": config.max_hold_num,
                "benchmark": config.income_base,
                "start_date": config.start_date,
                "end_date": config.end_date,
                "scope": "全部",  # 示例默认值
                "stamp_tax": "1",
                "fee": "0.02",
                "commission": "0.25",
                "min_commission": "5",
                "exclude_st": config.remove_st_stock,
                "exclude_suspended": config.remove_suspended_stok,
                "is_public": config.is_public,
            }
            # print("基础策略配置数据为：", strategy_config)
            backtest_config = {
                "capital": config.init_fund,
                "ratio": 100,  # 示例默认值
                "hold": config.max_hold_num,
                "benchmark": config.income_base,
                "start_date": config.start_date,
                "end_date": config.end_date,
                "scope": "全部",  # 示例默认值
                "stamp_tax": "1",
                "fee": "0.02",
                "commission": "0.25",
                "min_commission": "5",
                "optionfactor": config.optionfactor,  # 添加这一行
                "bottomfactor": config.bottomfactor  # 添加这一行
            }
            # print("回测配置数据为：", backtest_config)
            # 回测结果数据（如果存在相关数据则返回，否则返回空数据）
            backtest_result = {}

            # 尝试获取回测数据
            try:
                uid = request.session.get('user_id')
                if config.is_public:
                    uid = config.source_user_id
                    print('source_user_id', uid)
                print('uid', uid)
                if config:
                    sid = config.id  # 获取策略配置的ID
                    print('sid', sid)


                # 如果有配置的开始和结束时间，则尝试获取回测结果
                if config.start_date and config.end_date:
                    Start_time = datetime.strptime(str(config.start_date), '%Y-%m-%d').strftime('%Y%m%d')
                    End_time = datetime.strptime(str(config.end_date), '%Y-%m-%d').strftime('%Y%m%d')

                    # 获取回测结果数据
                    ShareHolding_data = list(
                        Current_shareholding_information.objects.filter(strategy_id=sid, user_id=uid,
                                                                        trade_date__range=[Start_time,
                                                                                           End_time]).order_by(
                            'trade_date').values(
                            "trade_date", 'st_code'))

                    Historical_transaction_data = list(
                        Historical_transaction_information.objects.filter(strategy_id=sid, user_id=uid,
                                                                          trade_date__range=[Start_time,
                                                                                             End_time]).order_by(
                            'trade_date').values(
                            "trade_date", 'st_code', 'trade_type', 'trade_price', 'number_of_transactions', 'turnover'))

                    incomeBase_data = list(
                        Daily_statistics.objects.filter(strategy_id=sid, user_id=uid,
                                                        trade_date__range=[Start_time, End_time]).order_by(
                            'trade_date').values(
                            "trade_date", 'profit_and_loss_ratio', 'assets'))
                    # 大盘盈亏表去重
                    incomeBaseline = list(
                        Baseline_Profit_Loss.objects.filter(strategy_id=sid, user_id=uid,
                                                            trade_date__range=[Start_time, End_time])
                        .order_by('trade_date')
                        .values("trade_date", 'profit_and_loss_ratio', 'assets')
                        .distinct()
                    )

                    if incomeBase_data and incomeBaseline:
                        # 处理持股数据
                        share_dict = defaultdict(list)
                        for item in ShareHolding_data:
                            share_dict[item['trade_date']].append(item['st_code'])
                        # 计算股票盈亏统计表
                        calculate_stock_profit_loss_data = calculate_stock_profit_loss(Historical_transaction_data)
                        # print("计算股票盈亏统计表数据为：", calculate_stock_profit_loss_data)

                        daily_returns = calculate_daily_returns(incomeBase_data, incomeBaseline)
                        # print("计算日收益率的数据为：",daily_returns)

                        # 处理交易数据
                        his_dict = defaultdict(list)
                        for item in Historical_transaction_data:
                            date = item['trade_date']
                            his_dict[date].append({
                                'st_code': item['st_code'],
                                'trade_type': item.get('trade_type', None),
                                'trade_price': item.get('trade_price', None),
                                'number_of_transactions': item.get('number_of_transactions', None),
                                'turnover': item.get('turnover', None)
                            })

                        # 提取收益率和资产数据
                        trade_date = [incomeBase_data[j]['trade_date'] for j in range(len(incomeBase_data))]
                        incomeBase_close = [incomeBaseline[i]['profit_and_loss_ratio'] for i in
                                            range(len(incomeBaseline))]
                        # print("收益率和资产数据为：", incomeBase_close)
                        back_return = [incomeBase_data[k]['profit_and_loss_ratio'] for k in range(len(incomeBase_data))]
                        stock_assets = [incomeBase_data[i]['assets'] for i in range(len(incomeBase_data))]
                        baseline_assets = [incomeBaseline[i]['assets'] for i in range(len(incomeBaseline))]

                        # 计算指标
                        risk_free_rate = 1.75 / 100
                        trading_days_per_year = 250

                        # 只有在有足够数据时才计算指标
                        if len(stock_assets) > 1 and len(baseline_assets) > 1:
                            transaction_data = pd.DataFrame(Historical_transaction_data)
                            # 最大回撤
                            stock_max_back = maxback(np.array(stock_assets))
                            # 夏普比率
                            stock_sharpe_ratio = sharpe_ratio(np.array(stock_assets), risk_free_rate,
                                                              trading_days_per_year)

                            stock_sortino_ratio = sortino_ratio(np.array(stock_assets), risk_free_rate,
                                                              trading_days_per_year)
                            # 年化收益率
                            stock_annualized_return = annualized_return(np.array(stock_assets), trading_days_per_year)
                            # 胜率
                            stock_win_rate = win_rate(transaction_data)
                            print("胜率为：", stock_win_rate)
                            baseline_max_back = maxback(np.array(incomeBase_close))
                            baseline_sharpe_ratio = sharpe_ratio(np.array(baseline_assets), risk_free_rate,
                                                                 trading_days_per_year)
                            baseline_annualized_return = incomeBase_close[-1] / len(
                                incomeBase_close) * trading_days_per_year

                            # 构建回测结果
                            backtest_result = {
                                'benchmarkReturns': incomeBase_close,
                                'dates': trade_date,
                                'strategyReturns': back_return,
                                'ShareHolding_stock': dict(share_dict),
                                'trades': dict(his_dict),
                                'calculate_stock_profit_loss': calculate_stock_profit_loss_data,
                                'daily_returns': daily_returns,
                                'metrics': {
                                    'strategy': {
                                        'maxDrawdown': stock_max_back,
                                        'sharpeRatio': stock_sharpe_ratio,
                                        'annualizedReturn': stock_annualized_return,
                                        'winRate': stock_win_rate,
                                        'sortinoRatio': stock_sortino_ratio
                                    },
                                    'benchmark': {
                                        'maxDrawdown': baseline_max_back,
                                        'sharpeRatio': baseline_sharpe_ratio,
                                        'annualizedReturn': baseline_annualized_return
                                    }
                                }
                            }

            except Exception as e:
                # 如果无法获取回测数据，则返回空的回测结果
                print(f"获取回测数据时出错: {e}")
                pass
            # print("回测结果为：", backtest_result)
            response_data = {
                'success': True,
                'received_data': strategy_config,
                'backtest_config': backtest_config,
                'backtest_result': backtest_result if backtest_result else {}
            }
            # 清理数据中的特殊值
            cleaned_response_data = clean_data_for_json(response_data)
            # 使用自定义编码器序列化
            json_string = json.dumps(cleaned_response_data, cls=DecimalJSONEncoder, ensure_ascii=False)
            final_response_data = json.loads(json_string)

            print("=== 序列化后的响应数据 ===")
            print("JSON字符串长度:", len(json_string))
            print("最终响应数据键:", list(final_response_data.keys()) if final_response_data else "无数据")

            return JsonResponse(final_response_data, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


def calculate_stock_profit_loss(history_data):
    """
    计算股票盈亏统计表
    """
    # 按日期排序
    sorted_data = sorted(history_data, key=lambda x: x['trade_date'])

    # 按股票代码分组存储交易记录
    stock_transactions = {}

    # 分组处理交易记录
    for record in sorted_data:
        st_code = record['st_code']
        if st_code not in stock_transactions:
            stock_transactions[st_code] = []
        stock_transactions[st_code].append(record)

    result = []

    # 处理每只股票的交易记录
    for st_code, transactions in stock_transactions.items():
        # 使用队列存储买入记录（先进先出）
        buy_queue = []

        for transaction in transactions:
            trade_type = transaction['trade_type']
            trade_date = transaction['trade_date']
            trade_price = transaction['trade_price']
            number_of_transactions = transaction['number_of_transactions']

            if trade_type == '买入':
                # 买入时将记录加入队列
                buy_queue.append({
                    'date': trade_date,
                    'price': trade_price,
                    'amount': number_of_transactions
                })
            elif trade_type == '卖出':
                # 卖出时从队列中匹配买入记录
                remaining_sell_amount = number_of_transactions

                while remaining_sell_amount > 0 and buy_queue:
                    # 取出最早的买入记录
                    buy_record = buy_queue[0]

                    # 计算可匹配的数量
                    matched_amount = min(remaining_sell_amount, buy_record['amount'])

                    # 计算盈亏（假设每手100股）
                    profit_loss = matched_amount * (trade_price - buy_record['price'])

                    # 添加到结果中
                    result.append({
                        '持股开始日期': buy_record['date'],
                        '持股终止日期': trade_date,
                        '股票代码': st_code,
                        '买入价格': float(buy_record['price']),
                        '卖出价格': float(trade_price),
                        '成交手数': matched_amount,
                        '盈亏资金': float(profit_loss)
                    })

                    # 更新买入记录的剩余数量
                    buy_record['amount'] -= matched_amount
                    remaining_sell_amount -= matched_amount

                    # 如果买入记录已完全匹配，则从队列中移除
                    if buy_record['amount'] <= 0:
                        buy_queue.pop(0)

    return result

def calculate_daily_returns(stock_data, benchmark_data):
    # 将数据转换为 DataFrame
    stock_df = pd.DataFrame(stock_data, columns=['trade_date', 'profit_and_loss_ratio'])
    benchmark_df = pd.DataFrame(benchmark_data, columns=['trade_date', 'profit_and_loss_ratio'])

    # 确保数据按日期排序
    stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
    benchmark_df['trade_date'] = pd.to_datetime(benchmark_df['trade_date'])
    stock_df = stock_df.sort_values(by='trade_date')
    benchmark_df = benchmark_df.sort_values(by='trade_date')

    # 计算日收益率
    stock_df['daily_return'] = stock_df['profit_and_loss_ratio'].diff()
    benchmark_df['daily_return'] = benchmark_df['profit_and_loss_ratio'].diff()

    # 合并两个 DataFrame
    merged_df = pd.merge(stock_df, benchmark_df, on='trade_date', suffixes=('_stock', '_benchmark'))

    # 构建结果列表，保留5位小数
    result = [
        {
            '日期': row['trade_date'].strftime('%Y-%m-%d'),
            '日收益率': round(row['daily_return_stock'], 5) if pd.notna(row['daily_return_stock']) else None,
            '日收益率（基准）': round(row['daily_return_benchmark'], 5) if pd.notna(
                row['daily_return_benchmark']) else None
        }
        for _, row in merged_df.iterrows()
    ]

    return result


# 订阅接口
@csrf_exempt
@permission_required('basic')
def subscribeStrategy(request):
    """
    用户订阅策略
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')
            print(" strategy_name：", strategy_name)
            print(" user_id：", user_id)
            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # 检查用户是否已经订阅了该策略
            existing_subscription = User_Strategy_Configuration.objects.filter(
                userID=user_id,
                strategyName=strategy_name
            ).first()

            print("existing_subscription：", existing_subscription)
            # 如果已经存在且已订阅，则返回错误
            if existing_subscription and existing_subscription.is_subscribed:
                return JsonResponse({'success': False, 'message': '您已经订阅了该策略'}, status=400)

            # 如果已存在但未订阅（即自建策略），也返回错误
            if existing_subscription and not existing_subscription.is_subscribed:
                return JsonResponse({'success': False, 'message': '您已创建同名策略'}, status=400)



            # 创建用户策略配置记录（订阅策略）
            User_Strategy_Configuration.objects.create(
                userID=user_id,
                strategyName=strategy_name,
                start_date=existing_subscription.start_date if hasattr(existing_subscription, 'start_date') else None,
                end_date=existing_subscription.end_date if hasattr(existing_subscription, 'end_date') else None,
                init_fund=existing_subscription.init_fund if hasattr(existing_subscription, 'init_fund') else 0,
                income_base=existing_subscription.income_base if hasattr(existing_subscription, 'income_base') else '沪深300',
                remove_st_stock=existing_subscription.remove_st_stock if hasattr(existing_subscription,
                                                                             'remove_st_stock') else False,
                remove_suspended_stok=existing_subscription.remove_suspended_stok if hasattr(existing_subscription,
                                                                                         'remove_suspended_stok') else False,
                optionfactor=existing_subscription.optionfactor if hasattr(existing_subscription, 'optionfactor') else None,
                bottomfactor=existing_subscription.bottomfactor if hasattr(existing_subscription, 'bottomfactor') else None,
                max_hold_num=existing_subscription.max_hold_num if hasattr(existing_subscription, 'max_hold_num') else 10,
                # 订阅相关字段
                is_subscribed=True,
                source_strategy_id=existing_subscription.strategy_id if hasattr(existing_subscription, 'strategy_id') else None
            )

            return JsonResponse({
                "success": True,
                "message": "订阅成功"
            }, status=200)

        except Exception as e:
            print("订阅策略出错:", str(e))  # 添加错误日志
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


# 公开策略
@csrf_exempt
def publicStrategy(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')

            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # 获取策略配置
            strategy_config = User_Strategy_Configuration.objects.filter(
                userID=user_id,
                strategyName=strategy_name
            ).first()

            if not strategy_config:
                return JsonResponse({'success': False, 'message': '未找到该策略配置'}, status=404)

            # 更新公开状态
            strategy_config.is_public = True
            strategy_config.source_user_id = user_id
            strategy_config.save()

            return JsonResponse({
                "success": True,
                "message": "策略已公开"
            }, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


@csrf_exempt
def getStockSelector(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("接收到的 StockSelector 数据为：", data)
            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')

            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # ✅ 使用 update_or_create 更新或创建记录
            obj, created = User_Strategy_Configuration.objects.update_or_create(
                userID=user_id,
                strategyName=strategy_name,
                defaults={
                    # 'factor': data.get('factor'),
                    'optionfactor': data.get('conditions'),

                    # 可以继续添加其他字段
                }
            )

            if created:
                msg = '策略配置已创建'
            else:
                msg = '策略配置已更新'

            # 此处可添加将数据保存到数据库的逻辑

            return JsonResponse({"success": True, "received_data": data}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)

@csrf_exempt
def getFactorConfig(request):
    if request.method == 'POST':
        print("请求头:", request.META.get('HTTP_COOKIE'))  # 查看是否收到 sessionid
        try:
            data = json.loads(request.body)
            print("接收到的 FactorConfig 数据为：", data)
            strategy_name = data.get('strategyName')
            user_id = request.session.get('user_id')
            print(" strategy_name：", strategy_name)
            print(" user_id：", user_id)
            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # ✅ 使用 update_or_create 更新或创建记录
            obj, created = User_Strategy_Configuration.objects.update_or_create(
                userID=user_id,
                strategyName=strategy_name,
                defaults={
                    # 'factor': data.get('factor'),
                    'bottomfactor': data.get('factors'),

                    # 可以继续添加其他字段
                }
            )

            if created:
                msg = '策略配置已创建'
            else:
                msg = '策略配置已更新'

            # 此处可添加将数据保存到数据库的逻辑

            return JsonResponse({"success": True, "received_data": data}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


def clear_backtest_memory():
    """清除回测相关的内存数据"""
    # 清除回测结果表
    sc.df_table_shareholding = pd.DataFrame(columns=[
        'trade_date', 'st_code', 'number_of_securities', 'saleable_quantity',
        'cost_price', 'profit_and_loss', 'profit_and_loss_ratio', 'latest_value',
        'current_price', 'strategy_id', 'user_id'
    ])

    sc.df_table_transaction = pd.DataFrame(columns=[
        'st_code', 'trade_date', 'trade_type', 'trade_price',
        'number_of_transactions', 'turnover', 'strategy_id', 'user_id'
    ])

    sc.df_table_statistic = pd.DataFrame(columns=[
        'trade_date', 'balance', 'available', 'reference_market_capitalization',
        'assets', 'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
    ])

    sc.df_table_baseline = pd.DataFrame(columns=[
        'trade_date', 'reference_market_capitalization', 'assets',
        'profit_and_loss', 'profit_and_loss_ratio', 'strategy_id', 'user_id'
    ])

    print("回测内存数据已清除")


@csrf_exempt
def getBackTrigger(request):
    if request.method == 'POST':
        try:
            clear_backtest_memory()
            gc.collect()
            # 1️⃣ 接收前端发来的完整参数
            raw_data = request.body.decode('utf-8')
            data = json.loads(raw_data)

            # 2️⃣ 提取各模块数据
            strategy_params = data.get('strategy', {})
            factor_data = data.get('factor', {}).get('received_data', {}).get('factors', [])
            selector_data = data.get('selector', {}).get('received_data', {}).get('conditions', [])


            strategy_name = strategy_params.get('strategyName')
            # 解析基础参数
            uid = request.session.get('user_id', '')
            config = User_Strategy_Configuration.objects.filter(
                userID=uid,
                strategyName=strategy_name
            ).first()

            if config:
                sid = config.id  # 获取策略配置的ID


            init_fund = strategy_params.get('capital')  # 初始资金
            Investment_ratio = strategy_params.get('ratio')  # 投资比例
            # incomeBase = strategy_params.get('incomeBase')
            hold_stock_num = strategy_params.get('hold')  # 持仓股票数
            start_time = strategy_params.get('start_date')# 开始时间
            end_time = strategy_params.get('end_date')# 结束时间



            # 转换资金、时间等基础参数
            Init_fund = float(init_fund) * 10000 if init_fund else 1000000.0
            Investment_ratio = float(Investment_ratio) if Investment_ratio else 1.0
            Hold_stock_num = int(hold_stock_num) if hold_stock_num else 10
            Start_time = datetime.strptime(start_time, '%Y-%m-%d').strftime('%Y%m%d')
            End_time = datetime.strptime(end_time, '%Y-%m-%d').strftime('%Y%m%d')

            Botfacname = {item["name"]: str(item["value"]) for item in factor_data}
            print('Botfacname',Botfacname)
            Optionfacname = {item["factor"  ]: str(item["operator"]) for item in selector_data}
            print('Optionfacname',Optionfacname)

            # 根据选股条件中的operator选择策略
            strategy_type = 'default'
            if selector_data and len(selector_data) > 0:
                strategy_type = selector_data[0].get('operator', 'default')
                print('strategy_type', strategy_type)

            # 获取对应的策略函数
            strategy_main = STRATEGY_MAIN_MAP.get(strategy_type, STRATEGY_MAIN_MAP['default'])
            print(f"使用的策略函数: {strategy_main.__name__}")
            # 调用策略函数
            strategy_main(Init_fund, Investment_ratio, Hold_stock_num, Start_time, End_time, Optionfacname, Botfacname,
                          sid, uid)

            try:
                # 添加分页查询，避免一次性加载过多数据
                shareholding_queryset = Current_shareholding_information.objects.filter(
                    strategy_id=sid, user_id=uid, trade_date__range=[Start_time, End_time]
                ).order_by('trade_date').values("trade_date", 'st_code')

                # 限制查询结果数量，添加异常处理
                ShareHolding_data = list(shareholding_queryset[:10000])  # 限制最多10000条记录
                # print(f"ShareHolding_data count: {len(ShareHolding_data)}")

                transaction_queryset = Historical_transaction_information.objects.filter(
                    strategy_id=sid, user_id=uid, trade_date__range=[Start_time, End_time]
                ).order_by('trade_date').values(
                    "trade_date", 'st_code', 'trade_type', 'trade_price', 'number_of_transactions', 'turnover'
                )

                Historical_transaction_data = list(transaction_queryset[:10000])  # 限制最多10000条记录
                # print(f"Historical_transaction_data count: {len(Historical_transaction_data)}")

                income_queryset = Daily_statistics.objects.filter(
                    strategy_id=sid, user_id=uid, trade_date__range=[Start_time, End_time]
                ).order_by('trade_date').values("trade_date", 'profit_and_loss_ratio', 'assets')

                incomeBase_data = list(income_queryset[:10000])  # 限制最多10000条记录
                # print(f"incomeBase_data count: {len(incomeBase_data)}")

                baseline_queryset = list(
                    Baseline_Profit_Loss.objects.filter(strategy_id=sid, user_id=uid,
                                                        trade_date__range=[Start_time, End_time])
                    .order_by('trade_date')
                    .values("trade_date", 'profit_and_loss_ratio', 'assets')
                    .distinct()
                )
                incomeBaseline = list(baseline_queryset[:10000])  # 限制最多10000条记录
                # print(f"incomeBaseline count: {len(incomeBaseline)}")

            except Exception as e:
                # print(f"数据库查询出错: {e}")
                return JsonResponse({"success": False, "error": f"数据库查询失败: {str(e)}"}, status=500)


                ShareHolding_data = shareholding_data
                Historical_transaction_data = transaction_data
                incomeBase_data = income_data
                incomeBaseline = baseline_data

            except Exception as e:
                return JsonResponse({"success": False, "error": f"数据处理失败: {str(e)}"}, status=500)
            # 以上的结果是用于输出到折线图中，结果是用户指定策略跑出的结果，折线图显示的应该是账户的总资产，包括在股市内的股票，而不是输出的可用资金。所以应该是assets而不是available
            trade_date = [incomeBase_data[j]['trade_date'] for j in range(len(incomeBase_data))]
            ShareHolding_stock = ShareHolding_data
            share_dict = defaultdict(list)
            for item in ShareHolding_stock:
                share_dict[item['trade_date']].append(item['st_code'])
            # print('share_dict', share_dict)

            his_dict = defaultdict(list)
            for item in Historical_transaction_data:
                date = item['trade_date']
                # 将每个 item 的所有字段加入字典
                his_dict[date].append({
                    'st_code': item['st_code'],
                    'trade_type': item.get('trade_type', None),  # 如果字段可能不存在，使用 get 设置默认值
                    'trade_price': item.get('trade_price', None),
                    'number_of_transactions': item.get('number_of_transactions', None),
                    'turnover': item.get('turnover', None)
                })
            # print('his_dict', his_dict)
            incomeBase_close = [incomeBaseline[i]['profit_and_loss_ratio'] for i in range(len(incomeBaseline))]
            back_return = [incomeBase_data[k]['profit_and_loss_ratio'] for k in range(len(incomeBase_data))]
            stock_assets = [incomeBase_data[i]['assets'] for i in range(len(incomeBase_data))]
            baseline_assets = [incomeBaseline[i]['assets'] for i in range(len(incomeBaseline))]
            risk_free_rate = 1.75 / 100
            trading_days_per_year = 250
            transaction_data = sc.df_table_transaction
            # 交易胜率
            stock_win_rate = win_rate(transaction_data)
            # 最大回撤
            stock_max_back = maxback(np.array(stock_assets))
            # 夏普比率
            stock_sharpe_ratio = sharpe_ratio(np.array(stock_assets), risk_free_rate, trading_days_per_year)
            # 年华收益
            stock_annualized_return = annualized_return(np.array(stock_assets), trading_days_per_year)
            # baseline_max_back = maxback(np.array(baseline_assets))

            baseline_max_back = maxback(np.array(incomeBase_close))
            # print('baseline_max_back', baseline_max_back)
            baseline_sharpe_ratio = sharpe_ratio(np.array(baseline_assets), risk_free_rate, trading_days_per_year)
            # baseline_annualized_return = annualized_return(np.array(baseline_assets), trading_days_per_year)
            baseline_annualized_return = incomeBase_close[-1] / len(incomeBase_close) * trading_days_per_year
            # print('maxback', stock_max_back)
            result = {
                      'benchmarkReturns': incomeBase_close,
                      'dates': trade_date,
                      'strategyReturns': back_return,
                      'ShareHolding_stock': dict(share_dict),
                      'trades': dict(his_dict)}

            # result = mock_backtest(data)
            return JsonResponse(result, status=200)


        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    elif request.method == 'GET':
        # 可选：用于调试时 GET 查看默认数据
        return JsonResponse(mock_backtest({}), status=200)

# 模拟回测函数
def mock_backtest(params):
    # 这里可以替换为真实回测逻辑
    return {
        "dates": ["20250101", "20250102", "20250103"],
        "benchmarkReturns": [0.01, -0.005, 0.008],
        "strategyReturns": [0.02, -0.01, 0.015],
        "holdings": {
            "20250101": ["600000.SH", "000001.SZ"],
            "20250102": [],
            "20250103": ["000001.SZ"]
        },
        "trades": {
            "20250101": [{"stock": "600000.SH", "type": "买入", "price": 10.0}],
            "20250103": [{"stock": "000001.SZ", "type": "卖出", "price": 10.5}]
        }
    }

def backTrader(request):
    return JsonResponse(mock_backtest({}), status=200)

# 新建策略
@method_decorator(csrf_exempt, name='dispatch')
# @method_decorator(permission_required('basic'), name='get')
class newConstruction(View):
    def get(self, request):
        user_id = request.session.get('user_id')
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        try:
            s = Session.objects.get(session_key=session_key)
            print(s.get_decoded())
        except Session.DoesNotExist:
            print("当前请求没有对应的 session")
        if not user_id:
            return JsonResponse({'error': '未登录'}, status=401)

        try:
            # 查询该用户的所有策略
            strategies = User_Strategy_Configuration.objects.filter(userID=user_id)

            # 将数据转换为前端可用格式
            strategy_list = [
                {
                    "strategyName": strategy.strategyName,
                    "start_date": strategy.start_date,
                    "end_date": strategy.end_date,
                    "init_fund": float(strategy.init_fund) if strategy.init_fund else 0,
                    "max_hold_num": strategy.max_hold_num,
                    "income_base": strategy.income_base,
                    "remove_st_stock": "true" if strategy.remove_st_stock else "false",
                    "remove_suspended_stok": "true" if strategy.remove_suspended_stok else "false"
                }
                for strategy in strategies
            ]

            return JsonResponse({"state": strategy_list}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

# 插入策略名称
@csrf_exempt
def insert_name(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            strategy_name = data.get('strategyName')
            print('strategy_name', strategy_name)

            if not strategy_name:
                return JsonResponse({'success': False, 'message': '策略名称不能为空'}, status=400)

            # 获取当前登录用户的 user_id
            user_id = request.session.get('user_id')
            print('user_id', user_id)
            if not user_id:
                return JsonResponse({'success': False, 'message': '未登录'}, status=401)
            # 使用数据库自增字段插入数据
            strategy_instance = User_Strategy_Configuration.objects.create(
                strategyName=strategy_name,
                userID=user_id
                # 如果 strategyID 是自增字段，无需手动指定
            )
            # strategy_id = strategy_instance.id  # 这就是你想要的自增ID
            # print('strategy_id', strategy_id)

            return JsonResponse({'success': True, 'message': '策略已保存'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

@csrf_exempt
def delete_strategy(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uid = request.session.get('user_id')
            strategy_name = data.get('strategyName')
            print('strategy_name', strategy_name)

            if not strategy_name:
                return JsonResponse({'success': False, 'message': '缺少策略名称'}, status=400)
            strategy_config = User_Strategy_Configuration.objects.filter(
                userID=uid,
                strategyName=strategy_name
            ).first()
            if strategy_config:
                sid = strategy_config.id  # 获取策略配置的ID
                print('sid', sid)
                sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_shareholding)
                sc.execute_sql(sql, (sid, uid))
                sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_transaction)
                sc.execute_sql(sql, (sid, uid))
                sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_statistic)
                sc.execute_sql(sql, (sid, uid))


                # 最后删除策略配置表中的数据
                strategy_config.delete()


            return JsonResponse({'success': True, 'message': '策略删除成功'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

import threading
from django.db import transaction
from django.db.models import Q

import concurrent.futures
from django.core.management import execute_from_command_line

def daily_backtest_scheduler(schedule_time=None):
    """
    每日定时执行回测的调度器
    在每天指定时间执行（默认下午2点50分）

    Args:
        schedule_time: 指定执行时间，格式为 "HH:MM" 字符串，如 "14:50"
                      如果为 None，则使用默认时间
    """

    def parse_schedule_time(time_str):
        """解析时间字符串"""
        if time_str:
            try:
                hour, minute = map(int, time_str.split(':'))
                return hour, minute
            except:
                print(f"时间格式错误 {time_str}，使用默认时间 14:50")
        return 14, 50  # 默认时间

    def run_daily_backtest():
        hour, minute = parse_schedule_time(schedule_time)

        while True:
            try:
                # 获取当前时间
                now = datetime.now()
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # 如果今天已经过了目标时间，则等待到明天
                if now > target_time:
                    target_time = target_time + timedelta(days=1)

                # 计算等待时间
                wait_seconds = (target_time - now).total_seconds()

                print(f"下次回测执行时间: {target_time} (每天 {hour:02d}:{minute:02d})")
                time.sleep(wait_seconds)

                # 执行每日回测
                execute_daily_backtests()

                # 等待到第二天
                time.sleep(60)  # 等待1分钟避免重复执行

            except Exception as e:
                print(f"定时回测调度器出错: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)  # 出错后等待1分钟再继续

    # 在后台线程中启动调度器
    scheduler_thread = threading.Thread(target=run_daily_backtest, daemon=True)
    scheduler_thread.start()
    print(f"每日回测调度器已启动，将在每天 {hour:02d}:{minute:02d} 执行")


def execute_daily_backtests(max_workers=3):
    """
    执行所有用户的当日回测

    Args:
        max_workers: 最大并发工作线程数，默认为3
    """
    try:
        print("开始执行每日回测任务...")

        # 获取所有需要执行回测的策略配置
        # 过滤掉参数不完整的策略
        strategies = User_Strategy_Configuration.objects.filter(
            # 确保必要参数不为空
            ~Q(strategyName__isnull=True) & ~Q(strategyName=''),
            ~Q(start_date__isnull=True),
            ~Q(end_date__isnull=True),
            ~Q(init_fund__isnull=True),
            ~Q(max_hold_num__isnull=True),
            ~Q(optionfactor=True),
            ~Q(bottomfactor=True),
        ).select_related()  # 使用select_related减少数据库查询

        print(f"找到 {strategies.count()} 个策略需要回测")

        # 使用线程池执行回测，控制并发数
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有回测任务
            future_to_strategy = {
                executor.submit(execute_single_backtest, strategy): strategy
                for strategy in strategies
            }

            # 等待所有任务完成
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy = future_to_strategy[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"策略 {strategy.strategyName} 执行出错: {e}")
                    import traceback
                    traceback.print_exc()

        print("所有回测任务执行完成")

    except Exception as e:
        print(f"执行每日回测时出错: {e}")
        import traceback
        traceback.print_exc()


def check_partition_table_data(date_str):
    """
    检查partition_table表中是否有指定日期的数据
    在一分钟内检查6次，每次间隔10秒
    """
    try:
        # 这里需要根据你的实际表结构来检查数据
        # 假设你有一个方法来检查数据

        # 如果你有具体的检查逻辑，可以替换下面的示例代码
        for i in range(6):
            try:
                # 示例：检查某个表中是否有指定日期的数据
                # 你需要根据实际的表结构和检查逻辑来实现
                # 例如：
                # from .models import YourPartitionModel
                # if YourPartitionModel.objects.filter(date_field=date_str).exists():
                #     return True

                # 暂时返回True用于测试
                return True
            except Exception as check_error:
                print(f"检查数据时出错 ({i + 1}/6): {check_error}")

            if i < 5:  # 最后一次不需要等待
                time.sleep(10)  # 等待10秒后再次检查

        return False  # 1分钟后仍未找到数据
    except Exception as e:
        print(f"检查partition_table数据时出错: {e}")
        return False


def parse_factor_config(factor_str):
    """
    解析因子配置字符串

    Args:
        factor_str: 因子配置字符串或对象

    Returns:
        解析后的因子字典
    """
    if not factor_str:
        return {}

    try:
        # 如果已经是字典格式，直接返回
        if isinstance(factor_str, dict):
            return factor_str

        # 如果是字符串，尝试解析
        if isinstance(factor_str, str):
            # 尝试JSON解析
            try:
                return json.loads(factor_str)
            except json.JSONDecodeError:
                # 尝试Python字面量解析
                import ast
                try:
                    return ast.literal_eval(factor_str)
                except:
                    print(f"无法解析因子配置: {factor_str}")
                    return {}

        return factor_str
    except Exception as e:
        print(f"解析因子配置时出错: {e}")
        return {}


def execute_single_backtest(strategy_config):
    """
    执行单个策略的回测
    """
    try:
        # 检查必要参数
        if not is_strategy_config_valid(strategy_config):
            print(f"策略 {strategy_config.strategyName} 参数不完整，跳过回测")
            return

        # 检查partition_table是否有当天数据
        today_str = datetime.now().strftime('%Y%m%d')
        # today_str = 20250801  # 测试用，实际使用时应为当前日期
        if not check_partition_table_data(today_str):
            print(f"partition_table中没有 {today_str} 的数据，跳过策略 {strategy_config.strategyName} 的回测")
            return

        print(f"开始执行策略 {strategy_config.strategyName} 的回测")

        # 提取回测参数
        uid = strategy_config.userID
        sid = strategy_config.id
        strategy_name = strategy_config.strategyName

        # 转换参数
        init_fund = float(strategy_config.init_fund) * 10000 if strategy_config.init_fund else 1000000.0
        print(f"策略 {strategy_name} 初始资金: {init_fund}")
        investment_ratio = 1.0  # 默认投资比例
        hold_stock_num = int(strategy_config.max_hold_num) if strategy_config.max_hold_num else 10

        # 使用策略配置中的开始时间到当前日期作为回测时间范围
        end_time = datetime.now().strftime('%Y%m%d')
        # 从策略配置中获取开始日期
        if strategy_config.start_date:
            start_time = datetime.strptime(str(strategy_config.start_date), '%Y-%m-%d').strftime('%Y%m%d')
        else:
            # 如果没有配置开始日期，则默认使用昨天
            start_time = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

        # 解析因子配置
        botfacname = {}  # bottomfactor格式: [{'name': '上涨幅度', 'operator': '大于', 'value': 5}, ...]
        optionfacname = {}  # optionfactor格式: [{'factor': '基本策略', 'operator': 'macd策略'}]

        # 处理bottomfactor
        if hasattr(strategy_config, 'bottomfactor') and strategy_config.bottomfactor:
            try:
                bottom_data = parse_factor_config(strategy_config.bottomfactor)
                if isinstance(bottom_data, list):
                    # 转换为字典格式 {name: value}
                    botfacname = {item.get('name', f'factor_{i}'): str(item.get('value', ''))
                                  for i, item in enumerate(bottom_data)
                                  if isinstance(item, dict) and 'name' in item}
                elif isinstance(bottom_data, dict):
                    botfacname = {k: str(v) for k, v in bottom_data.items()}
            except Exception as e:
                print(f"解析bottomfactor时出错: {e}")

        # 处理optionfactor
        if hasattr(strategy_config, 'optionfactor') and strategy_config.optionfactor:
            try:
                option_data = parse_factor_config(strategy_config.optionfactor)
                if isinstance(option_data, list):
                    # 转换为字典格式 {factor: operator}
                    optionfacname = {item.get('factor', f'strategy_{i}'): str(item.get('operator', ''))
                                     for i, item in enumerate(option_data)
                                     if isinstance(item, dict) and 'factor' in item}
                elif isinstance(option_data, dict):
                    optionfacname = {k: str(v) for k, v in option_data.items()}
            except Exception as e:
                print(f"解析optionfactor时出错: {e}")

        print(f"策略 {strategy_name} 参数:")
        print(f"  - 初始资金: {init_fund}")
        print(f"  - 持仓数量: {hold_stock_num}")
        print(f"  - 时间范围: {start_time} - {end_time}")
        print(f"  - bottomfactor: {botfacname}")
        print(f"  - optionfactor: {optionfacname}")

        # 执行回测
        from .final_project3_生产环境_备份 import main1
        main1(init_fund, investment_ratio, hold_stock_num, start_time, end_time,
              optionfacname, botfacname, sid, uid)

        print(f"策略 {strategy_config.strategyName} 回测执行完成")

    except Exception as e:
        print(f"执行策略 {strategy_config.strategyName} 回测时出错: {e}")
        import traceback
        traceback.print_exc()



def is_strategy_config_valid(strategy_config):
    """
    检查策略配置参数是否完整
    """
    required_fields = [
        'strategyName', 'start_date', 'end_date', 'init_fund', 'max_hold_num','bottomfactor','optionfactor',
    ]

    for field in required_fields:
        value = getattr(strategy_config, field, None)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            print(f"策略 {strategy_config.strategyName} 缺少必要参数: {field}")
            return False

    return True


# 启动定时回测调度器
def start_backtest_scheduler(schedule_time=None):
    """
    启动回测调度器

    Args:
        schedule_time: 指定执行时间，格式为 "HH:MM" 字符串，如 "14:50"
                      如果为 None，则使用默认时间
    """
    try:
        daily_backtest_scheduler(schedule_time)
        print("回测调度器启动成功")
    except Exception as e:
        print(f"启动回测调度器时出错: {e}")


# 手动触发回测的API端点
@csrf_exempt
def trigger_daily_backtest(request):
    """
    手动触发当日回测（用于测试）
    可以通过POST参数指定并发数和执行时间
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}

            # 获取参数
            max_workers = data.get('max_workers', 3)
            schedule_time = data.get('schedule_time', None)  # 用于测试的执行时间

            # 在后台线程中执行回测
            def run_backtest():
                if schedule_time:
                    # 如果指定了时间，立即执行一次测试
                    print(f"立即执行回测测试，使用 {max_workers} 个工作线程")
                    execute_daily_backtests(max_workers)
                else:
                    # 否则按正常调度执行
                    execute_daily_backtests(max_workers)

            backtest_thread = threading.Thread(target=run_backtest)
            backtest_thread.start()

            return JsonResponse({
                "success": True,
                "message": f"回测任务已启动，使用 {max_workers} 个工作线程",
                "command": "refresh_page"  # 前端可以监听这个命令来刷新页面
            }, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


# 立即执行单个策略回测的API端点
@csrf_exempt
def trigger_single_backtest(request):
    """
    立即执行单个策略的回测（用于测试）
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            strategy_name = data.get('strategyName')
            # user_id = request.session.get('user_id')
            user_id = data.get('user_id')

            if not strategy_name or not user_id:
                return JsonResponse({'success': False, 'message': '缺少 strategyName 或 userID'}, status=400)

            # 获取策略配置
            strategy_config = User_Strategy_Configuration.objects.filter(
                userID=user_id,
                strategyName=strategy_name
            ).first()

            if not strategy_config:
                return JsonResponse({'success': False, 'message': '未找到该策略配置'}, status=404)

            # 在后台线程中执行单个回测
            backtest_thread = threading.Thread(target=execute_single_backtest, args=(strategy_config,))
            backtest_thread.start()

            return JsonResponse({
                "success": True,
                "message": f"策略 {strategy_name} 回测任务已启动",
                "command": "refresh_page"
            }, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    else:
        return JsonResponse({"success": False, "error": "只支持 POST 请求"}, status=405)


# 策略模拟和相似股票

# 已下线模块（个股诊断、股票日历、策略模拟、相似股票模拟）相关历史实现已移除。

