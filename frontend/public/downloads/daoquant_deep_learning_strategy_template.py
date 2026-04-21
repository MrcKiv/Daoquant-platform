"""
Daoquant 深度学习策略模板

适用场景：
1. 使用 PyTorch 做时序特征提取、打分或小型模型推理
2. 在回测前对股票特征进行张量化处理
3. 复用平台内置深度学习策略或在其基础上做扩展

上传限制说明（系统会校验 import）：
- 允许的标准库子集：
  math, statistics, decimal, datetime, time, json, re, copy, typing,
  collections, itertools, functools, dataclasses, random, warnings,
  logging, traceback, uuid, hashlib, enum, operator, heapq, bisect
- 允许的第三方库：
  numpy, pandas, scipy, sklearn, sqlalchemy, pymysql
- 深度学习额外开放：
  torch
- 允许的平台内模块：
  strategy.*
- 限制导入的库：
  os, sys, pathlib, shutil, tempfile, glob, importlib, subprocess,
  multiprocessing, threading, asyncio, requests, urllib, http, socket,
  akshare, tushare, baostock, yfinance, tensorflow, keras, jax,
  xgboost, lightgbm, catboost, backtrader, talib, matplotlib,
  seaborn, plotly, cv2, PIL, pickle, joblib, redis

使用说明：
1. 目前平台深度学习模板只开放 PyTorch 体系，不支持 TensorFlow / Keras / JAX
2. 不建议在策略里访问外部网络、读取本地权重文件或启动额外进程
3. 你可以直接运行本模板，它默认复用内置 Stock_RL 策略
4. 如需自定义，请保留 strategy_main 入口和固定签名
"""

import torch
import torch.nn as nn


class DemoScoreModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.network(x)


def build_demo_score():
    """
    这里演示一个最小的 Torch 前向推理流程。
    真实策略中，你可以把股票特征整理成 tensor 后再做打分。
    """

    features = torch.tensor([[0.18, 0.42, 0.33, 0.71]], dtype=torch.float32)
    model = DemoScoreModel()
    model.eval()

    with torch.no_grad():
        score = model(features).item()

    return score


def strategy_main(
    Init_fund,
    Investment_ratio,
    Hold_stock_num,
    Start_time,
    End_time,
    Optionfacname,
    Botfacname,
    sid,
    uid,
):
    """
    平台会按这个固定签名调用你的策略。
    """

    demo_score = build_demo_score()
    print("深度学习策略模板已加载，当前示例复用内置深度学习 RL 策略。")
    print("上传阶段会校验 import，请仅使用平台开放的 Python 库。")
    print(f"示例 Torch 打分结果: {demo_score:.4f}")
    print(f"回测区间: {Start_time} -> {End_time}")
    print(f"策略选择配置: {Optionfacname}")
    print(f"因子配置: {Botfacname}")

    # 这是一个可直接运行的示例。
    # 如果你要改成自己的深度学习逻辑，请保留入口签名，并替换下面的调用。
    from strategy.策略.Stock_RL import main as stock_rl_main

    return stock_rl_main(
        Init_fund,
        Investment_ratio,
        Hold_stock_num,
        Start_time,
        End_time,
        Optionfacname,
        Botfacname,
        sid,
        uid,
    )
