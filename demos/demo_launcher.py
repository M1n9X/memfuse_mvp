#!/usr/bin/env python3
"""
MemFuse Demo Launcher
选择并运行不同类型的MemFuse M3工作流演示
"""

import sys
import subprocess
import requests
from pathlib import Path


def check_server_status(base_url: str = "http://localhost:8001") -> bool:
    """检查API服务器状态。"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def start_server_if_needed():
    """如果服务器未运行，提示启动。"""
    if not check_server_status():
        print("❌ API服务器未运行")
        print("\n请先启动服务器:")
        print("   poetry run python scripts/start_api_server.py --port 8001")
        print("\n或者在新终端中运行:")
        print("   poetry run uvicorn memfuse.api_server:app --port 8001")
        return False
    
    print("✅ API服务器运行正常")
    return True


def show_demo_menu():
    """显示demo选择菜单。"""
    print("\n🎭 MemFuse M3工作流演示菜单")
    print("=" * 50)
    print("请选择要运行的演示:")
    print()
    print("1. 🔬 研究分析Demo")
    print("   - 文献调研和知识整合")
    print("   - 技术趋势分析")
    print("   - 竞争格局分析")
    print()
    print("2. ✍️  内容创作Demo")
    print("   - 技术博客写作")
    print("   - 营销文案创作")
    print("   - 技术文档编写")
    print()
    print("3. 📊 数据分析Demo")
    print("   - 对话数据分析")
    print("   - 性能指标分析")
    print("   - 用户行为分析")
    print()
    print("4. 🎯 综合任务Demo")
    print("   - 产品发布规划")
    print("   - 技术架构设计")
    print("   - 复杂多步骤任务")
    print()
    print("5. ⚡ 快速功能测试")
    print("   - 基础API功能验证")
    print("   - M3工作流快速测试")
    print()
    print("0. 🚪 退出")
    print()


def run_demo(choice: str) -> bool:
    """运行选择的demo。"""
    demos = {
        "1": ("demos/research_analysis_demo.py", "研究分析Demo"),
        "2": ("demos/content_creation_demo.py", "内容创作Demo"),
        "3": ("demos/data_analysis_demo.py", "数据分析Demo"),
        "4": ("demos/comprehensive_demo.py", "综合任务Demo"),
        "5": ("scripts/test_api_simple.py", "快速功能测试")
    }
    
    if choice not in demos:
        print("❌ 无效选择")
        return False
    
    script_path, demo_name = demos[choice]
    
    print(f"\n🚀 启动 {demo_name}")
    print("=" * 50)
    
    try:
        # 检查脚本文件是否存在
        if not Path(script_path).exists():
            print(f"❌ Demo脚本不存在: {script_path}")
            return False
        
        # 运行demo
        result = subprocess.run([
            "poetry", "run", "python", script_path
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print(f"\n🎉 {demo_name} 执行成功!")
            return True
        else:
            print(f"\n❌ {demo_name} 执行失败 (退出码: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"\n💥 {demo_name} 执行异常: {e}")
        return False


def show_demo_info():
    """显示demo信息和说明。"""
    print("🎭 MemFuse M3工作流演示系统")
    print("=" * 50)
    print()
    print("📖 关于这些演示:")
    print()
    print("🔬 研究分析Demo:")
    print("   展示M3工作流在学术研究、文献调研和趋势分析中的应用")
    print("   适合: 研究人员、分析师、学者")
    print()
    print("✍️  内容创作Demo:")
    print("   展示M3工作流在内容策划、写作和编辑中的应用")
    print("   适合: 内容创作者、营销人员、技术写手")
    print()
    print("📊 数据分析Demo:")
    print("   展示M3工作流在数据挖掘、模式识别和洞察发现中的应用")
    print("   适合: 数据科学家、业务分析师、产品经理")
    print()
    print("🎯 综合任务Demo:")
    print("   展示M3工作流处理复杂多步骤任务的能力")
    print("   适合: 项目经理、战略规划师、高级用户")
    print()
    print("⚡ 快速功能测试:")
    print("   验证API基础功能和M3工作流的基本运行")
    print("   适合: 开发者、系统管理员、新用户")
    print()


def main():
    """主函数。"""
    print("🎭 MemFuse M3工作流演示启动器")
    print("=" * 50)
    
    # 检查服务器状态
    if not start_server_if_needed():
        return False
    
    while True:
        show_demo_menu()
        
        try:
            choice = input("请输入选择 (0-5): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "info":
                show_demo_info()
                continue
            elif choice in ["1", "2", "3", "4", "5"]:
                success = run_demo(choice)
                if success:
                    print("\n✨ Demo执行完成!")
                else:
                    print("\n💥 Demo执行失败!")
                
                input("\n按Enter键继续...")
            else:
                print("❌ 无效选择，请输入0-5")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，再见!")
            break
        except Exception as e:
            print(f"\n💥 发生错误: {e}")
            input("按Enter键继续...")
    
    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"💥 启动器错误: {e}")
        sys.exit(1)
