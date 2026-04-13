import pymysql
import os
import sys

pymysql.install_as_MySQLdb()
try:
    # 猴子补丁：伪装成 mysqlclient 2.2.0 以骗过 Django 检查
    import MySQLdb
    MySQLdb.__version__ = "2.2.6"
    MySQLdb.version_info = (2, 2, 6, "final", 0)
except ImportError:
    pass

# 猴子补丁：设置 tornado.options.ROOT_PATH 以修复 trest ConfigError
try:
    from tornado.options import options, define
    # 计算 items 根目录
    # 当前文件: backend_main/backend/__init__.py
    # 目标 ROOT_PATH: backend_main/ths_trade
    
    current_dir = os.path.dirname(os.path.abspath(__file__)) # backend_main/backend
    backend_main = os.path.dirname(current_dir) # backend_main
    ths_trade_path = os.path.join(backend_main, 'ths_trade')
    
    if not hasattr(options, 'ROOT_PATH'):
        define('ROOT_PATH', default=ths_trade_path, help='Project Root Path')
    
    # 确保有值
    # 注意：如果 options 已经被定义过，直接赋值
    options.ROOT_PATH = ths_trade_path
        
    print(f"Patched ROOT_PATH to: {options.ROOT_PATH}")
except ImportError:
    print("Tornado not found, skipping ROOT_PATH patch")
except Exception as e:
    print(f"Error patching ROOT_PATH: {e}")