#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MACD金叉匹配分析器 - 修正版本

功能：
1. 识别60分钟MACD金叉（限制在每日14:00和15:00的数据）
2. 识别日线MACD金叉
3. 匹配60分钟金叉与之后出现的日线金叉
4. 分析匹配成功率和时间分布
5. 导出完整结果

修正内容：
- 修复日线金叉判断逻辑错误
- 添加日线条件过滤（macd_dif > last_dif）
- 完整记录所有60分钟金叉匹配结果
- 添加股价上涨和收益率计算
- 导出完整匹配结果

新增（本次修改）：
- 增加 MACD否决（顶部动能回落过滤）：
  当日线柱体为正且开始回落（并可要求连续回落/或DIF拐头向下）时，对当天信号否决，
  使后续策略不再买入这些“强势但可能见顶”的票。
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
import warnings

warnings.filterwarnings('ignore')


class MACDGoldenCrossMatcher:
    def __init__(self, debug=False):
        """
        初始化匹配器

        参数:
        debug: 是否输出调试信息
        """
        self.debug = debug
        self.matched_results = pd.DataFrame()
        self.analysis_result = {}

        # 数据库连接配置
        self.engine = create_engine(
            "mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8"
        )

    def log(self, message):
        """输出日志信息"""
        if self.debug:
            print(message)

    def apply_macd_veto(self, df_daily, lookback=2):
        """
        MACD否决过滤（用于避免强势信号出现在阶段性顶部附近导致短期回调即止损）：

        默认规则（可按需要自行调整）：
        - 仅在柱体(macd_macd)为正时考虑“见顶回落”风险；
        - 若柱体连续回落（例如当日 < 昨日，且昨日 < 前日），则否决；
        - 或 DIF 已经拐头向下（macd_dif < last_dif）且柱体回落，则否决。

        返回:
            df_daily: 在原df基础上新增 bool 列 `macd_veto`（True=否决）
        """
        if df_daily is None or df_daily.empty:
            return df_daily

        df_daily = df_daily.copy()
        if 'macd_veto' not in df_daily.columns:
            df_daily['macd_veto'] = False

        required_cols = {'macd_macd', 'pre_macd_macd'}
        if not required_cols.issubset(df_daily.columns):
            # 缺少关键列，无法否决
            return df_daily

        # 1) 柱体为正，且当日柱体回落（动能减弱）
        hist_positive = df_daily['macd_macd'] > 0
        hist_falling_today = df_daily['macd_macd'] < df_daily['pre_macd_macd']

        veto = hist_positive & hist_falling_today

        # 2) 连续回落（需要 pre_pre_macd_macd）
        if lookback >= 2 and 'pre_pre_macd_macd' in df_daily.columns:
            hist_falling_yesterday = df_daily['pre_macd_macd'] < df_daily['pre_pre_macd_macd']
            veto = veto & hist_falling_yesterday

        # 3) DIF拐头向下（需要 macd_dif / last_dif），与柱体回落共同触发更稳健
        if 'macd_dif' in df_daily.columns and 'last_dif' in df_daily.columns:
            dif_turn_down = df_daily['macd_dif'] < df_daily['last_dif']
            veto = veto | (hist_positive & hist_falling_today & dif_turn_down)

        df_daily['macd_veto'] = veto.fillna(False)

        return df_daily

    def load_data(self, start_date=None, end_date=None):
        """
        加载60分钟和日线数据

        参数:
        start_date: 开始日期，格式'YYYYMMDD'
        end_date: 结束日期，格式'YYYYMMDD'

        返回:
        tuple: (df_60m, df_daily)
        """
        self.log("\n步骤1: 加载数据.")
        try:
            # 读取60分钟数据
            self.log("读取60分钟数据.")
            sql_60m = """
            SELECT stock_code, DATE(time) as trade_date, close, macd, pre_macd, pre_pre_macd,
                   dif, dea, pre_dif, pre_pre_dif, pre_dea, pre_pre_dea,
                   volume, vol_ma5, ma5, ma10
            FROM stock_60m_all
            """

            where_conditions = []
            if start_date:
                where_conditions.append(f"DATE(time) >= '{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'")
            if end_date:
                where_conditions.append(f"DATE(time) <= '{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'")

            # 只保留每日14:00和15:00的数据
            where_conditions.append("(HOUR(time) = 14 OR HOUR(time) = 15)")

            if where_conditions:
                sql_60m += " WHERE " + " AND ".join(where_conditions)

            self.log(f"60分钟数据查询SQL: {sql_60m}")
            df_60m = pd.read_sql(sql_60m, self.engine)
            self.log(f"60分钟数据加载完成，记录数: {len(df_60m)}")
            print("60分钟数据:", len(df_60m))

            # 读取日线数据
            self.log("读取日线数据.")
            sql_daily = """
            SELECT st_code, trade_date, close,
                   macd_macd, pre_macd_macd, pre_pre_macd_macd,
                   macd_dif, last_dif
            FROM stock_1d_all
            """

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

            return df_60m, df_daily

        except Exception as e:
            self.log(f"数据加载失败: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

    def find_golden_cross_60m_vectorized(self, df_60m, df_daily=None):
        """
        使用向量化操作找出60分钟数据中的MACD金叉，并根据日线数据进行过滤

        参数:
        df_60m: 60分钟数据DataFrame
        df_daily: 日线数据DataFrame（用于过滤）

        返回:
        DataFrame: 60分钟金叉数据（已过滤）
        """
        self.log("\n步骤2: 识别60分钟MACD金叉.")

        if df_60m.empty:
            self.log("60分钟数据为空")
            return pd.DataFrame()

        start_time = datetime.now()

        # 金叉条件：pre_macd < 0 AND macd > 0
        golden_cross_mask = (
            (df_60m['pre_macd'] < 0) & (df_60m['macd'] > 0)
            & ((df_60m['dif'] - df_60m['pre_dif']) / (df_60m['pre_dif'] - df_60m['pre_pre_dif']) > 1.2)
        )

        golden_cross_data = df_60m[golden_cross_mask].copy()
        print("60分钟MACD金叉数据:", len(golden_cross_data))
        if golden_cross_data.empty:
            self.log("未找到60分钟MACD金叉数据")
            return pd.DataFrame()

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        self.log(f"识别60分钟金叉耗时: {processing_time:.2f}秒")
        return golden_cross_data

    def find_golden_cross_daily_vectorized(self, df_daily):
        """
        使用向量化操作找出日线数据中的MACD金叉

        参数:
        df_daily: 日线数据DataFrame

        返回:
        DataFrame: 日线金叉数据
        """
        self.log("\n步骤3: 识别日线MACD金叉.")

        if df_daily.empty:
            self.log("日线数据为空")
            return pd.DataFrame()

        # 日线金叉条件：pre_macd_macd < 0 AND macd_macd > 0
        golden_cross_mask = (df_daily['pre_macd_macd'] < 0) & (df_daily['macd_macd'] > 0)
        golden_cross_data = df_daily[golden_cross_mask].copy()
        self.log(f"日线MACD金叉数据: {len(golden_cross_data)}")
        return golden_cross_data

    def match_golden_cross_complete(self, df_golden_cross_60m, df_golden_cross_daily, df_daily_all):
        """
        完整匹配所有60分钟金叉与之后出现的日线金叉，并计算股价上涨情况
        """
        self.log("\n步骤4: 完整匹配所有60分钟金叉与日线金叉.")

        if df_golden_cross_60m.empty:
            return pd.DataFrame()

        df_golden_cross_60m = df_golden_cross_60m.copy()
        df_golden_cross_daily = df_golden_cross_daily.copy()
        df_daily_all = df_daily_all.copy()

        df_golden_cross_60m['stock_code'] = df_golden_cross_60m['stock_code'].astype(str)
        df_golden_cross_daily['st_code'] = df_golden_cross_daily['st_code'].astype(str)
        df_daily_all['st_code'] = df_daily_all['st_code'].astype(str)

        df_golden_cross_60m['trade_date'] = pd.to_datetime(df_golden_cross_60m['trade_date']).dt.date
        df_golden_cross_daily['trade_date'] = pd.to_datetime(df_golden_cross_daily['trade_date']).dt.date
        df_daily_all['trade_date'] = pd.to_datetime(df_daily_all['trade_date']).dt.date

        results = []

        daily_group = df_golden_cross_daily.groupby('st_code')

        for idx, row in df_golden_cross_60m.iterrows():
            stock = str(row['stock_code'])
            cross_date_60m = row['trade_date']

            match_info = {
                'stock_code': stock,
                'golden_cross_date_60m': cross_date_60m,
                'macd_60m': row.get('macd', np.nan),
                'pre_macd_60m': row.get('pre_macd', np.nan),
                'is_matched': False,
                'golden_cross_date_daily': None,
                'days_to_daily_cross': None,
                'price_at_60m_cross': row.get('close', np.nan),
                'price_at_daily_cross': None,
                'return_rate': None,
            }

            if stock in daily_group.groups:
                daily_crosses = daily_group.get_group(stock)
                future_crosses = daily_crosses[daily_crosses['trade_date'] > cross_date_60m]
                if not future_crosses.empty:
                    first_cross = future_crosses.sort_values('trade_date').iloc[0]
                    match_info['is_matched'] = True
                    match_info['golden_cross_date_daily'] = first_cross['trade_date']
                    match_info['days_to_daily_cross'] = (first_cross['trade_date'] - cross_date_60m).days

                    # 价格/收益率
                    daily_price_row = df_daily_all[
                        (df_daily_all['st_code'] == stock) & (df_daily_all['trade_date'] == first_cross['trade_date'])
                    ]
                    if not daily_price_row.empty and 'close' in daily_price_row.columns:
                        match_info['price_at_daily_cross'] = float(daily_price_row.iloc[0]['close'])
                        if pd.notna(match_info['price_at_60m_cross']) and match_info['price_at_60m_cross'] != 0:
                            match_info['return_rate'] = (match_info['price_at_daily_cross'] - match_info['price_at_60m_cross']) / match_info['price_at_60m_cross']

            results.append(match_info)

        df_results = pd.DataFrame(results)
        self.matched_results = df_results
        return df_results

    def analyze_complete_results(self, df_all_results):
        """
        分析完整匹配结果
        """
        self.log("\n步骤5: 分析完整结果.")
        if df_all_results.empty:
            return {}

        total = len(df_all_results)
        matched = int(df_all_results['is_matched'].sum())
        unmatched = total - matched
        success_rate = matched / total if total else 0

        analysis = {
            'total_60m_crosses': total,
            'matched_count': matched,
            'unmatched_count': unmatched,
            'match_success_rate': success_rate
        }

        # days distribution
        if matched > 0 and 'days_to_daily_cross' in df_all_results.columns:
            matched_df = df_all_results[df_all_results['is_matched'] == True].copy()
            analysis['days_to_daily_cross_stats'] = matched_df['days_to_daily_cross'].describe().to_dict()

        self.analysis_result = analysis
        return analysis

    def export_complete_results(self, df_all_results, filename=None):
        """
        导出完整匹配结果
        """
        if df_all_results.empty:
            self.log("没有匹配结果可供导出")
            return None

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"macd_golden_cross_complete_{timestamp}.csv"
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

    def export_unmatched_results(self, df_all_results, filename=None):
        """
        导出未匹配成功的60分钟金叉数据
        """
        if df_all_results.empty:
            self.log("没有匹配结果可供导出")
            return None

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
            columns_to_export = ['stock_code', 'golden_cross_date_60m', 'macd_60m', 'pre_macd_60m']
            df_unmatched[columns_to_export].to_csv(filename, index=False, encoding='utf-8-sig')
            self.log(f"\n未匹配的60分钟金叉数据已导出到: {filename}")
            self.log(f"导出记录数: {len(df_unmatched)}")
            return filename
        except Exception as e:
            self.log(f"导出未匹配数据过程中发生错误: {str(e)}")
            return None

    def add_macd_score_to_daily_data(self, df_60m, df_daily):
        """
        给日线数据添加MACD分数列：
        - 所有60分钟金叉都可以进行打分
        - 但排除那些在日线当天也形成金叉的情况（避免未来数据泄漏）
        - 对符合条件的60分钟金叉给予固定分数（如80分）
        - 新增：MACD否决过滤（顶部动能回落过滤）
        """
        self.log("\n步骤X: 为日线数据添加MACD打分...")

        # 1. 找到60分钟金叉
        df_golden_cross_60m = self.find_golden_cross_60m_vectorized(df_60m, df_daily)

        # 2. 找到日线金叉
        df_golden_cross_daily = self.find_golden_cross_daily_vectorized(df_daily)

        # 3. 准备数据用于匹配
        df_60m_crosses = df_golden_cross_60m[['stock_code', 'trade_date']].copy()
        df_daily_crosses = df_golden_cross_daily[['st_code', 'trade_date']].copy()

        # 4. 确保股票代码和日期格式统一
        df_60m_crosses['stock_code'] = df_60m_crosses['stock_code'].astype(str)
        df_daily_crosses['st_code'] = df_daily_crosses['st_code'].astype(str)
        df_daily['st_code'] = df_daily['st_code'].astype(str)

        df_60m_crosses['trade_date'] = pd.to_datetime(df_60m_crosses['trade_date']).dt.date
        df_daily_crosses['trade_date'] = pd.to_datetime(df_daily_crosses['trade_date']).dt.date
        df_daily['trade_date'] = pd.to_datetime(df_daily['trade_date']).dt.date

        # 5. 找出在同一天既有60分钟金叉又有日线金叉的记录（需要排除的）
        same_day_crosses = pd.merge(
            df_60m_crosses,
            df_daily_crosses.rename(columns={'st_code': 'stock_code'}),
            on=['stock_code', 'trade_date'],
            how='inner'
        )

        print(f"需要排除的当日同时金叉记录数: {len(same_day_crosses)}")

        # 6. 从60分钟金叉中排除当日也形成日线金叉的记录
        df_60m_crosses_filtered = df_60m_crosses.merge(
            same_day_crosses,
            on=['stock_code', 'trade_date'],
            how='left',
            indicator=True
        )

        df_60m_crosses_only = df_60m_crosses_filtered[
            df_60m_crosses_filtered['_merge'] == 'left_only'
        ][['stock_code', 'trade_date']].copy()

        print(f"过滤后的60分钟金叉记录数: {len(df_60m_crosses_only)} (原始: {len(df_60m_crosses)})")

        # 7. 为过滤后的60分钟金叉准备打分数据
        matched_days = df_60m_crosses_only.copy()
        matched_days.rename(columns={'stock_code': 'st_code'}, inplace=True)

        # 8. 添加固定分数（例如80分）
        matched_days['match_score'] = 80

        # 9. 初始化日线数据中的MACD列为-1
        df_daily = df_daily.copy()
        df_daily['MACD'] = -1

        # 10. 将匹配分数合并到日线数据中
        df_daily = df_daily.merge(
            matched_days[['st_code', 'trade_date', 'match_score']],
            on=['st_code', 'trade_date'],
            how='left'
        )

        # 11. 更新MACD分数，如果匹配到则使用match_score，否则保持-1
        df_daily['MACD'] = df_daily['match_score'].fillna(df_daily['MACD']).astype(int)
        df_daily.drop(columns=['match_score'], inplace=True)

        # 11.5 应用MACD否决过滤（避免顶部附近动能回落导致短期回调即止损）
        df_daily = self.apply_macd_veto(df_daily, lookback=2)
        if 'macd_veto' in df_daily.columns:
            veto_count = int(df_daily['macd_veto'].sum())
            if veto_count > 0:
                print(f"MACD否决过滤触发数: {veto_count}，这些记录的MACD分数将被重置为-1")
            df_daily.loc[df_daily['macd_veto'] == True, 'MACD'] = -1

        # 12. 只返回需要的列（兼容不同来源的日线数据）
        required_cols = [
            'st_code', 'trade_date', 'open', 'high', 'low', 'close',
            'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci',
            'macd_macd', 'pre_macd_macd', 'MACD'
        ]
        # 兼容不同来源的日线数据：只选择存在的列，避免KeyError
        required_cols = [c for c in required_cols if c in df_daily.columns]
        result_df = df_daily[required_cols].copy()

        # 13. 打印 MACD 大于 0 的记录
        macd_positive_records = result_df[result_df['MACD'] > 0]
        if not macd_positive_records.empty:
            print(f"\n最终返回的df中MACD大于0的记录数: {len(macd_positive_records)}")
            print("MACD大于0的前10条记录:")
            print(macd_positive_records.head(10).to_string(index=False))
        else:
            print("最终返回的df中没有MACD大于0的记录")

        return result_df

    def run_complete_analysis(self, start_date=None, end_date=None, export_results=True):
        """
        运行完整的分析流程
        """
        total_start_time = datetime.now()

        self.log("=" * 100)
        self.log("MACD金叉完整匹配分析 - 修正版本")
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
            df_60m, df_daily = self.load_data(start_date, end_date)
            if df_60m.empty:
                self.log("60分钟数据为空")
                return result

            # 步骤2: 识别60分钟金叉
            df_golden_cross_60m = self.find_golden_cross_60m_vectorized(df_60m, df_daily)
            if df_golden_cross_60m.empty:
                self.log("未找到60分钟MACD金叉数据")
                return result

            # 步骤3: 识别日线金叉
            df_golden_cross_daily = self.find_golden_cross_daily_vectorized(df_daily)

            # 步骤4: 完整匹配所有60分钟金叉
            df_all_results = self.match_golden_cross_complete(df_golden_cross_60m, df_golden_cross_daily, df_daily)
            result['all_results'] = df_all_results

            # 步骤5: 分析完整结果
            analysis_result = self.analyze_complete_results(df_all_results)
            result['analysis_result'] = analysis_result

            # 步骤6: 导出结果
            if export_results:
                export_file = self.export_complete_results(df_all_results)
                result['export_file'] = export_file
                self.export_unmatched_results(df_all_results)

            result['success'] = True

            total_end_time = datetime.now()
            total_processing_time = (total_end_time - total_start_time).total_seconds()
            result['processing_time'] = total_processing_time

            self.log("\n" + "=" * 100)
            self.log("完整分析完成!")
            self.log("=" * 100)
            self.log(f"总处理时间: {total_processing_time:.2f}秒")
            self.log(f"60分钟金叉总数: {len(df_all_results)}")
            self.log(f"匹配成功数: {len(df_all_results[df_all_results['is_matched'] == True])}")

            return result

        except Exception as e:
            error_msg = f"分析过程中发生错误: {str(e)}"
            result['error_message'] = error_msg
            self.log(f"\n错误: {error_msg}")
            import traceback
            traceback.print_exc()
            return result


def main():
    """
    主函数 - 示例用法
    """
    print("MACD金叉完整匹配分析器 - 修正版本")
    print("=" * 50)

    matcher = MACDGoldenCrossMatcher(debug=True)

    print("\n运行完整分析.")
    result = matcher.run_complete_analysis(
        start_date='20250101',
        end_date='20250902',
        export_results=True
    )

    if result['success']:
        print("\n分析成功完成!")
        print(f"总处理时间: {result['processing_time']:.2f}秒")
        print("分析结果摘要:")
        for key, value in result['analysis_result'].items():
            print(f"  {key}: {value}")
    else:
        print(f"\n分析失败: {result['error_message']}")


if __name__ == "__main__":
    main()
