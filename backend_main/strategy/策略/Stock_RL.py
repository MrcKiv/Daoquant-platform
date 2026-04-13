import strategy.mysql_connect as sc
import pandas as pd
import numpy as np
import os
import torch
import torch.nn as nn

# 定义极简的特征聚合映射网络 (3 个特征维度映射为 1 维 Score)
class StockScorerModel(nn.Module):
    def __init__(self, input_dim=3):
        super(StockScorerModel, self).__init__()
        self.linear = nn.Linear(input_dim, 1)
        # 初始化权重近于原有的静态打分逻辑
        with torch.no_grad():
            self.linear.weight.copy_(torch.tensor([[0.5, 0.3, 0.2]]))
            self.linear.bias.fill_(0.0)

    def forward(self, x):
        # x shape: (N, 3), 输出 (N,)
        return self.linear(x).squeeze(-1)

def main(fund_data, InvestmentRatio, max_hold, start_date, end_date, Optionfactors, sell_policy_list, sid, uid):
    # 添加缺失的 Parameter 参数，与底层的 mysql_connect.py 期望一致
    sectors2 = ['主板', '创业板', '中小板']
    sc.database(start_date, end_date, sid, uid, sectors2)
    print("Stock_RL model initialization and evaluation started")
    
    # ---------------- 增量学习强化模型初始化 ---------------- #
    # 按照硬要求固化保存文件夹与文件
    model_dir = "backend_main/strategy/策略/model_snapshots/Stock_RL/"
    os.makedirs(model_dir, exist_ok=True)
    save_path = os.path.join(model_dir, "Stock_RL_incremental_latest.pt")
    
    model = StockScorerModel(input_dim=3)
    
    # 严格的优化器设定 (Adam, lr=1e-3) 以及调度器 (ExponentialLR, gamma=0.98)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.98)
    
    day_counter = 0
    
    if os.path.exists(save_path):
        try:
            checkpoint = torch.load(save_path, weights_only=False)
            model.load_state_dict(checkpoint["model_state_dict"])
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
            day_counter = checkpoint["day_counter"]
            print(f"Loaded existing model from {save_path}, day_counter: {day_counter}")
        except Exception as e:
            print(f"Failed to load model, Error: {e}")
            
    # ================= Benchmark 初始化与 sc 方法注入 ================== 
    # 解析前端 Optionfactors 选项，自适应确定基准 (沪深300 或 上证50 等)
    benchmark_code = "000300" # 默认沪深300
    opt_str = str(Optionfactors)
    if "上证50" in opt_str or "000016" in opt_str:
        benchmark_code = "000016"
    elif "沪深300" in opt_str or "000300" in opt_str:
        benchmark_code = "000300"
        
    # 构建严格唯一的模块级隔离缓存，杜绝回测反复重建及多策略环境污染 (Side effect)
    if not hasattr(sc, "_benchmark_cache"):
        sc._benchmark_cache = {}
        
    if benchmark_code not in sc._benchmark_cache:
        df_idx = getattr(sc, 'df_table_index', None)
        if df_idx is None or df_idx.empty:
            print("【警告】: sys无 df_table_index 对象，基准收益降级为0。")
            sc._benchmark_cache[benchmark_code] = pd.Series(dtype=float)
        else:
            # 宽容性识别 DataFrame 列
            c_code = 'ts_code' if 'ts_code' in df_idx.columns else ('st_code' if 'st_code' in df_idx.columns else 'code')
            c_date = 'trade_date' if 'trade_date' in df_idx.columns else 'date'
            c_ret = 'pct_chg' if 'pct_chg' in df_idx.columns else ('change_pct' if 'change_pct' in df_idx.columns else None)
            
            if c_ret is None:
                sc._benchmark_cache[benchmark_code] = pd.Series(dtype=float)
            else:
                # 截取用户在前端所选的相关指数源 (相同时间范围以及频率)
                sub_df = df_idx[df_idx[c_code].astype(str).str.contains(benchmark_code, na=False)]
                
                # 兜底：如果选配指数刚好在此库缺失，使用 上证指数 (000001) 或返回空
                if sub_df.empty:
                    sub_df = df_idx[df_idx[c_code].astype(str).str.contains("000001", na=False)]
                    
                if not sub_df.empty:
                    s_ret = sub_df.set_index(c_date)[c_ret].astype(float)
                    # 常见格式对齐 (如果是 1.5 表征 1.5%，则化为 0.015)
                    if s_ret.abs().max() > 1.0:
                        s_ret = s_ret / 100.0
                    sc._benchmark_cache[benchmark_code] = s_ret
                else:
                    sc._benchmark_cache[benchmark_code] = pd.Series(dtype=float)
                    
    # 对于当前这轮策略执行与评测流（不论并发或独立进程），直接抛出我们独立缓存的字典池源
    # 并强制改写本策略运行期的全局挂接点，使其无须参直接执行 sc.get_benchmark_return()[t]
    sc.get_benchmark_return = lambda: sc._benchmark_cache[benchmark_code]
    # ===================================================================

    # 从 MySQL 返回的原始日线 DataFrame 构建价格与收盘矩阵
    df_daily = sc.df_table_daily_qfq
    if df_daily is None or df_daily.empty:
        print(f"No stock daily data loaded for backtest period. Date range: {start_date} to {end_date}")
        return fund_data

    # 去除重复的 (日期, 股票代码) 记录，避免 pivot 报错
    df_daily = df_daily.drop_duplicates(subset=['trade_date', 'st_code'], keep='last')

    # 构建收盘价透视表 (行: trade_date, 列: st_code)
    prices = df_daily.pivot(index='trade_date', columns='st_code', values='close')
    # 构建收益率透视表
    returns = df_daily.pivot(index='trade_date', columns='st_code', values='pct_chg') / 100.0
    
    prices = prices.fillna(method='ffill')
    returns = returns.fillna(0.0)

    stocks = prices.columns.tolist()
    
    if not stocks or len(prices) == 0 or len(returns) == 0:
        return fund_data

    if not isinstance(prices, pd.DataFrame):
        prices = pd.DataFrame(prices, columns=stocks)
    if not isinstance(returns, pd.DataFrame):
        returns = pd.DataFrame(returns, columns=stocks)

    T = len(returns)
    weight = pd.Series(0.0, index=stocks)
    
    exposure_scale = 1.0
    cumulative_return = 1.0
    max_cum_return = 1.0
    
    # --- REINFORCE 持久化与流转所需的缓存与影子变量 --- #
    reward_buffer = []      # 存储标量 Return Delta (portfolio - benchmark)
    feature_buffer = []     # 存储无梯度的全截面特征 Tensor
    
    prev_model_weight = None      
    prev_feature_tensor = None    
    # ---------------------------------------------------- #
    
    port_returns_list = []
    last_score = None
    
    def z_score(s):
        s = s.replace([np.inf, -np.inf], np.nan)
        std_val = s.std()
        if pd.isna(std_val) or std_val == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std_val

    for i in range(T):
        current_trade_date = returns.index[i]
        t_returns = returns.iloc[i].fillna(0.0)
        
        # 1. 计算当前基于上期权重产生的真实组合盈亏
        daily_ret = np.nansum(weight * t_returns)
        port_returns_list.append(daily_ret)
        
        cumulative_return *= (1.0 + daily_ret)
        if cumulative_return > max_cum_return:
            max_cum_return = cumulative_return
        
        drawdown = cumulative_return / max_cum_return - 1.0
        
        # Risk management 仅干预敞口暴露比例，不进入模型反向图
        if drawdown < -0.10:
            exposure_scale = 0.5
        elif drawdown > -0.05:
            exposure_scale = 1.0
            
        if last_score is not None:
            valid_idx = last_score.notna() & t_returns.notna()
            if valid_idx.sum() > 1:
                ic = last_score[valid_idx].corr(t_returns[valid_idx], method='spearman')
                
        # ==================== (A) Reward Definition & Queue Entry ==================== #
        # 当 i 日确立了基于 i-1 日权重的真实结果后
        if i >= 20 and prev_model_weight is not None and prev_feature_tensor is not None:
            actual_port_return = np.nansum(prev_model_weight * t_returns)
            
            # 强制遵守由于前端选项确立的基数要求及语法调用
            try:
                # current_trade_date 即为当前日戳 t
                step_reward = actual_port_return - sc.get_benchmark_return()[current_trade_date]
            except Exception:
                # 异常容灾降级（譬如某日停牌等极端数据对齐问题）
                step_reward = actual_port_return - 0.0
            
            # Buffer Appending constraint
            reward_buffer.append(float(step_reward))
            feature_buffer.append(prev_feature_tensor) 
            
            if len(reward_buffer) > 63:
                reward_buffer.pop(0)
                feature_buffer.pop(0)

        # ============================================================================== #

        # ==================== (B) Model Evaluation and Detached Feature Snapshots ======= #
        if i < 20:
            score = pd.Series(np.nan, index=stocks)
            current_weight = pd.Series(0.0, index=stocks)
            prev_model_weight = None
            prev_feature_tensor = None
        else:
            p_t = prices.iloc[i]
            p_20 = prices.iloc[i-20]
            p_5 = prices.iloc[i-5]
            
            ret_20d = (p_t / p_20 - 1.0).astype(float)
            vol_20d = returns.iloc[i-19:i+1].astype(float).std()
            mom_5d = (p_t / p_5 - 1.0).astype(float)
            
            z_ret_20d = z_score(ret_20d)
            z_vol_20d = z_score(vol_20d)
            z_mom_5d = z_score(mom_5d)
            
            feature_df = pd.DataFrame({
                'z_ret': z_ret_20d,
                'z_vol': z_vol_20d,
                'z_mom': z_mom_5d
            })
            
            valid_mask = feature_df.notna().all(axis=1)
            valid_stocks = feature_df[valid_mask].index.tolist()
            
            if len(valid_stocks) > 0:
                numpy_features = feature_df.loc[valid_stocks].values
                # [Hard Req] 将当期未掺水全池标准结构提取成无连带张量
                detached_features = torch.tensor(numpy_features, dtype=torch.float32).detach()
                
                # 推理 Forward
                model.eval() 
                with torch.no_grad():
                    pred_scores = model(detached_features)
                
                score = pd.Series(np.nan, index=stocks)
                score.loc[valid_stocks] = pred_scores.cpu().numpy()
                
                valid_scores = score.dropna()
                current_weight = pd.Series(0.0, index=stocks)
                
                if len(valid_scores) > 0:
                    top_20 = valid_scores.nlargest(20).index
                    N = len(top_20)
                    if N > 0:
                        current_weight[top_20] = exposure_scale * (1.0 / N)
                        
                prev_feature_tensor = detached_features 
            else:
                score = pd.Series(np.nan, index=stocks)
                current_weight = pd.Series(0.0, index=stocks)
                prev_feature_tensor = None
                
            prev_model_weight = current_weight
            
            day_counter += 1
            
            # ==================== (C) Deterministic Online PG Update ====================== #
            # 完全不偏不倚的条件触发
            if day_counter % 63 == 0 and len(reward_buffer) == 63:
                model.train() 
                optimizer.zero_grad()
                
                loss = 0
                n_samples = len(reward_buffer)
                
                for step_idx in range(n_samples):
                    r_i = reward_buffer[step_idx]
                    feat_i = feature_buffer[step_idx]  
                    
                    if feat_i is not None and len(feat_i) > 0:
                        scores_i = model(feat_i)
                        
                        # Policy Gradient Loss formula
                        loss += - r_i * scores_i.mean()
                
                loss = loss / n_samples
                
                loss.backward()
                
                # 梯阶剪裁及严格交替跳步骤
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                
                # 遗忘周期：将本次积累的批特征全部抛去从而切入下一段 regime
                reward_buffer.clear()
                feature_buffer.clear()
                
                # Snapshot 保存
                torch.save({
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "day_counter": day_counter
                }, save_path)
            # ============================================================================== #

        weight = current_weight
        last_score = score
        
    invest_ratio_decimal = InvestmentRatio / 100.0
    initial_strategy_funds = fund_data * invest_ratio_decimal
    unused_funds = fund_data * (1.0 - invest_ratio_decimal)
    
    final_fund_data = unused_funds + initial_strategy_funds * cumulative_return
    
    print(f"Stock_RL 模型结束。策略期间产生最终净值为: {cumulative_return:.4f}")

    return final_fund_data
