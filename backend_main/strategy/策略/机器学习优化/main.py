# -*- coding: utf-8 -*-
"""
优化版股票筛选系统主程序
整合了所有功能模块，提供完整的股票筛选流程
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import glob

# 导入自定义模块
from database import DatabaseManager
from sequence_extractor import SequenceExtractor
from sequence_clustering import SequenceClustering
from stock_matcher import StockMatcher
from config import *


class StockScreeningSystem:
    def __init__(self):
        """初始化股票筛选系统"""
        self.db_manager = DatabaseManager()
        self.sequence_extractor = SequenceExtractor(
            window_size=WINDOW_SIZE,
            observation_days=OBSERVATION_DAYS,
            target_gain=TARGET_GAIN
        )
        self.sequence_clustering = SequenceClustering()
        self.stock_matcher = None
        self.clustering_results = {}

        print("=" * 60)
        print("优化版股票筛选系统")
        print("=" * 60)
        print(f"特征字段数: {len(FEATURE_COLUMNS)}")
        print(f"特征字段: {', '.join(FEATURE_COLUMNS)}")
        print(f"窗口大小: {WINDOW_SIZE} 天")
        print(f"观察期: {OBSERVATION_DAYS} 天")
        print(f"目标涨幅: {TARGET_GAIN:.1%}")
        print(f"匹配阈值: {MATCH_THRESHOLD:.1%}")
        print(f"训练数据表: {TRAINING_DATA_TABLE}")
        print(f"当前数据表: {STOCK_DATA_TABLE}")
        print("=" * 60)

    def test_system(self):
        """测试系统连接和基本功能"""
        print("\n🔍 测试系统连接...")

        # 测试数据库连接
        if not self.db_manager.test_connection():
            print("❌ 数据库连接失败！")
            return False

        # 获取数据统计信息
        print("\n📊 获取数据统计信息...")
        stats = self.db_manager.get_data_statistics()
        if stats:
            print(f"总记录数: {stats['total_records']}")
            print(f"股票数量: {stats['stock_count']}")
            print(f"数据范围: {stats['date_range']['start']} 到 {stats['date_range']['end']}")
            print(f"特征统计: {len(stats['feature_stats'])} 个字段")
        else:
            print("❌ 无法获取数据统计信息")
            return False

        print("✅ 系统测试通过！")
        return True

    def extract_training_sequences(self, start_date=None, end_date=None):
        """
        提取训练序列（优化版）- 使用大表数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            list: 提取的序列列表
        """
        print(f"\n🔍 提取训练序列（使用大表数据）...")
        print(f"时间范围: {start_date} 到 {end_date}")

        # 获取训练数据（从大表）
        stock_data = self.db_manager.get_training_data(start_date, end_date)
        if stock_data.empty:
            print("❌ 没有获取到训练数据")
            return []

        # 提取序列
        sequences = self.sequence_extractor.extract_sequences(stock_data)

        if sequences:
            print(f"✅ 成功提取 {len(sequences)} 个训练序列")

            # 保存序列到文件
            filename = f"extracted_sequences_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.sequence_extractor.save_sequences_to_file(sequences, filename)

            # 显示序列统计信息
            stats = self.sequence_extractor.get_sequence_statistics(sequences)
            if stats:
                print(f"\n📊 序列统计信息:")
                print(f"  总序列数: {stats['total_sequences']}")
                print(f"  涉及股票数: {stats['unique_stocks']}")
                print(f"  平均涨幅: {stats['gain_statistics']['mean']:.2%}")
                print(f"  涨幅标准差: {stats['gain_statistics']['std']:.2%}")
                print(f"  最小涨幅: {stats['gain_statistics']['min']:.2%}")
                print(f"  最大涨幅: {stats['gain_statistics']['max']:.2%}")
        else:
            print("❌ 没有提取到符合条件的序列")

        return sequences

    def train_clustering_model(self, sequences):
        """
        训练聚类模型（优化版）

        Args:
            sequences: 训练序列列表

        Returns:
            dict: 聚类结果
        """
        if not sequences:
            print("❌ 没有序列数据，无法训练聚类模型")
            return {}

        print(f"\n🎯 训练聚类模型...")
        print(f"输入序列数: {len(sequences)}")

        # 执行聚类
        clustering_results = self.sequence_clustering.cluster_sequences(sequences)

        if clustering_results:
            print(f"✅ 聚类训练完成，生成 {len(clustering_results)} 个通用序列模式")

            # 保存聚类结果
            filename = f"clustering_results_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.sequence_clustering.save_clustering_results(clustering_results, filename)

            # 显示聚类统计信息
            total_sequences = sum(len(cluster['sequences']) for cluster in clustering_results.values())
            avg_success_rate = np.mean([cluster['success_rate'] for cluster in clustering_results.values()])
            avg_gain = np.mean([cluster['avg_gain'] for cluster in clustering_results.values()])

            print(f"\n📊 聚类统计信息:")
            print(f"  总序列数: {total_sequences}")
            print(f"  聚类数量: {len(clustering_results)}")
            print(f"  平均成功率: {avg_success_rate:.2%}")
            print(f"  平均涨幅: {avg_gain:.2%}")

            # 保存聚类结果到实例变量
            self.clustering_results = clustering_results

            return clustering_results
        else:
            print("❌ 聚类训练失败")
            return {}

    def match_current_stocks(self, start_date=None, end_date=None):
        """
        匹配当前股票（优化版）

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 匹配结果，包含股票代码、日期、价格信息和分数
        """
        if not self.clustering_results:
            print("❌ 请先训练聚类模型")
            return pd.DataFrame()

        # 设置默认日期
        if start_date is None:
            start_date = '2025-04-02'
        if end_date is None:
            end_date = '2025-04-15'

        print(f"正在获取 {start_date} 到 {end_date} 的股票数据...")

        # 获取当前股票数据（从partition_table）
        current_stock_data = self.db_manager.get_stock_data(start_date, end_date)

        if current_stock_data.empty:
            print("❌ 没有获取到当前股票数据")
            return pd.DataFrame()

        print(f"成功获取 {len(current_stock_data)} 条股票数据")

        # 按股票分组
        stock_groups = current_stock_data.groupby('st_code')
        stock_data_dict = {}

        for stock_code, group in stock_groups:
            if len(group) >= WINDOW_SIZE:
                stock_data_dict[stock_code] = group

        if not stock_data_dict:
            print("❌ 没有股票有足够的数据")
            return pd.DataFrame()

        print(f"找到 {len(stock_data_dict)} 只有足够数据的股票")
        print("开始批量匹配...")

        # 创建股票匹配器
        self.stock_matcher = StockMatcher(self.clustering_results, MATCH_THRESHOLD)

        # 执行批量匹配
        match_results = self.stock_matcher.batch_match_stocks(stock_data_dict)

        if not match_results:
            print("❌ 没有找到匹配的股票")
            return pd.DataFrame()

        print(f"✅ 匹配完成，共找到 {len(match_results)} 个匹配结果")

        # 转换为DataFrame格式
        result_data = []
        for result in match_results:
            stock_code = result['stock_code']
            # 获取该股票的最新数据
            stock_data = stock_data_dict[stock_code].iloc[-1] if stock_code in stock_data_dict else None

            if stock_data is not None:
                row = {
                    'st_code': stock_code,
                    'trade_date': stock_data['trade_date'],
                    'open': stock_data.get('open', 0),
                    'high': stock_data.get('high', 0),
                    'low': stock_data.get('low', 0),
                    'close': stock_data.get('close', 0),
                    'pre_close': stock_data.get('pre_close', 0),
                    'pct_chg': stock_data.get('pct_chg', 0),
                    'vol': stock_data.get('vol', 0),
                    'cci': stock_data.get('cci', 0),
                    'pre_cci': stock_data.get('pre_cci', 0),
                    'macd_macd': stock_data.get('macd_macd', 0),
                    'pre_macd_macd': stock_data.get('pre_macd_macd', 0),
                    'score': result['final_score']
                }
                result_data.append(row)

        # 创建DataFrame并按分数排序
        result_df = pd.DataFrame(result_data)
        if not result_df.empty:
            result_df = result_df.sort_values('score', ascending=False)

        return result_df

    def run_complete_pipeline(self, training_start_date=None, training_end_date=None,
                              current_start_date=None, current_end_date=None):
        """
        运行完整的股票筛选流程（优化版）

        Args:
            training_start_date: 训练数据开始日期（从大表获取）
            training_end_date: 训练数据结束日期（从大表获取）
            current_start_date: 当前数据开始日期（从partition_table获取）
            current_end_date: 当前数据结束日期（从partition_table获取）

        Returns:
            DataFrame: 匹配结果，包含股票代码、日期、价格信息和分数
        """
        print("\n" + "=" * 60)
        print("🚀 开始运行完整股票筛选流程")
        print("=" * 60)

        # 步骤1: 系统测试
        if not self.test_system():
            print("❌ 系统测试失败，流程终止")
            return pd.DataFrame()

        # 步骤2: 提取训练序列（使用大表）
        training_sequences = self.extract_training_sequences(training_start_date, training_end_date)
        if not training_sequences:
            print("❌ 训练序列提取失败，流程终止")
            return pd.DataFrame()

        # 步骤3: 训练聚类模型
        clustering_results = self.train_clustering_model(training_sequences)
        if not clustering_results:
            print("❌ 聚类模型训练失败，流程终止")
            return pd.DataFrame()

        # 步骤4: 匹配当前股票（使用partition_table）
        result_df = self.match_current_stocks(current_start_date, current_end_date)
        if result_df.empty:
            print("❌ 股票匹配失败，流程终止")
            return pd.DataFrame()

        print("\n" + "=" * 60)
        print("🎉 完整流程执行成功！")
        print("=" * 60)
        print(f"训练序列数: {len(training_sequences)}")
        print(f"聚类模式数: {len(clustering_results)}")
        print(f"匹配结果数: {len(result_df)}")

        return result_df

    def run_demo(self):
        """
        运行演示模式

        Returns:
            DataFrame: 匹配结果，包含股票代码、日期、价格信息和分数
        """
        print("\n🎬 运行演示模式...")

        # 设置演示参数
        training_start_date = '2025-01-01'
        training_end_date = '2025-03-01'
        current_start_date = '2025-03-02'
        current_end_date = '2025-04-15'

        print(f"训练数据（大表）: {training_start_date} 到 {training_end_date}")
        print(f"当前数据（partition_table）: {current_start_date} 到 {current_end_date}")

        # 运行完整流程
        result_df = self.run_complete_pipeline(
            training_start_date, training_end_date,
            current_start_date, current_end_date
        )

        if result_df.empty:
            print("\n❌ 演示模式运行失败！")
        else:
            print("\n✅ 演示模式运行成功！")

        return result_df

    def run_custom_pipeline(self):
        """
        运行自定义参数流程

        Returns:
            DataFrame: 匹配结果，包含股票代码、日期、价格信息和分数
        """
        try:
            print("请输入训练数据时间范围（大表）:")
            training_start = input("训练开始日期 (YYYY-MM-DD): ").strip()
            training_end = input("训练结束日期 (YYYY-MM-DD): ").strip()

            print("请输入当前数据时间范围（partition_table）:")
            current_start = input("当前开始日期 (YYYY-MM-DD): ").strip()
            current_end = input("当前结束日期 (YYYY-MM-DD): ").strip()

            # 验证日期格式
            for date_str in [training_start, training_end, current_start, current_end]:
                datetime.strptime(date_str, '%Y-%m-%d')

            # 运行流程
            result_df = self.run_complete_pipeline(
                training_start, training_end,
                current_start, current_end
            )

            return result_df

        except ValueError:
            print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            return pd.DataFrame()
        except KeyboardInterrupt:
            print("\n❌ 用户取消操作")
            return pd.DataFrame()

    def show_menu(self):
        """显示主菜单"""
        while True:
            print("\n" + "=" * 60)
            print("📋 优化版股票筛选系统主菜单")
            print("=" * 60)
            print("1. 系统测试")
            print("2. 提取训练序列（大表）")
            print("3. 训练聚类模型")
            print("4. 匹配当前股票（partition_table）")
            print("5. 运行完整流程")
            print("6. 运行演示模式")
            print("7. 自定义参数运行")
            print("0. 退出系统")
            print("=" * 60)

            try:
                choice = input("请选择操作 (0-7): ").strip()

                if choice == '0':
                    print("👋 感谢使用，再见！")
                    break
                elif choice == '1':
                    self.test_system()
                elif choice == '2':
                    start_date = input("开始日期 (YYYY-MM-DD): ").strip()
                    end_date = input("结束日期 (YYYY-MM-DD): ").strip()
                    self.extract_training_sequences(start_date, end_date)
                elif choice == '3':
                    if hasattr(self, 'training_sequences'):
                        self.train_clustering_model(self.training_sequences)
                    else:
                        print("❌ 请先提取训练序列")
                elif choice == '4':
                    if not self.clustering_results:
                        print("❌ 请先训练聚类模型")
                    else:
                        start_date = input("开始日期 (YYYY-MM-DD): ").strip()
                        end_date = input("结束日期 (YYYY-MM-DD): ").strip()
                        result_df = self.match_current_stocks(start_date, end_date)
                        if not result_df.empty:
                            print(f"\n匹配结果预览（前5条）:")
                            print(result_df.head())
                elif choice == '5':
                    result_df = self.run_complete_pipeline()
                    if not result_df.empty:
                        print(f"\n完整流程结果预览（前5条）:")
                        print(result_df.head())
                elif choice == '6':
                    result_df = self.run_demo()
                    if not result_df.empty:
                        print(f"\n演示模式结果预览（前5条）:")
                        print(result_df.head())
                elif choice == '7':
                    result_df = self.run_custom_pipeline()
                    if not result_df.empty:
                        print(f"\n自定义流程结果预览（前5条）:")
                        print(result_df.head())
                else:
                    print("❌ 无效选择，请重新输入")

            except KeyboardInterrupt:
                print("\n❌ 用户取消操作")
                break
            except Exception as e:
                print(f"❌ 操作失败: {e}")

    def load_sequences_from_file(self, filename):
        """
        从txt文件加载序列数据

        Args:
            filename: 序列文件名

        Returns:
            list: 序列列表
        """
        try:
            print(f"📖 从文件加载序列: {filename}")

            # 检查文件是否存在
            if not os.path.exists(filename):
                print(f"❌ 文件不存在: {filename}")
                return []

            # 查找最新的序列文件
            if filename == 'auto':
                files = glob.glob('extracted_sequences_*.txt')
                if not files:
                    print("❌ 没有找到序列文件")
                    return []
                filename = max(files, key=os.path.getctime)
                print(f"🔍 自动选择最新文件: {filename}")

            sequences = []
            current_sequence = {}

            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 解析文件内容
            for line in lines:
                line = line.strip()

                if line.startswith('序列ID:'):
                    if current_sequence:
                        sequences.append(current_sequence)
                    current_sequence = {'sequence_id': line.split(':', 1)[1].strip()}

                elif line.startswith('股票代码:'):
                    current_sequence['stock_code'] = line.split(':', 1)[1].strip()

                elif line.startswith('窗口期:'):
                    dates = line.split(':', 1)[1].strip()
                    if ' 到 ' in dates:
                        start_date, end_date = dates.split(' 到 ')
                        current_sequence['start_date'] = start_date
                        current_sequence['end_date'] = end_date

                elif line.startswith('观察期:'):
                    dates = line.split(':', 1)[1].strip()
                    if ' 到 ' in dates:
                        start_date, end_date = dates.split(' 到 ')
                        current_sequence['observation_start'] = start_date
                        current_sequence['observation_end'] = end_date

                elif line.startswith('累计涨幅:'):
                    gain_str = line.split(':', 1)[1].strip().rstrip('%')
                    try:
                        current_sequence['total_gain'] = float(gain_str) / 100
                    except ValueError:
                        current_sequence['total_gain'] = 0.0

            # 添加最后一个序列
            if current_sequence:
                sequences.append(current_sequence)

            print(f"✅ 成功加载 {len(sequences)} 个序列信息")

            # 重新提取特征数据
            print("🔄 重新提取特征数据...")
            sequences_with_features = self._reconstruct_sequences(sequences)

            return sequences_with_features

        except Exception as e:
            print(f"❌ 加载序列文件失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _reconstruct_sequences(self, sequence_info_list):
        """
        重新构建完整的序列数据（包含特征向量）

        Args:
            sequence_info_list: 从文件加载的序列信息列表

        Returns:
            list: 完整的序列列表
        """
        try:
            print("🔄 重新构建序列特征...")

            # 获取训练数据
            all_stock_data = self.db_manager.get_training_data()
            if all_stock_data.empty:
                print("❌ 无法获取训练数据来重建特征")
                return []

            reconstructed_sequences = []

            for seq_info in sequence_info_list:
                stock_code = seq_info.get('stock_code')
                start_date = seq_info.get('start_date')
                end_date = seq_info.get('end_date')

                if not all([stock_code, start_date, end_date]):
                    continue

                # 获取该股票在指定时间范围的数据
                stock_data = all_stock_data[
                    (all_stock_data['st_code'] == stock_code) &
                    (all_stock_data['trade_date'] >= start_date) &
                    (all_stock_data['trade_date'] <= end_date)
                    ].sort_values('trade_date')

                if len(stock_data) >= WINDOW_SIZE:
                    # 重新创建序列
                    sequence = self.sequence_extractor._create_sequence(
                        stock_data, stock_code, seq_info.get('total_gain', 0.0)
                    )
                    if sequence:
                        reconstructed_sequences.append(sequence)

            print(f"✅ 成功重建 {len(reconstructed_sequences)} 个完整序列")
            return reconstructed_sequences

        except Exception as e:
            print(f"❌ 重建序列失败: {e}")
            return []

    def run_from_sequence_file(self, filename='auto'):
        """
        从序列文件直接运行后续步骤

        Args:
            filename: 序列文件名，'auto'表示自动选择最新文件

        Returns:
            DataFrame: 匹配结果
        """
        print("🚀 从序列文件开始运行...")

        # 步骤1：加载序列文件
        sequences = self.load_sequences_from_file(filename)

        if not sequences:
            print("❌ 无法加载序列数据，程序终止")
            return pd.DataFrame()

        # 步骤2：训练聚类模型
        clustering_results = self.train_clustering_model(sequences)

        if not clustering_results:
            print("❌ 聚类训练失败，程序终止")
            return pd.DataFrame()

        # 步骤3：匹配当前股票
        df = self.match_current_stocks()

        return df

    def find_sequence_files(self):
        """
        查找所有可用的序列文件

        Returns:
            list: 文件列表
        """
        files = glob.glob('extracted_sequences_*.txt')
        if not files:
            # 尝试其他可能的模式
            files = glob.glob('*sequences*.txt')

        return files


def run_stock_screening(training_start_date='2025-01-01', training_end_date='2025-04-01',
                        current_start_date='2025-04-02', current_end_date='2025-04-15'):
    """
    股票筛选系统主接口函数

    Args:
        training_start_date: 训练数据开始日期（从大表获取）
        training_end_date: 训练数据结束日期（从大表获取）
        current_start_date: 当前数据开始日期（从partition_table获取）
        current_end_date: 当前数据结束日期（从partition_table获取）

    Returns:
        DataFrame: 匹配结果，包含以下列：
        ['st_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close',
         'pct_chg', 'vol', 'cci', 'pre_cci', 'macd_macd', 'pre_macd_macd', 'score']
    """
    try:
        # 创建系统实例
        system = StockScreeningSystem()

        # 运行完整流程
        result_df = system.run_complete_pipeline(
            training_start_date, training_end_date,
            current_start_date, current_end_date
        )

        return result_df

    except Exception as e:
        print(f"股票筛选系统运行失败: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def main():
    """主函数"""
    try:
        # 创建系统实例
        system = StockScreeningSystem()

        # 显示菜单
        system.show_menu()

    except Exception as e:
        print(f"❌ 系统运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
