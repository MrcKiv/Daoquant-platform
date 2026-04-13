# -*- coding: utf-8 -*-
"""
优化版序列聚类模块
支持更多聚类算法和更好的聚类质量评估
"""

import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import RobustScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from config import *

class SequenceClustering:
    def __init__(self, n_clusters=20, min_samples=5):
        """
        初始化聚类器（优化版）
        
        Args:
            n_clusters: 聚类数量
            min_samples: 最小样本数量
        """
        self.n_clusters = n_clusters
        self.min_samples = min_samples
        self.scaler = RobustScaler()  # 使用RobustScaler处理异常值
        self.cluster_centers = []
        self.cluster_labels = []
        self.clustering_quality = {}
        
    def prepare_features(self, sequences):
        """
        准备聚类特征（优化版）
        
        Args:
            sequences: 序列列表
            
        Returns:
            numpy.array: 特征矩阵
        """
        print("准备聚类特征（优化版）...")
        
        features_list = []
        valid_sequences = []
        
        for seq in sequences:
            try:
                # 将15天的特征数据展平为一维向量
                features = np.array(seq['features']).flatten()
                
                # 检查特征是否有效
                if not np.any(np.isnan(features)) and not np.any(np.isinf(features)):
                    # 特征标准化处理
                    features = self._normalize_features(features)
                    features_list.append(features)
                    valid_sequences.append(seq)
                else:
                    print(f"跳过无效序列: {seq['sequence_id']}")
            except Exception as e:
                print(f"处理序列 {seq['sequence_id']} 失败: {e}")
                continue
        
        if not features_list:
            print("没有有效的特征数据")
            return np.array([]), []
        
        # 转换为numpy数组
        feature_matrix = np.array(features_list)
        print(f"特征矩阵形状: {feature_matrix.shape}")
        
        # 特征降维（如果维度太高）
        if feature_matrix.shape[1] > 100:
            feature_matrix = self._reduce_dimensions(feature_matrix)
        
        return feature_matrix, valid_sequences
    
    def _normalize_features(self, features):
        """特征标准化处理"""
        try:
            # 处理异常值
            features = np.clip(features, -10, 10)  # 限制在合理范围内
            
            # 标准化到0-1范围
            features = (features - np.min(features)) / (np.max(features) - np.min(features) + 1e-8)
            
            return features
        except Exception as e:
            print(f"特征标准化失败: {e}")
            return features
    
    def _reduce_dimensions(self, feature_matrix):
        """特征降维"""
        try:
            print("特征维度较高，进行降维处理...")
            pca = PCA(n_components=100, random_state=42)
            reduced_features = pca.fit_transform(feature_matrix)
            print(f"降维后特征矩阵形状: {reduced_features.shape}")
            print(f"保留方差比例: {np.sum(pca.explained_variance_ratio_):.3f}")
            return reduced_features
        except Exception as e:
            print(f"特征降维失败: {e}")
            return feature_matrix
    
    def cluster_sequences(self, sequences):
        """
        对序列进行聚类（优化版）
        
        Args:
            sequences: 序列列表
            
        Returns:
            dict: 聚类结果
        """
        # 准备特征
        feature_matrix, valid_sequences = self.prepare_features(sequences)
        
        if len(feature_matrix) == 0:
            return {}
        
        # 标准化特征
        print("标准化特征...")
        scaled_features = self.scaler.fit_transform(feature_matrix)
        
        # 确定最佳聚类数量
        best_n_clusters = self._find_optimal_clusters(scaled_features)
        print(f"最佳聚类数量: {best_n_clusters}")
        
        # 执行聚类
        print("执行聚类...")
        clustering_results = self._perform_clustering(scaled_features, best_n_clusters)
        
        if clustering_results:
            # 组织聚类结果
            final_results = self._organize_clustering_results(valid_sequences, clustering_results)
            
            print(f"聚类完成，共生成 {len(final_results)} 个通用序列模式")
            
            # 评估聚类质量
            self._evaluate_clustering_quality(scaled_features, clustering_results)
            
            return final_results
        
        return {}

    def _perform_clustering(self, features, n_clusters):
        """执行聚类（支持多种算法）"""
        try:
            # 尝试K-means聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features)

            # 保存聚类中心
            self.cluster_centers = kmeans.cluster_centers_
            self.cluster_labels = cluster_labels

            print(f"K-means聚类成功，生成 {n_clusters} 个聚类")
            return {
                'labels': cluster_labels,
                'centers': self.cluster_centers,
                'algorithm': 'kmeans'
            }

        except Exception as e:
            print(f"K-means聚类失败: {e}")

            # 尝试层次聚类
            try:
                print("尝试层次聚类...")
                hierarchical = AgglomerativeClustering(n_clusters=n_clusters)
                cluster_labels = hierarchical.fit_predict(features)

                # 计算聚类中心
                self.cluster_centers = self._calculate_cluster_centers(features, cluster_labels, n_clusters)
                self.cluster_labels = cluster_labels

                print(f"层次聚类成功，生成 {n_clusters} 个聚类")
                return {
                    'labels': cluster_labels,
                    'centers': self.cluster_centers,
                    'algorithm': 'hierarchical'
                }

            except Exception as e2:
                print(f"层次聚类也失败: {e2}")
                return None
    
    def _calculate_cluster_centers(self, features, labels, n_clusters):
        """计算聚类中心"""
        centers = []
        for i in range(n_clusters):
            cluster_points = features[labels == i]
            if len(cluster_points) > 0:
                center = np.mean(cluster_points, axis=0)
                centers.append(center)
            else:
                centers.append(np.zeros(features.shape[1]))
        return np.array(centers)
    
    def _find_optimal_clusters(self, features, max_clusters=None):
        """
        寻找最佳聚类数量（优化版）
        
        Args:
            features: 特征矩阵
            max_clusters: 最大聚类数量
            
        Returns:
            int: 最佳聚类数量
        """
        if len(features) < 10:
            return min(3, len(features))
        
        if max_clusters is None:
            max_clusters = min(CLUSTERING_CONFIG['max_clusters'], len(features) // 2)
        
        if max_clusters < 2:
            return 2
        
        print(f"测试聚类数量范围: 2 到 {max_clusters}")
        
        # 评估指标
        silhouette_scores = []
        calinski_scores = []
        davies_scores = []
        cluster_numbers = range(2, max_clusters + 1)
        
        for n in cluster_numbers:
            try:
                kmeans = KMeans(n_clusters=n, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(features)
                
                # 计算多个评估指标
                sil_score = silhouette_score(features, cluster_labels)
                cal_score = calinski_harabasz_score(features, cluster_labels)
                dav_score = davies_bouldin_score(features, cluster_labels)
                
                silhouette_scores.append(sil_score)
                calinski_scores.append(cal_score)
                davies_scores.append(dav_score)
                
                print(f"聚类数 {n}: 轮廓系数={sil_score:.3f}, Calinski={cal_score:.0f}, Davies={dav_score:.3f}")
                
            except Exception as e:
                print(f"聚类数 {n} 评估失败: {e}")
                silhouette_scores.append(0)
                calinski_scores.append(0)
                davies_scores.append(0)
        
        # 综合评估选择最佳聚类数
        best_n = self._select_best_clusters(cluster_numbers, silhouette_scores, calinski_scores, davies_scores)
        
        return best_n
    
    def _select_best_clusters(self, cluster_numbers, sil_scores, cal_scores, dav_scores):
        """选择最佳聚类数量"""
        try:
            # 标准化分数
            sil_norm = (np.array(sil_scores) - np.min(sil_scores)) / (np.max(sil_scores) - np.min(sil_scores) + 1e-8)
            cal_norm = (np.array(cal_scores) - np.min(cal_scores)) / (np.max(cal_scores) - np.min(cal_scores) + 1e-8)
            dav_norm = 1 - (np.array(dav_scores) - np.min(dav_scores)) / (np.max(dav_scores) - np.min(dav_scores) + 1e-8)
            
            # 综合分数
            combined_scores = sil_norm * 0.5 + cal_norm * 0.3 + dav_norm * 0.2
            
            best_idx = np.argmax(combined_scores)
            best_n = cluster_numbers[best_idx]
            
            print(f"综合评估结果:")
            print(f"  轮廓系数权重: 50%")
            print(f"  Calinski权重: 30%")
            print(f"  Davies权重: 20%")
            print(f"  最佳聚类数: {best_n}")
            
            return best_n
            
        except Exception as e:
            print(f"综合评估失败: {e}")
            # 回退到轮廓系数
            best_idx = np.argmax(sil_scores)
            return cluster_numbers[best_idx]

    def _organize_clustering_results(self, sequences, clustering_result):
        """
        组织聚类结果，将序列按聚类分组并计算统计信息

        Args:
            sequences: 原始序列列表
            clustering_result: 聚类结果字典，包含 labels 和 centers

        Returns:
            dict: 组织后的聚类结果
        """
        try:
            if not clustering_result or 'labels' not in clustering_result:
                print("聚类结果格式错误")
                return {}

            cluster_labels = clustering_result['labels']
            cluster_centers = clustering_result['centers']

            if len(sequences) != len(cluster_labels):
                print(f"序列数量({len(sequences)})与聚类标签数量({len(cluster_labels)})不匹配")
                return {}

            # 按聚类分组
            clusters = {}
            for i, label in enumerate(cluster_labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(sequences[i])

            # 计算每个聚类的统计信息
            final_results = {}
            for cluster_id, cluster_sequences in clusters.items():
                if len(cluster_sequences) == 0:
                    continue

                # 计算成功率
                success_count = sum(1 for seq in cluster_sequences if seq.get('success_count', 0) > 0)
                total_count = len(cluster_sequences)
                success_rate = success_count / total_count if total_count > 0 else 0

                # 计算平均收益
                gains = [seq.get('total_gain', 0) for seq in cluster_sequences]
                avg_gain = np.mean(gains) if gains else 0
                gain_std = np.std(gains) if len(gains) > 1 else 0

                # 计算成功分数
                success_score = self._calculate_success_score(success_rate, avg_gain, gain_std)

                # 获取聚类中心特征
                if cluster_centers is not None and cluster_id < len(cluster_centers):
                    center_features = cluster_centers[cluster_id]
                else:
                    center_features = None

                # 组织聚类信息
                final_results[cluster_id] = {
                    'cluster_id': cluster_id,
                    'sequences': cluster_sequences,
                    'sequence_count': len(cluster_sequences),
                    'success_count': success_count,
                    'total_count': total_count,
                    'success_rate': success_rate,
                    'avg_gain': avg_gain,
                    'gain_std': gain_std,
                    'success_score': success_score,
                    'center_features': center_features,
                    'stock_codes': [seq.get('stock_code', '') for seq in cluster_sequences],
                    'date_range': {
                        'start': min([seq.get('start_date', '') for seq in cluster_sequences]),
                        'end': max([seq.get('end_date', '') for seq in cluster_sequences])
                    },
                    'created_at': datetime.now()
                }

            # 按成功分数排序
            sorted_results = dict(sorted(
                final_results.items(),
                key=lambda x: x[1]['success_score'],
                reverse=True
            ))

            print(f"聚类结果组织完成，共 {len(sorted_results)} 个聚类")
            for cluster_id, cluster_data in sorted_results.items():
                print(f"  聚类 {cluster_id}: {cluster_data['sequence_count']} 个序列, "
                      f"成功率: {cluster_data['success_rate']:.2%}, "
                      f"平均收益: {cluster_data['avg_gain']:.3f}, "
                      f"成功分数: {cluster_data['success_score']:.3f}")

            return sorted_results

        except Exception as e:
            print(f"组织聚类结果时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _calculate_success_score(self, success_count, total_count, gain_std):
        """
        计算成功分数（优化版）
        
        Args:
            success_count: 成功次数
            total_count: 总次数
            gain_std: 涨幅标准差
            
        Returns:
            float: 成功分数
        """
        if total_count == 0:
            return 0.0
        
        base_score = success_count / total_count
        
        # 样本量奖励
        sample_bonus = min(total_count / 100, 0.1)
        
        # 置信度奖励
        confidence_bonus = base_score * 0.1
        
        # 稳定性奖励（标准差越小越好）
        stability_bonus = max(0, (0.1 - gain_std) * 2) if gain_std < 0.1 else 0
        
        final_score = min(base_score + sample_bonus + confidence_bonus + stability_bonus, 1.0)
        return round(final_score, 3)
    
    def _calculate_feature_importance(self, sequences):
        """计算特征重要性"""
        try:
            if not sequences:
                return {}
            
            # 提取所有特征
            all_features = []
            for seq in sequences:
                features = np.array(seq['features']).flatten()
                all_features.append(features)
            
            feature_matrix = np.array(all_features)
            
            # 计算每个特征的方差（方差越大，重要性越高）
            feature_variances = np.var(feature_matrix, axis=0)
            
            # 归一化重要性分数
            total_variance = np.sum(feature_variances)
            if total_variance > 0:
                feature_importance = feature_variances / total_variance
            else:
                feature_importance = np.ones(len(feature_variances)) / len(feature_variances)
            
            # 转换为字典格式
            importance_dict = {}
            for i, importance in enumerate(feature_importance):
                importance_dict[f'feature_{i}'] = float(importance)
            
            return importance_dict
            
        except Exception as e:
            print(f"计算特征重要性失败: {e}")
            return {}

    def _evaluate_clustering_quality(self, features, clustering_result):
        """
        评估聚类质量

        Args:
            features: 特征矩阵
            clustering_result: 聚类结果字典
        """
        try:
            if not clustering_result or 'labels' not in clustering_result:
                print("聚类结果为空，无法评估质量")
                return

            labels = clustering_result['labels']

            # 检查标签数组的形状
            if labels.ndim > 1:
                labels = labels.flatten()

            if len(labels) == 0:
                print("聚类标签为空，无法评估质量")
                return

            # 计算评估指标
            try:
                silhouette = silhouette_score(features, labels)
                print(f"轮廓系数: {silhouette:.3f}")
            except Exception as e:
                print(f"轮廓系数计算失败: {e}")

            try:
                calinski = calinski_harabasz_score(features, labels)
                print(f"Calinski-Harabasz指数: {calinski:.3f}")
            except Exception as e:
                print(f"Calinski-Harabasz指数计算失败: {e}")

            try:
                davies = davies_bouldin_score(features, labels)
                print(f"Davies-Bouldin指数: {davies:.3f}")
            except Exception as e:
                print(f"Davies-Bouldin指数计算失败: {e}")

            # 计算聚类内距离
            unique_labels = np.unique(labels)
            print(f"聚类数量: {len(unique_labels)}")

            for label in unique_labels:
                cluster_points = features[labels == label]
                if len(cluster_points) > 1:
                    cluster_center = np.mean(cluster_points, axis=0)
                    distances = np.linalg.norm(cluster_points - cluster_center, axis=1)
                    avg_distance = np.mean(distances)
                    print(f"  聚类 {label}: {len(cluster_points)} 个点, 平均距离: {avg_distance:.3f}")

        except Exception as e:
            print(f"聚类质量评估失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_clustering_results(self, clustering_results, filename='clustering_results_optimized.txt'):
        """
        保存聚类结果到文件（优化版）
        
        Args:
            clustering_results: 聚类结果
            filename: 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("优化版聚类结果汇总\n")
                f.write("=" * 60 + "\n\n")
                
                # 聚类质量信息
                if self.clustering_quality:
                    f.write("聚类质量评估:\n")
                    f.write(f"  轮廓系数: {self.clustering_quality.get('silhouette_score', 0):.3f}\n")
                    f.write(f"  Calinski-Harabasz指数: {self.clustering_quality.get('calinski_harabasz_score', 0):.0f}\n")
                    f.write(f"  Davies-Bouldin指数: {self.clustering_quality.get('davies_bouldin_score', 0):.3f}\n")
                    f.write(f"  聚类数量: {self.clustering_quality.get('n_clusters', 0)}\n")
                    f.write(f"  样本数量: {self.clustering_quality.get('n_samples', 0)}\n\n")
                
                # 聚类详细信息
                for cluster_id, cluster_data in clustering_results.items():
                    f.write(f"聚类 {cluster_id}\n")
                    f.write(f"序列数量: {len(cluster_data['sequences'])}\n")
                    f.write(f"成功率: {cluster_data['success_rate']:.2%}\n")
                    f.write(f"成功分数: {cluster_data['success_score']:.3f}\n")
                    f.write(f"平均涨幅: {cluster_data['avg_gain']:.2%}\n")
                    f.write(f"涨幅标准差: {cluster_data['gain_std']:.2%}\n")
                    f.write(f"特征维度: {cluster_data['feature_dimensions']}\n")
                    
                    # 特征重要性
                    if cluster_data['feature_importance']:
                        f.write("特征重要性 (前5个):\n")
                        sorted_features = sorted(cluster_data['feature_importance'].items(), 
                                               key=lambda x: x[1], reverse=True)[:5]
                        for feature, importance in sorted_features:
                            f.write(f"  {feature}: {importance:.3f}\n")
                    
                    f.write("-" * 40 + "\n")
            
            print(f"聚类结果已保存到文件: {filename}")
        except Exception as e:
            print(f"保存聚类结果失败: {e}")
