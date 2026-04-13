# -*- coding: utf-8 -*-
"""
股票匹配模块 - 趋势模式聚类版本适配
包含所有股票匹配功能，可以直接调用已保存的肘部法则聚类模型
"""

import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
import json
import glob
import warnings
warnings.filterwarnings('ignore')

# JSON序列化辅助函数
def convert_numpy_types(obj):
    """递归转换numpy数据类型为Python原生类型，用于JSON序列化"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

# 科学计算库
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.signal import find_peaks
from scipy.stats import entropy

# 数据库配置
try:
    from sqlalchemy import create_engine, text, inspect
    import pymysql
except ImportError:
    print("警告: 数据库库未安装，请安装 sqlalchemy 和 pymysql")

# 配置参数（与data_preprocessing_elbow.py保持一致）
WINDOW_SIZE = 60              # 滑动窗口大小
OBSERVATION_DAYS = 5          # 观察期天数
MATCH_THRESHOLD = 0.15        # 匹配度阈值（大幅降低，让更多股票匹配成功）
MIN_SAMPLE_SIZE = 10         # 最小样本数量

# ==================== 日期配置区域 ====================
# 在这里修改你的匹配日期范围
MATCH_START_DATE = '2024-06-03'    # 匹配开始日期 (YYYY-MM-DD)
MATCH_END_DATE = '2025-08-15'      # 匹配结束日期 (YYYY-MM-DD)
# 或者设置为动态日期（最近N天）
USE_DYNAMIC_DATES = False          # True: 使用动态日期, False: 使用固定日期
DYNAMIC_DAYS = 30                  # 如果使用动态日期，匹配最近多少天
# ===================================================

# 数据库配置
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'jdgp'

# 数据库表名（与data_preprocessing_elbow.py保持一致）
STOCK_DATA_TABLE = 'partition_table'      # 当前股票数据表（用于匹配）

# 相似度匹配配置（适配趋势模式特征）
SIMILARITY_CONFIG = {
    'cosine': 0.25,                # 余弦相似度权重
    'euclidean': 0.20,             # 欧氏距离相似度权重
    'manhattan': 0.15,             # 曼哈顿距离相似度权重
    'pearson': 0.15,               # 皮尔逊相关系数权重
    'trend_pattern': 0.15,         # 趋势模式特征相似度权重
    'price_path': 0.10             # 价格路径和波动特征相似度权重
}

# 最终评分配置（从config.py整合）
SCORING_CONFIG = {
    'match_weight': 0.5,                  # 匹配分数权重
    'success_weight': 0.3,                # 成功分数权重
    'stability_weight': 0.2,              # 稳定性分数权重
    'stability_method': 'inverse_std'     # 稳定性计算方法
}

class DatabaseManager:
    """数据库管理类 - 整合版本"""
    
    def __init__(self):
        """初始化数据库管理器"""
        try:
            self.engine = create_engine(
                f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
            )
            print("✅ 数据库连接初始化成功")
        except Exception as e:
            print(f"❌ 数据库连接初始化失败: {e}")
            self.engine = None
        
    def test_connection(self):
        """测试数据库连接"""
        try:
            if not self.engine:
                return False
                
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("✅ 数据库连接成功！")
                return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False
        
    def get_stock_data(self, stock_code, start_date, end_date):
        """获取股票数据"""
        try:
            if not self.engine:
                print("❌ 数据库未连接")
                return pd.DataFrame()
            
            # 构建查询 - 获取所有需要的列
            query = f"""
            SELECT st_code, trade_date, open, high, low, close, 
                   pct_chg, vol, cci, macd_macd, macd_dif
            FROM {STOCK_DATA_TABLE}
            WHERE st_code = %(stock_code)s 
            AND trade_date BETWEEN %(start_date)s AND %(end_date)s
            ORDER BY trade_date
            """
            
            # 执行查询
            # df = pd.read_sql(query, self.engine, params={...})
            import strategy.mysql_connect as sc
            df = sc.safe_read_sql(query, params={
                'stock_code': stock_code,
                'start_date': start_date,
                'end_date': end_date
            })
            
            if not df.empty:
                # 重命名列以匹配代码中的期望
                df = df.rename(columns={
                    'st_code': 'stock_code',
                    'vol': 'volume'
                })
                
                print(f"✅ 获取股票 {stock_code} 数据: {len(df)} 条记录")
                return df
            else:
                print(f"⚠️ 股票 {stock_code} 在指定日期范围内没有数据")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 获取股票 {stock_code} 数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self, start_date=None, end_date=None):
        """获取股票列表"""
        try:
            if not self.engine:
                print("❌ 数据库未连接")
                return []
            
            # 构建查询条件
            conditions = ["1=1"]
            params = {}
            
            if start_date:
                conditions.append("trade_date >= %(start_date)s")
                params['start_date'] = start_date
            
            if end_date:
                conditions.append("trade_date <= %(end_date)s")
                params['end_date'] = end_date
            
            # 从数据表获取股票代码列表
            query = f"""
            SELECT DISTINCT st_code 
            FROM {STOCK_DATA_TABLE} 
            WHERE {' AND '.join(conditions)}
            ORDER BY st_code
            """
            
            import strategy.mysql_connect as sc
            df = sc.safe_read_sql(query, params=params)
            stock_list = df['st_code'].tolist()
            print(f"✅ 从数据库获取到 {len(stock_list)} 只股票")
            return stock_list
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []

class StandaloneStockMatcher:
    """独立股票匹配器"""
    
    def __init__(self, clustering_results_file=None, match_threshold=MATCH_THRESHOLD):
        """
        初始化独立股票匹配器
        
        Args:
            clustering_results_file: 肘部法则聚类结果文件路径，如果为None则自动查找
            match_threshold: 匹配度阈值
        """
        self.match_threshold = match_threshold
        self.scaler = StandardScaler()
        self.matching_stats = {}
        self.clustering_results = {}
        self.db_manager = DatabaseManager()
        
        # 测试数据库连接
        if not self.db_manager.test_connection():
            print("⚠️ 数据库连接失败，将无法获取真实数据")
        
        # 加载肘部法则聚类结果
        if clustering_results_file:
            self.load_clustering_results(clustering_results_file)
        else:
            self._auto_load_clustering_results()
    
    def _auto_load_clustering_results(self):
        """自动查找并加载最新的趋势模式聚类结果文件"""
        try:
            # 查找趋势模式聚类结果文件（支持多种命名格式）
            clustering_files = []
            
            # 查找data_preprocessing_elbow.py生成的文件
            clustering_files.extend(glob.glob('clustering_results_trend_pattern_*.pkl'))
            
            # 查找其他可能的聚类结果文件
            clustering_files.extend(glob.glob('clustering_results_*.pkl'))
            
            if not clustering_files:
                print("❌ 没有找到聚类结果文件")
                print("💡 请先运行 data_preprocessing_elbow.py 生成聚类结果")
                return
            
            # 选择最新的文件
            latest_file = max(clustering_files, key=os.path.getctime)
            print(f"🔍 自动找到聚类结果文件: {latest_file}")
            
            self.load_clustering_results(latest_file)
            
        except Exception as e:
            print(f"❌ 自动加载聚类结果失败: {e}")
    
    def load_clustering_results(self, filename):
        """从文件加载肘部法则聚类结果"""
        try:
            if not os.path.exists(filename):
                print(f"❌ 文件不存在: {filename}")
                return False
            
            with open(filename, 'rb') as f:
                self.clustering_results = pickle.load(f)
            
            print(f"✅ 成功加载肘部法则聚类结果: {filename}")
            print(f"   聚类数量: {len(self.clustering_results)}")
            
            # 验证聚类结果格式
            if self.clustering_results:
                sample_cluster = list(self.clustering_results.values())[0]
                if 'center_features' in sample_cluster:
                    feature_dim = len(sample_cluster['center_features'])
                    if feature_dim != 14:
                        print(f"⚠️ 警告: 特征维度为 {feature_dim}，期望为 14（趋势模式特征）")
                    else:
                        print(f"✅ 特征维度正确: {feature_dim}（趋势模式特征）")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载趋势模式聚类结果失败: {e}")
            return False
    
    def match_single_stock(self, stock_data, stock_code):
        """匹配单只股票"""
        if self.clustering_results is None or not self.clustering_results:
            print("❌ 没有加载趋势模式聚类结果，无法进行匹配")
            return None
        
        if len(stock_data) < WINDOW_SIZE:
            print(f"股票 {stock_code} 数据不足 {WINDOW_SIZE} 天")
            return None
        
        try:
            # 提取最近WINDOW_SIZE天的数据
            recent_data = stock_data.tail(WINDOW_SIZE)
            
            # 准备趋势特征
            trend_features = self._prepare_trend_features(recent_data)
            if trend_features is None:
                return None
            
            # 与所有趋势模式聚类中心进行匹配
            match_results = []
            
            print(f"🔍 股票 {stock_code} 开始匹配，共 {len(self.clustering_results)} 个聚类...")
            print(f"   匹配阈值: {self.match_threshold:.4f}")
            print(f"   特征维度: {len(trend_features)}")
            print("-" * 60)
            
            for cluster_id, cluster_data in self.clustering_results.items():
                # 计算趋势特征相似度
                similarity_scores = self._calculate_trend_similarities(
                    trend_features, cluster_data['center_features']
                )
                
                # 综合匹配分数
                match_score = self._combine_similarity_scores(similarity_scores)
                
                # 显示简化的匹配信息
                print(f"📊 聚类 {cluster_id}:")
                print(f"   聚类信息:")
                print(f"     - 序列数量: {len(cluster_data.get('sequences', []))}")
                print(f"     - 成功率: {cluster_data.get('success_rate', 0):.2%}")
                print(f"     - 平均收益: {cluster_data.get('avg_gain', 0):.2%}")
                print(f"     - 收益标准差: {cluster_data.get('gain_std', 0):.4f}")
                
                print(f"   综合匹配分数: {match_score:.4f}")
                print(f"   阈值比较: {match_score:.4f} {'>=' if match_score >= self.match_threshold else '<'} {self.match_threshold}")
                
                if match_score >= self.match_threshold:
                    print(f"     ✅ 匹配成功！分数 {match_score:.4f} >= 阈值 {self.match_threshold}")
                    match_result = {
                        'stock_code': stock_code,
                        'cluster_id': cluster_id,
                        'match_score': match_score,
                        'similarity_scores': similarity_scores,
                        'cluster_success_score': cluster_data.get('success_score', 0.0),
                        'cluster_success_rate': cluster_data.get('success_rate', 0.0),
                        'cluster_avg_gain': cluster_data.get('avg_gain', 0.0),
                        'cluster_gain_std': cluster_data.get('gain_std', 0.0),
                        'final_score': 0.0  # 将在后面计算
                    }
                    match_results.append(match_result)
                else:
                    print(f"     ❌ 匹配失败，分数 {match_score:.4f} < 阈值 {self.match_threshold}")
                
                print("-" * 40)
            
            if not match_results:
                print(f"股票 {stock_code} 没有匹配的趋势模式聚类")
                return None
            
            # 计算最终分数
            print(f"🎯 计算最终综合分数...")
            for match_result in match_results:
                match_result['final_score'] = self._calculate_final_score(
                    match_result['match_score'],
                    match_result['cluster_success_score'],
                    match_result['cluster_gain_std']
                )
                print(f"   聚类 {match_result['cluster_id']}: 最终分数 = {match_result['final_score']:.4f}")
            
            # 按最终分数排序
            match_results.sort(key=lambda x: x['final_score'], reverse=True)
            
            print(f"📈 股票 {stock_code} 匹配结果排序:")
            for i, match_result in enumerate(match_results):
                print(f"   {i+1}. 聚类 {match_result['cluster_id']}: "
                      f"匹配分数={match_result['match_score']:.4f}, "
                      f"最终分数={match_result['final_score']:.4f}, "
                      f"成功率={match_result['cluster_success_rate']:.2%}")
            
            print(f"✅ 股票 {stock_code} 匹配完成，共匹配到 {len(match_results)} 个趋势模式聚类")
            return match_results
            
        except Exception as e:
            print(f"❌ 匹配股票 {stock_code} 失败: {e}")
            return None
    
    def match_stock_list(self, stock_data_dict):
        """批量匹配股票列表"""
        if not stock_data_dict:
            print("❌ 没有股票数据")
            return {}
        
        all_match_results = {}
        successful_matches = 0
        
        for i, (stock_code, stock_data) in enumerate(stock_data_dict.items()):
            if i % 50 == 0:
                print(f"📊 匹配进度: {i}/{len(stock_data_dict)}")
            
            try:
                match_result = self.match_single_stock(stock_data, stock_code)
                if match_result:
                    all_match_results[stock_code] = match_result
                    successful_matches += 1
                    
            except Exception as e:
                print(f"❌ 匹配股票 {stock_code} 失败: {e}")
                continue
        
        print(f"✅ 批量匹配完成，成功匹配 {successful_matches}/{len(stock_data_dict)} 只股票（趋势模式聚类）")
        
        return all_match_results
    
    def match_stocks_from_database(self, start_date, end_date, stock_codes=None):
        """
        从数据库获取股票数据进行匹配
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            stock_codes: 指定股票代码列表，如果为None则获取所有股票
        
        Returns:
            dict: 匹配结果
        """
        try:
            # 获取股票列表
            if stock_codes is None:
                stock_codes = self.db_manager.get_stock_list(start_date, end_date)
            
            if not stock_codes:
                print("❌ 没有获取到股票列表")
                return {}
            
            print(f"📈 准备匹配 {len(stock_codes)} 只股票")
            
            # 批量获取股票数据
            stock_data_dict = {}
            successful_fetches = 0
            
            for i, stock_code in enumerate(stock_codes):
                if i % 50 == 0:
                    print(f"📊 数据获取进度: {i}/{len(stock_codes)}")
                
                try:
                    stock_data = self.db_manager.get_stock_data(stock_code, start_date, end_date)
                    if not stock_data.empty and len(stock_data) >= WINDOW_SIZE:
                        stock_data_dict[stock_code] = stock_data
                        successful_fetches += 1
                    
                except Exception as e:
                    print(f"❌ 获取股票 {stock_code} 数据失败: {e}")
                    continue
            
            print(f"✅ 成功获取 {successful_fetches}/{len(stock_codes)} 只股票的数据")
            
            if not stock_data_dict:
                print("❌ 没有获取到有效的股票数据")
                return {}
            
            # 执行匹配
            return self.match_stock_list(stock_data_dict)
            
        except Exception as e:
            print(f"❌ 从数据库匹配股票失败: {e}")
            return {}
    
    def create_scoring_dataframe(self, start_date, end_date, stock_codes=None):
        """
        创建包含所有股票数据和匹配分数的DataFrame，每天按分数从高到低排序
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            stock_codes: 指定股票代码列表，如果为None则获取所有股票
        
        Returns:
            pd.DataFrame: 包含股票数据、技术指标和匹配分数的DataFrame，每天按分数排序
        """
        try:
            # 获取股票列表
            if stock_codes is None:
                stock_codes = self.db_manager.get_stock_list(start_date, end_date)
            
            if not stock_codes:
                print("❌ 没有获取到股票列表")
                return pd.DataFrame()
            
            print(f"📈 准备处理 {len(stock_codes)} 只股票")
            
            # 存储所有股票的数据
            all_stock_data = []
            
            for i, stock_code in enumerate(stock_codes):
                if i % 50 == 0:
                    print(f"📊 处理进度: {i}/{len(stock_codes)}")
                
                try:
                    # 获取股票数据
                    stock_data = self.db_manager.get_stock_data(stock_code, start_date, end_date)
                    if stock_data.empty or len(stock_data) < WINDOW_SIZE:
                        continue
                    
                    # 计算技术指标
                    stock_data = self._calculate_technical_indicators(stock_data)
                    
                    # 计算匹配分数
                    match_results = self.match_single_stock(stock_data, stock_code)
                    
                    # 为每行数据添加匹配分数
                    if match_results and len(match_results) > 0:
                        # 使用最佳匹配的分数
                        best_score = match_results[0]['final_score']
                        stock_data['MACD'] = best_score  # 使用MACD列名存储分数
                    else:
                        stock_data['MACD'] = 0.0  # 没有匹配时分数为0
                    
                    # 添加到总数据中
                    all_stock_data.append(stock_data)
                    
                except Exception as e:
                    print(f"❌ 处理股票 {stock_code} 失败: {e}")
                    continue
            
            if not all_stock_data:
                print("❌ 没有获取到有效的股票数据")
                return pd.DataFrame()
            
            # 合并所有股票数据
            final_df = pd.concat(all_stock_data, ignore_index=True)
            
            # 确保列名正确 - 修复st_code列名问题
            final_df = final_df.rename(columns={
                'stock_code': 'st_code',  # 修复：从stock_code改为st_code
                'trade_date': 'trade_date',
                'volume': 'vol'  # 修复：从volume改为vol
            })
            
            # 选择需要的列并重新排序
            required_columns = [
                'st_code', 'trade_date', 'open', 'high', 'low', 'close', 
                'pre_close', 'pct_chg', 'vol', 'cci', 'pre_cci', 
                'macd_macd', 'pre_macd_macd', 'MACD'
            ]
            
            # 检查哪些列存在，不存在的用0填充
            for col in required_columns:
                if col not in final_df.columns:
                    if col in ['open', 'high', 'low', 'pre_close', 'pre_cci', 'pre_macd_macd']:
                        final_df[col] = 0.0
                    elif col in ['pct_chg', 'cci', 'macd_macd']:
                        final_df[col] = 0.0
                    else:
                        final_df[col] = ''
            
            # 重新排序列
            final_df = final_df[required_columns]
            
            # 按日期分组，每天按分数从高到低排序
            # 确保trade_date列是datetime类型
            final_df['trade_date'] = pd.to_datetime(final_df['trade_date'])
            
            # 按日期分组，每天按分数排序
            sorted_dfs = []
            unique_dates = final_df['trade_date'].dt.date.unique()
            
            for date in sorted(unique_dates):
                # 获取当天的数据
                daily_data = final_df[final_df['trade_date'].dt.date == date].copy()
                
                if not daily_data.empty:
                    # 按分数从高到低排序
                    daily_data_sorted = daily_data.sort_values('MACD', ascending=False)
                    sorted_dfs.append(daily_data_sorted)
            
            # 合并所有排序后的数据
            if sorted_dfs:
                final_sorted_df = pd.concat(sorted_dfs, ignore_index=True)
                
                # 重新排序列（严格按照要求的格式，不包含daily_rank）
                final_sorted_df = final_sorted_df[required_columns]
                
                print(f"✅ 成功创建评分DataFrame，包含 {len(final_sorted_df)} 行数据")
                
                return final_sorted_df
            else:
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ 创建评分DataFrame失败: {e}")
            return pd.DataFrame()
    
    def _calculate_technical_indicators(self, stock_data):
        """计算技术指标"""
        try:
            if stock_data.empty:
                return stock_data
            
            # 确保有足够的数据
            if len(stock_data) < 2:
                return stock_data
            
            # 计算前一日数据
            stock_data['pre_close'] = stock_data['close'].shift(1)
            stock_data['pre_cci'] = stock_data['cci'].shift(1)
            stock_data['pre_macd_macd'] = stock_data['macd_macd'].shift(1)
            
            # 填充NaN值
            stock_data['pre_close'] = stock_data['pre_close'].fillna(stock_data['close'])
            stock_data['pre_cci'] = stock_data['pre_cci'].fillna(stock_data['cci'])
            stock_data['pre_macd_macd'] = stock_data['pre_macd_macd'].fillna(stock_data['macd_macd'])
            
            return stock_data
            
        except Exception as e:
            print(f"❌ 计算技术指标失败: {e}")
            return stock_data
    
    def _prepare_trend_features(self, stock_data):
        """准备股票趋势特征 - 适配趋势模式聚类"""
        try:
            if stock_data.empty or len(stock_data) < 10:
                return None
            
            # 提取价格序列
            if 'close' in stock_data.columns:
                price_series = stock_data['close'].values
            else:
                price_series = stock_data.iloc[:, 0].values
            
            if len(price_series) < 10:
                return None
            
            # 使用与data_preprocessing_elbow.py相同的特征提取方法
            trend_features = self._extract_trend_pattern_features(price_series)
            
            if trend_features is None:
                return None
            
            return trend_features
            
        except Exception as e:
            print(f"❌ 准备趋势特征失败: {e}")
            return None
    
    def _extract_trend_pattern_features(self, price_series):
        """提取趋势模式特征 - 与data_preprocessing_elbow.py保持一致"""
        try:
            if len(price_series) < 10:
                return None
                
            # 1. 趋势方向特征（线性回归斜率）
            x = np.arange(len(price_series))
            slope, _, r_value, _, _ = stats.linregress(x, price_series)
            trend_direction = np.sign(slope)  # 1: 上升, -1: 下降, 0: 横盘
            
            # 2. 趋势强度特征（价格变化的一致性）
            price_changes = np.diff(price_series)
            trend_strength = np.abs(slope) / np.mean(price_series) if np.mean(price_series) > 0 else 0
            
            # 3. 回调特征
            # 最大回调深度
            max_pullback = 0
            peak_price = price_series[0]
            for price in price_series:
                if price > peak_price:
                    peak_price = price
                pullback = (peak_price - price) / peak_price
                max_pullback = max(max_pullback, pullback)
            
            # 回调次数
            pullback_count = 0
            for i in range(1, len(price_series)):
                if price_series[i] < price_series[i-1]:
                    pullback_count += 1
            
            # 回调反弹速度
            if pullback_count > 0:
                pullback_speed = max_pullback / pullback_count
            else:
                pullback_speed = 0
            
            # 4. 突破特征
            # 突破强度（相对于移动平均线）
            ma20 = np.mean(price_series[-20:]) if len(price_series) >= 20 else np.mean(price_series)
            breakout_strength = (price_series[-1] - ma20) / ma20 if ma20 > 0 else 0
            
            # 突破确认度
            recent_prices = price_series[-5:] if len(price_series) >= 5 else price_series
            breakout_confirmation = np.sum(recent_prices > ma20) / len(recent_prices)
            
            # 突破持续性
            if len(price_series) >= 10:
                early_ma = np.mean(price_series[:10])
                late_ma = np.mean(price_series[-10:])
                breakout_continuation = (late_ma - early_ma) / early_ma if early_ma > 0 else 0
            else:
                breakout_continuation = 0
            
            # 5. 价格路径特征
            # R平方值（趋势拟合度）
            r_squared = r_value ** 2
            
            # 价格路径平滑度
            price_smoothness = 1.0 / (1.0 + np.std(np.diff(price_series)))
            
            # 价格单调性
            monotonicity = np.sum(np.diff(price_series) >= 0) / (len(price_series) - 1)
            
            # 6. 波动特征
            # 价格波动性
            volatility = np.std(price_series) / np.mean(price_series) if np.mean(price_series) > 0 else 0
            
            # 价格稳定性
            stability = 1.0 / (1.0 + volatility)
            
            # 极端价格频率
            mean_price = np.mean(price_series)
            std_price = np.std(price_series)
            extreme_frequency = np.sum(np.abs(price_series - mean_price) > 2 * std_price) / len(price_series)
            
            # 组合所有特征
            features = np.array([
                trend_direction, trend_strength,
                max_pullback, pullback_count, pullback_speed,
                breakout_strength, breakout_confirmation, breakout_continuation,
                r_squared, price_smoothness, monotonicity,
                volatility, stability, extreme_frequency
            ])
            
            # 检查特征有效性
            if np.any(np.isnan(features)) or np.any(np.isinf(features)):
                return None
                
            return features
            
        except Exception as e:
            print(f"❌ 提取趋势模式特征失败: {e}")
            return None
    

    
    def _calculate_trend_similarities(self, features1, features2):
        """计算两个趋势特征向量的相似度"""
        try:
            # 确保特征向量是numpy数组
            f1 = np.array(features1).flatten()
            f2 = np.array(features2).flatten()
            
            if len(f1) != len(f2):
                print(f"❌ 特征向量长度不匹配: {len(f1)} vs {len(f2)}")
                return {}
            
            # 计算各种相似度
            similarities = {}
            
            # 1. 余弦相似度
            try:
                cosine_sim = cosine_similarity(f1.reshape(1, -1), f2.reshape(1, -1))[0, 0]
                similarities['cosine'] = float(cosine_sim)
            except:
                similarities['cosine'] = 0.0
            
            # 2. 欧氏距离相似度
            try:
                euclidean_dist = np.linalg.norm(f1 - f2)
                euclidean_sim = 1 / (1 + euclidean_dist)
                similarities['euclidean'] = float(euclidean_sim)
            except:
                similarities['euclidean'] = 0.0
            
            # 3. 曼哈顿距离相似度
            try:
                manhattan_dist = np.sum(np.abs(f1 - f2))
                manhattan_sim = 1 / (1 + manhattan_dist)
                similarities['manhattan'] = float(manhattan_sim)
            except:
                similarities['manhattan'] = 0.0
            
            # 4. 皮尔逊相关系数
            try:
                pearson_corr = np.corrcoef(f1, f2)[0, 1]
                pearson_sim = (pearson_corr + 1) / 2 if not np.isnan(pearson_corr) else 0.5
                similarities['pearson'] = float(pearson_sim)
            except:
                similarities['pearson'] = 0.5
            
            # 5. 趋势模式特征相似度（前7个特征：趋势方向、强度、回调相关）
            try:
                trend_pattern_sim = 1 / (1 + np.sum(np.abs(f1[:7] - f2[:7])))
                similarities['trend_pattern'] = float(trend_pattern_sim)
            except:
                similarities['trend_pattern'] = 0.0
            
            # 6. 价格路径和波动特征相似度（后7个特征）
            try:
                price_path_sim = 1 / (1 + np.sum(np.abs(f1[7:] - f2[7:])))
                similarities['price_path'] = float(price_path_sim)
            except:
                similarities['price_path'] = 0.0
            
            return similarities
            
        except Exception as e:
            print(f"❌ 计算趋势相似度失败: {e}")
            return {}
    
    def _combine_similarity_scores(self, similarity_scores):
        """组合各种相似度分数"""
        try:
            if not similarity_scores:
                return 0.0
            
            # 权重配置
            weights = SIMILARITY_CONFIG
            
            # 计算加权平均
            total_score = 0.0
            total_weight = 0.0
            
            for metric, weight in weights.items():
                if metric in similarity_scores:
                    total_score += similarity_scores[metric] * weight
                    total_weight += weight
            
            if total_weight > 0:
                return total_score / total_weight
            else:
                return 0.0
                
        except Exception as e:
            print(f"❌ 组合相似度分数失败: {e}")
            return 0.0
    
    def _calculate_final_score(self, match_score, success_score, gain_std):
        """计算最终综合分数"""
        try:
            # 匹配分数权重 70%
            match_weight = 0.7
            
            # 稳定性分数权重 30%（基于收益标准差）
            stability_score = 1 / (1 + gain_std) if gain_std > 0 else 0.5
            stability_weight = 0.3
            
            # 计算最终分数
            final_score = (match_score * match_weight + 
                          stability_score * stability_weight)
            
            return float(final_score)
            
        except Exception as e:
            print(f"❌ 计算最终分数失败: {e}")
            return 0.0
    
    def get_matching_summary(self):
        """获取匹配结果摘要"""
        if not hasattr(self, 'matching_stats') or not self.matching_stats:
            return {}
        
        return self.matching_stats
    
    def save_matching_results(self, matching_results, filename=None):
        """保存匹配结果到文件"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"matching_results_{timestamp}.json"
            
            # 使用辅助函数转换所有numpy数据类型
            json_results = convert_numpy_types(matching_results)
            
            # 保存到文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 匹配结果已保存到: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ 保存匹配结果失败: {e}")
            return None

class StockMatcher:
    """股票匹配器主类"""
    
    def __init__(self, clustering_results_file=None, match_threshold=MATCH_THRESHOLD):
        """初始化股票匹配器"""
        self.matcher = StandaloneStockMatcher(clustering_results_file, match_threshold)
    
    def match_single_stock(self, stock_data, stock_code):
        """匹配单只股票"""
        return self.matcher.match_single_stock(stock_data, stock_code)
    
    def match_stock_list(self, stock_data_dict):
        """批量匹配股票列表"""
        return self.matcher.match_stock_list(stock_data_dict)
    
    def create_scoring_dataframe(self, start_date, end_date, stock_codes=None):
        """创建包含所有股票数据和匹配分数的DataFrame"""
        return self.matcher.create_scoring_dataframe(start_date, end_date, stock_codes)
    
    def get_clustering_summary(self):
        """获取肘部法则聚类摘要"""
        if not self.matcher.clustering_results:
            return {}
        
        summary = {
            'total_clusters': len(self.matcher.clustering_results),
            'total_sequences': sum(len(cluster.get('sequences', [])) for cluster in self.matcher.clustering_results.values()),
            'avg_success_rate': np.mean([cluster.get('success_rate', 0.0) for cluster in self.matcher.clustering_results.values()]),
            'avg_gain': np.mean([cluster.get('avg_gain', 0.0) for cluster in self.matcher.clustering_results.values()])
        }
        
        return summary
    
    def save_matching_results(self, matching_results, filename=None):
        """保存匹配结果"""
        return self.matcher.save_matching_results(matching_results, filename)





def main():
    """主函数 - 直接调用评分DataFrame创建功能"""
    try:
        # 直接运行评分DataFrame创建功能
        scoring_df = create_and_save_scoring_dataframe()
        
        if scoring_df is not None:
            return scoring_df
        else:
            return None
        
    except Exception as e:
        print(f"❌ 股票匹配模块运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_and_save_scoring_dataframe():
    """创建评分DataFrame并保存为CSV文件"""
    try:
        # 创建匹配器
        matcher = StockMatcher()
        
        if not matcher.matcher.clustering_results:
            print("❌ 没有趋势模式聚类结果，无法进行匹配")
            return None
        
        # 根据配置设置日期范围
        if USE_DYNAMIC_DATES:
            # 使用动态日期（最近N天）
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=DYNAMIC_DAYS)).strftime('%Y-%m-%d')
        else:
            # 使用固定日期
            start_date = MATCH_START_DATE
            end_date = MATCH_END_DATE
        
        # 创建评分DataFrame
        scoring_df = matcher.create_scoring_dataframe(start_date, end_date)
        
        if not scoring_df.empty:
            # 保存为CSV文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"stock_scoring_results_{timestamp}.csv"
            
            try:
                scoring_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
                print(f"💾 评分结果已保存到CSV文件: {csv_filename}")
                
            except Exception as e:
                print(f"❌ 保存CSV文件失败: {e}")
            
            # 返回DataFrame供其他代码调用
            return scoring_df
        else:
            print("❌ 创建评分DataFrame失败")
            return None
            
    except Exception as e:
        print(f"❌ 创建评分DataFrame失败: {e}")
        import traceback
        traceback.print_exc()
        return None



if __name__ == "__main__":
    # 直接运行主函数，返回DataFrame
    scoring_df = main()
    
    if scoring_df is not None:
        print(f"✅ 成功获取评分DataFrame，包含 {len(scoring_df)} 行数据")
    else:
        print("❌ 未能获取评分DataFrame")
