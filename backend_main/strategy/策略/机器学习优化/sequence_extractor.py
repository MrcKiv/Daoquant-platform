# -*- coding: utf-8 -*-
"""
优化版序列提取模块
支持更多特征字段和更好的数据处理
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import *

class SequenceExtractor:
    def __init__(self, window_size=WINDOW_SIZE, observation_days=OBSERVATION_DAYS, target_gain=TARGET_GAIN):
        """
        初始化序列提取器
        
        Args:
            window_size: 滑动窗口大小
            observation_days: 观察期天数
            target_gain: 目标涨幅
        """
        self.window_size = window_size
        self.observation_days = observation_days
        self.target_gain = target_gain
        
    def extract_sequences(self, stock_data):
        """
        从股票数据中提取符合条件的序列（优化版）
        
        Args:
            stock_data: DataFrame，包含股票数据
            
        Returns:
            list: 符合条件的序列列表
        """
        sequences = []
        
        # 按股票代码分组
        grouped = stock_data.groupby('st_code')
        
        print(f"开始处理 {len(grouped)} 只股票...")
        
        # 统计信息
        total_stocks = len(grouped)
        processed_stocks = 0
        successful_stocks = 0
        
        for stock_code, group in grouped:
            processed_stocks += 1
            
            if len(group) < self.window_size + self.observation_days:
                continue
                
            stock_sequences = self._extract_stock_sequences(stock_code, group)
            if stock_sequences:
                sequences.extend(stock_sequences)
                successful_stocks += 1
            
            # 进度显示
            if processed_stocks % 20 == 0:
                print(f"已处理 {processed_stocks}/{total_stocks} 只股票，成功提取 {len(sequences)} 个序列")
        
        print(f"序列提取完成！")
        print(f"处理股票数: {processed_stocks}")
        print(f"成功股票数: {successful_stocks}")
        print(f"总序列数: {len(sequences)}")
        
        return sequences
    
    def _extract_stock_sequences(self, stock_code, stock_group):
        """
        从单只股票中提取序列（优化版）
        
        Args:
            stock_code: 股票代码
            stock_group: 单只股票的数据组
            
        Returns:
            list: 该股票的序列列表
        """
        sequences = []
        
        # 按日期排序
        stock_group = stock_group.sort_values('trade_date')
        
        # 数据质量检查
        if not self._check_stock_data_quality(stock_group):
            return sequences
        
        # 滑动窗口提取序列
        for i in range(len(stock_group) - self.window_size - self.observation_days + 1):
            # 提取15天窗口数据
            window_data = stock_group.iloc[i:i + self.window_size]
            
            # 提取观察期数据
            observation_data = stock_group.iloc[i + self.window_size:i + self.window_size + self.observation_days]
            
            # 检查是否符合条件
            if self._check_sequence_condition(window_data, observation_data):
                sequence = self._create_sequence(stock_code, window_data, observation_data)
                if sequence:
                    sequences.append(sequence)
        
        return sequences
    
    def _check_stock_data_quality(self, stock_group):
        """检查股票数据质量"""
        try:
            # 检查必需字段
            required_fields = ['close', 'pct_chg']
            for field in required_fields:
                if field not in stock_group.columns:
                    return False
            
            # 检查数据连续性
            if len(stock_group) < self.window_size + self.observation_days:
                return False
            
            # 检查价格数据有效性
            close_data = stock_group['close'].dropna()
            if len(close_data) < self.window_size + self.observation_days:
                return False
            
            # 检查是否有异常值
            if (close_data <= 0).any():
                return False
            
            return True
            
        except Exception as e:
            print(f"数据质量检查失败: {e}")
            return False
    
    def _check_sequence_condition(self, window_data, observation_data):
        """
        检查序列是否符合条件（优化版）
        
        Args:
            window_data: 窗口期数据
            observation_data: 观察期数据
            
        Returns:
            bool: 是否符合条件
        """
        if len(observation_data) == 0:
            return False
        
        try:
            # 计算观察期内的累计涨幅
            start_price = window_data.iloc[-1]['close']
            end_price = observation_data.iloc[-1]['close']
            
            # 数据有效性检查
            if pd.isna(start_price) or pd.isna(end_price) or start_price <= 0:
                return False
            
            total_gain = (end_price - start_price) / start_price
            
            # 检查涨幅是否达到目标
            if total_gain >= self.target_gain:
                # 额外检查：确保不是异常波动
                if self._validate_gain_pattern(window_data, observation_data, total_gain):
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def _validate_gain_pattern(self, window_data, observation_data, total_gain):
        """验证涨幅模式的合理性"""
        try:
            # 检查价格变化的连续性
            window_prices = window_data['close'].values
            obs_prices = observation_data['close'].values
            
            # 检查是否有异常的价格跳跃
            all_prices = np.concatenate([window_prices, obs_prices])
            price_changes = np.diff(all_prices) / all_prices[:-1]
            
            # 如果单日涨幅超过20%，可能是异常数据
            if np.any(np.abs(price_changes) > 0.2):
                return False
            
            # 检查成交量合理性（如果有数据）
            if 'vol' in window_data.columns and 'vol' in observation_data.columns:
                avg_vol = window_data['vol'].mean()
                obs_vol = observation_data['vol'].mean()
                
                # 如果观察期成交量异常放大（超过10倍），可能是异常
                if obs_vol > avg_vol * 10:
                    return False
            
            return True
            
        except Exception as e:
            return True  # 如果验证失败，默认通过
    
    def _create_sequence(self, stock_code, window_data, observation_data):
        """
        创建序列对象（优化版）
        
        Args:
            stock_code: 股票代码
            window_data: 窗口期数据
            observation_data: 观察期数据
            
        Returns:
            dict: 序列对象
        """
        try:
            # 计算观察期涨幅
            start_price = window_data.iloc[-1]['close']
            end_price = observation_data.iloc[-1]['close']
            total_gain = (end_price - start_price) / start_price
            
            # 提取特征数据（优化版）
            features = []
            for _, row in window_data.iterrows():
                feature_vector = []
                for col in FEATURE_COLUMNS:
                    if col in row and not pd.isna(row[col]):
                        # 特殊处理某些字段
                        if col == 'close_max__20':
                            # 20日最高价，转换为相对价格
                            if row['close'] > 0:
                                feature_vector.append(float(row[col] / row['close']))
                            else:
                                feature_vector.append(1.0)
                        else:
                            feature_vector.append(float(row[col]))
                    else:
                        # 缺失值处理
                        if col == 'close_max__20':
                            feature_vector.append(1.0)  # 默认值
                        elif col in ['pct_chg', 'macd_macd', 'macd_dif', 'kdj_k', 'kdj_d', 'cci', 'wr_wr1']:
                            feature_vector.append(0.0)  # 技术指标默认值
                        else:
                            feature_vector.append(0.0)  # 其他字段默认值
                
                features.append(feature_vector)
            
            # 验证特征数据
            if len(features) != self.window_size:
                return None
            
            sequence = {
                'sequence_id': f"{stock_code}_{window_data.iloc[-1]['trade_date']}",
                'stock_code': stock_code,
                'start_date': window_data.iloc[0]['trade_date'],
                'end_date': window_data.iloc[-1]['trade_date'],
                'observation_start': observation_data.iloc[0]['trade_date'],
                'observation_end': observation_data.iloc[-1]['trade_date'],
                'features': features,
                'total_gain': total_gain,
                'success_count': 1,  # 初始值
                'total_count': 1,    # 初始值
                'success_rate': 1.0, # 初始值
                'success_score': 1.0, # 初始值
                'feature_count': len(FEATURE_COLUMNS),  # 特征数量
                'created_at': datetime.now()
            }
            
            return sequence
            
        except Exception as e:
            print(f"创建序列失败: {e}")
            return None
    
    def save_sequences_to_file(self, sequences, filename='extracted_sequences_optimized.txt'):
        """
        将序列保存到文件（优化版）
        
        Args:
            sequences: 序列列表
            filename: 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("优化版序列提取结果\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"总序列数: {len(sequences)}\n")
                f.write(f"特征字段数: {len(FEATURE_COLUMNS)}\n")
                f.write(f"特征字段: {', '.join(FEATURE_COLUMNS)}\n")
                f.write(f"窗口大小: {self.window_size} 天\n")
                f.write(f"观察期: {self.observation_days} 天\n")
                f.write(f"目标涨幅: {self.target_gain:.1%}\n\n")
                
                for i, seq in enumerate(sequences[:100]):  # 只显示前100个
                    f.write(f"序列 {i+1}\n")
                    f.write(f"序列ID: {seq['sequence_id']}\n")
                    f.write(f"股票代码: {seq['stock_code']}\n")
                    f.write(f"窗口期: {seq['start_date']} 到 {seq['end_date']}\n")
                    f.write(f"观察期: {seq['observation_start']} 到 {seq['observation_end']}\n")
                    f.write(f"累计涨幅: {seq['total_gain']:.2%}\n")
                    f.write(f"特征维度: {len(seq['features'])} x {len(seq['features'][0])}\n")
                    f.write("-" * 50 + "\n")
                
                if len(sequences) > 100:
                    f.write(f"\n... 还有 {len(sequences) - 100} 个序列未显示\n")
            
            print(f"序列已保存到文件: {filename}")
        except Exception as e:
            print(f"保存序列失败: {e}")
    
    def get_sequence_statistics(self, sequences):
        """获取序列统计信息"""
        if not sequences:
            return {}
        
        gains = [seq['total_gain'] for seq in sequences]
        stock_codes = list(set([seq['stock_code'] for seq in sequences]))
        
        stats = {
            'total_sequences': len(sequences),
            'unique_stocks': len(stock_codes),
            'gain_statistics': {
                'mean': np.mean(gains),
                'std': np.std(gains),
                'min': np.min(gains),
                'max': np.max(gains),
                'median': np.median(gains)
            },
            'feature_count': len(FEATURE_COLUMNS),
            'window_size': self.window_size,
            'observation_days': self.observation_days,
            'target_gain': self.target_gain
        }
        
        return stats
