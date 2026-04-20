import subprocess
import time
import webbrowser
import socket
import os
import sys
import threading

import re

def kill_process_on_port(port):
    """
    Finds and kills the process listening on the specified port (Windows).
    """
    try:
        # Find PID
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode()
        lines = output.strip().split('\n')
        
        pids = set()
        for line in lines:
            if 'LISTENING' in line:
                parts = line.split()
                # The PID is usually the last element
                pid = parts[-1]
                pids.add(pid)
        
        if not pids:
            print(f"   - 端口 {port} 未被占用。")
            return

        for pid in pids:
            print(f"   - 正在终止 PID {pid} (Port {port})...")
            os.system(f'taskkill /F /PID {pid} >nul 2>&1')
            
    except subprocess.CalledProcessError:
        # netstat returns non-zero if not found
        print(f"   - 端口 {port} 未被占用。")
    except Exception as e:
        print(f"   ⚠️ 无法清理端口 {port}: {e}")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_backend():
    print("🚀 正在启动 Django 后端 (Port 8000)...")
    if is_port_in_use(8000):
        print("⚠️ 端口 8000 已被占用，假设后端已在运行。")
        return None
    
    # 假设在根目录下运行，后端在 backend_main
    cwd = os.path.join(os.getcwd(), 'backend_main')
    
    # 设置 PYTHONPATH 环境变量，确保能找到模块
    env = os.environ.copy()
    # 响应用户指令: 将PYTHONPATH设置为下述路径：D:\Daoquant-platform\backend_main;%PYTHONPATH%
    # 同时保留当前目录(项目根目录)以防 breaks 'import backend_main'
    backend_main_path = os.path.join(os.getcwd(), 'backend_main')
    env['PYTHONPATH'] = f"{backend_main_path};{os.getcwd()};{env.get('PYTHONPATH', '')}"

    try:
        proc = subprocess.Popen(
            [sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'],
            cwd=cwd,
            env=env,
            shell=True
        )
        return proc
    except Exception as e:
        print(f"❌ 后端启动失败: {e}")
        return None

def start_frontend():
    print("🚀 正在启动 Vite 前端...")
    if is_port_in_use(5173):
        print("⚠️ 端口 5173 已被占用，假设前端已在运行。")
        return None

    cwd = os.path.join(os.getcwd(), 'frontend')
    try:
        # 使用 npm run dev
        proc = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=cwd,
            shell=True
        )
        return proc
    except Exception as e:
        print(f"❌ 前端启动失败: {e}")
        return None

def main():
    print("="*50)
    print(" Daoquant-platform 一键启动脚本")
    print("="*50)

    # 0. Cleanup Ports
    print("🧹 清理旧进程 (Port 8000, 5173)...")
    kill_process_on_port(8000)
    kill_process_on_port(5173)
    time.sleep(2)

    # 1. Start Backend
    backend_proc = start_backend()
    
    # 2. Start Frontend
    frontend_proc = start_frontend()

    # 3. Wait a bit for services to warm up
    print("⏳ 等待服务启动...")
    time.sleep(5)

    # 4. Open Browser
    print("🌐 打开前端首页...")
    webbrowser.open('http://localhost:5173/')

    print("\n✅ 系统启动尝试完成。请保持此窗口开启。")
    print("按 Ctrl+C 停止所有服务 (如果由此脚本启动)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        if backend_proc: backend_proc.terminate()
        if frontend_proc: frontend_proc.terminate()
        sys.exit(0)

if __name__ == '__main__':
    main()
