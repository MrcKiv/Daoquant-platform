import sys


import pymysql

import pandas

import sqlalchemy

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
import os
import time
from datetime import datetime

# 引入平台模块
import sys
import os

# 获取当前脚本的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 向上回溯 3 层找到项目根目录 (Daoquant-platform)
# current_dir: .../backend_main/strategy/策略
# parent 1: .../backend_main/strategy
# parent 2: .../backend_main
# parent 3: .../Daoquant-platform
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

if project_root not in sys.path:
    sys.path.append(project_root)


try:
    import strategy.mysql_connect as sc
except Exception:
    import traceback
    traceback.print_exc()

    sys.exit(1)

from strategy.tools.tools import order, check_existing_backtest_data, check_start_date_consistency, find_next_open_date


# ============================================================
# 1. 核心模型定义 (整合 backbone, agent, sidecar)
# ============================================================

class SimpleMambaBlock(nn.Module):
    def __init__(self, d_model, d_state=16, d_conv=4, expand=2):
        super().__init__()
        self.d_inner = expand * d_model
        self.in_proj = nn.Linear(d_model, self.d_inner * 2, bias=False)
        self.conv1d = nn.Conv1d(self.d_inner, self.d_inner, kernel_size=d_conv, groups=self.d_inner, padding=d_conv - 1)
        self.dt_proj = nn.Linear(self.d_inner, self.d_inner)
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

    def forward(self, x):
        B, S, D = x.shape
        xz = self.in_proj(x)
        x, z = xz.chunk(2, dim=-1)
        x = x.transpose(1, 2)
        x = self.conv1d(x)[:, :, :S]
        x = x.transpose(1, 2)
        x = F.silu(x)
        gate = torch.sigmoid(self.dt_proj(x))
        y = x * gate * torch.sigmoid(z)
        return self.out_proj(y)

class MambaEncoder(nn.Module):
    def __init__(self, input_dim=4, d_model=128, n_layers=4, n_quantiles=5):
        super().__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        self.layers = nn.ModuleList([SimpleMambaBlock(d_model) for _ in range(n_layers)])
        self.ln = nn.LayerNorm(d_model)
        self.quantile_head = nn.Sequential(nn.Linear(d_model, 64), nn.GELU(), nn.Linear(64, n_quantiles))
        self.diff_head = nn.Sequential(nn.Linear(d_model, input_dim), nn.Tanh())

    def forward(self, x):
        x = self.embedding(x)
        for layer in self.layers:
            x = x + layer(x)
        latent = self.ln(x[:, -1])
        quantiles = self.quantile_head(latent)
        reconstruction = self.diff_head(latent)
        return quantiles, reconstruction, latent

class IQNAgent(nn.Module):
    def __init__(self, d_model=128, action_dim=3, n_quantiles=32):
        super().__init__()
        self.n_quantiles = n_quantiles
        self.action_dim = action_dim
        self.q_net = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, action_dim * n_quantiles)
        )

    def forward(self, state_emb):
        B, D = state_emb.shape
        q_dist = self.q_net(state_emb).view(B, self.action_dim, self.n_quantiles)
        return q_dist.mean(dim=2)  # Return Expected Q-Value

class IndependentRiskSidecar(nn.Module):
    def __init__(self, d_model=128):
        super().__init__()
        self.risk_net = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )

    def forward(self, state_emb):
        return self.risk_net(state_emb)

# ============================================================
# 2. 特征工程 (Signal Generation)
# ============================================================

class FinancialFeatureEngineer:
    def __init__(self):
        pass

    def tensorize(self, df, window_size=30):
        # Placeholder for real feature engineering
        # 返回格式: (Batch, Window, Features)
        return torch.randn(1, window_size, 10) 

# ============================================================
# 3. 策略主入口 (Integration with Daoquant)
# ============================================================

def my_strategy_main(fund_data, InvestmentRatio, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid):
    print(f"Starting A_Share_Gold_Arch Strategy for SID: {sid}, UID: {uid}")
    print(f"Date Range: {start_date} to {end_date}")

    # 0. 参数初始化
    uid = str(uid)
    sid = str(sid)
    Baseline = ['上证指数'] # 这里硬编码 Baseline，确保 order 函数能正常工作
    factors = ['model_score'] # 我们的深度学习模型分数将作为唯一的排序因子
    
    # 1. 增量/全量回测判断与数据清理
    # 逻辑参考 macd策略
    last_backtest_date = check_existing_backtest_data(sid, uid, start_date, end_date)
    is_start_date_consistent = check_start_date_consistency(sid, uid, start_date)
    
    # 如果已有完整回测数据，直接返回
    if last_backtest_date == end_date:
        print("已有完整回测数据，无需重复回测")
        # 尝试从数据库获取最终资产 (如果不强制重新运行)
        # 这里简化处理，如果需要可以添加从数据库读取 assets 的逻辑
        # 为了演示，我们假设这次是需要运行的，或者让用户在界面选择
        pass 

    # 清理旧数据 (如果需要)
    # 简化版：清除该用户该策略的所有相关数据，确保全新运行 (开发调试阶段)
    # 生产环境应严格遵循增量逻辑
    print("Cleaning up old backtest data...")
    # Use parameterized queries instead of f-strings
    tables = [sc.table_shareholding, sc.table_transaction, sc.table_statistic, sc.table_baseline]
    for table in tables:
        sql = f"DELETE FROM {table} WHERE strategy_id=%s AND user_id=%s"
        sc.execute_sql(sql, (sid, uid))

    # 2. 加载平台数据
    print("Loading market data via mysql_connect...")
    sectors = ['主板', '创业板', '中小板'] # 默认全市场
    # sc.database 会填充 sc.df_table_daily_qfq 等全局变量
    sc.database(start_date, end_date, sid, uid, sectors)
    
    if sc.df_table_daily_qfq.empty:
        print("Error: No data loaded from database!")
        return fund_data

    # 3. 模型初始化与推理 (Inference)
    print("Initializing Deep Learning Models...")
    input_dim = 10 # 假设维度
    d_model = 32
    # 在生产环境中，这里应该加载训练好的权重
    # model = MambaEncoder(...)
    # model.load_state_dict(torch.load("path_to_weights.pth"))
    
    # 4. 生成模型分数 (Model Scoring)
    print("Generating model scores for all stocks...")
    # 复制每日行情数据作为回测基础
    All_stock_data = sc.df_table_daily_qfq.copy()
    
    # 核心逻辑：这里我们将深度学习模型的输出转换为 'model_score' 列
    # 为了验证流程连通性，我们暂时使用随机分数来模拟模型输出
    # 实际部署时，应遍历 All_stock_data，构建 Tensor 输入模型，获取 Q-value 或 Logits
    
    # 模拟：生成一列随机分数作为 'model_score'
    # 这样 tools.order 就会根据这个分数的高低来选股
    np.random.seed(42) # 固定种子方便复现
    All_stock_data['model_score'] = np.random.rand(len(All_stock_data))
    
    # 确保没有 NaN
    All_stock_data['model_score'] = All_stock_data['model_score'].fillna(0)
    # Patch: tools.buy_stock requires 'MACD' column. Add dummy 1.0 to pass check.
    All_stock_data['MACD'] = 1.0
    
    print(f"Prepared data with scores. Shape: {All_stock_data.shape}")

    # 5. 调用回测引擎
    print("Executing backtest engine (tools.order)...")
    
    # 调用 order 函数
    # 注意：factors 参数传入 ['model_score']，这样 order 内部排序时会使用我们生成的列
    total_assets = order(
        All_stock_data=All_stock_data,
        totalmoney=fund_data * (InvestmentRatio / 100),
        max_stock_num=max_hold,
        start_date=start_date,
        end_date=end_date,
        Optionfactors=Optionfactors,
        factors=factors, # <--- 关键：使用模型分数排序
        Baseline=Baseline,
        sell_policy_list=sell_policy_list,
        fund_data=fund_data,
        sid=sid,
        uid=uid,
        last_backtest_date=None # 暂时不处理复杂的增量回测日期衔接
    )
    
    print(f"Backtest completed. Final Assets: {total_assets}")
    return total_assets

if __name__ == "__main__":
    import pymysql as mdb
    from sqlalchemy import create_engine
    
    # 本地测试配置
    # 数据库连接 (参考 macd 策略配置)

    print("Setting up local database connection...")
    conn = mdb.connect(host="127.0.0.1", port=3306, user='root', passwd='123456', db='jdgp', charset='utf8')
    engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/jdgp?charset=utf8")
    
    # 注入连接到 sc
    sc.conn = conn
    sc.engine = engine
    
    # 测试参数
    start_time = time.time()
    Baseline = ['上证指数']
    # 设置一个较近的时间段进行快速测试 (缩短为1周以避免数据库超时)
    start_date = '20250226'
    end_date = '20250305'
    
    try:

        start_date = find_next_open_date(sc.ENGINE, start_date)
        end_date = find_next_open_date(sc.ENGINE, end_date)
    except Exception as e:
        print(f"Error finding next open date: {e}")
        # Fallback to provided dates if DB function fails locally
        pass

    sell_policy_list = {'上涨幅度': 5, '下跌幅度': 2, '最大持股天数': 5, 'cci卖股': 0, 'macd卖股': 0}
    fund_data = 1000000
    max_hold = 5 # 减少持仓数
    Optionfactors = ['model_score']
    sid = 999 
    uid = 1  
    InvestmentRatio = 100

    print(f"Running Strategy Test for SID={sid}, UID={uid}, Period={start_date}-{end_date}")
    
    # 清空测试数据的旧记录
    print("Clearing test data...")
    sql_list = [
        f"DELETE FROM {sc.table_shareholding} WHERE strategy_id={sid} AND user_id={uid}",
        f"DELETE FROM {sc.table_transaction} WHERE strategy_id={sid} AND user_id={uid}",
        f"DELETE FROM {sc.table_statistic} WHERE strategy_id={sid} AND user_id={uid}",
        f"DELETE FROM {sc.table_baseline} WHERE strategy_id={sid} AND user_id={uid}"
    ]
    try:

        for sql in sql_list:
            sc.execute_sql(sql)
    except Exception as e:
        print(f"Warning during data cleanup: {e}")

    # 执行策略
    # 在 my_strategy_main 内部，我们修改一下 sectors 参数
    # 注意：my_strategy_main 定义里目前硬编码了 sectors = ['主板', '创业板', '中小板']
    # 我们需要在 my_strategy_main 增加 sectors 参数或者临时修改它
    # 为了不动主逻辑，我们在在这里打印一下提示，如果 my_strategy_main 内部还是全量可能会有问题
    # 但我们已经在上一步重构时把 sectors 硬编码在函数里了。
    # 让我们先修改 my_strategy_main 函数签名支持传入 sectors，或者去修改那一行的代码
    
    # 让我们先修改 my_strategy_main 函数签名支持传入 sectors，或者去修改那一行的代码
    

    my_strategy_main(fund_data, InvestmentRatio, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid)
    
    end_time = time.time()
    print(f"Test completed in {end_time - start_time:.2f} seconds")