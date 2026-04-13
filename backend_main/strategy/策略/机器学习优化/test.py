# from main import StockScreeningSystem
#
# # 创建系统实例
# system = StockScreeningSystem()
#
# # 步骤1：提取训练序列（使用大表）
# # sequences = system.extract_training_sequences(
# #     start_date='2020-06-02',
# #     end_date='2024-12-31'
# # )
#
#
# # 指定具体的序列文件
# sequences = system.run_from_sequence_file('./extracted_sequences_optimized_20250821_142836.txt')
# # 步骤2：训练聚类模型
# clustering_results = system.train_clustering_model(sequences)
#
# # 步骤3：匹配当前股票
# df = system.match_current_stocks(
#     start_date='2025-01-01',
#     end_date='2025-05-14'
# )

from main import StockScreeningSystem
import os
import glob

# 创建系统实例
system = StockScreeningSystem()

# 调试信息
print(f"当前工作目录: {os.getcwd()}")
print(f"目录内容:")
for item in os.listdir('.'):
    if item.endswith('.txt'):
        print(f"  - {item}")

# 查找所有序列文件
sequence_files = glob.glob('extracted_sequences_*.txt')
print(f"找到的序列文件: {sequence_files}")

if sequence_files:
    # 使用第一个找到的文件
    df = system.run_from_sequence_file(sequence_files[0])
else:
    print("没有找到序列文件")