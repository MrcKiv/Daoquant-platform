# import struct
# import mmap
# import os
# import json
#
# # ✅ 字段信息（与 export_to_bin.py 保持完全一致）
# FIELDS = [
#     'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg',
#     'vol', 'amount', 'rsv', 'kdj_k', 'kdj_d', 'kdj_j', 'ema26', 'ema12', 'macd_dif',
#     'last_dif', 'macd_dea', 'macd_macd', 'pre_macd_macd', 'pre_pre_macd_macd',
#     'wr_wr1', 'wr_wr2', 'boll_boll', 'boll_ub', 'boll_lb', 'week_ema_short',
#     'week_ema_long', 'week_macd_dif', 'lastweek_macd_dif', 'lastlastweek_macd_dif',
#     'week_macd_dea', 'week_macd_macd', 'lastweek_macd_macd', 'lastlastweek_macd_macd',
#     'TYP', 'ma_TYP_14', 'AVEDEV', 'cci', 'pre_cci', 'close_max__20', 'macd_max__20'
# ]
#
# STRUCT_FMT = '<I' + 'f' * (len(FIELDS) - 1)
# RECORD_SIZE = struct.calcsize(STRUCT_FMT)
#
#
# def read_range_from_bin(symbol: str, start: int = 0, end: int = 10, bin_dir='bin_data'):
#     """
#     从 .bin 文件中读取某支股票的第 start~end 条记录
#     """
#     path = os.path.join(bin_dir, f'{symbol}.bin')
#     if not os.path.exists(path):
#         raise FileNotFoundError(f'❌ 未找到文件: {path}')
#
#     results = []
#     with open(path, 'rb') as f:
#         mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
#         total_records = mm.size() // RECORD_SIZE
#         end = min(end, total_records)
#
#         for i in range(start, end):
#             offset = i * RECORD_SIZE
#             data = mm[offset:offset + RECORD_SIZE]
#             unpacked = struct.unpack(STRUCT_FMT, data)
#
#             row = {FIELDS[j]: (str(val) if j == 0 else round(val, 4)) for j, val in enumerate(unpacked)}
#             results.append(row)
#
#         mm.close()
#     return results
#
#
# def read_range_all_stocks(symbols: list[str], start: int = 0, end: int = 10, bin_dir='bin_data'):
#     """
#     ✅ 一次读取多个股票的第 start~end 条记录
#     返回字典结构：{ '000001.SZ': [row1, row2, ...], '600000.SH': [...], ... }
#     """
#     all_data = {}
#     for symbol in symbols:
#         try:
#             rows = read_range_from_bin(symbol, start, end, bin_dir)
#             all_data[symbol] = rows
#         except FileNotFoundError:
#             print(f"⚠️ 缺失二进制文件：{symbol}")
#     return all_data
#
#
# def read_stock_by_date_range(symbol: str, start_date: str, end_date: str, bin_dir='bin_data'):
#     """
#     ✅ 从某支股票中读取某日期范围内的记录（使用 .idx 索引）
#     """
#     idx_path = os.path.join(bin_dir, f'{symbol}.idx')
#     if not os.path.exists(idx_path):
#         raise FileNotFoundError(f'未找到索引文件: {idx_path}')
#
#     with open(idx_path, 'r', encoding='utf-8') as f:
#         index = json.load(f)
#
#     sorted_dates = sorted([int(d) for d in index.keys()])
#     start_int, end_int = int(start_date), int(end_date)
#     line_nums = [index[str(d)] for d in sorted_dates if start_int <= d <= end_int]
#     if not line_nums:
#         return []
#     return read_range_from_bin(symbol, min(line_nums), max(line_nums)+1, bin_dir)
#
#
# def read_all_stocks_by_date(target_date: str, bin_dir='bin_data'):
#     """
#     ✅ 给定某个日期，读取所有股票在该日的数据（如果有）
#     """
#     results = {}
#     for filename in os.listdir(bin_dir):
#         if filename.endswith('.idx'):
#             symbol = filename.replace('.idx', '')
#             idx_path = os.path.join(bin_dir, filename)
#             bin_path = os.path.join(bin_dir, f'{symbol}.bin')
#
#             try:
#                 with open(idx_path, 'r', encoding='utf-8') as f:
#                     index = json.load(f)
#                 if target_date in index:
#                     row = read_range_from_bin(symbol, index[target_date], index[target_date]+1, bin_dir)[0]
#                     results[symbol] = row
#             except Exception as e:
#                 print(f"⚠️ 错误: {symbol} - {e}")
#
#     return results
#
#
# # ✅ 示例运行
# if __name__ == '__main__':
#     print('🔹 测试: 单支股票按行号读取')
#     data = read_range_from_bin('000001.SZ', 0, 5)
#     for row in data:
#         print(row)
#
#     print('\n🔸 测试: 多支股票读取')
#     symbols = ['000001.SZ', '000002.SZ']
#     result = read_range_all_stocks(symbols, 0, 3)
#     for symbol, rows in result.items():
#         print(f"\n📌 {symbol}:")
#         for r in rows:
#             print(r)
#
#     print('\n✅ 测试: 读取某支股票指定日期范围')
#     result = read_stock_by_date_range('000001.SZ', '20220101', '20220110')
#     for r in result:
#         print(r)
#
#     print('\n📅 测试: 所有股票指定日期横截面')
#     cross_section = read_all_stocks_by_date('20220104')
#     for symbol, row in cross_section.items():
#         print(f'{symbol}:', row)

import struct
import mmap
import os
import json

# ✅ 字段与二进制格式定义（保持一致）
FIELDS = [
    'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg',
    'vol', 'amount', 'rsv', 'kdj_k', 'kdj_d', 'kdj_j', 'ema26', 'ema12', 'macd_dif',
    'last_dif', 'macd_dea', 'macd_macd', 'pre_macd_macd', 'pre_pre_macd_macd',
    'wr_wr1', 'wr_wr2', 'boll_boll', 'boll_ub', 'boll_lb', 'week_ema_short',
    'week_ema_long', 'week_macd_dif', 'lastweek_macd_dif', 'lastlastweek_macd_dif',
    'week_macd_dea', 'week_macd_macd', 'lastweek_macd_macd', 'lastlastweek_macd_macd',
    'TYP', 'ma_TYP_14', 'AVEDEV', 'cci', 'pre_cci', 'close_max__20', 'macd_max__20'
]

STRUCT_FMT = '<I' + 'f' * (len(FIELDS) - 1)
RECORD_SIZE = struct.calcsize(STRUCT_FMT)


def read_range_from_bin(symbol: str, start: int = 0, end: int = 10, bin_dir='bin_data'):
    """
    从某支股票的 .bin 文件中读取第 start~end 行（不含 end）
    """
    path = os.path.join(bin_dir, f'{symbol}.bin')
    if not os.path.exists(path):
        raise FileNotFoundError(f'❌ 未找到文件: {path}')

    results = []
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        total_records = mm.size() // RECORD_SIZE
        end = min(end, total_records)

        for i in range(start, end):
            offset = i * RECORD_SIZE
            data = mm[offset:offset + RECORD_SIZE]
            unpacked = struct.unpack(STRUCT_FMT, data)

            row = {FIELDS[j]: (str(val) if j == 0 else round(val, 4)) for j, val in enumerate(unpacked)}
            results.append(row)

        mm.close()
    return results


def read_range_all_stocks(symbols: list[str], start: int = 0, end: int = 10, bin_dir='bin_data'):
    """
    读取多支股票在指定行号范围的数据（按 .bin 文件）
    返回字典结构 {symbol: [row1, row2, ...]}
    """
    all_data = {}
    for symbol in symbols:
        try:
            rows = read_range_from_bin(symbol, start, end, bin_dir)
            all_data[symbol] = rows
        except FileNotFoundError:
            print(f"⚠️ 缺失二进制文件：{symbol}")
    return all_data


def read_stock_by_date_range(symbol: str, start_date: str, end_date: str, bin_dir='bin_data'):
    """
    读取某支股票在指定日期范围内的所有记录（基于 .idx 索引定位）
    """
    idx_path = os.path.join(bin_dir, f'{symbol}.idx')
    if not os.path.exists(idx_path):
        raise FileNotFoundError(f'未找到索引文件: {idx_path}')

    with open(idx_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    sorted_dates = sorted([int(d) for d in index.keys()])
    start_int, end_int = int(start_date), int(end_date)
    line_nums = [index[str(d)] for d in sorted_dates if start_int <= d <= end_int]

    if not line_nums:
        return []

    return read_range_from_bin(symbol, min(line_nums), max(line_nums)+1, bin_dir)


def read_all_stocks_by_date(target_date: str, bin_dir='bin_data'):
    """
    读取所有股票在某一日期上的横截面数据（若存在该日记录）
    返回结构：{symbol: row_dict}
    """
    results = {}
    for filename in os.listdir(bin_dir):
        if filename.endswith('.idx'):
            symbol = filename.replace('.idx', '')
            idx_path = os.path.join(bin_dir, filename)

            try:
                with open(idx_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                if target_date in index:
                    row = read_range_from_bin(symbol, index[target_date], index[target_date]+1, bin_dir)[0]
                    results[symbol] = row
            except Exception as e:
                print(f"⚠️ 读取错误：{symbol} - {e}")

    return results
