# -*- coding: utf-8 -*-
"""
优化版股票筛选系统快速启动脚本
提供一键运行功能，无需手动配置参数
"""

import os
import sys
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import StockScreeningSystem

def quick_start():
    """快速启动函数"""
    print("🚀 优化版股票筛选系统 - 快速启动")
    print("=" * 60)
    
    # 创建系统实例
    system = StockScreeningSystem()
    
    # 设置默认参数
    training_start_date = '2025-01-01'
    training_end_date = '2025-04-01'
    current_start_date = '2025-04-02'
    current_end_date = '2025-04-15'
    
    print(f"📅 训练数据时间范围: {training_start_date} 到 {training_end_date}")
    print(f"📅 当前数据时间范围: {current_start_date} 到 {current_end_date}")
    print(f"🎯 目标涨幅: 2%")
    print(f"🔍 匹配阈值: 70%")
    print(f"📊 特征字段数: 12个")
    print("=" * 60)
    
    # 询问用户是否继续
    try:
        choice = input("是否继续运行？(y/n): ").strip().lower()
        if choice not in ['y', 'yes', '是']:
            print("👋 用户取消操作")
            return
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        return
    
    # 运行完整流程
    print("\n🚀 开始运行完整流程...")
    success = system.run_complete_pipeline(
        training_start_date, training_end_date,
        current_start_date, current_end_date
    )
    
    if success:
        print("\n🎉 快速启动完成！")
        print("📁 结果文件已保存到当前目录")
        print("🔍 可以查看生成的结果文件了解详细信息")
    else:
        print("\n❌ 快速启动失败！")
        print("💡 建议检查数据库连接和配置参数")

def custom_start():
    """自定义参数启动"""
    print("⚙️ 自定义参数启动")
    print("=" * 60)
    
    try:
        # 获取用户输入
        print("请输入训练数据时间范围:")
        training_start = input("训练开始日期 (YYYY-MM-DD): ").strip()
        training_end = input("训练结束日期 (YYYY-MM-DD): ").strip()
        
        print("\n请输入当前数据时间范围:")
        current_start = input("当前开始日期 (YYYY-MM-DD): ").strip()
        current_end = input("当前结束日期 (YYYY-MM-DD): ").strip()
        
        # 验证日期格式
        for date_str in [training_start, training_end, current_start, current_end]:
            datetime.strptime(date_str, '%Y-%m-%d')
        
        print(f"\n✅ 参数验证通过")
        print(f"训练数据: {training_start} 到 {training_end}")
        print(f"当前数据: {current_start} 到 {current_end}")
        
        # 创建系统实例并运行
        system = StockScreeningSystem()
        success = system.run_complete_pipeline(
            training_start, training_end,
            current_start, current_end
        )
        
        if success:
            print("\n🎉 自定义启动完成！")
        else:
            print("\n❌ 自定义启动失败！")
            
    except ValueError:
        print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")

def test_mode():
    """测试模式"""
    print("🧪 测试模式")
    print("=" * 60)
    
    try:
        # 运行系统测试
        system = StockScreeningSystem()
        
        print("开始系统测试...")
        if system.test_system():
            print("✅ 系统测试通过")
            
            # 询问是否继续运行演示
            choice = input("\n是否运行演示模式？(y/n): ").strip().lower()
            if choice in ['y', 'yes', '是']:
                print("\n🎬 运行演示模式...")
                system.run_demo()
        else:
            print("❌ 系统测试失败")
            
    except Exception as e:
        print(f"❌ 测试模式运行失败: {e}")

def show_menu():
    """显示启动菜单"""
    while True:
        print("\n" + "=" * 60)
        print("🚀 优化版股票筛选系统 - 启动菜单")
        print("=" * 60)
        print("1. 快速启动 (使用默认参数)")
        print("2. 自定义参数启动")
        print("3. 测试模式")
        print("4. 交互式菜单")
        print("0. 退出")
        print("=" * 60)
        
        try:
            choice = input("请选择启动方式 (0-4): ").strip()
            
            if choice == '0':
                print("👋 感谢使用，再见！")
                break
            elif choice == '1':
                quick_start()
            elif choice == '2':
                custom_start()
            elif choice == '3':
                test_mode()
            elif choice == '4':
                # 启动交互式菜单
                system = StockScreeningSystem()
                system.show_menu()
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")

def main():
    """主函数"""
    try:
        # 检查依赖
        print("🔍 检查系统依赖...")
        
        required_modules = ['pandas', 'numpy', 'sklearn', 'sqlalchemy', 'pymysql']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print(f"❌ 缺少必要的依赖模块: {', '.join(missing_modules)}")
            print("💡 请运行: pip install -r requirements.txt")
            return
        
        print("✅ 依赖检查通过")
        
        # 显示启动菜单
        show_menu()
        
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
