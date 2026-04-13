#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复个股诊断模块404错误的脚本
"""

import os
import sys

def print_banner():
    """打印横幅"""
    print("🔧 个股诊断模块404错误修复脚本")
    print("=" * 50)

def check_common_issues():
    """检查常见问题"""
    print("🔍 检查常见问题...")
    
    issues = []
    
    # 检查1: 文件是否存在
    required_files = [
        'backend_main/stock_analysis/__init__.py',
        'backend_main/stock_analysis/models.py',
        'backend_main/stock_analysis/views.py',
        'backend_main/stock_analysis/urls.py',
        'backend_main/stock_analysis/apps.py'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            issues.append(f"❌ 缺少文件: {file_path}")
        else:
            print(f"✅ 文件存在: {file_path}")
    
    # 检查2: apps.py配置
    apps_file = 'backend_main/stock_analysis/apps.py'
    if os.path.exists(apps_file):
        with open(apps_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'StockAnalysisConfig' not in content:
                issues.append("❌ apps.py配置不正确")
            else:
                print("✅ apps.py配置正确")
    
    # 检查3: __init__.py
    init_file = 'backend_main/stock_analysis/__init__.py'
    if os.path.exists(init_file):
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'default_app_config' not in content:
                print("⚠️  __init__.py中缺少default_app_config")
    
    return issues

def fix_apps_py():
    """修复apps.py文件"""
    print("\n🔧 修复apps.py文件...")
    
    apps_content = '''from django.apps import AppConfig


class StockAnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stock_analysis'
    verbose_name = '个股诊断'
'''
    
    apps_file = 'backend_main/stock_analysis/apps.py'
    with open(apps_file, 'w', encoding='utf-8') as f:
        f.write(apps_content)
    
    print("✅ apps.py文件已修复")

def fix_init_py():
    """修复__init__.py文件"""
    print("\n🔧 修复__init__.py文件...")
    
    init_content = '''default_app_config = 'stock_analysis.apps.StockAnalysisConfig'
'''
    
    init_file = 'backend_main/stock_analysis/__init__.py'
    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    print("✅ __init__.py文件已修复")

def check_settings():
    """检查settings.py配置"""
    print("\n🔍 检查settings.py配置...")
    
    settings_file = 'backend_main/backend/settings.py'
    if not os.path.exists(settings_file):
        print("❌ settings.py文件不存在")
        return False
    
    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        if 'stock_analysis' not in content:
            print("❌ settings.py中缺少stock_analysis应用")
            return False
        else:
            print("✅ settings.py中已包含stock_analysis应用")
            return True

def check_urls():
    """检查URL配置"""
    print("\n🔍 检查URL配置...")
    
    # 检查主URL配置
    main_urls = 'backend_main/backend/urls.py'
    if os.path.exists(main_urls):
        with open(main_urls, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'stock_analysis.urls' in content:
                print("✅ 主URL配置正确")
            else:
                print("❌ 主URL配置中缺少stock_analysis.urls")
    
    # 检查应用URL配置
    app_urls = 'backend_main/stock_analysis/urls.py'
    if os.path.exists(app_urls):
        with open(app_urls, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'index/' in content:
                print("✅ 应用URL配置正确")
            else:
                print("❌ 应用URL配置中缺少index/路径")

def create_test_view():
    """创建一个测试视图"""
    print("\n🔧 创建测试视图...")
    
    test_view_content = '''
@csrf_exempt
@require_http_methods(["GET"])
def test_api(request):
    """测试API"""
    return JsonResponse({
        'message': '个股诊断模块API正常工作',
        'status': 'success',
        'timestamp': datetime.now().isoformat()
    })
'''
    
    views_file = 'backend_main/stock_analysis/views.py'
    if os.path.exists(views_file):
        with open(views_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'test_api' not in content:
            # 在文件末尾添加测试视图
            with open(views_file, 'a', encoding='utf-8') as f:
                f.write(test_view_content)
            print("✅ 测试视图已添加")
        else:
            print("✅ 测试视图已存在")

def add_test_url():
    """添加测试URL"""
    print("\n🔧 添加测试URL...")
    
    test_url = '    path("test/", views.test_api, name="test_api"),\n'
    
    urls_file = 'backend_main/stock_analysis/urls.py'
    if os.path.exists(urls_file):
        with open(urls_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'test_api' not in content:
            # 在urlpatterns中添加测试URL
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'urlpatterns = [' in line:
                    lines.insert(i + 1, test_url)
                    break
            
            with open(urls_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print("✅ 测试URL已添加")
        else:
            print("✅ 测试URL已存在")

def print_fix_instructions():
    """打印修复说明"""
    print("\n📋 修复说明:")
    print("1. 已修复apps.py和__init__.py文件")
    print("2. 已添加测试视图和URL")
    print("3. 请重启Django服务")
    print("4. 测试以下URL:")
    print("   - http://localhost:8000/api/stock_analysis/test/")
    print("   - http://localhost:8000/api/stock_analysis/index/")
    print("   - http://localhost:8000/api/stock_analysis/search/?q=000001")

def main():
    """主函数"""
    print_banner()
    
    # 检查常见问题
    issues = check_common_issues()
    
    if issues:
        print("\n⚠️  发现以下问题:")
        for issue in issues:
            print(f"  {issue}")
    
    # 检查配置
    check_settings()
    check_urls()
    
    # 修复文件
    fix_apps_py()
    fix_init_py()
    create_test_view()
    add_test_url()
    
    # 打印修复说明
    print_fix_instructions()
    
    print("\n🎯 修复完成！请重启Django服务并测试。")

if __name__ == "__main__":
    main()

