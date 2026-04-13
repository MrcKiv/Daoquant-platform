# -*- coding: utf-8 -*-
"""
优化版股票匹配模块
支持更多匹配算法和更好的评分机制
"""

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler
from config import *

class StockMatcher:
    def __init__(self, clustering_results, match_threshold=MATCH_THRESHOLD):
        """
        初始化股票匹配器（优化版）
        
        Args:
            clustering_results: 聚类结果
            match_threshold: 匹配度阈值
        """
        self.clustering_results = clustering_results
        self.match_threshold = match_threshold
        self.scaler = StandardScaler()
        self.matching_stats = {}
        
    def match_stock(self, stock_data, stock_code):
        """
        匹配单只股票（优化版）
        
        Args:
            stock_data: 股票数据（最近15天）
            stock_code: 股票代码
            
        Returns:
            dict: 匹配结果
        """
        if len(stock_data) < WINDOW_SIZE:
            print(f"股票 {stock_code} 数据不足 {WINDOW_SIZE} 天")
            return None
        
        # 提取最近15天的数据
        recent_data = stock_data.tail(WINDOW_SIZE)
        
        # 准备特征
        features = self._prepare_stock_features(recent_data)
        if features is None:
            return None
        
        # 与所有聚类中心进行匹配
        match_results = []
        
        for cluster_id, cluster_data in self.clustering_results.items():
            # 计算多种相似度
            similarity_scores = self._calculate_multiple_similarities(features, cluster_data['center_features'])
            
            # 综合匹配分数
            match_score = self._combine_similarity_scores(similarity_scores)
            
            if match_score >= self.match_threshold:
                match_result = {
                    'stock_code': stock_code,
                    'cluster_id': cluster_id,
                    'match_score': match_score,
                    'similarity_scores': similarity_scores,
                    'cluster_success_score': cluster_data['success_score'],
                    'cluster_success_rate': cluster_data['success_rate'],
                    'cluster_avg_gain': cluster_data['avg_gain'],
                    'cluster_gain_std': cluster_data.get('gain_std', 0.0),
                    'final_score': 0.0  # 将在后面计算
                }
                match_results.append(match_result)
        
        if not match_results:
            print(f"股票 {stock_code} 没有匹配的序列")
            return None
        
        # 计算最终分数
        for match_result in match_results:
            match_result['final_score'] = self._calculate_final_score(
                match_result['match_score'],
                match_result['cluster_success_score'],
                match_result['cluster_gain_std']
            )
        
        # 按最终分数排序
        match_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        print(f"股票 {stock_code} 匹配到 {len(match_results)} 个序列")
        return match_results
    
    def _prepare_stock_features(self, stock_data):
        """
        准备股票特征（优化版）
        
        Args:
            stock_data: 股票数据
            
        Returns:
            numpy.array: 特征向量
        """
        try:
            features = []
            for _, row in stock_data.iterrows():
                feature_vector = []
                for col in FEATURE_COLUMNS:
                    if col in row:
                        value = row[col]
                        # 处理缺失值和异常值
                        if pd.isna(value) or np.isinf(value):
                            feature_vector.append(self._get_default_value(col))
                        else:
                            # 特殊处理某些字段
                            if col == 'close_max__20':
                                # 20日最高价，转换为相对价格
                                if row['close'] > 0:
                                    feature_vector.append(float(value / row['close']))
                                else:
                                    feature_vector.append(1.0)
                            else:
                                feature_vector.append(float(value))
                    else:
                        feature_vector.append(self._get_default_value(col))
                features.append(feature_vector)
            
            # 转换为numpy数组并展平
            feature_array = np.array(features).flatten()
            
            # 检查特征是否有效
            if np.any(np.isnan(feature_array)) or np.any(np.isinf(feature_array)):
                print("特征数据包含无效值")
                return None
            
            # 特征标准化
            feature_array = self._normalize_features(feature_array)
            
            return feature_array
            
        except Exception as e:
            print(f"准备特征失败: {e}")
            return None
    
    def _get_default_value(self, column_name):
        """获取字段的默认值"""
        if column_name == 'close_max__20':
            return 1.0
        elif column_name in ['pct_chg', 'macd_macd', 'macd_dif', 'kdj_k', 'kdj_d', 'cci', 'wr_wr1']:
            return 0.0
        elif column_name == 'vol':
            return 1000000  # 默认成交量
        elif column_name in ['ema12', 'ema26']:
            return 100.0  # 默认价格
        else:
            return 0.0
    
    def _normalize_features(self, features):
        """特征标准化"""
        try:
            # 处理异常值
            features = np.clip(features, -10, 10)
            
            # 标准化到0-1范围
            features = (features - np.min(features)) / (np.max(features) - np.min(features) + 1e-8)
            
            return features
        except Exception as e:
            return features
    
    def _calculate_multiple_similarities(self, stock_features, cluster_features):
        """
        计算多种相似度（优化版）
        
        Args:
            stock_features: 股票特征
            cluster_features: 聚类中心特征
            
        Returns:
            dict: 各种相似度分数
        """
        try:
            # 确保特征维度一致
            if len(stock_features) != len(cluster_features):
                print(f"特征维度不匹配: 股票 {len(stock_features)}, 聚类 {len(cluster_features)}")
                return {}
            
            # 重塑为2D数组
            stock_features_2d = stock_features.reshape(1, -1)
            cluster_features_2d = cluster_features.reshape(1, -1)
            
            # 1. 余弦相似度
            cosine_sim = cosine_similarity(stock_features_2d, cluster_features_2d)[0][0]
            
            # 2. 欧氏距离相似度
            euclidean_dist = euclidean_distances(stock_features_2d, cluster_features_2d)[0][0]
            euclidean_sim = 1 / (1 + euclidean_dist)  # 转换为相似度
            
            # 3. 曼哈顿距离相似度
            manhattan_dist = np.sum(np.abs(stock_features - cluster_features))
            manhattan_sim = 1 / (1 + manhattan_dist)
            
            # 4. 皮尔逊相关系数
            correlation = np.corrcoef(stock_features, cluster_features)[0, 1]
            if np.isnan(correlation):
                correlation = 0.0
            correlation_sim = (correlation + 1) / 2  # 转换为0-1范围
            
            similarity_scores = {
                'cosine': cosine_sim,
                'euclidean': euclidean_sim,
                'manhattan': manhattan_sim,
                'correlation': correlation_sim
            }
            
            return similarity_scores
            
        except Exception as e:
            print(f"计算相似度失败: {e}")
            return {}
    
    def _combine_similarity_scores(self, similarity_scores):
        """
        综合多种相似度分数
        
        Args:
            similarity_scores: 各种相似度分数
            
        Returns:
            float: 综合匹配分数
        """
        if not similarity_scores:
            return 0.0
        
        try:
            # 权重设置
            weights = {
                'cosine': 0.4,      # 余弦相似度权重最高
                'euclidean': 0.25,  # 欧氏距离
                'manhattan': 0.2,   # 曼哈顿距离
                'correlation': 0.15 # 相关系数
            }
            
            # 计算加权平均
            total_score = 0.0
            total_weight = 0.0
            
            for sim_type, weight in weights.items():
                if sim_type in similarity_scores:
                    total_score += similarity_scores[sim_type] * weight
                    total_weight += weight
            
            if total_weight > 0:
                combined_score = total_score / total_weight
                return round(combined_score, 3)
            else:
                return 0.0
                
        except Exception as e:
            print(f"综合相似度分数失败: {e}")
            # 回退到余弦相似度
            return similarity_scores.get('cosine', 0.0)
    
    def _calculate_final_score(self, match_score, cluster_success_score, cluster_gain_std):
        """
        计算最终分数（优化版）
        
        Args:
            match_score: 匹配分数
            cluster_success_score: 聚类成功分数
            cluster_gain_std: 聚类涨幅标准差
            
        Returns:
            float: 最终分数
        """
        try:
            # 基础权重
            match_weight = 0.5      # 匹配度权重
            success_weight = 0.3    # 历史成功率权重
            stability_weight = 0.2  # 稳定性权重
            
            # 稳定性分数（标准差越小越好）
            stability_score = max(0, (0.1 - cluster_gain_std) * 10) if cluster_gain_std < 0.1 else 0
            stability_score = min(1.0, stability_score)
            
            # 计算最终分数
            final_score = (match_score * match_weight + 
                          cluster_success_score * success_weight + 
                          stability_score * stability_weight)
            
            return round(final_score, 3)
            
        except Exception as e:
            print(f"计算最终分数失败: {e}")
            # 回退到简单加权
            return round(match_score * 0.6 + cluster_success_score * 0.4, 3)
    
    def batch_match_stocks(self, stock_data_dict):
        """
        批量匹配股票（优化版）
        
        Args:
            stock_data_dict: 股票数据字典 {stock_code: data}
            
        Returns:
            list: 所有匹配结果
        """
        all_match_results = []
        
        print(f"开始批量匹配 {len(stock_data_dict)} 只股票...")
        
        # 统计信息
        total_stocks = len(stock_data_dict)
        matched_stocks = 0
        total_matches = 0
        
        for stock_code, stock_data in stock_data_dict.items():
            match_results = self.match_stock(stock_data, stock_code)
            if match_results:
                all_match_results.extend(match_results)
                matched_stocks += 1
                total_matches += len(match_results)
        
        # 按最终分数排序
        all_match_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # 更新统计信息
        self.matching_stats = {
            'total_stocks': total_stocks,
            'matched_stocks': matched_stocks,
            'total_matches': total_matches,
            'match_rate': matched_stocks / total_stocks if total_stocks > 0 else 0,
            'avg_matches_per_stock': total_matches / matched_stocks if matched_stocks > 0 else 0
        }
        
        print(f"批量匹配完成！")
        print(f"总股票数: {total_stocks}")
        print(f"匹配成功股票数: {matched_stocks}")
        print(f"总匹配数: {total_matches}")
        print(f"匹配成功率: {self.matching_stats['match_rate']:.2%}")
        print(f"平均每只股票匹配数: {self.matching_stats['avg_matches_per_stock']:.1f}")
        
        return all_match_results
    
    def save_match_results(self, match_results, filename='match_results_optimized.txt'):
        """
        保存匹配结果到文件（优化版）
        
        Args:
            match_results: 匹配结果列表
            filename: 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("优化版股票匹配结果汇总\n")
                f.write("=" * 60 + "\n\n")
                
                # 匹配统计信息
                if self.matching_stats:
                    f.write("匹配统计信息:\n")
                    f.write(f"  总股票数: {self.matching_stats['total_stocks']}\n")
                    f.write(f"  匹配成功股票数: {self.matching_stats['matched_stocks']}\n")
                    f.write(f"  总匹配数: {self.matching_stats['total_matches']}\n")
                    f.write(f"  匹配成功率: {self.matching_stats['match_rate']:.2%}\n")
                    f.write(f"  平均每只股票匹配数: {self.matching_stats['avg_matches_per_stock']:.1f}\n\n")
                
                # 匹配结果详情
                for i, result in enumerate(match_results, 1):
                    f.write(f"排名 {i}\n")
                    f.write(f"股票代码: {result['stock_code']}\n")
                    f.write(f"聚类ID: {result['cluster_id']}\n")
                    f.write(f"综合匹配分数: {result['match_score']:.3f}\n")
                    
                    # 详细相似度分数
                    if 'similarity_scores' in result:
                        f.write("详细相似度分数:\n")
                        for sim_type, score in result['similarity_scores'].items():
                            f.write(f"  {sim_type}: {score:.3f}\n")
                    
                    f.write(f"聚类成功分数: {result['cluster_success_score']:.3f}\n")
                    f.write(f"聚类成功率: {result['cluster_success_rate']:.2%}\n")
                    f.write(f"聚类平均涨幅: {result['cluster_avg_gain']:.2%}\n")
                    f.write(f"聚类涨幅标准差: {result['cluster_gain_std']:.2%}\n")
                    f.write(f"最终分数: {result['final_score']:.3f}\n")
                    f.write("-" * 40 + "\n")
            
            print(f"匹配结果已保存到文件: {filename}")
        except Exception as e:
            print(f"保存匹配结果失败: {e}")
    
    def get_top_stocks(self, match_results, top_n=10):
        """
        获取排名前N的股票（优化版）
        
        Args:
            match_results: 匹配结果列表
            top_n: 前N名
            
        Returns:
            list: 前N名股票
        """
        if not match_results:
            return []
        
        # 去重（每只股票只保留最高分）
        stock_scores = {}
        for result in match_results:
            stock_code = result['stock_code']
            if stock_code not in stock_scores or result['final_score'] > stock_scores[stock_code]['final_score']:
                stock_scores[stock_code] = result
        
        # 按分数排序
        top_stocks = sorted(stock_scores.values(), key=lambda x: x['final_score'], reverse=True)
        
        return top_stocks[:top_n]
    
    def analyze_matching_quality(self, match_results):
        """分析匹配质量"""
        if not match_results:
            return {}
        
        try:
            # 分数分布
            final_scores = [r['final_score'] for r in match_results]
            match_scores = [r['match_score'] for r in match_results]
            
            analysis = {
                'score_distribution': {
                    'final_score': {
                        'mean': np.mean(final_scores),
                        'std': np.std(final_scores),
                        'min': np.min(final_scores),
                        'max': np.max(final_scores),
                        'median': np.median(final_scores)
                    },
                    'match_score': {
                        'mean': np.mean(match_scores),
                        'std': np.std(match_scores),
                        'min': np.min(match_scores),
                        'max': np.max(match_scores),
                        'median': np.median(match_scores)
                    }
                },
                'cluster_distribution': {},
                'quality_rating': self._rate_matching_quality(final_scores)
            }
            
            # 聚类分布
            for result in match_results:
                cluster_id = result['cluster_id']
                if cluster_id not in analysis['cluster_distribution']:
                    analysis['cluster_distribution'][cluster_id] = 0
                analysis['cluster_distribution'][cluster_id] += 1
            
            return analysis
            
        except Exception as e:
            print(f"分析匹配质量失败: {e}")
            return {}
    
    def _rate_matching_quality(self, scores):
        """评估匹配质量"""
        if not scores:
            return "未知"
        
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        if mean_score > 0.8 and std_score < 0.1:
            return "优秀"
        elif mean_score > 0.6 and std_score < 0.2:
            return "良好"
        elif mean_score > 0.4 and std_score < 0.3:
            return "一般"
        else:
            return "较差"
