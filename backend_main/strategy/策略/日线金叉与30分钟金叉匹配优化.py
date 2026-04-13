#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MACD金叉匹配器 - 极宽松条件版本
日线级别看趋势，不指定金叉；30分钟级别数据看金叉和向上趋势
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

from sqlalchemy import create_engine


class MACDGoldenCrossMatcher:
    """
    MACD金叉匹配器类 - 极宽松条件版本
    """

    def __init__(self, debug=True):
        """
        初始化匹配器

        参数:
        debug: 是否输出调试信息
        """
        self.debug = debug
        self.matched_results = pd.DataFrame()
        self.analysis_result = {}

        # 数据库连接
        self.engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8")

    def log(self, message):
        """输出日志信息"""
        if self.debug:
            print(message)

    def load_data(self, start_date=None, end_date=None):
        """
        加载30分钟和日线数据

        参数:
        start_date: 开始日期，格式'YYYYMMDD'
        end_date: 结束日期，格式'YYYYMMDD'

        返回:
        tuple: (30分钟数据, 日线数据)
        """
        self.log("=" * 80)
        self.log("步骤1: 加载数据...")

        try:
            # 读取30分钟数据
            self.log("读取30分钟数据...")
            sql_30m = """
            SELECT stock_code, DATE(time) as trade_date, close, macd, pre_macd, pre_pre_macd, dif, dea, pre_dif, pre_pre_dif, pre_dea, pre_pre_dea,volume,vol_ma5,ma5,ma10
            FROM stock_30m_all
            """

            # 添加日期过滤条件
            where_conditions = []
            if start_date:
                where_conditions.append(f"DATE(time) >= '{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'")
            if end_date:
                where_conditions.append(f"DATE(time) <= '{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'")

            if where_conditions:
                sql_30m += " WHERE " + " AND ".join(where_conditions)

            self.log(f"30分钟数据查询SQL: {sql_30m}")
            df_30m = pd.read_sql(sql_30m, self.engine)
            self.log(f"30分钟数据加载完成，记录数: {len(df_30m)}")
            print("30分钟数据:", len(df_30m))

            # 读取日线数据（增加close列用于计算股价上涨）
            self.log("读取日线数据...")
            sql_daily = """
            SELECT st_code, trade_date, close,pre_close,
                   macd_macd, pre_macd_macd, pre_pre_macd_macd, macd_dif, last_dif
            FROM 小股池_partition_table
            """

            # 添加日期过滤条件
            where_conditions = []
            if start_date:
                where_conditions.append(f"trade_date >= '{start_date}'")
            if end_date:
                where_conditions.append(f"trade_date <= '{end_date}'")

            if where_conditions:
                sql_daily += " WHERE " + " AND ".join(where_conditions)

            self.log(f"日线数据查询SQL: {sql_daily}")
            df_daily = pd.read_sql(sql_daily, self.engine)
            self.log(f"日线数据加载完成，记录数: {len(df_daily)}")

            return df_30m, df_daily

        except Exception as e:
            self.log(f"数据加载失败: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def find_golden_cross_30m_vectorized(self, df_30m):
        """
        使用向量化操作找出30分钟数据中的MACD金叉（更严格的筛选条件）

        参数:
        df_30m: 30分钟数据DataFrame

        返回:
        DataFrame: 30分钟金叉数据
        """
        self.log("\n步骤2: 识别30分钟MACD金叉...")

        if df_30m.empty:
            self.log("30分钟数据为空")
            return pd.DataFrame()

        start_time = datetime.now()

        # 更严格的金叉条件组合
        golden_cross_mask = (
            # 基本金叉条件：pre_macd < 0 AND macd > 0
                ((df_30m['pre_macd'] < 0) & (df_30m['macd'] > 0)) &
                # DIF斜率条件（更强的动量要求）
                (((df_30m['dif'] - df_30m['pre_dif']) / (df_30m['pre_dif'] - df_30m['pre_pre_dif'])) > 1.5) &
                # 成交量条件：成交量放大（避免无量上涨）
                (df_30m['volume'] > 1.3 * df_30m['vol_ma5']) &
                # 价格位置条件：收盘价在均线之上（趋势确认）
                ((df_30m['close'] > df_30m['ma5']) | (df_30m['close'] > df_30m['ma10'])) &
                # 避免追高：短期涨幅限制
                ((df_30m['close'] / df_30m['close'].shift(5)) < 1.08)
        )

        golden_cross_data = df_30m[golden_cross_mask].copy()
        print("30分钟MACD金叉数据:", len(golden_cross_data))

        if golden_cross_data.empty:
            self.log("未找到30分钟MACD金叉数据")
            return pd.DataFrame()

        # 按股票代码和日期分组，每天只取第一个金叉
        if not golden_cross_data.empty:
            df_golden_cross_30m = (golden_cross_data
                                   .sort_values(['stock_code', 'trade_date'])
                                   .groupby(['stock_code', 'trade_date'])
                                   .first()
                                   .reset_index())
        else:
            df_golden_cross_30m = pd.DataFrame()

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        self.log(f"找到30分钟MACD金叉记录数: {len(df_golden_cross_30m)}")
        self.log(f"处理时间: {processing_time:.2f}秒")

        if len(df_golden_cross_30m) > 0:
            self.log("30分钟金叉数据示例:")
            self.log(df_golden_cross_30m.head().to_string())

        return df_golden_cross_30m

    def find_trend_daily_vectorized(self, df_daily):
        """
        使用向量化操作找出日线数据中的上升趋势股票（金叉条件）

        参数:
        df_daily: 日线数据DataFrame

        返回:
        DataFrame: 日线金叉数据
        """
        self.log("\n步骤3: 识别日线MACD金叉...")

        if df_daily.empty:
            self.log("日线数据为空")
            return pd.DataFrame()

        start_time = datetime.now()

        # 日线金叉条件：更复杂的金叉判断逻辑
        golden_cross_mask = (
                ((df_daily['pre_macd_macd'] < 0) & (df_daily['macd_macd'] > 0)) |
                ((df_daily['macd_macd'] > df_daily['pre_macd_macd']) &
                 (df_daily['pre_macd_macd'] < df_daily['pre_pre_macd_macd']) &
                 (df_daily['pre_pre_macd_macd'] > 0) &
                 (df_daily['macd_dif'] > 0)) |
                ((df_daily['macd_macd'] > df_daily['pre_macd_macd']) &
                 (df_daily['pre_macd_macd'] < df_daily['pre_pre_macd_macd']) &
                 (df_daily['macd_macd'] < 0) &
                 (df_daily['macd_dif'] < 0))
        )

        # 注意：原条件中还有周线DIF动量判断部分，但当前数据结构似乎不包含这些字段
        # 如果需要这部分条件，请确保数据中包含 'week_macd_dif', 'lastweek_macd_dif', 'lastlastweek_macd_dif' 字段

        golden_cross_daily = df_daily[golden_cross_mask].copy()

        # 重命名列以保持一致性
        golden_cross_daily = golden_cross_daily.rename(columns={
            'st_code': 'stock_code'
        })

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        self.log(f"找到日线MACD金叉记录数: {len(golden_cross_daily)}")
        self.log(f"处理时间: {processing_time:.2f}秒")

        if len(golden_cross_daily) > 0:
            self.log("日线金叉数据示例:")
            self.log(golden_cross_daily.head().to_string())

        return golden_cross_daily

    def load_calendar_data(self):
        """
        加载股票日历表数据

        返回:
        DataFrame: 股票日历数据
        """
        self.log("加载股票日历表数据...")
        try:
            sql = "SELECT exchange, cal_date, is_open, cycle, day, week, month, month_num, year, trade_day FROM 股票日历_new"
            df_calendar = pd.read_sql(sql, self.engine)
            df_calendar['cal_date'] = pd.to_datetime(df_calendar['cal_date']).dt.date
            self.log(f"股票日历表加载完成，记录数: {len(df_calendar)}")
            return df_calendar
        except Exception as e:
            self.log(f"股票日历表加载失败: {str(e)}")
            return pd.DataFrame()

    def get_next_trading_days(self, calendar_data, base_date, n_days):
        base_date = base_date.date()

        future_trading_days = calendar_data[
            (calendar_data['cal_date'] > base_date) & (calendar_data['is_open'] == "1")
            ].sort_values('cal_date')

        # 返回第n个交易日
        if len(future_trading_days) >= n_days:
            return future_trading_days.iloc[n_days - 1]['cal_date']

        return None

    def match_golden_cross_complete(self, df_golden_cross_30m, df_trend_daily, df_daily_full):
        """
        完整匹配所有30分钟金叉与日线上升趋势的对应关系，并计算股价上涨概率

        参数:
        df_golden_cross_30m: 30分钟金叉数据
        df_trend_daily: 日线上升趋势数据
        df_daily_full: 完整的日线数据（用于计算股价上涨）

        返回:
        DataFrame: 完整匹配结果（包括未匹配的）
        """
        self.log("\n步骤4: 完整匹配30分钟金叉和日线上升趋势...")

        if df_golden_cross_30m.empty:
            self.log("30分钟金叉数据为空")
            return pd.DataFrame()

        start_time = datetime.now()

        # 加载股票日历数据
        df_calendar = self.load_calendar_data()

        # 为每个30分钟金叉创建完整的匹配记录
        all_results = []

        # 准备日线数据用于匹配
        df_daily_converted = df_trend_daily.copy()
        if not df_daily_converted.empty:
            df_daily_converted['trade_date'] = pd.to_datetime(df_daily_converted['trade_date'])

        # 准备完整日线数据用于计算股价上涨概率
        df_daily_prices = df_daily_full.copy()
        if not df_daily_prices.empty:
            df_daily_prices['trade_date'] = pd.to_datetime(df_daily_prices['trade_date'])

        # 遍历每个30分钟金叉
        for _, row_30m in df_golden_cross_30m.iterrows():
            stock_code = row_30m['stock_code']
            golden_cross_date = pd.to_datetime(row_30m['trade_date'])

            # 获取该股票的日线上升趋势数据
            stock_daily_data = df_daily_converted[
                df_daily_converted['stock_code'] == stock_code] if not df_daily_converted.empty else pd.DataFrame()

            # 查找匹配的日线上升趋势
            matched_daily = None
            match_type = None
            days_diff = None

            # 检查当日
            daily_same_day = stock_daily_data[stock_daily_data['trade_date'].dt.date == golden_cross_date.date()]
            if not daily_same_day.empty:
                matched_daily = daily_same_day.iloc[0]
                match_type = "当日"
                days_diff = 0

            # 检查后一天（按自然日查找）
            if matched_daily is None:
                next_trading_date = self.get_next_trading_days(df_calendar, golden_cross_date, 1)
                daily_next_day = stock_daily_data[(stock_daily_data['trade_date'].dt.date) == next_trading_date]
                if not daily_next_day.empty:
                    matched_daily = daily_next_day.iloc[0]
                    match_type = "后一天"
                    days_diff = 1

            # 检查后两天（按自然日查找）
            if matched_daily is None:
                next_trading_date = self.get_next_trading_days(df_calendar, golden_cross_date, 2)
                daily_next2_day = stock_daily_data[stock_daily_data['trade_date'].dt.date == next_trading_date]
                if not daily_next2_day.empty:
                    matched_daily = daily_next2_day.iloc[0]
                    match_type = "后两天"
                    days_diff = 2

            # 检查后三天（按自然日查找）
            if matched_daily is None:
                next_trading_date = self.get_next_trading_days(df_calendar, golden_cross_date, 3)
                daily_next3_day = stock_daily_data[stock_daily_data['trade_date'].dt.date == next_trading_date]
                if not daily_next3_day.empty:
                    matched_daily = daily_next3_day.iloc[0]
                    match_type = "后三天"
                    days_diff = 3

            # 计算股价上涨概率相关数据
            price_up_1d = None
            price_up_2d = None
            price_up_3d = None
            price_up_5d = None

            if not df_daily_prices.empty:
                stock_price_data = df_daily_prices[df_daily_prices['st_code'] == stock_code]
                if not stock_price_data.empty:
                    # 找到金叉日的收盘价
                    cross_day_data = stock_price_data[
                        stock_price_data['trade_date'].dt.date == golden_cross_date.date()]

                    if not cross_day_data.empty:
                        cross_day_close = cross_day_data.iloc[0]['close']

                        # 计算未来1天、2天、3天、5天的股价变化
                        for i in [1, 2, 3, 5]:
                            future_date = golden_cross_date + pd.Timedelta(days=i)
                            future_data = stock_price_data[
                                stock_price_data['trade_date'].dt.date == future_date.date()]

                            if not future_data.empty:
                                future_close = future_data.iloc[0]['close']
                                price_change = (future_close - cross_day_close) / cross_day_close * 100

                                if i == 1:
                                    price_up_1d = price_change
                                elif i == 2:
                                    price_up_2d = price_change
                                elif i == 3:
                                    price_up_3d = price_change
                                elif i == 5:
                                    price_up_5d = price_change

            # 创建结果记录
            result = {
                'stock_code': stock_code,
                'golden_cross_date_30m': golden_cross_date.strftime('%Y-%m-%d'),
                'macd_30m': row_30m['macd'],
                'pre_macd_30m': row_30m['pre_macd'],
                'is_matched': matched_daily is not None,
                'match_type': match_type if matched_daily is not None else '未匹配',
                'days_difference': days_diff if matched_daily is not None else None,
                'trend_date_daily': matched_daily['trade_date'].strftime(
                    '%Y-%m-%d') if matched_daily is not None else None,
                'match_score': 0,  # 未匹配的分数为0
                # 股价上涨数据
                'price_up_1d': price_up_1d,
                'price_up_2d': price_up_2d,
                'price_up_3d': price_up_3d,
                'price_up_5d': price_up_5d
            }

            # 如果找到匹配，计算匹配度分数
            if matched_daily is not None:
                # 创建临时DataFrame用于计算分数
                temp_df = pd.DataFrame([{
                    'days_difference': days_diff,
                    'macd_30m': row_30m['macd'],
                    'pre_macd_30m': row_30m['pre_macd']
                }])

                temp_df = self.calculate_match_score_vectorized(temp_df)
                result['match_score'] = temp_df['match_score'].iloc[0]

            all_results.append(result)

        # 转换为DataFrame
        df_all_results = pd.DataFrame(all_results)

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 统计匹配情况
        total_30m_crosses = len(df_all_results)
        matched_count = df_all_results['is_matched'].sum()
        unmatched_count = total_30m_crosses - matched_count
        match_rate = (matched_count / total_30m_crosses * 100) if total_30m_crosses > 0 else 0

        self.log(f"完整匹配分析完成")
        self.log(f"处理时间: {processing_time:.2f}秒")
        self.log(f"\n匹配统计:")
        self.log(f"  30分钟金叉总数: {total_30m_crosses}")
        self.log(f"  匹配成功数: {matched_count}")
        self.log(f"  未匹配数: {unmatched_count}")
        self.log(f"  匹配率: {match_rate:.1f}%")

        if matched_count > 0:
            matched_results = df_all_results[df_all_results['is_matched'] == True]
            self.log(f"\n匹配类型分布:")
            match_type_counts = matched_results['match_type'].value_counts()
            for match_type, count in match_type_counts.items():
                self.log(f"  {match_type}: {count} ({count / matched_count * 100:.1f}%)")

            self.log(f"\n匹配度统计:")
            self.log(f"  平均匹配度: {matched_results['match_score'].mean():.1f}")
            self.log(f"  最高匹配度: {matched_results['match_score'].max():.1f}")
            self.log(f"  最低匹配度: {matched_results['match_score'].min():.1f}")

            # 高匹配度统计
            high_score_count = (matched_results['match_score'] >= 80).sum()
            self.log(f"  高匹配度(>=80分): {high_score_count} ({high_score_count / matched_count * 100:.1f}%)")

        # 计算股价上涨概率
        self.calculate_price_up_probability(df_all_results)

        return df_all_results

    def calculate_price_up_probability(self, df_results):
        """
        计算股价上涨概率（隔离统计，上涨天数之间不重复计算）
        排除当日形成金叉的股票

        参数:
        df_results: 匹配结果DataFrame
        """
        self.log("\n步骤5: 计算股价上涨概率（隔离统计，排除当日金叉）...")

        if df_results.empty:
            self.log("无数据用于计算股价上涨概率")
            return

        # 排除当日形成金叉的股票
        df_filtered = df_results[df_results['match_type'] != '当日'].copy()
        total_30m_crosses = len(df_filtered)  # 以30分钟金叉总数为基准（排除当日金叉）

        self.log(f"\n30分钟金叉总数（计算基准，排除当日金叉）: {total_30m_crosses}")

        if total_30m_crosses == 0:
            self.log("无非当日金叉数据用于计算")
            return

        # 过滤有价格数据的记录
        valid_results = df_filtered.dropna(subset=['price_up_1d', 'price_up_2d', 'price_up_3d', 'price_up_5d'],
                                           how='all')

        valid_count = len(valid_results)
        invalid_count = total_30m_crosses - valid_count

        self.log(f"有效样本数（能计算股价变化）: {valid_count}")
        self.log(f"无效样本数（无法计算股价变化）: {invalid_count}")
        self.log(f"数据完整率: {valid_count / total_30m_crosses * 100:.1f}%")

        if valid_results.empty:
            self.log("无有效价格数据用于计算")
            return

        # 独立统计各时间段上涨概率（以30分钟金叉总数为基准分母）
        up_1d_count = (valid_results['price_up_1d'] > 0).sum()
        up_2d_count = (valid_results['price_up_2d'] > 0).sum()
        up_3d_count = (valid_results['price_up_3d'] > 0).sum()
        up_5d_count = (valid_results['price_up_5d'] > 0).sum()

        # 使用总金叉数作为基准计算概率
        up_1d_prob_total = up_1d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        up_2d_prob_total = up_2d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        up_3d_prob_total = up_3d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        up_5d_prob_total = up_5d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0

        self.log(f"\n股价上涨概率统计（隔离计算，各天数独立统计，排除当日金叉）:")
        self.log(f"  第1天上涨概率: {up_1d_prob_total:.1f}% ({up_1d_count}/{total_30m_crosses})")
        self.log(f"  第2天上涨概率: {up_2d_prob_total:.1f}% ({up_2d_count}/{total_30m_crosses})")
        self.log(f"  第3天上涨概率: {up_3d_prob_total:.1f}% ({up_3d_count}/{total_30m_crosses})")
        self.log(f"  第5天上涨概率: {up_5d_prob_total:.1f}% ({up_5d_count}/{total_30m_crosses})")

        # 连续上涨概率统计（更严格的统计方式）
        consecutive_1d_count = (valid_results['price_up_1d'] > 0).sum()
        consecutive_2d_count = ((valid_results['price_up_1d'] > 0) & (valid_results['price_up_2d'] > 0)).sum()
        consecutive_3d_count = ((valid_results['price_up_1d'] > 0) & (valid_results['price_up_2d'] > 0) & (
                valid_results['price_up_3d'] > 0)).sum()
        consecutive_5d_count = ((valid_results['price_up_1d'] > 0) & (valid_results['price_up_2d'] > 0) & (
                valid_results['price_up_3d'] > 0) & (valid_results['price_up_5d'] > 0)).sum()

        consecutive_1d_prob = consecutive_1d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        consecutive_2d_prob = consecutive_2d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        consecutive_3d_prob = consecutive_3d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0
        consecutive_5d_prob = consecutive_5d_count / total_30m_crosses * 100 if total_30m_crosses > 0 else 0

        self.log(f"\n连续上涨概率统计（更严格的统计方式，排除当日金叉）:")
        self.log(f"  第1天持续上涨概率: {consecutive_1d_prob:.1f}% ({consecutive_1d_count}/{total_30m_crosses})")
        self.log(f"  连续2天上涨概率: {consecutive_2d_prob:.1f}% ({consecutive_2d_count}/{total_30m_crosses})")
        self.log(f"  连续3天上涨概率: {consecutive_3d_prob:.1f}% ({consecutive_3d_count}/{total_30m_crosses})")
        self.log(f"  连续5天上涨概率: {consecutive_5d_prob:.1f}% ({consecutive_5d_count}/{total_30m_crosses})")

    def calculate_match_score_vectorized(self, df_matched):
        """
        使用向量化操作计算匹配度分数

        参数:
        df_matched: 匹配结果DataFrame

        返回:
        DataFrame: 包含匹配度分数的DataFrame
        """
        # 基础分数：找到匹配就得到50分
        base_score = 50

        # 时间匹配度：当日匹配得30分，后一天得20分，后两天得10分，后三天得5分
        time_scores = np.where(df_matched['days_difference'] == 0, 30,
                               np.where(df_matched['days_difference'] == 1, 20,
                                        np.where(df_matched['days_difference'] == 2, 10,
                                                 np.where(df_matched['days_difference'] == 3, 5, 0))))

        # MACD强度匹配度
        macd_change_30m = np.abs(df_matched['macd_30m'] - df_matched['pre_macd_30m'])

        strength_scores = np.where(
            macd_change_30m > 0.01, 10,
            np.where(macd_change_30m > 0.005, 5, 0)
        )

        # MACD值正向性
        positivity_scores = np.where(
            (df_matched['macd_30m'] > 0), 10, 0
        )

        # 计算总分
        total_scores = base_score + time_scores + strength_scores + positivity_scores

        # 确保分数不超过100
        df_matched['match_score'] = np.minimum(total_scores, 100)

        return df_matched

    def analyze_complete_results(self, df_all_results):
        """
        分析完整匹配结果

        参数:
        df_all_results: 完整匹配结果DataFrame

        返回:
        dict: 分析结果
        """
        if df_all_results.empty:
            return {}

        self.log("\n" + "=" * 80)
        self.log("完整匹配结果分析")
        self.log("=" * 80)

        analysis = {}

        # 基本统计
        total_30m_crosses = len(df_all_results)
        matched_results = df_all_results[df_all_results['is_matched'] == True]
        unmatched_results = df_all_results[df_all_results['is_matched'] == False]

        analysis['basic_stats'] = {
            'total_30m_crosses': total_30m_crosses,
            'matched_count': len(matched_results),
            'unmatched_count': len(unmatched_results),
            'match_rate': len(matched_results) / total_30m_crosses * 100
        }

        self.log(f"基本统计:")
        self.log(f"  30分钟金叉总数: {total_30m_crosses}")
        self.log(f"  匹配成功数: {len(matched_results)}")
        self.log(f"  未匹配数: {len(unmatched_results)}")
        self.log(f"  匹配率: {len(matched_results) / total_30m_crosses * 100:.1f}%")

        if not matched_results.empty:
            # 匹配类型分布
            match_type_counts = matched_results['match_type'].value_counts()
            analysis['match_type_distribution'] = match_type_counts.to_dict()

            self.log(f"\n匹配类型分布:")
            for match_type, count in match_type_counts.items():
                self.log(f"  {match_type}: {count} ({count / len(matched_results) * 100:.1f}%)")

            # 匹配度统计
            analysis['score_stats'] = {
                'mean': matched_results['match_score'].mean(),
                'median': matched_results['match_score'].median(),
                'std': matched_results['match_score'].std(),
                'min': matched_results['match_score'].min(),
                'max': matched_results['match_score'].max()
            }

            self.log(f"\n匹配度统计:")
            self.log(f"  平均匹配度: {analysis['score_stats']['mean']:.1f}")
            self.log(f"  中位数匹配度: {analysis['score_stats']['median']:.1f}")
            self.log(f"  标准差: {analysis['score_stats']['std']:.1f}")
            self.log(f"  最高匹配度: {analysis['score_stats']['max']:.1f}")
            self.log(f"  最低匹配度: {analysis['score_stats']['min']:.1f}")

            # 高匹配度统计
            high_score_results = matched_results[matched_results['match_score'] >= 80]
            analysis['high_score_stats'] = {
                'count': len(high_score_results),
                'percentage': len(high_score_results) / len(matched_results) * 100,
                'stocks': high_score_results['stock_code'].unique().tolist()
            }

            self.log(f"\n高匹配度统计 (>=80分):")
            self.log(f"  数量: {analysis['high_score_stats']['count']}")
            self.log(f"  比例: {analysis['high_score_stats']['percentage']:.1f}%")
            self.log(f"  涉及股票数: {len(analysis['high_score_stats']['stocks'])}")

        return analysis

    def export_complete_results(self, df_all_results, filename=None):
        """
        导出完整匹配结果

        参数:
        df_all_results: 完整匹配结果DataFrame
        filename: 输出文件名

        返回:
        str: 输出文件路径
        """
        if df_all_results.empty:
            self.log("没有匹配结果可供导出")
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"macd_golden_cross_complete_analysis_{timestamp}.csv"

        if not filename.endswith('.csv'):
            filename += '.csv'

        try:
            df_all_results.to_csv(filename, index=False, encoding='utf-8-sig')
            self.log(f"\n完整匹配结果已导出到: {filename}")
            self.log(f"导出记录数: {len(df_all_results)}")
            return filename
        except Exception as e:
            self.log(f"导出过程中发生错误: {str(e)}")
            return None

    def run_complete_analysis(self, start_date=None, end_date=None, export_results=True):
        """
        运行完整的分析流程 - 极宽松条件版本

        参数:
        start_date: 开始日期，格式'YYYYMMDD'
        end_date: 结束日期，格式'YYYYMMDD'
        export_results: 是否导出结果

        返回:
        dict: 分析结果
        """
        total_start_time = datetime.now()

        self.log("=" * 100)
        self.log("MACD金叉匹配分析 - 极宽松条件版本")
        self.log("=" * 100)
        self.log(f"分析时间范围: {start_date or '全部'} 到 {end_date or '全部'}")
        self.log(f"导出结果: {'是' if export_results else '否'}")
        self.log("=" * 100)

        result = {
            'all_results': pd.DataFrame(),
            'matched_results': pd.DataFrame(),
            'analysis_result': {},
            'export_file': None,
            'success': False,
            'error_message': None,
            'processing_time': 0
        }

        try:
            # 步骤1: 加载数据
            df_30m, df_daily = self.load_data(start_date, end_date)
            if df_30m.empty:
                self.log("30分钟数据为空")
                return result

            # 步骤2: 识别30分钟金叉
            df_golden_cross_30m = self.find_golden_cross_30m_vectorized(df_30m)
            if df_golden_cross_30m.empty:
                self.log("未找到30分钟MACD金叉数据")
                return result

            # 步骤3: 识别日线上升趋势（极宽松条件）
            df_trend_daily = self.find_trend_daily_vectorized(df_daily)

            # 步骤4: 完整匹配所有30分钟金叉（传入完整日线数据用于计算股价上涨）
            df_all_results = self.match_golden_cross_complete(df_golden_cross_30m, df_trend_daily, df_daily)
            result['all_results'] = df_all_results

            # 步骤5: 分析完整结果
            analysis_result = self.analyze_complete_results(df_all_results)
            result['analysis_result'] = analysis_result

            # 步骤6: 导出结果
            if export_results:
                export_file = self.export_complete_results(df_all_results)
                result['export_file'] = export_file

                # 导出未匹配的数据
                self.export_unmatched_results(df_all_results)

            result['success'] = True

            total_end_time = datetime.now()
            total_processing_time = (total_end_time - total_start_time).total_seconds()
            result['processing_time'] = total_processing_time

            self.log("\n" + "=" * 100)
            self.log("完整分析完成!")
            self.log("=" * 100)
            self.log(f"总处理时间: {total_processing_time:.2f}秒")
            self.log(f"30分钟金叉总数: {len(df_all_results)}")
            self.log(f"匹配成功数: {len(df_all_results[df_all_results['is_matched'] == True])}")
            self.log(
                f"匹配率: {len(df_all_results[df_all_results['is_matched'] == True]) / len(df_all_results) * 100:.1f}%")
            if result['export_file']:
                self.log(f"结果已导出到: {result['export_file']}")

            return result

        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            result['error_message'] = error_msg
            self.log(f"\n错误: {error_msg}")
            import traceback
            traceback.print_exc()
            return result

    def export_unmatched_results(self, df_all_results, filename=None):
        """
        导出未匹配成功的30分钟金叉数据

        参数:
        df_all_results: 完整匹配结果DataFrame
        filename: 输出文件名

        返回:
        str: 输出文件路径
        """
        if df_all_results.empty:
            self.log("没有匹配结果可供导出")
            return None

        # 筛选出未匹配的数据
        df_unmatched = df_all_results[df_all_results['is_matched'] == False]

        if df_unmatched.empty:
            self.log("没有未匹配的数据需要导出")
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"macd_golden_cross_unmatched_{timestamp}.csv"

        if not filename.endswith('.csv'):
            filename += '.csv'

        try:
            # 只导出关键字段
            columns_to_export = ['stock_code', 'golden_cross_date_30m', 'macd_30m', 'pre_macd_30m']
            df_unmatched[columns_to_export].to_csv(filename, index=False, encoding='utf-8-sig')
            self.log(f"\n未匹配的30分钟金叉数据已导出到: {filename}")
            self.log(f"导出记录数: {len(df_unmatched)}")
            return filename
        except Exception as e:
            self.log(f"导出未匹配数据过程中发生错误: {str(e)}")
            return None

    def add_macd_score_to_daily_data(self, df_30m, df_daily):
        """
        给日线数据添加MACD分数列：
        - 30分钟级别看金叉信号
        - 日线级别看上升趋势（极宽松条件）
        - 通过指标筛选符合条件的股票并打分
        """
        self.log("\n步骤X: 为日线数据添加MACD打分...")

        # 1. 识别30分钟级别金叉信号
        df_golden_cross_30m = self.find_golden_cross_30m_vectorized(df_30m)

        # 2. 识别日线上升趋势（极宽松条件）
        df_trend_daily = self.find_trend_daily_vectorized(df_daily)

        # 3. 准备数据用于筛选
        df_30m_signals = df_golden_cross_30m[['stock_code', 'trade_date']].copy()
        df_daily_trends = df_trend_daily[['stock_code', 'trade_date']].copy()

        # 4. 确保股票代码和日期格式统一
        df_30m_signals['stock_code'] = df_30m_signals['stock_code'].astype(str)
        df_daily_trends['stock_code'] = df_daily_trends['stock_code'].astype(str)
        df_daily['st_code'] = df_daily['st_code'].astype(str)

        df_30m_signals['trade_date'] = pd.to_datetime(df_30m_signals['trade_date']).dt.date
        df_daily_trends['trade_date'] = pd.to_datetime(df_daily_trends['trade_date']).dt.date
        df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date']).dt.date

        # 5. 找出在同一天既有30分钟金叉又有日线上升趋势的记录
        matched_signals = pd.merge(
            df_30m_signals,
            df_daily_trends,
            on=['stock_code', 'trade_date'],
            how='inner'
        )

        print(f"匹配成功的记录数: {len(matched_signals)}")

        # 6. 为匹配成功的记录准备打分数据
        matched_days = matched_signals.copy()
        matched_days.rename(columns={
            'stock_code': 'st_code',
            'trade_date': 'trade_date'
        }, inplace=True)

        # 7. 计算综合分数
        matched_days['match_score'] = self.calculate_composite_score(df_30m, df_daily, matched_days)

        # 8. 初始化日线数据中的MACD列为-1
        df_daily = df_daily.copy()
        df_daily['MACD'] = -1

        # 9. 将匹配分数合并到日线数据中
        df_daily = df_daily.merge(
            matched_days[['st_code', 'trade_date', 'match_score']],
            on=['st_code', 'trade_date'],
            how='left'
        )

        # 10. 更新MACD分数，如果匹配到则使用match_score，否则保持-1
        df_daily['MACD'] = df_daily['match_score'].fillna(df_daily['MACD']).astype(int)
        df_daily.drop(columns=['match_score'], inplace=True)

        # 11. 只返回需要的列
        required_cols = [
            'st_code', 'trade_date', 'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci',
            'macd_macd', 'pre_macd_macd', 'MACD'
        ]
        result_df = df_daily[required_cols].copy()

        # 12. 打印 MACD 大于 0 的记录
        macd_positive_records = result_df[result_df['MACD'] > 0]
        if not macd_positive_records.empty:
            print(f"\n最终返回的df中MACD大于0的记录数: {len(macd_positive_records)}")
            print("MACD大于0的前10条记录:")
            print(macd_positive_records.head(10).to_string(index=False))
        else:
            print("最终返回的df中没有MACD大于0的记录")

        return result_df

    def calculate_composite_score(self, df_30m, df_daily, matched_signals):
        """
        计算综合分数

        参数:
        df_30m: 30分钟数据
        df_daily: 日线数据
        matched_signals: 匹配成功的信号

        返回:
        Series: 分数序列
        """
        scores = []

        for _, signal in matched_signals.iterrows():
            st_code = signal['st_code']
            trade_date = signal['trade_date']

            # 获取30分钟数据
            df_30m_stock = df_30m[
                (df_30m['stock_code'] == st_code) &
                (pd.to_datetime(df_30m['trade_date']).dt.date == trade_date)
                ]

            # 获取日线数据
            df_daily_stock = df_daily[
                (df_daily['st_code'] == st_code) &
                (pd.to_datetime(df_daily['trade_date']).dt.date == trade_date)
                ]

            score = 0

            if not df_30m_stock.empty:
                row_30m = df_30m_stock.iloc[0]

                # 30分钟金叉强度评分 (0-40分)
                macd_strength = abs(row_30m['macd'] - row_30m['pre_macd'])
                if macd_strength > 0.01:
                    score += 20
                elif macd_strength > 0.005:
                    score += 10

                # MACD正值加分 (0-20分)
                if row_30m['macd'] > 0:
                    score += 20

                # DIF斜率加分 (0-20分)
                if (row_30m['dif'] - row_30m['pre_dif']) / (row_30m['pre_dif'] - row_30m['pre_pre_dif']) > 1.2:
                    score += 20

            if not df_daily_stock.empty:
                row_daily = df_daily_stock.iloc[0]

                # 日线上升趋势评分 (0-20分)
                # MACD上升
                if row_daily['macd_macd'] > row_daily['pre_macd_macd']:
                    score += 10
                # 股价上涨
                if row_daily['close'] > row_daily['pre_close']:
                    score += 5
                # DIF上升
                if row_daily['macd_dif'] > row_daily['last_dif']:
                    score += 5

            # 确保分数不超过100
            score = min(score, 100)
            scores.append(max(score, 0))  # 确保不为负数

        return pd.Series(scores, index=matched_signals.index)


def main():
    """
    主函数 - 示例用法
    """
    print("MACD金叉匹配分析器 - 极宽松条件版本")
    print("=" * 50)

    # 创建匹配器实例
    matcher = MACDGoldenCrossMatcher(debug=True)

    # 运行完整分析
    print("\n运行完整分析...")
    result = matcher.run_complete_analysis(
        start_date='20251201',
        end_date='20251210',
        export_results=True
    )

    if result['success']:
        print(f"\n✓ 分析成功!")
        print(f"总处理时间: {result['processing_time']:.2f}秒")

        all_results = result['all_results']
        matched_results = all_results[all_results['is_matched'] == True]

        print(f"30分钟金叉总数: {len(all_results)}")
        print(f"匹配成功数: {len(matched_results)}")
        print(f"匹配率: {len(matched_results) / len(all_results) * 100:.1f}%")

        if not matched_results.empty:
            print(f"平均匹配度: {matched_results['match_score'].mean():.1f}")

            # 显示匹配类型分布
            print(f"\n匹配类型分布:")
            match_type_counts = matched_results['match_type'].value_counts()
            for match_type, count in match_type_counts.items():
                print(f"  {match_type}: {count} ({count / len(matched_results) * 100:.1f}%)")
    else:
        print(f"\n✗ 分析失败: {result['error_message']}")

    return result


if __name__ == "__main__":
    main()
