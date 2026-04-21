"""
Daoquant 普通策略模板

适用场景：
1. 规则策略、指标策略、因子打分策略
2. 基于 numpy / pandas / scipy / sklearn 的统计模型策略
3. 需要复用平台内置 strategy.* 模块的自定义策略

上传限制说明（系统会校验 import）：
- 允许的标准库子集：
  math, statistics, decimal, datetime, time, json, re, copy, typing,
  collections, itertools, functools, dataclasses, random, warnings,
  logging, traceback, uuid, hashlib, enum, operator, heapq, bisect
- 允许的第三方库：
  numpy, pandas, scipy, sklearn, sqlalchemy, pymysql
- 允许的平台内模块：
  strategy.*
- 限制导入的库：
  os, sys, pathlib, shutil, tempfile, glob, importlib, subprocess,
  multiprocessing, threading, asyncio, requests, urllib, http, socket,
  akshare, tushare, baostock, yfinance, tensorflow, keras, jax,
  xgboost, lightgbm, catboost, backtrader, talib, matplotlib,
  seaborn, plotly, cv2, PIL, pickle, joblib, redis

使用说明：
1. 保留 strategy_main 作为入口函数名
2. 函数签名不要改，平台会按固定参数调用
3. 你可以直接运行本模板，它默认复用内置 Mark 策略
4. 想写自己的逻辑时，把 return mark_main(...) 换成你的实现
"""


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

    参数说明：
    - Init_fund: 初始资金
    - Investment_ratio: 投资比例
    - Hold_stock_num: 最大持仓数
    - Start_time: 回测开始日期，格式 YYYYMMDD
    - End_time: 回测结束日期，格式 YYYYMMDD
    - Optionfacname: 策略选择配置
    - Botfacname: 因子配置
    - sid: 当前策略配置 ID
    - uid: 当前用户 ID
    """

    print("普通策略模板已加载，当前示例复用内置 Mark 策略。")
    print("上传阶段会校验 import，请只使用平台开放的 Python 库。")
    print(f"回测区间: {Start_time} -> {End_time}")
    print(f"策略选择配置: {Optionfacname}")
    print(f"因子配置: {Botfacname}")

    # 这是一个可直接运行的示例。
    # 如果你要完全自定义，请保留入口签名，并用你自己的回测逻辑替换下面的调用。
    from strategy.策略.Mark import mark_main

    return mark_main(
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
