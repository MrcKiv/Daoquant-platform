from xtquant import xtdatacenter as xtdc
from xtquant import xtdata
import time
import pandas as pd
from sqlalchemy import create_engine

# ====== 1. 初始化 ======
print("正在初始化行情模块...")
xtdc.set_token('210097f139884e84e93e28e6045b6266325b5023')
addr_list = [
    '115.231.218.73:55310',
    '115.231.218.79:55310',
    '42.228.16.211:55300',
    '42.228.16.210:55300',
    '36.99.48.20:55300',
    '36.99.48.21:55300'
]
xtdc.set_allow_optmize_address(addr_list)
xtdc.init()
print("✅ 行情模块初始化完成")

# ====== 2. 数据库连接 ======
# 密码: 920416, 数据库: stocks
engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/stocks?charset=utf8")

# ====== 3. 核心功能函数 ======

def save_chunk_to_mysql(stock_list, start_date, end_date):
    """
    处理一个小批次：下载 -> 读取 -> 存库
    """
    # --- 1. 强制下载历史数据到本地缓存 ---
    for stock in stock_list:
        xtdata.download_history_data(stock, period='1d', start_time=start_date, end_time=end_date)
    
    # 稍作等待，确保文件写入
    time.sleep(1)

    # --- 2. 从本地读取数据 ---
    # 使用 start_time 和 end_time 精确获取范围
    data_1d = xtdata.get_market_data_ex(
        field_list=["time", "open", "high", "low", "close", "volume"],
        stock_list=stock_list,
        period="1d",
        start_time=start_date,
        end_time=end_date,
        dividend_type="front", # 前复权
        fill_data=True,
    )

    # --- 3. 转换并存入 MySQL ---
    all_dfs = []
    for stock_code, df in data_1d.items():
        if not df.empty:
            df_copy = df.copy()
            df_copy['stock_code'] = stock_code
            
            # 时间戳转换
            df_copy['time'] = (
                pd.to_datetime(df_copy["time"], unit="ms", utc=True)
                .dt.tz_convert("Asia/Shanghai")
                .dt.tz_localize(None)
            )
            
            # 重命名列以匹配你的数据库结构
            df_copy.rename(columns={
                'stock_code': 'st_code',
                'time': 'trade_date',
                'volume': 'vol',
            }, inplace=True)
            
            all_dfs.append(df_copy)

    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        # 存入 stock_1d 表
        combined_df.to_sql("stock_1d", engine, if_exists="append", index=False)
        return len(combined_df)
    else:
        return 0

def download_all_ashares_daily(start_date, end_date):
    # 1. 获取全市场股票列表
    print("正在获取全市场A股列表...")
    # 获取沪深A股板块的所有成分股
    all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
    
    # 如果获取不到(有时板块数据需下载)，可以使用备用方案：获取所有合约
    if not all_stocks:
        print("⚠️ '沪深A股'板块为空，尝试获取全市场合约...")
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股') # 再次尝试或检查板块数据
        # 如果还是空，可以用 get_market_data 返回所有 keys，这里假设板块数据正常
    
    print(f"📊 共获取到 {len(all_stocks)} 只股票，准备开始下载...")
    
    # 2. 分批处理配置
    batch_size = 50  # 每次处理50只股票（防内存溢出）
    total_stocks = len(all_stocks)
    total_saved_rows = 0
    
    # 3. 循环分批
    for i in range(0, total_stocks, batch_size):
        batch_stocks = all_stocks[i : i + batch_size]
        
        print(f"🔄 [进度 {i}/{total_stocks}] 正在处理: {batch_stocks[0]} 等 {len(batch_stocks)} 只...")
        
        try:
            # 调用处理函数
            rows = save_chunk_to_mysql(batch_stocks, start_date, end_date)
            total_saved_rows += rows
            print(f"   ✅ 本批次入库 {rows} 条记录")
        except Exception as e:
            print(f"   ❌ 本批次发生错误: {e}")

    print("="*30)
    print(f"🏁 全市场下载任务完成！")
    print(f"📈 总计入库数据行数: {total_saved_rows}")
    print("="*30)

# ====== 主程序 ======
if __name__ == "__main__":
    start_time_clock = time.time()
    
    # 设置你想要的时间范围 (格式: YYYYMMDD)
    START_DATE = '20200101'
    END_DATE   = '20251217'
    
    print(f"📅 目标时间范围: {START_DATE} 至 {END_DATE}")
    
    download_all_ashares_daily(START_DATE, END_DATE)
    
    print(f"⏱️ 总耗时: {(time.time() - start_time_clock)/60:.2f} 分钟")