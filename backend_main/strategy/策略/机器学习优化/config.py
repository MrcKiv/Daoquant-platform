# -*- coding: utf-8 -*-
"""
优化版配置文件
增加了更多技术指标字段
"""

# 数据库配置
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'stockdb'

# 策略参数
WINDOW_SIZE = 60  # 滑动窗口大小
OBSERVATION_DAYS = 5  # 观察期天数
TARGET_GAIN = 0.05  # 目标涨幅
MATCH_THRESHOLD = 0.70  # 匹配度阈值
MIN_SAMPLE_SIZE = 10  # 最小样本数量

# 特征字段（优化版 - 增加了更多技术指标）
FEATURE_COLUMNS = [
    'close', 'pct_chg', 'vol',           # 基础价格和成交量
    'macd_macd', 'macd_dif',             # MACD指标
    'ema12', 'ema26',                     # 指数移动平均线
    'kdj_k', 'kdj_d',                    # KDJ指标
    'cci', 'wr_wr1',                     # CCI和威廉指标
    'close_max__20'                       # 20日最高价
]

# 数据库表名
STOCK_DATA_TABLE = '前复权日线行情_移动股池'      # 当前股票数据表（用于匹配）
TRAINING_DATA_TABLE = '前复权日线行情_移动股池'              # 训练数据表（用于提取序列和聚类）
STOCK_LABEL_TABLE = '股票标签'
INDUSTRY_TAG_TABLE = 'advanced_industry_tags'

# 优化版特有配置
FEATURE_WEIGHTS = {
    'price': 0.3,      # 价格相关指标权重
    'trend': 0.3,      # 趋势指标权重
    'momentum': 0.2,   # 动量指标权重
    'volume': 0.2      # 成交量指标权重
}

# 聚类优化参数
CLUSTERING_CONFIG = {
    'max_clusters': 50,      # 最大聚类数量
    'min_samples_per_cluster': 3,  # 每个聚类最小样本数
    'silhouette_threshold': 0.3    # 轮廓系数阈值
}