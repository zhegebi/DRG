#!/usr/bin/env python3
"""
位于 server/script/runner.py
供 uv run dev / uv run prod 调用
"""

import subprocess
import sys
import time
from pathlib import Path

# 路径定义
SERVER_DIR = Path(__file__).parent.parent          # server 目录
ROOT_DIR = SERVER_DIR.parent                       # DRG 根目录
CLIENT_DIR = ROOT_DIR / "client"                   # client 目录

def run_command(cmd, cwd):
    """启动子进程（跨平台，Windows 使用 shell=True）"""
    if sys.platform == "win32":
        # Windows 下需要 shell=True 来执行 .cmd / .bat 文件
        # 如果 cmd 是列表，转换成字符串
        if isinstance(cmd, list):
            # 简单拼接，适用于无空格参数的场景
            cmd_str = " ".join(cmd)
        else:
            cmd_str = cmd
        return subprocess.Popen(
            cmd_str,
            cwd=cwd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            shell=True,
        )
    else:
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=sys.stdout,
            stderr=sys.stderr,
            shell=False,
        )

def kill_process(proc):
    """安全终止进程"""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)

def dev():
    """开发模式：同时启动前端 dev server 和后端 uvicorn --reload"""
    print("🚀 启动开发模式...")
    print("   前端: http://localhost:5173")
    print("   后端: http://localhost:8000")
    print("   按 Ctrl+C 停止\n")

    # 启动后端
    backend_cmd = ["uvicorn", "main:app", "--reload", "--port", "8000"]
    backend_proc = run_command(backend_cmd, cwd=SERVER_DIR)

    time.sleep(1)  # 等待后端初始化

    # 启动前端
    frontend_cmd = ["npm", "run", "dev"]
    frontend_proc = run_command(frontend_cmd, cwd=CLIENT_DIR)

    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("❌ 后端进程已退出，终止前端...")
                kill_process(frontend_proc)
                sys.exit(1)
            if frontend_proc.poll() is not None:
                print("❌ 前端进程已退出，终止后端...")
                kill_process(backend_proc)
                sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭所有服务...")
    finally:
        kill_process(backend_proc)
        kill_process(frontend_proc)
        print("✅ 已退出")

def prod():
    """生产模式：构建前端，然后启动后端（托管静态文件）"""
    print("🏗️  生产模式...")
    print("   1. 构建前端项目")
    build_cmd = ["npm", "run", "build"]
    build_proc = run_command(build_cmd, cwd=CLIENT_DIR)
    build_proc.wait()
    if build_proc.returncode != 0:
        print("❌ 前端构建失败")
        sys.exit(1)
    print("✅ 前端构建完成")

    print("\n🚀 启动后端服务器 (http://localhost:8000)")
    print("   按 Ctrl+C 停止\n")
    backend_cmd = ["uvicorn", "main:app", "--port", "8000"]
    backend_proc = run_command(backend_cmd, cwd=SERVER_DIR)
    try:
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("❌ 后端进程已退出")
                sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 收到中断信号，正在关闭后端...")
    finally:
        kill_process(backend_proc)
        print("✅ 已退出")

if __name__ == "__main__":
    # 支持直接运行脚本（备用）
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        dev()
    elif len(sys.argv) > 1 and sys.argv[1] == "prod":
        prod()
    else:
        print("用法: uv run dev  或  uv run prod")
        sys.exit(1)