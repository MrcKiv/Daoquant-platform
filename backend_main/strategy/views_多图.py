import gc
import random
from decimal import Decimal
import requests
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
import json
from collections import defaultdict
from datetime import datetime, timedelta
import time
import traceback

from scipy.constants import hour, minute
from sqlalchemy import create_engine

from user.models import User
from ._missing_strategy import unavailable_strategy
from .StockSimilarCal import find_similar_stocks_adaptive, get_All_Stocks, get_Target_Stock
from .decorators import permission_required
from .final_project3_生产环境_macd策略 import macd_main
from .final_project3_生产环境_macd纯 import macd_you_main
from .final_project3_生产环境_macd_行业 import macd_industry_main
from .final_project3_生产环境_增量回测概念 import macd_concept_main
from .final_project3_生产环境_sby import sby_main
try:
    from .final_project3_生产环境_韩冰冰 import hbb_main
except Exception as exc:
    hbb_main = unavailable_strategy("hbb策略", exc)
from .final_project3_生产环境_cmy import cmy_main
from .final_project3_生产环境_60分钟金叉与日线金叉匹配_自动交易 import daily_60m_cross_main
from .models import Current_shareholding_information, Historical_transaction_information, \
    Daily_statistics, Baseline_Profit_Loss, User_Strategy_Configuration, Strategy, SaveState, Industry_Daily_Info, \
    Stock_Basic_Info, Baseline_index
from .report_cache import load_backtest_cache, save_backtest_cache
import strategy.mysql_connect as sc
from scipy.signal import find_peaks
from django.contrib.sessions.models import Session
from django.middleware.csrf import get_token
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
    peak_values = time_series[peaks]
    valley_values = time_series[valleys]
    safe_peak_values = np.where(np.abs(peak_values) < 1e-12, np.nan, peak_values)
    drawdowns = np.divide(
        peak_values - valley_values,
        safe_peak_values,
        out=np.zeros_like(peak_values, dtype=float),
        where=~np.isnan(safe_peak_values),
    )
    finite_drawdowns = drawdowns[np.isfinite(drawdowns)]
    if finite_drawdowns.size == 0:
        return 0.0
    maxdiff = finite_drawdowns.max()

    return round(float(maxdiff), 3)
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


class DecimalJSONEncoder(DjangoJSONEncoder):
    """自定义JSON编码器，处理Decimal和numpy标量"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, np.generic):
            return obj.item()
        return super().default(obj)


def clean_data_for_json(data):
    """递归清理数据，将inf、NaN等特殊值转换为None"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    if isinstance(data, tuple):
        return [clean_data_for_json(item) for item in data]
    if isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    if isinstance(data, np.ndarray):
        return [clean_data_for_json(item) for item in data.tolist()]
    if isinstance(data, np.generic):
        return clean_data_for_json(data.item())
    if isinstance(data, float):
        if not np.isfinite(data):
            return None
        return data
    if isinstance(data, Decimal):
        return float(data)
    return data


FULL_REPORT_RESULT_KEYS = [
    'daily_returns',
    'period_returns',
    'annual_returns',
    'stock_performance_attribution_range',
    'stock_performance_attribution_loss_range',
    'industry_allocation_timeline',
    'holdings_timeline',
    'industry_holdings_analysis',
    'end_period_market_value_proportion',
    'transaction_type_analysis',
    'transaction_type_analysis_sell',
    'calculate_stock_profit_loss',
    'metrics',
]


def serialize_json_field(value):
    """Serialize list/dict payloads before storing them in text columns."""
    if value in (None, ""):
        return None
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return value


def deserialize_json_field(value, default=None):
    """Parse JSON/Python-literal strings back into Python objects."""
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            import ast
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return default if default is not None else value
    return default if default is not None else value


def get_strategy_config_queryset(user_id, strategy_name):
    return User_Strategy_Configuration.objects.filter(
        userID=str(user_id),
        strategyName=strategy_name
    ).order_by('-id')


def get_latest_strategy_config(user_id, strategy_name):
    queryset = get_strategy_config_queryset(user_id, strategy_name)
    strategy_config = queryset.first()
    duplicate_count = queryset.count()
    if strategy_config and duplicate_count > 1:
        print(
            f"Warning: found {duplicate_count} strategy configs for "
            f"user={user_id}, strategy={strategy_name}. Using latest id={strategy_config.id}."
        )
    return strategy_config


@csrf_exempt
def getStrategyConfig(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("接收到的数据为：", data)

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
                    'labels': serialize_json_field(data.get('labels')),
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
            print(f"getStrategyConfig error: {e}")
            traceback.print_exc()
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

# 获取数据
# 获取数据
def fetch_backtest_data(sid, uid, start_time, end_time):
    """
    获取回测结果数据

    Args:
        sid: 策略ID
        uid: 用户ID
        start_time: 开始时间 (YYYYMMDD格式)
        end_time: 结束时间 (YYYYMMDD格式)

    Returns:
        tuple: 包含五个元素的元组:
            - ShareHolding_data: 持股信息列表
            - Historical_transaction_data: 历史交易信息列表
            - incomeBase_data: 日常统计数据列表
            - incomeBaseline: 基准收益数据列表
            - stock_performance_data: 个股绩效归因数据列表
    """

    # 获取回测结果数据
    ShareHolding_data = list(
        Current_shareholding_information.objects.filter(strategy_id=sid, user_id=uid,
                                                        trade_date__range=[start_time,
                                                                           end_time]).order_by(
            'trade_date').values(
            "trade_date", 'st_code', 'latest_value'))

    Historical_transaction_data = list(
        Historical_transaction_information.objects.filter(strategy_id=sid, user_id=uid,
                                                          trade_date__range=[start_time,
                                                                             end_time]).order_by(
            'trade_date').values(
            "trade_date", 'st_code', 'trade_type', 'trade_price', 'number_of_transactions', 'turnover'))

    incomeBase_data = list(
        Daily_statistics.objects.filter(strategy_id=sid, user_id=uid,
                                        trade_date__range=[start_time, end_time]).order_by(
            'trade_date').values(
            "trade_date", 'profit_and_loss_ratio', 'assets'))

    # 大盘盈亏表去重
    incomeBaseline = list(
        Baseline_Profit_Loss.objects.filter(strategy_id=sid, user_id=uid,
                                            trade_date__range=[start_time, end_time])
        .order_by('trade_date')
        .values("trade_date", 'profit_and_loss_ratio', 'assets')
        .distinct()
    )

    # 获取个股绩效归因数据
    stock_performance_data = list(
        Current_shareholding_information.objects.filter(strategy_id=sid, user_id=uid,
                                                        trade_date__range=[start_time, end_time])
        .values('st_code', 'number_of_securities', 'current_price', 'profit_and_loss')
    )

    # 获取行业配置数据
    industry_data = list(
        Industry_Daily_Info.objects.all()
        .values('st_code', 'Industry_name')
    )

    # 获取股票基本信息数据
    stock_basic_data = list(
        Stock_Basic_Info.objects.all()
        .values('st_code', 'name', 'list_date')
    )

    # print(f"=== fetch_backtest_data 调试信息 ===")
    # print(f"ShareHolding_data 长度: {len(ShareHolding_data)}")
    # print(f"Historical_transaction_data 长度: {len(Historical_transaction_data)}")
    # print(f"incomeBase_data 长度: {len(incomeBase_data)}")
    # print(f"incomeBaseline 长度: {len(incomeBaseline)}")
    # print(f"stock_performance_data 长度: {len(stock_performance_data)}")
    # print(f"industry_data 长度: {len(industry_data)}")
    # print(f"stock_basic_data 长度: {len(stock_basic_data)}")

    # if industry_data:
    #     print(f"industry_data 示例 (前3条): {industry_data[:3]}")
    # else:
    #     print("industry_data 为空!")

    # if ShareHolding_data:
    #     print(f"ShareHolding_data 示例 (前3条): {ShareHolding_data[:3]}")
    # else:
    #     print("ShareHolding_data 为空!")

    return ShareHolding_data, Historical_transaction_data, incomeBase_data, incomeBaseline, stock_performance_data, industry_data, stock_basic_data

    # print(f"获取到指定时间范围内个股绩效归因原始数据: {len(stock_performance_data)} 条")
    # if stock_performance_data:
    #     print(f"数据示例: {stock_performance_data[:2]}")
    #     # 检查数据字段
    #     for i, item in enumerate(stock_performance_data[:3]):
    #         print(f"  数据{i+1}: st_code={item.get('st_code')}, "
    #               f"number_of_securities={item.get('number_of_securities')} (类型: {type(item.get('number_of_securities'))}), "
    #               f"current_price={item.get('current_price')} (Type: {type(item.get('current_price'))}), "
    #               f"profit_and_loss={item.get('profit_and_loss')} (类型: {type(item.get('profit_and_loss'))})")


def fetch_all_backtest_data(sid, uid):
    """
    获取所有回测结果数据（不局限于指定的时间范围）

    Args:
        sid: 策略ID
        uid: 用户ID

    Returns:
        tuple: 包含五个元素的元组:
            - ShareHolding_data: 持股信息列表
            - Historical_transaction_data: 历史交易信息列表
            - incomeBase_data: 日常统计数据列表
            - incomeBaseline: 基准收益数据列表
            - stock_performance_data: 个股绩效归因数据列表
    """

    # 获取所有回测结果数据
    ShareHolding_data = list(
        Current_shareholding_information.objects.filter(strategy_id=sid, user_id=uid)
        .order_by('trade_date').values("trade_date", 'st_code', 'latest_value'))

    Historical_transaction_data = list(
        Historical_transaction_information.objects.filter(strategy_id=sid, user_id=uid)
        .order_by('trade_date').values(
            "trade_date", 'st_code', 'trade_type', 'trade_price', 'number_of_transactions', 'turnover'))

    incomeBase_data = list(
        Daily_statistics.objects.filter(strategy_id=sid, user_id=uid)
        .order_by('trade_date').values("trade_date", 'profit_and_loss_ratio', 'assets'))

    # 大盘盈亏表去重
    incomeBaseline = list(
        Baseline_Profit_Loss.objects.filter(strategy_id=sid, user_id=uid)
        .order_by('trade_date')
        .values("trade_date", 'profit_and_loss_ratio', 'assets')
        .distinct()
    )

    # 获取个股绩效归因数据
    stock_performance_data = list(
        Current_shareholding_information.objects.filter(strategy_id=sid, user_id=uid)
        .values('st_code', 'number_of_securities', 'current_price', 'profit_and_loss')
    )

    # 获取行业配置数据
    industry_data = list(
        Industry_Daily_Info.objects.all()
        .values('st_code', 'Industry_name')
    )

    # 获取股票基本信息数据
    stock_basic_data = list(
        Stock_Basic_Info.objects.all()
        .values('st_code', 'name', 'list_date')
    )

    # 获取大盘指数数据
    market_index_data = list(
        Baseline_index.objects.all()
        .order_by('trade_date')
        .values('trade_date', 'close')
    )

    # print(f"=== fetch_all_backtest_data 调试信息 ===")
    # print(f"ShareHolding_data 长度: {len(ShareHolding_data)}")
    # print(f"Historical_transaction_data 长度: {len(Historical_transaction_data)}")
    # print(f"incomeBase_data 长度: {len(incomeBase_data)}")
    # print(f"incomeBaseline 长度: {len(incomeBaseline)}")
    # print(f"stock_performance_data 长度: {len(stock_performance_data)}")
    # print(f"industry_data 长度: {len(industry_data)}")
    # print(f"stock_basic_data 长度: {len(stock_basic_data)}")
    # print(f"market_index_data 长度: {len(market_index_data)}")

    # if industry_data:
    #     print(f"industry_data 示例 (前3条): {industry_data[:3]}")
    # else:
    #     print("industry_data 为空!")

    # print(f"ShareHolding_data 示例 (前3条): {ShareHolding_data[:3]}")
    # else:
    #     print("ShareHolding_data 为空!")

    return ShareHolding_data, Historical_transaction_data, incomeBase_data, incomeBaseline, stock_performance_data, industry_data, stock_basic_data, market_index_data

    # print(f"获取到个股绩效归因原始数据: {len(stock_performance_data)} 条")
    # if stock_performance_data:
    #     print(f"数据示例: {stock_performance_data[:2]}")
    #     # 检查数据字段
    #     for i, item in enumerate(stock_performance_data[:3]):
    #         print(f"  数据{i+1}: st_code={item.get('st_code')}, "
    #               f"number_of_securities={item.get('number_of_securities')} (类型: {type(item.get('number_of_securities'))}), "
    #               f"current_price={item.get('current_price')} (类型: {type(item.get('current_price'))}), "
    #               f"profit_and_loss={item.get('profit_and_loss')} (类型: {type(item.get('profit_and_loss'))})")


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
            user_config = get_latest_strategy_config(user_id, strategy_name)

            public_config = User_Strategy_Configuration.objects.filter(
                is_public=True
            ).exclude(userID=user_id).first()
            print(" public_config：", public_config)
            config = user_config or public_config

            if not config:
                return JsonResponse({'success': False, 'message': '未找到该策略配置'}, status=404)
            print("查询到的数据为：", config)

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
                "labels": deserialize_json_field(config.labels, default=[]),
                "is_public": config.is_public,
            }
            print("基础策略配置数据为：", strategy_config)
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
            print("回测配置数据为：", backtest_config)
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

                cached_result = load_backtest_cache(uid, strategy_name)
                if cached_result:
                    missing_report_keys = [key for key in FULL_REPORT_RESULT_KEYS if key not in cached_result]
                    if not missing_report_keys:
                        response_data = {
                            "success": True,
                            "received_data": strategy_config,
                            "backtest_config": backtest_config,
                            "backtest_result": cached_result,
                        }
                        cleaned_response_data = clean_data_for_json(response_data)
                        json_string = json.dumps(cleaned_response_data, cls=DecimalJSONEncoder, ensure_ascii=False)
                        final_response_data = json.loads(json_string)
                        return JsonResponse(final_response_data, status=200)
                    print("缓存结果缺少完整报告字段，改为实时重算：", missing_report_keys)

                # 如果有配置的开始和结束时间，则尝试获取回测结果
                if config.start_date and config.end_date:
                    Start_time = datetime.strptime(str(config.start_date), '%Y-%m-%d').strftime('%Y%m%d')
                    End_time = datetime.strptime(str(config.end_date), '%Y-%m-%d').strftime('%Y%m%d')

                    # 获取回测结果数据（指定时间范围内的）
                    ShareHolding_data, Historical_transaction_data, incomeBase_data, incomeBaseline, stock_performance_data_range, industry_data, stock_basic_data = fetch_backtest_data(
                        sid, uid, Start_time, End_time)

                    # 获取全部回测结果数据（用于计算除"统计期内"外的其他时间段收益）
                    _, _, incomeBase_data_all, incomeBaseline_all, stock_performance_data, industry_data_all, stock_basic_data_all, market_index_data_all = fetch_all_backtest_data(
                        sid, uid)

                    # 调试信息

                    if incomeBase_data and incomeBaseline:
                        # 处理持股数据
                        share_dict = defaultdict(list)
                        for item in ShareHolding_data:
                            share_dict[item['trade_date']].append(item['st_code'])
                        # 计算股票盈亏统计表
                        calculate_stock_profit_loss_data = calculate_stock_profit_loss(Historical_transaction_data)
                        print("计算股票盈亏统计表数据为：", calculate_stock_profit_loss_data)

                        daily_returns = calculate_daily_returns(incomeBase_data, incomeBaseline)
                        print("计算日收益率的数据为：", daily_returns)

                        # 传入全部数据用于计算除"统计期内"外的其他时间段收益
                        period_returns = calculate_period_returns(incomeBase_data, incomeBaseline,
                                                                  incomeBase_data_all, incomeBaseline_all,
                                                                  Start_time, End_time)
                        print("计算期间收益数据为：", period_returns)  # 这里测量的日期和回测的日期相同，而不是搜寻全表的数据

                        # 计算年度回报率
                        annual_returns = calculate_annual_returns(incomeBase_data_all, incomeBaseline_all)
                        print("计算年度回报率数据为：", annual_returns)

                        # 计算个股绩效归因（盈利前十）
                        stock_performance_attribution = calculate_stock_performance_attribution(stock_performance_data)
                        print("计算个股绩效归因数据为：", stock_performance_attribution)

                        # 计算指定时间范围内的个股绩效归因
                        stock_performance_attribution_range = calculate_stock_performance_attribution(
                            stock_performance_data_range)
                        print("计算指定时间范围内个股绩效归因数据为：", stock_performance_attribution_range)

                        # 计算指定时间范围内的个股绩效归因（亏损前十）
                        stock_performance_attribution_loss_range = calculate_stock_performance_attribution_loss(
                            stock_performance_data_range)
                        print("计算指定时间范围内个股绩效归因（亏损前十）数据为：",
                              stock_performance_attribution_loss_range)

                        industry_allocation_timeline = calculate_industry_allocation_timeline(ShareHolding_data,
                                                                                              industry_data)
                        print("计算申万行业配置时序数据为：", industry_allocation_timeline)

                        # 计算持股数量时序
                        holdings_timeline = calculate_holdings_timeline(ShareHolding_data, stock_basic_data)
                        print("计算持股数量时序数据为：", holdings_timeline)

                        # 计算持股行业分析
                        industry_holdings_analysis = calculate_industry_holdings_analysis(ShareHolding_data,
                                                                                          industry_data)
                        print("计算持股行业分析数据为：", industry_holdings_analysis)

                        # 计算期末市值占比
                        end_period_market_value_proportion = calculate_end_period_market_value_proportion(
                            ShareHolding_data, industry_data)
                        print("计算期末市值占比数据为：", end_period_market_value_proportion)

                        # 计算交易类型分析（买入）
                        transaction_type_analysis = calculate_transaction_type_analysis(Historical_transaction_data,
                                                                                        market_index_data_all)
                        print("计算交易类型分析（买入）数据为：", transaction_type_analysis)

                        # 计算交易类型分析（卖出）
                        transaction_type_analysis_sell = calculate_transaction_type_analysis_sell(
                            Historical_transaction_data, market_index_data_all)
                        print("计算交易类型分析（卖出）数据为：", transaction_type_analysis_sell)

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
                        baseline_dict = {item['trade_date']: item for item in incomeBaseline}
                        incomeBase_close = []
                        baseline_assets = []
                        last_ratio = 0.0
                        last_asset = 0.0
                        incomeBase_close = [incomeBaseline[i]['profit_and_loss_ratio'] for i in
                                            range(len(incomeBaseline))]
                        print("收益率和资产数据为：", incomeBase_close)
                        back_return = [incomeBase_data[k]['profit_and_loss_ratio'] for k in range(len(incomeBase_data))]
                        stock_assets = [incomeBase_data[i]['assets'] for i in range(len(incomeBase_data))]
                        baseline_assets = [incomeBaseline[i]['assets'] for i in range(len(incomeBaseline))]
                        incomeBase_close = []
                        baseline_assets = []
                        last_asset = float(stock_assets[0]) if len(stock_assets) > 0 else 0.0
                        for day in trade_date:
                            if day in baseline_dict:
                                last_ratio = float(baseline_dict[day]['profit_and_loss_ratio'])
                                last_asset = float(baseline_dict[day]['assets'])
                            incomeBase_close.append(last_ratio)
                            baseline_assets.append(last_asset)
                        print("鏀剁泭鐜囧拰璧勪骇鏁版嵁涓猴細", incomeBase_close)

                        # 计算指标
                        risk_free_rate = 1.75 / 100
                        trading_days_per_year = 250

                        # 只有在有足够数据时才计算指标
                        if len(stock_assets) > 1 and len(baseline_assets) > 1:
                            stock_max_back = maxback(np.array(stock_assets))
                            stock_sharpe_ratio = sharpe_ratio(np.array(stock_assets), risk_free_rate,
                                                              trading_days_per_year)
                            stock_sortino_ratio = sortino_ratio(np.array(stock_assets), risk_free_rate,
                                                                trading_days_per_year)
                            stock_annualized_return = annualized_return(np.array(stock_assets), trading_days_per_year)
                            transaction_data = pd.DataFrame(Historical_transaction_data)
                            stock_win_rate = win_rate(transaction_data)

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
                                'daily_returns': daily_returns,  # 日收益
                                'period_returns': period_returns,  # 收益率
                                'annual_returns': annual_returns,  # 年收益率
                                'stock_performance_attribution': stock_performance_attribution,  # 个股绩效归因
                                'stock_performance_attribution_range': stock_performance_attribution_range,
                                # 指定时间范围内个股绩效归因
                                'stock_performance_attribution_loss_range': stock_performance_attribution_loss_range,
                                # 指定时间范围内个股绩效归因（亏损前十）
                                'industry_allocation_timeline': industry_allocation_timeline,  # 申万行业配置时序
                                'holdings_timeline': holdings_timeline,  # 持股数量时序
                                'industry_holdings_analysis': industry_holdings_analysis,  # 持股行业分析
                                'end_period_market_value_proportion': end_period_market_value_proportion,  # 期末市值占比
                                'transaction_type_analysis': transaction_type_analysis,  # 交易类型分析（买入）
                                'transaction_type_analysis_sell': transaction_type_analysis_sell,  # 交易类型分析（卖出）
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
                            save_backtest_cache(uid, strategy_name, backtest_result)

            except Exception as e:
                # 如果无法获取回测数据，则返回空的回测结果
                print(f"获取回测数据时出错: {e}")
                pass
            print("回测结果为：", backtest_result)
            response_data = {
                "success": True,
                "received_data": strategy_config,
                "backtest_config": backtest_config,
                "backtest_result": backtest_result if backtest_result else {}
            }
            cleaned_response_data = clean_data_for_json(response_data)
            json_string = json.dumps(cleaned_response_data, cls=DecimalJSONEncoder, ensure_ascii=False)
            final_response_data = json.loads(json_string)
            return JsonResponse(final_response_data, status=200)

        except Exception as e:
            print(f"loadStrategyConfig error: {e}")
            traceback.print_exc()
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

def calculate_period_returns(incomeBase_data, incomeBaseline,
                             incomeBase_data_all, incomeBaseline_all,
                             start_time, end_time):
    """
    计算不同时间段的收益分析

    Args:
        incomeBase_data: 指定时间范围内的策略收益数据列表，包含trade_date和assets字段
        incomeBaseline: 指定时间范围内的基准收益数据列表，包含trade_date和assets字段
        incomeBase_data_all: 全部策略收益数据列表，包含trade_date和assets字段
        incomeBaseline_all: 全部基准收益数据列表，包含trade_date和assets字段
        start_time: 统计开始时间 (YYYYMMDD格式)
        end_time: 统计结束时间 (YYYYMMDD格式)

    Returns:
        list: 包含不同时段收益分析结果的列表
    """
    # 检查数据是否为空
    if not incomeBase_data or not incomeBaseline or not incomeBase_data_all or not incomeBaseline_all:
        return []

    # 将数据转换为 DataFrame
    stock_df = pd.DataFrame(incomeBase_data, columns=['trade_date', 'assets'])
    benchmark_df = pd.DataFrame(incomeBaseline, columns=['trade_date', 'assets'])

    # 将全部数据转换为 DataFrame
    stock_df_all = pd.DataFrame(incomeBase_data_all, columns=['trade_date', 'assets'])
    benchmark_df_all = pd.DataFrame(incomeBaseline_all, columns=['trade_date', 'assets'])

    # 确保数据按日期排序
    stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
    benchmark_df['trade_date'] = pd.to_datetime(benchmark_df['trade_date'])
    stock_df = stock_df.sort_values(by='trade_date')
    benchmark_df = benchmark_df.sort_values(by='trade_date')

    # 确保全部数据按日期排序
    stock_df_all['trade_date'] = pd.to_datetime(stock_df_all['trade_date'])
    benchmark_df_all['trade_date'] = pd.to_datetime(benchmark_df_all['trade_date'])
    stock_df_all = stock_df_all.sort_values(by='trade_date')
    benchmark_df_all = benchmark_df_all.sort_values(by='trade_date')

    # 将end_time和start_time转换为datetime格式
    end_date = pd.to_datetime(end_time, format='%Y%m%d')
    start_date = pd.to_datetime(start_time, format='%Y%m%d')

    # 计算各时间段的起始日期
    one_month_ago = end_date - pd.DateOffset(months=1)
    three_months_ago = end_date - pd.DateOffset(months=3)
    six_months_ago = end_date - pd.DateOffset(months=6)
    one_year_ago = end_date - pd.DateOffset(years=1)

    # 找到成立以来的第一天（使用全部数据）
    inception_date_stock = stock_df_all['trade_date'].min() if len(stock_df_all) > 0 else None
    inception_date_benchmark = benchmark_df_all['trade_date'].min() if len(benchmark_df_all) > 0 else None

    if inception_date_stock is None or inception_date_benchmark is None:
        return []

    inception_date = max(inception_date_stock, inception_date_benchmark)

    def calculate_return(df, start_date_period, end_date_period, date_col='trade_date', value_col='assets'):
        """
        计算指定时间段的收益率
        """
        # 确保起始日期在数据范围内
        if start_date_period < df[date_col].min():
            start_date_period = df[date_col].min()

        # 获取起始和结束日期的数据
        start_data = df[df[date_col] >= start_date_period]
        if len(start_data) == 0:
            return None
        start_value = start_data.iloc[0][value_col]

        end_data = df[df[date_col] <= end_date_period]
        if len(end_data) == 0:
            return None
        end_value = end_data.iloc[-1][value_col]

        # 计算收益率
        if start_value != 0:
            return (end_value - start_value) / start_value
        else:
            return None if start_value == 0 and end_value == 0 else float('inf')

    # 定义所有需要计算的时间段
    periods = {
        '统计期内': (start_date, end_date),
        '近一月': (one_month_ago, end_date),
        '近三月': (three_months_ago, end_date),
        '近六月': (six_months_ago, end_date),
        '近一年': (one_year_ago, end_date),
        '成立以来': (inception_date, end_date)
    }

    result = []

    for period_name, (period_start, period_end) in periods.items():
        # 对于"统计期内"使用限定日期范围的数据，其他时间段使用全部数据
        if period_name == '统计期内':
            strategy_return = calculate_return(stock_df, period_start, period_end)
            benchmark_return = calculate_return(benchmark_df, period_start, period_end)
        else:
            strategy_return = calculate_return(stock_df_all, period_start, period_end)
            benchmark_return = calculate_return(benchmark_df_all, period_start, period_end)

        result.append({
            'period': period_name,
            'strategy_return': round(strategy_return, 5) if strategy_return is not None else None,
            'benchmark_return': round(benchmark_return, 5) if benchmark_return is not None else None
        })

    return result

def calculate_stock_performance_attribution(stock_performance_data):
    """
    计算个股绩效归因（盈利前十）

    Args:
        stock_performance_data: 从数据库获取的个股绩效数据列表

    Returns:
        list: 包含盈利前十股票的绩效归因数据
    """
    try:
        # print(f"开始计算个股绩效归因，输入数据长度: {len(stock_performance_data) if stock_performance_data else 0}")
        # print(f"输入数据示例: {stock_performance_data[:2] if stock_performance_data else 'None'}")

        # 将数据转换为 DataFrame 便于处理
        df = pd.DataFrame(stock_performance_data)
        # print(f"DataFrame 形状: {df.shape}")
        # print(f"DataFrame 列名: {df.columns.tolist() if not df.empty else 'Empty'}")

        if df.empty:
            # print("DataFrame 为空，返回空列表")
            return []

        # 过滤掉无效数据
        df = df.dropna(subset=['st_code', 'number_of_securities', 'current_price', 'profit_and_loss'])
        # print(f"过滤无效数据后 DataFrame 形状: {df.shape}")

        if df.empty:
            # print("过滤后 DataFrame 为空，返回空列表")
            return []

        # 数据类型转换和清理
        # print(f"数据类型检查:")
        # print(f"  st_code: {df['st_code'].dtype}")
        # print(f"  number_of_securities: {df['number_of_securities'].dtype}")
        # print(f"  number_of_securities 示例值: {df['number_of_securities'].iloc[0] if not df.empty else 'N/A'}")
        # print(f"  current_price: {df['current_price'].dtype}")
        # print(f"  current_price 示例值: {df['current_price'].iloc[0] if not df.empty else 'N/A'}")
        # print(f"  profit_and_loss: {df['profit_and_loss'].dtype}")
        # print(f"  profit_and_loss 示例值: {df['profit_and_loss'].iloc[0] if not df.empty else 'N/A'}")

        # 转换数据类型
        try:
            # 处理可能的字符串类型数据
            def safe_convert_numeric(series):
                """安全转换数值类型，处理各种可能的格式"""
                if series.dtype == 'object':
                    # 如果是字符串类型，先清理数据
                    cleaned = series.astype(str).str.replace(',', '').str.replace(' ', '')
                    # 尝试转换为数值
                    return pd.to_numeric(cleaned, errors='coerce')
                else:
                    return pd.to_numeric(series, errors='coerce')

            df['number_of_securities'] = safe_convert_numeric(df['number_of_securities'])
            df['current_price'] = safe_convert_numeric(df['current_price'])
            df['profit_and_loss'] = safe_convert_numeric(df['profit_and_loss'])

            # print(f"转换后的数据类型:")
            # print(f"  number_of_securities: {df['number_of_securities'].dtype}")
            # print(f"  current_price: {df['current_price'].dtype}")
            # print(f"  profit_and_loss: {df['profit_and_loss'].dtype}")

            # 再次过滤掉转换后为NaN的数据
            df = df.dropna(subset=['number_of_securities', 'current_price', 'profit_and_loss'])
            # print(f"数据类型转换后 DataFrame 形状: {df.shape}")

            if df.empty:
                # print("数据类型转换后 DataFrame 为空，返回空列表")
                return []

        except Exception as e:
            # print(f"数据类型转换失败: {e}")
            # import traceback
            # traceback.print_exc()
            return []

        # 计算每只股票的持仓权重
        df['market_value'] = df['number_of_securities'] * df['current_price']
        total_market_value = df['market_value'].sum()
        # print(f"总市值: {total_market_value}")

        if total_market_value == 0:
            # print("总市值为0，返回空列表")
            return []

        df['weight_percentage'] = (df['market_value'] / total_market_value) * 100

        # 计算每只股票的收益额（万元）
        df['profit_amount_wan'] = df['profit_and_loss'] / 10000

        # 数据验证
        # print(f"数据验证:")
        # print(f"  持股数量范围: {df['number_of_securities'].min()} - {df['number_of_securities'].max()}")
        # print(f"  当前价格范围: {df['current_price'].min()} - {df['current_price'].max()}")
        # print(f"  盈亏金额范围: {df['profit_and_loss'].min()} - {df['profit_and_loss'].max()}")
        # print(f"  盈利股票数量: {len(df[df['profit_and_loss'] > 0])}")
        # print(f"  亏损股票数量: {len(df[df['profit_and_loss'] < 0])}")

        # 数据质量检查
        # print(f"数据质量检查:")
        # print(f"  持股数量为0的股票: {len(df[df['number_of_securities'] == 0])}")
        # print(f"  当前价格为0的股票: {len(df[df['current_price'] == 0])}")
        # print(f"  盈亏金额为0的股票: {len(df[df['profit_and_loss'] == 0])}")

        # 过滤掉无效数据
        df = df[df['number_of_securities'] > 0]
        df = df[df['current_price'] > 0]
        # print(f"过滤无效数据后 DataFrame 形状: {df.shape}")

        if df.empty:
            # print("过滤无效数据后 DataFrame 为空，返回空列表")
            return []

        # 按盈亏金额排序，获取盈利前十的股票
        profitable_stocks = df[df['profit_and_loss'] > 0].nlargest(10, 'profit_and_loss')
        # print(f"盈利前十股票数量: {len(profitable_stocks)}")

        if profitable_stocks.empty:
            # print("没有盈利股票，返回空列表")
            return []

        # 获取股票名称
        stock_codes = profitable_stocks['st_code'].tolist()
        stock_names = {}

        try:
            # 从股票基本信息表获取股票名称
            stock_info = Stock_Basic_Info.objects.filter(st_code__in=stock_codes)
            # print(f"从数据库获取到 {len(stock_info)} 只股票的名称信息")
            for stock in stock_info:
                stock_names[stock.st_code] = stock.name
        except Exception as e:
            # print(f"获取股票名称失败: {e}")
            # 如果获取失败，使用股票代码作为名称
            for code in stock_codes:
                stock_names[code] = code

        # 构建返回结果
        result = []
        for _, row in profitable_stocks.iterrows():
            stock_code = row['st_code']
            stock_name = stock_names.get(stock_code, stock_code)

            result.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'weight_percentage': round(row['weight_percentage'], 2),
                'profit_amount_wan': round(row['profit_amount_wan'], 2)
            })

        # 按盈利金额降序排列
        result.sort(key=lambda x: x['profit_amount_wan'], reverse=True)

        # print(f"最终返回结果: {result}")
        return result

    except Exception as e:
        # print(f"计算个股绩效归因失败: {e}")
        # import traceback
        # traceback.print_exc()
        return []

def calculate_annual_returns(incomeBase_data, incomeBaseline):
    """
    计算年度回报率

    Args:
        incomeBase_data: 策略收益数据列表，包含trade_date和assets字段
        incomeBaseline: 基准收益数据列表，包含trade_date和assets字段

    Returns:
        list: 包含年度回报率数据的列表
    """
    # 将数据转换为 DataFrame
    stock_df = pd.DataFrame(incomeBase_data, columns=['trade_date', 'assets'])
    benchmark_df = pd.DataFrame(incomeBaseline, columns=['trade_date', 'assets'])

    # 确保数据按日期排序
    stock_df['trade_date'] = pd.to_datetime(stock_df['trade_date'])
    benchmark_df['trade_date'] = pd.to_datetime(benchmark_df['trade_date'])
    stock_df = stock_df.sort_values(by='trade_date')
    benchmark_df = benchmark_df.sort_values(by='trade_date')

    # 获取最新日期
    latest_date = stock_df['trade_date'].max()

    # 计算一年前的日期
    one_year_ago = latest_date - pd.DateOffset(years=1)

    # 确定起始日期（一年前或数据最早的日期）
    start_date = max(one_year_ago, stock_df['trade_date'].min())

    # 获取起始日期和结束日期对应的资产值（策略）
    start_stock_data = stock_df[stock_df['trade_date'] >= start_date]
    end_stock_data = stock_df[stock_df['trade_date'] <= latest_date]

    if len(start_stock_data) == 0 or len(end_stock_data) == 0:
        stock_annual_return = None
    else:
        start_stock_value = start_stock_data.iloc[0]['assets']
        end_stock_value = end_stock_data.iloc[-1]['assets']
        # 计算策略年度回报率
        if start_stock_value != 0:
            stock_annual_return = (end_stock_value - start_stock_value) / start_stock_value
        else:
            stock_annual_return = None if start_stock_value == 0 and end_stock_value == 0 else float('inf')

    # 获取起始日期和结束日期对应的资产值（基准）
    start_benchmark_data = benchmark_df[benchmark_df['trade_date'] >= start_date]
    end_benchmark_data = benchmark_df[benchmark_df['trade_date'] <= latest_date]

    if len(start_benchmark_data) == 0 or len(end_benchmark_data) == 0:
        benchmark_annual_return = None
    else:
        start_benchmark_value = start_benchmark_data.iloc[0]['assets']
        end_benchmark_value = end_benchmark_data.iloc[-1]['assets']
        # 计算基准年度回报率
        if start_benchmark_value != 0:
            benchmark_annual_return = (end_benchmark_value - start_benchmark_value) / start_benchmark_value
        else:
            benchmark_annual_return = None if start_benchmark_value == 0 and end_benchmark_value == 0 else float('inf')

    # 构建结果列表，保留5位小数
    result = [
        {
            'period': '年度回报率',
            'strategy_return': round(stock_annual_return, 5) if stock_annual_return is not None else None,
            'benchmark_return': round(benchmark_annual_return, 5) if benchmark_annual_return is not None else None
        }
    ]

    return result


def calculate_stock_performance_attribution_loss(stock_performance_data):
    """
    计算个股绩效归因（亏损前十）

    Args:
        stock_performance_data: 从数据库获取的个股绩效数据列表

    Returns:
        list: 包含亏损前十股票的绩效归因数据
    """
    try:
        # 将数据转换为 DataFrame 便于处理
        df = pd.DataFrame(stock_performance_data)

        if df.empty:
            return []

        # 过滤掉无效数据
        df = df.dropna(subset=['st_code', 'number_of_securities', 'current_price', 'profit_and_loss'])

        if df.empty:
            return []

        # 数据类型转换和清理
        try:
            # 处理可能的字符串类型数据
            def safe_convert_numeric(series):
                """安全转换数值类型，处理各种可能的格式"""
                if series.dtype == 'object':
                    # 如果是字符串类型，先清理数据
                    cleaned = series.astype(str).str.replace(',', '').str.replace(' ', '')
                    # 尝试转换为数值
                    return pd.to_numeric(cleaned, errors='coerce')
                else:
                    return pd.to_numeric(series, errors='coerce')

            df['number_of_securities'] = safe_convert_numeric(df['number_of_securities'])
            df['current_price'] = safe_convert_numeric(df['current_price'])
            df['profit_and_loss'] = safe_convert_numeric(df['profit_and_loss'])

            # 再次过滤掉转换后为NaN的数据
            df = df.dropna(subset=['number_of_securities', 'current_price', 'profit_and_loss'])

            if df.empty:
                return []

        except Exception as e:
            return []

        # 计算每只股票的持仓权重
        df['market_value'] = df['number_of_securities'] * df['current_price']
        total_market_value = df['market_value'].sum()

        if total_market_value == 0:
            return []

        df['weight_percentage'] = (df['market_value'] / total_market_value) * 100

        # 计算每只股票的亏损额（万元）
        df['loss_amount_wan'] = df['profit_and_loss'] / 10000

        # 过滤掉无效数据
        df = df[df['number_of_securities'] > 0]
        df = df[df['current_price'] > 0]

        if df.empty:
            return []

        # 按亏损金额排序，获取亏损前十的股票（亏损金额为负数，所以用nsmallest）
        loss_stocks = df[df['profit_and_loss'] < 0].nsmallest(10, 'profit_and_loss')

        if loss_stocks.empty:
            return []

        # 获取股票名称
        stock_codes = loss_stocks['st_code'].tolist()
        stock_names = {}

        try:
            # 从股票基本信息表获取股票名称
            stock_info = Stock_Basic_Info.objects.filter(st_code__in=stock_codes)
            for stock in stock_info:
                stock_names[stock.st_code] = stock.name
        except Exception as e:
            # 如果获取失败，使用股票代码作为名称
            for code in stock_codes:
                stock_names[code] = code

        # 构建返回结果
        result = []
        for _, row in loss_stocks.iterrows():
            stock_code = row['st_code']
            stock_name = stock_names.get(stock_code, stock_code)

            result.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'weight_percentage': round(row['weight_percentage'], 2),
                'loss_amount_wan': round(abs(row['loss_amount_wan']), 2)  # 取绝对值显示
            })

        # 按亏损金额降序排列（亏损金额越大，排名越靠前）
        result.sort(key=lambda x: x['loss_amount_wan'], reverse=True)

        return result

    except Exception as e:
        return []

def calculate_industry_allocation_timeline(shareholding_data, industry_data):
    """
    计算申万行业配置时序

    Args:
        shareholding_data: 持股信息数据列表
        industry_data: 行业信息数据列表

    Returns:
        dict: 包含行业配置时序数据
    """
    # print("=== 开始计算申万行业配置时序 ===")
    # print(f"输入参数 - shareholding_data 类型: {type(shareholding_data)}, 长度: {len(shareholding_data) if shareholding_data else 0}")
    # print(f"输入参数 - industry_data 类型: {type(industry_data)}, 长度: {len(industry_data) if industry_data else 0}")

    # if shareholding_data:
    #     print(f"持股数据示例 (前3条): {shareholding_data[:3]}")
    # if industry_data:
    #     print(f"行业数据示例 (前3条): {industry_data[:3]}")

    try:
        # 将数据转换为 DataFrame
        df_holding = pd.DataFrame(shareholding_data)
        df_industry = pd.DataFrame(industry_data)

        # print(f"持股DataFrame形状: {df_holding.shape}")
        # print(f"行业DataFrame形状: {df_industry.shape}")

        # if not df_holding.empty:
        #     print(f"持股DataFrame列名: {list(df_holding.columns)}")
        #     print(f"持股DataFrame前3行:\n{df_holding.head(3)}")

        # if not df_industry.empty:
        #     print(f"行业DataFrame列名: {list(df_industry.columns)}")
        #     print(f"行业DataFrame前3行:\n{df_industry.head(3)}")

        if df_holding.empty or df_industry.empty:
            # print("持股数据或行业数据为空，返回空字典")
            return {}

        # 过滤掉无效数据
        # print("开始过滤无效数据...")
        df_holding_before = len(df_holding)
        df_holding = df_holding.dropna(subset=['trade_date', 'st_code', 'latest_value'])
        df_holding_after = len(df_holding)
        # print(f"持股数据过滤后: {df_holding_before} -> {df_holding_after}")

        df_industry_before = len(df_industry)
        df_industry = df_industry.dropna(subset=['st_code', 'Industry_name'])
        df_industry_after = len(df_industry)
        # print(f"行业数据过滤后: {df_industry_before} -> {df_industry_after}")

        if df_holding.empty or df_industry.empty:
            # print("过滤后数据为空，返回空字典")
            return {}

        # 数据类型转换
        try:
            # print("开始数据类型转换...")
            def safe_convert_numeric(series):
                if series.dtype == 'object':
                    cleaned = series.astype(str).str.replace(',', '').str.replace(' ', '')
                    return pd.to_numeric(cleaned, errors='coerce')
                else:
                    return pd.to_numeric(series, errors='coerce')

            df_holding['latest_value'] = safe_convert_numeric(df_holding['latest_value'])
            df_holding = df_holding.dropna(subset=['latest_value'])
            # print(f"数据类型转换后持股数据长度: {len(df_holding)}")

        except Exception as e:
            # print(f"数据类型转换失败: {e}")
            return {}

        # 合并持股数据和行业数据
        # print("开始合并持股数据和行业数据...")
        df_merged = pd.merge(df_holding, df_industry, on='st_code', how='inner')
        # print(f"合并后数据形状: {df_merged.shape}")

        # if not df_merged.empty:
        #     print(f"合并后数据列名: {list(df_merged.columns)}")
        #     print(f"合并后数据前3行:\n{df_merged.head(3)}")

        if df_merged.empty:
            # print("合并后数据为空，返回空字典")
            return {}

        # 按日期和行业分组，计算行业市值
        # print("开始按日期和行业分组计算...")
        industry_daily = df_merged.groupby(['trade_date', 'Industry_name'])['latest_value'].sum().reset_index()
        # print(f"分组后数据形状: {industry_daily.shape}")
        # print(f"分组后数据前5行:\n{industry_daily.head()}")

        # 计算每日全市场总市值
        daily_total = industry_daily.groupby('trade_date')['latest_value'].sum().reset_index()
        daily_total.columns = ['trade_date', 'total_market_value']
        # print(f"每日总市值数据形状: {daily_total.shape}")
        # print(f"每日总市值数据前5行:\n{daily_total.head()}")

        # 合并行业市值和全市场市值
        result_df = pd.merge(industry_daily, daily_total, on='trade_date', how='left')
        # print(f"最终结果数据形状: {result_df.shape}")
        # print(f"最终结果数据前5行:\n{result_df.head()}")

        # 计算行业占比
        result_df['industry_percentage'] = (result_df['latest_value'] / result_df['total_market_value']) * 100
        # print(f"计算行业占比后数据前5行:\n{result_df.head()}")

        # 按日期排序
        result_df = result_df.sort_values('trade_date')
        # print(f"排序后数据前5行:\n{result_df.head()}")

        # 转换为前端需要的格式
        dates = result_df['trade_date'].unique().tolist()
        industries = result_df['Industry_name'].unique().tolist()
        # print(f"唯一日期数量: {len(dates)}")
        # print(f"唯一行业数量: {len(industries)}")
        # print(f"日期列表: {dates[:10]}...")  # 只显示前10个
        # print(f"行业列表: {industries}")

        # 构建堆叠面积图数据
        series_data = []
        for industry in industries:
            industry_data = result_df[result_df['Industry_name'] == industry]
            data = []
            for date in dates:
                date_data = industry_data[industry_data['trade_date'] == date]
                if not date_data.empty:
                    data.append(round(date_data.iloc[0]['industry_percentage'], 2))
                else:
                    data.append(0)

            series_data.append({
                'name': industry,
                'type': 'line',
                'stack': 'Total',
                'areaStyle': {},
                'data': data
            })
            # print(f"行业 '{industry}' 数据点数量: {len(data)}")

        final_result = {
            'dates': dates,
            'series': series_data
        }

        # print(f"=== 申万行业配置时序计算完成 ===")
        # print(f"返回数据 - dates长度: {len(dates)}, series长度: {len(series_data)}")
        # print(f"返回数据示例: {final_result}")

        return final_result

    except Exception as e:
        # print(f"=== 申万行业配置时序计算失败 ===")
        # print(f"错误信息: {e}")
        # import traceback
        # traceback.print_exc()
        return {}


def calculate_holdings_timeline(shareholding_data, stock_basic_data, months_to_exclude=3):
    """
    计算持股数量时序（排除新股）

    Args:
        shareholding_data: 持股信息数据列表
        stock_basic_data: 股票基本信息数据列表
        months_to_exclude: 排除上市不足几个月的股票，默认3个月

    Returns:
        dict: 包含持股数量时序数据
    """
    try:
        # 将数据转换为 DataFrame
        df_holding = pd.DataFrame(shareholding_data)
        df_stock_basic = pd.DataFrame(stock_basic_data)

        if df_holding.empty:
            return {}

        # 过滤掉无效数据
        df_holding = df_holding.dropna(subset=['trade_date', 'st_code'])
        df_stock_basic = df_stock_basic.dropna(subset=['st_code', 'list_date'])

        if df_holding.empty or df_stock_basic.empty:
            return {}

        # 合并持股数据和股票基本信息
        df_merged = pd.merge(df_holding, df_stock_basic, on='st_code', how='left')

        if df_merged.empty:
            return {}

        # 获取所有交易日期
        all_dates = sorted(df_merged['trade_date'].unique())

        # 计算每日持股数量（包含新股）
        total_holdings = []
        filtered_holdings = []

        for date in all_dates:
            # 当日所有持股
            daily_data = df_merged[df_merged['trade_date'] == date]
            total_count = daily_data['st_code'].nunique()
            total_holdings.append(total_count)

            # 过滤新股后的持股
            filtered_data = daily_data.copy()

            # 计算上市日期与当前日期的差值
            for idx, row in filtered_data.iterrows():
                try:
                    list_date_str = str(row['list_date'])
                    if len(list_date_str) == 8:  # YYYYMMDD 格式
                        list_date = datetime.strptime(list_date_str, '%Y%m%d')
                        current_date = datetime.strptime(str(date), '%Y%m%d')

                        # 计算月份差
                        months_diff = (current_date.year - list_date.year) * 12 + (current_date.month - list_date.month)

                        # 如果上市不足指定月数，则标记为新股
                        if months_diff < months_to_exclude:
                            filtered_data.loc[idx, 'is_new_stock'] = True
                        else:
                            filtered_data.loc[idx, 'is_new_stock'] = False
                    else:
                        filtered_data.loc[idx, 'is_new_stock'] = False
                except:
                    filtered_data.loc[idx, 'is_new_stock'] = False

            # 排除新股
            filtered_data = filtered_data[filtered_data['is_new_stock'] == False]
            filtered_count = filtered_data['st_code'].nunique()
            filtered_holdings.append(filtered_count)

        # 转换为前端需要的格式
        result = {
            'dates': all_dates,
            'total_holdings': total_holdings,
            'filtered_holdings': filtered_holdings
        }

        return result

    except Exception as e:
        return {}


def calculate_industry_holdings_analysis(shareholding_data, industry_data):
    """
    计算持股行业分析（前十大行业市值占比）

    Args:
        shareholding_data: 持股信息数据列表
        industry_data: 行业数据列表

    Returns:
        dict: 包含前十大行业市值占比数据
    """
    try:
        # 将数据转换为 DataFrame
        df_holding = pd.DataFrame(shareholding_data)
        df_industry = pd.DataFrame(industry_data)

        if df_holding.empty or df_industry.empty:
            print("DataFrame 为空，返回空结果")
            return {}

        # 更宽松的过滤条件
        df_holding = df_holding.dropna(subset=['trade_date', 'st_code'])
        df_industry = df_industry.dropna(subset=['st_code', 'Industry_name'])

        # print(f"过滤后 df_holding 行数: {len(df_holding)}")
        # print(f"filtered_holdings 行数: {len(df_industry)}")

        if df_holding.empty or df_industry.empty:
            # print("过滤后 DataFrame 为空，返回空结果")
            return {}

        # 合并持股数据和行业数据
        # print("开始合并数据...")
        df_merged = pd.merge(df_holding, df_industry, on='st_code', how='left')
        if df_merged.empty:
            return {}

        # 处理 latest_value 为空的情况
        df_merged['latest_value'] = df_merged['latest_value'].fillna(0)

        industry_daily = df_merged.groupby(['trade_date', 'Industry_name'])['latest_value'].sum().reset_index()
        # print(f"分组后数据形状: {industry_daily.shape}")

        # 计算每日全市场总市值
        daily_total = industry_daily.groupby('trade_date')['latest_value'].sum().reset_index()
        daily_total.columns = ['trade_date', 'total_market_value']
        # print(f"每日总市值数据形状: {daily_total.shape}")

        # 合并行业市值和全市场市值
        result_df = pd.merge(industry_daily, daily_total, on='trade_date', how='left')
        # print(f"合并后数据形状: {result_df.shape}")

        # 计算每日行业占比
        # 确保数据类型转换正确
        result_df['latest_value'] = pd.to_numeric(result_df['latest_value'], errors='coerce')
        result_df['total_market_value'] = pd.to_numeric(result_df['total_market_value'], errors='coerce')

        result_df['industry_percentage'] = (result_df['latest_value'] / result_df['total_market_value']) * 100

        industry_avg = result_df.groupby('Industry_name')['industry_percentage'].mean().reset_index()
        industry_avg.columns = ['industry_name', 'avg_percentage']

        # 确保 avg_percentage 是数值类型
        industry_avg['avg_percentage'] = pd.to_numeric(industry_avg['avg_percentage'], errors='coerce')

        # 过滤掉空值
        industry_avg_clean = industry_avg.dropna(subset=['avg_percentage'])
        # print(f"过滤空值后数据形状: {industry_avg_clean.shape}")

        if industry_avg_clean.empty:
            # print("过滤空值后数据为空，返回空结果")
            return {}

        top_10_industries = industry_avg_clean.nlargest(10, 'avg_percentage')

        # 转换为前端需要的格式
        # print("开始转换数据格式...")
        industries = top_10_industries['industry_name'].tolist()
        percentages = top_10_industries['avg_percentage'].round(2).tolist()
        # print(f"转换后的行业列表: {industries}")
        # print(f"转换后的占比列表: {percentages}")

        result = {
            'industries': industries,
            'percentages': percentages
        }

        # print(f"=== 持股行业分析计算完成 ===")
        # print(f"前十大行业: {industries}")
        # print(f"对应占比: {percentages}")
        # print(f"返回结果: {result}")

        return result

    except Exception as e:
        return {}


def calculate_end_period_market_value_proportion(shareholding_data, industry_data):
    """
    计算期末市值占比（饼图）

    Args:
        shareholding_data: 持股信息数据列表
        industry_data: 行业数据列表

    Returns:
        dict: 包含期末市值占比数据
    """
    try:
        # 将数据转换为 DataFrame
        df_holding = pd.DataFrame(shareholding_data)
        df_industry = pd.DataFrame(industry_data)

        if df_holding.empty or df_industry.empty:
            return {}

        # 过滤掉无效数据
        df_holding = df_holding.dropna(subset=['trade_date', 'st_code', 'latest_value'])
        df_industry = df_industry.dropna(subset=['st_code', 'Industry_name'])

        if df_holding.empty or df_industry.empty:
            return {}

        # 1. 筛选期末数据：取最近一个交易日(期末)的持仓数据
        latest_date = df_holding['trade_date'].max()
        end_period_data = df_holding[df_holding['trade_date'] == latest_date]

        if end_period_data.empty:
            return {}

        # 2. 合并持股数据和行业数据
        df_merged = pd.merge(end_period_data, df_industry, on='st_code', how='left')

        if df_merged.empty:
            return {}

        # 3. 行业市值汇总：按行业分类汇总持仓市值
        industry_summary = df_merged.groupby('Industry_name')['latest_value'].sum().reset_index()
        industry_summary.columns = ['industry_name', 'market_value']

        # 4. 计算全市场总市值：所有行业的行业市值汇总
        total_market_value = industry_summary['market_value'].sum()

        # 5. 计算行业占比：行业市值/全市场市值× 100%
        # 将 Decimal 转换为 float 类型
        industry_summary['market_value'] = pd.to_numeric(industry_summary['market_value'], errors='coerce')
        total_market_value = float(total_market_value)

        industry_summary['percentage'] = (industry_summary['market_value'] / total_market_value) * 100

        # 6. 行业分类处理：将占比小的行业合并为"其他"类别，保留主要行业单独显示
        # 设定阈值：占比小于2%的行业合并为"其他"
        threshold = 2.0
        major_industries = industry_summary[industry_summary['percentage'] >= threshold].copy()
        minor_industries = industry_summary[industry_summary['percentage'] < threshold]

        # 如果有小行业，合并为"其他"
        if not minor_industries.empty:
            other_percentage = minor_industries['percentage'].sum()
            other_market_value = minor_industries['market_value'].sum()

            # 添加到主要行业列表
            major_industries = pd.concat([major_industries, pd.DataFrame({
                'industry_name': ['其他'],
                'market_value': [other_market_value],
                'percentage': [other_percentage]
            })], ignore_index=True)

        # 按占比排序
        major_industries = major_industries.sort_values('percentage', ascending=False)

        # 转换为前端需要的格式
        industries = major_industries['industry_name'].tolist()
        percentages = major_industries['percentage'].round(2).tolist()
        market_values = major_industries['market_value'].round(2).tolist()

        result = {
            'industries': industries,
            'percentages': percentages,
            'market_values': market_values,
            'end_date': latest_date
        }

        return result

    except Exception as e:
        return {}


def calculate_transaction_type_analysis(transaction_data, market_index_data):
    """
    计算交易类型分析（买入）

    Args:
        transaction_data: 历史成交信息数据列表
        market_index_data: 大盘指数数据列表

    Returns:
        dict: 包含交易类型分析数据
    """
    try:
        print("=== 交易类型分析（买入）调试信息 ===")
        print(f"传入的 transaction_data 长度: {len(transaction_data)}")
        print(f"传入的 market_index_data 长度: {len(market_index_data)}")

        if transaction_data:
            print(f"transaction_data 前3条示例: {transaction_data[:3]}")
        if market_index_data:
            print(f"market_index_data 前3条示例: {market_index_data[:3]}")

        # 将数据转换为 DataFrame
        df_transaction = pd.DataFrame(transaction_data)
        df_market = pd.DataFrame(market_index_data)

        print(f"df_transaction 形状: {df_transaction.shape}")
        print(f"df_market 形状: {df_market.shape}")

        if df_transaction.empty or df_market.empty:
            print("DataFrame 为空，返回空字典")
            return {}

        # 过滤掉无效数据
        df_transaction = df_transaction.dropna(subset=['trade_date', 'st_code', 'trade_type'])
        df_market = df_market.dropna(subset=['trade_date', 'close'])

        print(f"过滤后 df_transaction 形状: {df_transaction.shape}")
        print(f"过滤后 df_market 形状: {df_market.shape}")

        if df_transaction.empty or df_market.empty:
            print("过滤后 DataFrame 为空，返回空字典")
            return {}

        # 只保留买入交易
        df_buy = df_transaction[df_transaction['trade_type'] == '买入'].copy()
        print(f"买入交易数量: {len(df_buy)}")

        if df_buy.empty:
            print("没有买入交易，返回空字典")
            return {}

        # 数据类型转换
        df_market['close'] = pd.to_numeric(df_market['close'], errors='coerce')
        df_market = df_market.dropna(subset=['close'])

        print(f"转换后 df_market 形状: {df_market.shape}")

        if df_market.empty:
            print("转换后 market DataFrame 为空，返回空字典")
            return {}

        # 统一日期格式 - 将市场数据的日期转换为 YYYYMMDD 格式
        def convert_date_format(date_str):
            """将各种日期格式转换为 YYYYMMDD 格式"""
            try:
                date_str = str(date_str).strip()

                # 如果已经是 YYYYMMDD 格式
                if len(date_str) == 8 and date_str.isdigit():
                    return date_str

                # 如果是 YYYY-MM-DD 格式
                if '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

                # 如果是 YYYY/MM/DD 格式
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

                # 如果是 datetime 对象
                if hasattr(date_str, 'strftime'):
                    return date_str.strftime('%Y%m%d')

                print(f"无法识别的日期格式: {date_str} (类型: {type(date_str)})")
                return str(date_str)
            except Exception as e:
                print(f"日期转换错误: {date_str}, 错误: {e}")
                return str(date_str)

        # 转换市场数据日期格式
        df_market['trade_date'] = df_market['trade_date'].apply(convert_date_format)
        df_buy['trade_date'] = df_buy['trade_date'].astype(str)

        print(f"日期转换后 df_market 前5条: {df_market['trade_date'].head().tolist()}")
        print(f"日期转换后 df_buy 前5条: {df_buy['trade_date'].head().tolist()}")

        # 检查日期范围
        market_dates = set(df_market['trade_date'].tolist())
        trade_dates = set(df_buy['trade_date'].tolist())
        common_dates = market_dates.intersection(trade_dates)

        print(f"市场数据日期范围: {min(market_dates)} 到 {max(market_dates)}")
        print(f"交易数据日期范围: {min(trade_dates)} 到 {max(trade_dates)}")
        print(f"共同日期数量: {len(common_dates)}")

        if len(common_dates) == 0:
            print("警告: 没有找到匹配的日期，尝试使用最近的日期进行匹配")
            # 尝试找到最近的日期进行匹配
            df_buy['trade_date_matched'] = df_buy['trade_date'].apply(
                lambda x: find_nearest_date(x, market_dates)
            )
            print(f"日期匹配后 df_buy 前5条: {df_buy[['trade_date', 'trade_date_matched']].head().to_dict('records')}")
            # 使用匹配后的日期
            df_buy['trade_date'] = df_buy['trade_date_matched']

        # 按日期排序
        df_market = df_market.sort_values('trade_date')

        # 计算N日均价 (N=5,10,20,30)
        periods = [5, 10, 20, 30]
        result = {}

        for period in periods:
            print(f"\n--- 计算 {period}日 移动平均 ---")

            # 计算移动平均
            df_market[f'ma_{period}'] = df_market['close'].rolling(window=period).mean()

            # 计算前一天的移动平均
            df_market[f'ma_{period}_prev'] = df_market[f'ma_{period}'].shift(1)

            # 判断信号日：如果N日均价大于前一天的N日均价，则是信号日
            df_market[f'signal_{period}'] = df_market[f'ma_{period}'] > df_market[f'ma_{period}_prev']

            print(f"{period}日移动平均非空数量: {df_market[f'ma_{period}'].notna().sum()}")
            print(f"{period}日信号日数量: {df_market[f'signal_{period}'].sum()}")

            # 创建日期到信号日的映射
            signal_map = dict(zip(df_market['trade_date'], df_market[f'signal_{period}']))
            print(f"信号映射字典大小: {len(signal_map)}")

            # 统计买入交易类型
            trend_buy_count = 0  # 趋势买入次数
            reversal_buy_count = 0  # 反转买入次数
            unmatched_dates = []

            for _, row in df_buy.iterrows():
                trade_date = row['trade_date']
                if trade_date in signal_map:
                    if signal_map[trade_date]:  # 信号日
                        trend_buy_count += 1
                    else:  # 非信号日
                        reversal_buy_count += 1
                else:
                    unmatched_dates.append(trade_date)

            if unmatched_dates:
                print(f"警告: 以下交易日期在信号映射中未找到: {unmatched_dates[:10]}...")  # 只显示前10个

            total_buy_count = trend_buy_count + reversal_buy_count
            print(f"{period}日 - 趋势买入: {trend_buy_count}, 反转买入: {reversal_buy_count}, 总计: {total_buy_count}")

            if total_buy_count > 0:
                trend_percentage = (trend_buy_count / total_buy_count) * 100
                reversal_percentage = 100 - trend_percentage
            else:
                trend_percentage = 0
                reversal_percentage = 0

            result[f'{period}日'] = {
                'trend_buy_count': trend_buy_count,
                'reversal_buy_count': reversal_buy_count,
                'total_buy_count': total_buy_count,
                'trend_percentage': round(trend_percentage, 2),
                'reversal_percentage': round(reversal_percentage, 2)
            }

        print(f"\n最终结果: {result}")
        return result

    except Exception as e:
        print(f"计算交易类型分析（买入）时出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def calculate_transaction_type_analysis_sell(transaction_data, market_index_data):
    """
    计算交易类型分析（卖出）

    Args:
        transaction_data: 历史成交信息数据列表
        market_index_data: 大盘指数数据列表

    Returns:
        dict: 包含卖出交易类型分析数据
    """
    try:
        print("=== 交易类型分析（卖出）调试信息 ===")
        print(f"传入的 transaction_data 长度: {len(transaction_data)}")
        print(f"传入的 market_index_data 长度: {len(market_index_data)}")

        if transaction_data:
            print(f"transaction_data 前3条示例: {transaction_data[:3]}")
        if market_index_data:
            print(f"market_index_data 前3条示例: {market_index_data[:3]}")

        # 将数据转换为 DataFrame
        df_transaction = pd.DataFrame(transaction_data)
        df_market = pd.DataFrame(market_index_data)

        print(f"df_transaction 形状: {df_transaction.shape}")
        print(f"df_market 形状: {df_market.shape}")

        if df_transaction.empty or df_market.empty:
            print("DataFrame 为空，返回空字典")
            return {}

        # 过滤掉无效数据
        df_transaction = df_transaction.dropna(subset=['trade_date', 'st_code', 'trade_type'])
        df_market = df_market.dropna(subset=['trade_date', 'close'])

        print(f"过滤后 df_transaction 形状: {df_transaction.shape}")
        print(f"过滤后 df_market 形状: {df_market.shape}")

        if df_transaction.empty or df_market.empty:
            print("过滤后 DataFrame 为空，返回空字典")
            return {}

        # 只保留卖出交易
        df_sell = df_transaction[df_transaction['trade_type'] == '卖出'].copy()
        print(f"卖出交易数量: {len(df_sell)}")

        if df_sell.empty:
            print("没有卖出交易，返回空字典")
            return {}

        # 数据类型转换
        df_market['close'] = pd.to_numeric(df_market['close'], errors='coerce')
        df_market = df_market.dropna(subset=['close'])

        print(f"转换后 df_market 形状: {df_market.shape}")

        if df_market.empty:
            print("转换后 market DataFrame 为空，返回空字典")
            return {}

        # 统一日期格式 - 将市场数据的日期转换为 YYYYMMDD 格式
        def convert_date_format(date_str):
            """将各种日期格式转换为 YYYYMMDD 格式"""
            try:
                date_str = str(date_str).strip()

                # 如果已经是 YYYYMMDD 格式
                if len(date_str) == 8 and date_str.isdigit():
                    return date_str

                # 如果是 YYYY-MM-DD 格式
                if '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

                # 如果是 YYYY/MM/DD 格式
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        return f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"

                # 如果是 datetime 对象
                if hasattr(date_str, 'strftime'):
                    return date_str.strftime('%Y%m%d')

                print(f"无法识别的日期格式: {date_str} (类型: {type(date_str)})")
                return str(date_str)
            except Exception as e:
                print(f"日期转换错误: {date_str}, 错误: {e}")
                return str(date_str)

        # 转换市场数据日期格式
        df_market['trade_date'] = df_market['trade_date'].apply(convert_date_format)
        df_sell['trade_date'] = df_sell['trade_date'].astype(str)

        print(f"日期转换后 df_market 前5条: {df_market['trade_date'].head().tolist()}")
        print(f"日期转换后 df_sell 前5条: {df_sell['trade_date'].head().tolist()}")

        # 检查日期范围
        market_dates = set(df_market['trade_date'].tolist())
        trade_dates = set(df_sell['trade_date'].tolist())
        common_dates = market_dates.intersection(trade_dates)

        print(f"市场数据日期范围: {min(market_dates)} 到 {max(market_dates)}")
        print(f"交易数据日期范围: {min(trade_dates)} 到 {max(trade_dates)}")
        print(f"共同日期数量: {len(common_dates)}")

        if len(common_dates) == 0:
            print("警告: 没有找到匹配的日期，尝试使用最近的日期进行匹配")
            # 尝试找到最近的日期进行匹配
            df_sell['trade_date_matched'] = df_sell['trade_date'].apply(
                lambda x: find_nearest_date(x, market_dates)
            )
            print(
                f"日期匹配后 df_sell 前5条: {df_sell[['trade_date', 'trade_date_matched']].head().to_dict('records')}")
            # 使用匹配后的日期
            df_sell['trade_date'] = df_sell['trade_date_matched']

        # 按日期排序
        df_market = df_market.sort_values('trade_date')

        # 计算N日均价 (N=5,10,20,30)
        periods = [5, 10, 20, 30]
        result = {}

        for period in periods:
            print(f"\n--- 计算 {period}日 移动平均 ---")

            # 计算移动平均
            df_market[f'ma_{period}'] = df_market['close'].rolling(window=period).mean()

            # 计算前一天的移动平均
            df_market[f'ma_{period}_prev'] = df_market[f'ma_{period}'].shift(1)

            # 判断信号日：如果N日均价大于前一天的N日均价，则是信号日
            df_market[f'signal_{period}'] = df_market[f'ma_{period}'] > df_market[f'ma_{period}_prev']

            print(f"{period}日移动平均非空数量: {df_market[f'ma_{period}'].notna().sum()}")
            print(f"{period}日信号日数量: {df_market[f'signal_{period}'].sum()}")

            # 创建日期到信号日的映射
            signal_map = dict(zip(df_market['trade_date'], df_market[f'signal_{period}']))
            print(f"信号映射字典大小: {len(signal_map)}")

            # 统计卖出交易类型
            trend_sell_count = 0  # 趋势卖出次数
            reversal_sell_count = 0  # 反转卖出次数
            unmatched_dates = []

            for _, row in df_sell.iterrows():
                trade_date = row['trade_date']
                if trade_date in signal_map:
                    if signal_map[trade_date]:  # 信号日
                        trend_sell_count += 1
                    else:  # 非信号日
                        reversal_sell_count += 1
                else:
                    unmatched_dates.append(trade_date)

            if unmatched_dates:
                print(f"警告: 以下交易日期在信号映射中未找到: {unmatched_dates[:10]}...")  # 只显示前10个

            total_sell_count = trend_sell_count + reversal_sell_count
            print(
                f"{period}日 - 趋势卖出: {trend_sell_count}, 反转卖出: {reversal_sell_count}, 总计: {total_sell_count}")

            if total_sell_count > 0:
                trend_percentage = (trend_sell_count / total_sell_count) * 100
                reversal_percentage = 100 - trend_percentage
            else:
                trend_percentage = 0
                reversal_percentage = 0

            result[f'{period}日'] = {
                'trend_sell_count': trend_sell_count,
                'reversal_sell_count': reversal_sell_count,
                'total_sell_count': total_sell_count,
                'trend_percentage': round(trend_percentage, 2),
                'reversal_percentage': round(reversal_percentage, 2)
            }

        print(f"\n最终结果: {result}")
        return result

    except Exception as e:
        print(f"计算交易类型分析（卖出）时出错: {e}")
        import traceback
        traceback.print_exc()
        return {}


def find_nearest_date(target_date, available_dates):
    """
    找到最接近目标日期的可用日期

    Args:
        target_date: 目标日期 (YYYYMMDD 格式字符串)
        available_dates: 可用日期集合

    Returns:
        str: 最接近的可用日期
    """
    try:
        target_date = str(target_date)
        if target_date in available_dates:
            return target_date

        # 如果目标日期不在可用日期中，找到最接近的
        target_int = int(target_date)
        min_diff = float('inf')
        nearest_date = None

        for date_str in available_dates:
            try:
                date_int = int(str(date_str))
                diff = abs(target_int - date_int)
                if diff < min_diff:
                    min_diff = diff
                    nearest_date = str(date_str)
            except (ValueError, TypeError):
                continue

        if nearest_date:
            print(f"日期 {target_date} 匹配到最近的日期: {nearest_date}")
            return nearest_date
        else:
            print(f"无法为日期 {target_date} 找到匹配的日期")
            return target_date

    except Exception as e:
        print(f"查找最近日期时出错: {e}")
        return str(target_date)


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
                    'optionfactor': serialize_json_field(data.get('conditions')),

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
            print(f"getStockSelector error: {e}")
            traceback.print_exc()
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
                    'bottomfactor': serialize_json_field(data.get('factors')),

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
            print(f"getFactorConfig error: {e}")
            traceback.print_exc()
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
                sql = "DELETE FROM {} WHERE strategy_id=%s AND user_id=%s".format(sc.table_baseline)
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

# class SimulateClose(View):
#     def get(self, request):
#         sid = '1'
#         state = list(SaveState.objects.filter(state_id=sid).values('id', 'state_name', 'save_time'))
#         result = {}
#         result['state'] = state
#
#         return render(request, 'strategy/strategy-simulateclose.html', context=result)
@csrf_exempt
def queryClosePrice(request):
    date = request.GET.get('date')
    stock_code = request.GET.get('stockCode')
    print('date', date)
    print('stock_code', stock_code)
    # 根据股票代码的长度或特定格式添加后缀
    if len(stock_code) == 6:
        if stock_code.startswith(('00', '30')):
            stock_code += '.SZ'  # 深圳证券交易所
        elif stock_code.startswith('60'):
            stock_code += '.SH'  # 上海证券交易所
        else:
            # 处理其他情况或抛出异常
            return JsonResponse({'error': 'Invalid stock code'}, status=400)
    # 将字符串转换为 datetime 对象
    date = datetime.strptime(date, '%Y-%m-%d')
    # 开始日期
    start_date = date - relativedelta(days=30)
    print('start_date', start_date)
    # 将date，start_date转化格式
    start_date = start_date.strftime('%Y%m%d')
    date = date.strftime('%Y%m%d')
    # 查询收盘价语句
    sql = f"SELECT * FROM partition_table WHERE trade_date = '{date}' and st_code = '{stock_code}'"
    engine = create_engine("mysql+mysqldb://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    today_close = pd.read_sql(sql, engine)
    print('today_close', today_close)
    if not today_close.empty:
        close_price = today_close.loc[0, 'close']
        response_data = {'close_price': close_price}
        return JsonResponse(response_data)
    else:
        return JsonResponse({'error': 'No data found'}, status=404)
def ema(data, period=0, column='close', name='ema'):
    data[name] = data[column].ewm(span=period, adjust=False).mean()
    return data
def macd(data, period_long=26, period_short=12, period_signal=9, column='close'):
    if period_long <= period_short or period_short <= period_signal:
        data['macd'] = 0
        data['macd_dea'] = 0
        data['macd_dif'] = 0
        data['macd_dea'] = 0
    else:
        data = ema(data, period_long, column, 'ema' + str(period_long))
        data = ema(data, period_short, column, 'ema' + str(period_short))
        data['macd_dif'] = data['ema' + str(period_short)] - data['ema' + str(period_long)]
        data = ema(data, period_signal, 'macd_dif', 'macd_dea')
        data['macd_macd'] = 2 * (data['macd_dif'] - data['macd_dea'])
    return data
def predictedMacd(date,stock_code,predictedClosePrice):
    date1 = date + relativedelta(days=1)
    # 将date，date1转化格式
    date = date.strftime('%Y%m%d')

    sql = f"SELECT * FROM partition_table WHERE trade_date BETWEEN DATE_SUB('{date}', INTERVAL 30 DAY) AND '{date}' AND st_code = '{stock_code}'"

    engine = create_engine("mysql+mysqldb://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    data = pd.read_sql(sql, engine)
    data['trade_date'] = pd.to_datetime(data['trade_date']).dt.strftime('%Y-%m-%d')

    # 获取前一天的收盘价
    prev_close_price = data.iloc[-1]['close']
    prev_open_price = data.iloc[-1]['open']
    prev_low_price = data.iloc[-1]['low']
    prev_high_price = data.iloc[-1]['high']
    prev_vol_price = data.iloc[-1]['vol']

    print('prev_close_price', prev_close_price)
    print('prev_open_price', prev_open_price)
    # 检查 date1 是否已经在数据中
    if date1 not in data['trade_date'].values:
        # 获取数据集中的所有列名
        columns = data.columns
        # 创建一个新的字典，所有列的值初始化为0
        new_row_dict = {col: 0 for col in columns}
        # 更新新行字典中已知的列值
        new_row_dict['open'] = prev_open_price
        new_row_dict['high'] = prev_high_price
        new_row_dict['low'] = prev_low_price
        new_row_dict['vol'] = prev_vol_price
        new_row_dict['st_code'] = stock_code
        new_row_dict['trade_date'] = date1
        new_row_dict['close'] = predictedClosePrice
        # 计算涨跌幅
        if prev_close_price is not None:
            new_row_dict['pct_chg'] = ((predictedClosePrice - prev_close_price) / prev_close_price) * 100
            print(new_row_dict['pct_chg'])
        else:
            new_row_dict['pct_chg'] = 0  # 或者其他默认值
        # 创建新的DataFrame行
        new_row = pd.DataFrame([new_row_dict])
        # 将新行与原始数据合并
        all_data = pd.concat([new_row, data], ignore_index=True)

    all_data['trade_date'] = pd.to_datetime(all_data['trade_date'])
    # 确保数据按日期排序
    all_data.sort_values(by='trade_date', inplace=True)
    # 假设 df 是你的 DataFrame
    # pd.set_option('display.max_rows', None)  # 显示所有行
    # pd.set_option('display.max_columns', None)  # 显示所有列
    # pd.set_option('display.width', None)  # 自动调整显示宽度
    # pd.set_option('display.max_colwidth', None)  # 显示完整的列内容
    # 计算 MACD
    result_data = macd(all_data, period_long=26, period_short=12, period_signal=9, column='close')
    # print('result_data', result_data)
    # 只保留给定日期的数据
    final_result = result_data[result_data['trade_date'] == date1]
    final_result.rename(columns={'open': 'opens', 'close': 'closes', 'low': 'lows', 'high': 'highs', 'vol': 'vols',
                           'pct_chg': 'pct_chg'},
                  inplace=True)
    print('final_result', final_result)
    return final_result

@csrf_exempt
def getKlineChart(request):
    date = request.GET.get('date')
    print("date",date)
    days = int(request.GET.get('days'))
    print("days", days)
    stock_code = request.GET.get('stockCode')
    print("stockCode", stock_code)
    # 根据股票代码的长度或特定格式添加后缀
    if len(stock_code) == 6:
        if stock_code.startswith(('00', '30')):
            stock_code += '.SZ'  # 深圳证券交易所
        elif stock_code.startswith('60'):
            stock_code += '.SH'  # 上海证券交易所
        else:
            # 处理其他情况或抛出异常
            return JsonResponse({'error': 'Invalid stock code'}, status=400)

    predictedClosePrice = request.GET.get('predictedClosePrice')
    # 将字符串转换为 datetime 对象
    date = datetime.strptime(date, '%Y-%m-%d')
    predictedClosePrice = float(predictedClosePrice)
    print(111111111111111111111111111111111111111111111111)
    pm = predictedMacd(date, stock_code,predictedClosePrice)
    # 开始日期
    start_date = date - relativedelta(days=days)
    date1 = date + relativedelta(days=1)
    print('start_date', start_date)
    # 将date，start_date转化格式
    start_date = start_date.strftime('%Y%m%d')
    date = date.strftime('%Y%m%d')
    date1 = date1.strftime('%Y%m%d')

    # 查询30天数据语句
    k_sql = f"SELECT * FROM partition_table WHERE trade_date BETWEEN '{start_date}' AND '{date}' AND st_code = '{stock_code}'"

    engine = create_engine("mysql+mysqldb://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    k_data = pd.read_sql(k_sql, engine)
    k_data['trade_date'] = pd.to_datetime(k_data['trade_date']).dt.strftime('%Y-%m-%d')
    k_data.rename(columns={'open': 'opens', 'close': 'closes', 'low': 'lows', 'high': 'highs', 'vol': 'vols',
                           'pct_chg': 'pct_chg'},
                  inplace=True)
    # 假设 pm 是从 predictedMacd 返回的 DataFrame
    k_data = pd.concat([k_data, pm], ignore_index=True)
    print('k_data', k_data)
    # 将数据转换为列表
    # dates = k_data['trade_date'].tolist()
    macd = k_data[['macd_dif', 'macd_dea', 'macd_macd']].values.tolist()
    klines = k_data[['trade_date', 'opens', 'highs', 'lows', 'closes', 'vols', 'pct_chg', 'macd_dif', 'macd_dea',
                     'macd_macd']].values.tolist()

    chart_data = {
        'macd': macd,
        'klines': klines,
    }

    print('chart_data', chart_data)
    if not k_data.empty:
        response_data = {'chart_data': chart_data}
        return JsonResponse(response_data)
    else:
        return JsonResponse({'error': 'No data found'}, status=404)

# @csrf_exempt
# def getSimilar(request):
#     code = request.GET.get('code')
#     print("code",code)
#     startDate = request.GET.get('startDate')
#     print("startDate", startDate)
#     endDate = request.GET.get('endDate')
#     print("endDate", endDate)
#
#     # 根据股票代码的长度或特定格式添加后缀
#     if len(code) == 6:
#         if code.startswith(('00', '30')):
#             code += '.SZ'  # 深圳证券交易所
#         elif code.startswith('60'):
#             code += '.SH'  # 上海证券交易所
#         else:
#             # 处理其他情况或抛出异常
#             return JsonResponse({'error': 'Invalid stock code'}, status=400)
#
#     predictedClosePrice = request.GET.get('predictedClosePrice')
#     # 将字符串转换为 datetime 对象
#     startDate = datetime.strptime(startDate, '%Y-%m-%d')
#     endDate = datetime.strptime(endDate, '%Y-%m-%d')
#     # # 将date，start_date转化格式
#     startDate = startDate.strftime('%Y%m%d')
#     endDate = endDate.strftime('%Y%m%d')
#     # date = date.strftime('%Y%m%d')
#     # date1 = date1.strftime('%Y%m%d')
#
#     # 查询30天数据语句
#     k_sql = f"SELECT * FROM partition_table WHERE trade_date BETWEEN '{startDate}' AND '{endDate}' AND st_code = '{code}'"
#
#     engine = create_engine("mysql+mysqldb://root:123456@localhost:3306/jdgp?charset=utf8")
#     k_data = pd.read_sql(k_sql, engine)
#     k_data['trade_date'] = pd.to_datetime(k_data['trade_date']).dt.strftime('%Y-%m-%d')
#     k_data.rename(columns={'open': 'opens', 'close': 'closes', 'low': 'lows', 'high': 'highs', 'vol': 'vols',
#                            'pct_chg': 'pct_chg'},
#                   inplace=True)
#     # 假设 pm 是从 predictedMacd 返回的 DataFrame
#     # k_data = pd.concat([k_data, pm], ignore_index=True)
#     # print('k_data', k_data)
#     # 将数据转换为列表
#     # dates = k_data['trade_date'].tolist()
#     # macd = k_data[['macd_dif', 'macd_dea', 'macd_macd']].values.tolist()
#     # klines = k_data[['trade_date', 'opens', 'highs', 'lows', 'closes', 'vols', 'pct_chg', 'macd_dif', 'macd_dea',
#     #                  'macd_macd']].values.tolist()
#
#     dates = k_data['trade_date'].tolist()
#     values = k_data[['opens', 'closes', 'lows', 'highs']].values.tolist()
#
#     chart_data = {
#         'code': code,
#         'data': {
#             'dates': dates,
#             'values': values
#         }
#     }
#     print('chart_data', chart_data)
#     return JsonResponse(chart_data)
@csrf_exempt
def getSimilar(request):
    code = request.GET.get('code')
    startDate = request.GET.get('startDate')
    endDate = request.GET.get('endDate')
    # 代码后缀补全
    if len(code) == 6:
        if code.startswith(('00', '30')):
            code += '.SZ'
        elif code.startswith('60'):
            code += '.SH'
        else:
            return JsonResponse({'error': 'Invalid stock code'}, status=400)

    try:
        startDate = datetime.strptime(startDate, '%Y-%m-%d').strftime('%Y%m%d')
        endDate = datetime.strptime(endDate, '%Y-%m-%d').strftime('%Y%m%d')
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    target_stock = get_Target_Stock(code)
    all_stocks = get_All_Stocks()
    print('target_stock',target_stock)
    print('all_stocks',all_stocks)
    results = find_similar_stocks_adaptive(target_stock, all_stocks, datetime.strptime('2022-01-04', '%Y-%m-%d').date(),
                                           datetime.strptime('2022-02-09', '%Y-%m-%d').date(),
                                           window_size_range=(0.8, 1.2))
    # 按相似度从高到低排序后再取前10条
    top_10 = results.sort_values(by='相似度', ascending=False).head(10)
    # 标准化数据字段名 + 修正日期格式 + 处理 NaN
    processed_results = []
    for _, row in top_10.iterrows():
        similarity = row['相似度']
        if pd.isna(similarity):
            similarity = None  # 或者设为 0 等默认值

        processed_results.append({
            "code": row["股票代码"],
            "startDate": datetime.strptime(row["起始日期"], "%Y%m%d").strftime("%Y-%m-%d"),
            "endDate": datetime.strptime(row["终止日期"], "%Y%m%d").strftime("%Y-%m-%d"),
            "similarity": similarity,
            "windowSize": int(row["窗口大小"])
        })

    return JsonResponse({"list": processed_results}, safe=False)

@csrf_exempt
def getBase(request):
    code = request.GET.get('code')
    startDate = request.GET.get('startDate')
    endDate = request.GET.get('endDate')

    if not code or not startDate or not endDate:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    # 代码后缀补全
    if len(code) == 6:
        if code.startswith(('00', '30')):
            code += '.SZ'
        elif code.startswith('60'):
            code += '.SH'
        else:
            return JsonResponse({'error': 'Invalid stock code'}, status=400)

    try:
        startDate = datetime.strptime(startDate, '%Y-%m-%d').strftime('%Y%m%d')
        endDate = datetime.strptime(endDate, '%Y-%m-%d').strftime('%Y%m%d')
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    # 查询数据库
    sql = f"""
        SELECT trade_date, open, close, low, high
        FROM partition_table
        WHERE trade_date BETWEEN '{startDate}' AND '{endDate}'
        AND st_code = '{code}'
        ORDER BY trade_date ASC
    """

    engine = create_engine("mysql+mysqldb://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    df = pd.read_sql(sql, engine)
    print('df', df)
    if df.empty:
        return JsonResponse({'error': 'No data found'}, status=404)

    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
    dates = df['trade_date'].tolist()
    values = df[['open', 'close', 'low', 'high']].values.tolist()
    print("values",values)
    return JsonResponse({
        'code': code,
        'data': {
            'dates': dates,
            'values': values
        }
    })

def getSingleStock(request):
    startDate = request.GET.get('startDate')
    print("startDate", startDate)
    endDate = request.GET.get('endDate')
    print("endDate", endDate)
    code = request.GET.get('code')
    print("code", code)
    # 根据股票代码的长度或特定格式添加后缀
    if len(code) == 6:
        if code.startswith(('00', '30')):
            code += '.SZ'  # 深圳证券交易所
        elif code.startswith('60'):
            code += '.SH'  # 上海证券交易所
        else:
            # 处理其他情况或抛出异常
            return JsonResponse({'error': 'Invalid stock code'}, status=400)

    # 将字符串转换为 datetime 对象
    startDate = datetime.strptime(startDate, '%Y-%m-%d')
    endDate = datetime.strptime(endDate, '%Y-%m-%d')
    print(111111111111111111111111111111111111111111111111)
    # 将date，start_date转化格式
    startDate = startDate.strftime('%Y%m%d')
    endDate = endDate.strftime('%Y%m%d')

    # 查询30天数据语句
    k_sql = f"SELECT * FROM 前复权日线行情_筛_小表 WHERE trade_date BETWEEN '{startDate}' AND '{endDate}' AND st_code = '{code}'"

    engine = create_engine("mysql+mysqldb://root:123456@localhost:3306/jdgp?charset=utf8")
    k_data = pd.read_sql(k_sql, engine)
    k_data['trade_date'] = pd.to_datetime(k_data['trade_date']).dt.strftime('%Y-%m-%d')
    k_data.rename(columns={'open': 'opens', 'close': 'closes', 'low': 'lows', 'high': 'highs', 'vol': 'vols',
                           'pct_chg': 'pct_chg'},
                  inplace=True)

    print('k_data', k_data)
    # 将数据转换为列表
    # dates = k_data['trade_date'].tolist()
    klines = k_data[['trade_date', 'opens', 'highs', 'lows', 'closes', 'vols', 'pct_chg']].values.tolist()

    chart_data = {
        'klines': klines,
    }

    print('chart_data', chart_data)
    if not k_data.empty:
        response_data = {'chart_data': chart_data}
        return JsonResponse(response_data)
    else:
        return JsonResponse({'error': 'No data found'}, status=404)


def getSimilarStock(request):
    return None

