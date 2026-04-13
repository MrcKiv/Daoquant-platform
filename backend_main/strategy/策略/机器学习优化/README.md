# 优化版股票筛选系统

## 概述

这是一个基于机器学习的股票筛选系统，使用滑动窗口、序列聚类和模式匹配技术来识别具有潜在上涨趋势的股票。

## 主要特性

- **多维度特征分析**：使用12个技术指标作为特征
- **智能聚类算法**：支持K-means和层次聚类，自动选择最优聚类数量
- **多相似度度量**：结合余弦相似度、欧几里得距离、曼哈顿距离和皮尔逊相关系数
- **综合评分机制**：结合匹配度、成功率和稳定性评分
- **DataFrame输出**：直接返回标准化的DataFrame格式，便于集成到其他系统

## DataFrame输出格式

系统的主要输出是一个pandas DataFrame，包含以下列：

```python
['st_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 
 'pct_chg', 'vol', 'cci', 'pre_cci', 'macd_macd', 'pre_macd_macd', 'score']
```

### 列说明

- `st_code`: 股票代码
- `trade_date`: 交易日期
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `pre_close`: 前收盘价
- `pct_chg`: 涨跌幅
- `vol`: 成交量
- `cci`: CCI指标
- `pre_cci`: 前一日CCI指标
- `macd_macd`: MACD指标
- `pre_macd_macd`: 前一日MACD指标
- `score`: 综合评分（按此列降序排列）

## 快速使用

### 方法1：直接调用接口函数

```python
from main import run_stock_screening

# 运行股票筛选系统
result_df = run_stock_screening(
    training_start_date='2025-01-01',
    training_end_date='2025-04-01',
    current_start_date='2025-04-02',
    current_end_date='2025-04-15'
)

# 查看结果
print(result_df.head())
```

### 方法2：使用系统实例

```python
from main import StockScreeningSystem

# 创建系统实例
system = StockScreeningSystem()

# 运行完整流程
result_df = system.run_complete_pipeline(
    training_start_date='2025-01-01',
    training_end_date='2025-04-01',
    current_start_date='2025-04-02',
    current_end_date='2025-04-15'
)

# 查看结果
print(result_df.head())
```

### 方法3：分步执行

```python
from main import StockScreeningSystem

# 创建系统实例
system = StockScreeningSystem()

# 步骤1：提取训练序列
sequences = system.extract_training_sequences('2025-01-01', '2025-04-01')

# 步骤2：训练聚类模型
clustering_results = system.train_clustering_model(sequences)

# 步骤3：匹配当前股票
result_df = system.match_current_stocks('2025-04-02', '2025-04-15')

# 查看结果
print(result_df.head())
```

## 配置参数

主要配置参数在 `config.py` 中：

```python
# 策略参数
WINDOW_SIZE = 15              # 滑动窗口大小
OBSERVATION_DAYS = 3          # 观察天数
TARGET_GAIN = 0.02           # 目标涨幅
MATCH_THRESHOLD = 0.70       # 匹配阈值
MIN_SAMPLE_SIZE = 5          # 最小样本数

# 特征字段
FEATURE_COLUMNS = [
    'close', 'pct_chg', 'vol',           # 基础价格和成交量
    'macd_macd', 'macd_dif',             # MACD指标
    'ema12', 'ema26',                     # 指数移动平均线
    'kdj_k', 'kdj_d',                    # KDJ指标
    'cci', 'wr_wr1',                     # CCI和威廉指标
    'close_max__20'                       # 20日最高价
]
```

## 文件结构

```
机器学习优化/
├── main.py                 # 主程序入口
├── config.py              # 配置文件
├── database.py            # 数据库管理
├── sequence_extractor.py  # 序列提取
├── sequence_clustering.py # 序列聚类
├── stock_matcher.py       # 股票匹配
├── test_system.py         # 系统测试
├── quick_start.py         # 快速启动
├── test_dataframe_output.py # DataFrame输出测试
├── requirements.txt       # 依赖包
└── README.md             # 说明文档
```

## 安装和运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置数据库连接（在 `config.py` 中）

3. 运行系统：
```bash
python main.py
```

4. 测试DataFrame输出：
```bash
python test_dataframe_output.py
```

## 核心算法

### 1. 序列提取
- 使用滑动窗口提取固定长度的价格序列
- 筛选出后续观察期内达到目标涨幅的序列
- 计算多维度技术指标作为特征

### 2. 序列聚类
- 使用RobustScaler进行特征标准化
- 应用PCA进行降维
- 使用轮廓系数、Calinski-Harabasz指数和Davies-Bouldin指数评估聚类质量
- 支持K-means和层次聚类算法

### 3. 股票匹配
- 计算当前股票序列与聚类中心的多种相似度
- 使用加权平均组合不同相似度度量
- 结合匹配度和聚类成功率计算最终分数

### 4. 评分机制
- 匹配分数（50%）：当前股票与聚类模式的匹配程度
- 成功分数（30%）：聚类模式的历史成功率
- 稳定性分数（20%）：聚类模式的收益稳定性

## 输出结果

系统返回的DataFrame按综合评分降序排列，包含：
- 股票基本信息（代码、日期、价格等）
- 技术指标数据
- 综合评分

可以直接用于：
- 股票筛选和排序
- 进一步的分析和处理
- 集成到其他交易系统

## 注意事项

1. 确保数据库连接正常
2. 数据时间范围要合理设置
3. 根据实际数据情况调整策略参数
4. 建议先用小数据集测试系统功能

## 故障排除

如果遇到问题，请检查：
1. 数据库连接配置
2. 数据时间范围设置
3. 策略参数配置
4. 依赖包安装情况

## 扩展功能

系统支持以下扩展：
- 添加新的技术指标
- 调整聚类算法
- 修改评分权重
- 增加新的相似度度量
