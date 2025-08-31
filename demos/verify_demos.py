#!/usr/bin/env python3
"""
验证所有demo的完整性和可运行性
"""

import os
import sys
import subprocess
from pathlib import Path


def check_demo_files():
    """检查demo文件是否存在。"""
    print("📁 检查Demo文件")
    print("-" * 30)
    
    demo_files = [
        "demos/research_analysis_demo.py",
        "demos/content_creation_demo.py", 
        "demos/data_analysis_demo.py",
        "demos/comprehensive_demo.py",
        "demos/demo_launcher.py",
        "demos/start_demo_server.py"
    ]
    
    missing_files = []
    for file_path in demo_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ 缺少 {len(missing_files)} 个demo文件")
        return False
    
    print(f"\n✅ 所有 {len(demo_files)} 个demo文件都存在")
    return True


def check_syntax():
    """检查demo文件的语法。"""
    print("\n🔍 检查Demo语法")
    print("-" * 30)
    
    demo_files = [
        "demos/research_analysis_demo.py",
        "demos/content_creation_demo.py",
        "demos/data_analysis_demo.py", 
        "demos/comprehensive_demo.py",
        "demos/demo_launcher.py",
        "demos/start_demo_server.py"
    ]
    
    syntax_errors = []
    
    for file_path in demo_files:
        try:
            result = subprocess.run([
                "python", "-m", "py_compile", file_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path}: {result.stderr}")
                syntax_errors.append(file_path)
                
        except Exception as e:
            print(f"❌ {file_path}: {e}")
            syntax_errors.append(file_path)
    
    if syntax_errors:
        print(f"\n❌ {len(syntax_errors)} 个文件有语法错误")
        return False
    
    print(f"\n✅ 所有demo文件语法正确")
    return True


def check_imports():
    """检查demo的导入依赖。"""
    print("\n📦 检查Demo导入")
    print("-" * 30)
    
    try:
        # 检查核心依赖
        import requests
        print("✅ requests")
        
        import fastapi
        print("✅ fastapi")
        
        import uvicorn
        print("✅ uvicorn")
        
        # 检查MemFuse模块
        from memfuse.config import Settings
        print("✅ memfuse.config")
        
        from memfuse.db import Database
        print("✅ memfuse.db")
        
        from memfuse.api_server import app
        print("✅ memfuse.api_server")
        
        print("\n✅ 所有导入依赖正常")
        return True
        
    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        return False


def create_demo_summary():
    """创建demo功能总结。"""
    print("\n📋 Demo功能总结")
    print("-" * 30)
    
    demos = {
        "研究分析Demo": {
            "文件": "demos/research_analysis_demo.py",
            "功能": ["文献调研", "趋势分析", "竞争分析"],
            "用户": "研究人员、分析师"
        },
        "内容创作Demo": {
            "文件": "demos/content_creation_demo.py", 
            "功能": ["博客写作", "营销文案", "技术文档"],
            "用户": "内容创作者、营销人员"
        },
        "数据分析Demo": {
            "文件": "demos/data_analysis_demo.py",
            "功能": ["对话分析", "性能分析", "行为分析"],
            "用户": "数据科学家、业务分析师"
        },
        "综合任务Demo": {
            "文件": "demos/comprehensive_demo.py",
            "功能": ["产品规划", "架构设计", "项目管理"],
            "用户": "项目经理、架构师"
        }
    }
    
    for demo_name, info in demos.items():
        print(f"\n🎭 {demo_name}")
        print(f"   📄 文件: {info['文件']}")
        print(f"   🔧 功能: {', '.join(info['功能'])}")
        print(f"   👥 用户: {info['用户']}")
    
    return True


def main():
    """主验证函数。"""
    print("🧪 MemFuse Demo验证系统")
    print("=" * 50)
    
    checks = [
        ("Demo文件检查", check_demo_files),
        ("语法检查", check_syntax),
        ("导入检查", check_imports),
        ("功能总结", create_demo_summary)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        try:
            if check_func():
                passed += 1
            else:
                print(f"❌ {check_name} 失败")
        except Exception as e:
            print(f"💥 {check_name} 异常: {e}")
    
    print(f"\n📊 验证结果: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有Demo验证通过!")
        print("\n🚀 使用方法:")
        print("1. 启动服务器: poetry run python demos/start_demo_server.py")
        print("2. 运行demo: poetry run python demos/demo_launcher.py")
        print("3. 查看文档: open demos/README.md")
    else:
        print("\n❌ 部分验证失败，请检查错误信息")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
