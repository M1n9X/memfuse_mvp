#!/usr/bin/env python3
"""
Demo服务器启动脚本
专门为演示优化的API服务器启动器
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """检查依赖是否安装。"""
    try:
        import fastapi
        import uvicorn
        print("✅ FastAPI依赖已安装")
        return True
    except ImportError:
        print("❌ 缺少FastAPI依赖")
        print("请运行: poetry install")
        return False


def check_database():
    """检查数据库连接。"""
    try:
        from memfuse.config import Settings
        from memfuse.db import Database
        
        settings = Settings.from_env()
        db = Database.from_settings(settings)
        
        with db.connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


def setup_demo_database():
    """设置demo所需的数据库表。"""
    try:
        from memfuse.config import Settings
        from memfuse.db import Database
        
        settings = Settings.from_env()
        db = Database.from_settings(settings)
        
        print("🔧 设置demo数据库...")
        
        with db.connect() as conn, conn.cursor() as cur:
            # 创建API表（如果不存在）
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    type VARCHAR(100) DEFAULT 'assistant',
                    description TEXT,
                    config JSONB DEFAULT '{}',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
                    name VARCHAR(255),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    tags TEXT[] DEFAULT '{}',
                    workflow_id UUID,
                    step_index INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_mappings (
                    old_session_id VARCHAR(255) PRIMARY KEY,
                    new_session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        print("✅ Demo数据库设置完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库设置失败: {e}")
        return False


def start_demo_server(port: int = 8001):
    """启动demo服务器。"""
    print(f"🚀 启动MemFuse Demo服务器 (端口: {port})")
    print("=" * 50)
    
    try:
        # 使用uvicorn直接启动，避免复杂的依赖问题
        cmd = [
            "poetry", "run", "uvicorn", 
            "memfuse.api_server:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--log-level", "info"
        ]
        
        print("📡 启动命令:", " ".join(cmd))
        print(f"📖 API文档: http://localhost:{port}/docs")
        print(f"🔍 健康检查: http://localhost:{port}/health")
        print("\n按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        # 启动服务器
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"\n❌ 服务器启动失败: {e}")
        return False
    
    return True


def main():
    """主函数。"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MemFuse Demo服务器启动器")
    parser.add_argument("--port", type=int, default=8001, help="服务器端口")
    parser.add_argument("--skip-checks", action="store_true", help="跳过依赖检查")
    
    args = parser.parse_args()
    
    print("🎭 MemFuse Demo服务器启动器")
    print("=" * 40)
    
    # 检查依赖
    if not args.skip_checks:
        if not check_dependencies():
            sys.exit(1)
        
        if not check_database():
            print("尝试设置数据库...")
            if not setup_demo_database():
                sys.exit(1)
    
    # 启动服务器
    success = start_demo_server(args.port)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
