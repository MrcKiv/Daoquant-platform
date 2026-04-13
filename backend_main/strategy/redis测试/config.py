# config.py

from sqlalchemy import create_engine

# ------------------------
# Redis 配置
# ------------------------
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0
# Redis 不设置 TTL，永久保存
# Redis 键命名格式：stock:{date}，例如 stock:2025-07-30

# ------------------------
# MySQL 配置
# ------------------------
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_HOST = '127.0.0.1'
DB_PORT = '3306'
DB_NAME = 'jdgp'  # 含空格，连接时注意 URL 编码

# 表名
TABLE_NAME = 'partition_table'

# SQLAlchemy Engine
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# ------------------------
# 股票数据字段（用于 SELECT 查询）
# ------------------------
FIELDS = [
    'st_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'rsv', 'kdj_k', 'kdj_d',
    'kdj_j', 'ema26', 'ema12', 'macd_dif', 'macd_dea', 'macd_macd',
    'wr_wr1', 'wr_wr2', 'boll_boll', 'boll_ub', 'boll_lb', 'week_ema_short',
    'week_ema_long', 'week_macd_dif', 'lastweek_macd_dif', 'lastlastweek_macd_dif',
    'week_macd_dea', 'week_macd_macd', 'lastweek_macd_macd', 'lastlastweek_macd_macd',
    'TYP', 'ma_TYP_14', 'AVEDEV', 'cci', 'last_dif', 'pre_macd_macd', 'pre_pre_macd_macd',
    'pre_cci', 'close_max__20', 'macd_max__20', 'pre_close', 'pct_chg'
]

# ------------------------
# 缓存设置
# ------------------------
CACHE_DAYS = 60  # 可调整为 30
REDIS_KEY_TEMPLATE = "stock:{date}"  # 每日一个 Key，Value 是该日所有股票数据的字典，key 为 st_code

# ------------------------
# 查询输出设置
# ------------------------
SHOW_ROW_LIMIT = 10  # 查询展示前10条记录
