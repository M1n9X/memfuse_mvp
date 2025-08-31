#!/usr/bin/env python3
"""
MemFuse Research Analysis Demo
展示M3工作流在研究分析任务中的应用
"""

import requests
import time
import json
from typing import Dict, Any, List


class ResearchAnalysisDemo:
    """研究分析demo，展示M3工作流的研究能力。"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        
    def setup_research_environment(self) -> Dict[str, str]:
        """设置研究环境：创建研究员用户和研究助手智能体。"""
        print("🔬 设置研究分析环境")
        print("=" * 40)
        
        timestamp = str(int(time.time()))
        
        # 创建研究员用户
        researcher_data = {
            "name": f"researcher_{timestamp}",
            "email": f"researcher_{timestamp}@lab.ai",
            "metadata": {
                "role": "senior_researcher",
                "department": "AI_research",
                "specialization": ["machine_learning", "nlp", "computer_vision"]
            }
        }
        
        response = requests.post(f"{self.base_url}/users/", json=researcher_data)
        researcher = response.json()
        print(f"✅ 研究员用户创建: {researcher['name']}")
        
        # 创建研究助手智能体
        assistant_data = {
            "name": f"research_assistant_{timestamp}",
            "type": "research_assistant",
            "description": "AI研究助手，专门用于文献调研、数据分析和报告生成",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 4000,
                "research_capabilities": [
                    "literature_review",
                    "data_analysis", 
                    "trend_identification",
                    "report_generation"
                ]
            },
            "metadata": {
                "specialization": "research_analysis",
                "version": "1.0"
            }
        }
        
        response = requests.post(f"{self.base_url}/agents/", json=assistant_data)
        assistant = response.json()
        print(f"✅ 研究助手创建: {assistant['name']}")
        
        # 创建研究会话
        session_data = {
            "user_id": researcher["id"],
            "agent_id": assistant["id"],
            "name": f"AI研究分析会话 - {timestamp}",
            "metadata": {
                "session_type": "research_analysis",
                "research_domain": "artificial_intelligence"
            }
        }
        
        response = requests.post(f"{self.base_url}/sessions/", json=session_data)
        session = response.json()
        self.session_id = session["id"]
        print(f"✅ 研究会话创建: {session['name']}")
        
        return {
            "researcher_id": researcher["id"],
            "assistant_id": assistant["id"],
            "session_id": session["id"]
        }
    
    def demo_literature_review(self):
        """演示文献调研功能。"""
        print("\n📚 演示：文献调研分析")
        print("-" * 30)
        
        research_query = """
        请帮我进行一次关于"大语言模型在代码生成中的应用"的文献调研。
        我需要：
        1. 最新的研究趋势和发展方向
        2. 主要的技术方法和模型架构
        3. 当前存在的挑战和限制
        4. 未来的研究机会
        
        请使用M3工作流进行深度分析，并生成结构化的调研报告。
        """
        
        print("🔍 发起文献调研请求...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": research_query,
                "enable_m3": True,
                "metadata": {
                    "task_type": "literature_review",
                    "domain": "code_generation",
                    "depth": "comprehensive"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 文献调研完成 ({duration:.1f}秒)")
            print(f"📄 报告长度: {len(result['content'])} 字符")
            
            # 显示报告摘要
            content = result['content']
            lines = content.split('\n')
            summary_lines = [line for line in lines[:10] if line.strip()]
            print(f"📋 报告摘要:")
            for line in summary_lines:
                print(f"   {line}")
            
            if len(lines) > 10:
                print(f"   ... (还有 {len(lines)-10} 行)")
                
            return result
        else:
            print(f"❌ 文献调研失败: {response.status_code}")
            return None
    
    def demo_trend_analysis(self):
        """演示趋势分析功能。"""
        print("\n📈 演示：技术趋势分析")
        print("-" * 30)
        
        trend_query = """
        基于当前的AI发展状况，请分析以下技术趋势：
        1. 多模态大模型的发展趋势
        2. AI Agent系统的演进方向
        3. 边缘AI和模型压缩技术
        4. AI安全和对齐研究进展
        
        请使用M3工作流进行深度分析，识别关键趋势并预测未来发展。
        """
        
        print("📊 发起趋势分析请求...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": trend_query,
                "enable_m3": True,
                "metadata": {
                    "task_type": "trend_analysis",
                    "analysis_scope": "technology_trends",
                    "time_horizon": "2024-2025"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 趋势分析完成 ({duration:.1f}秒)")
            print(f"📊 分析报告长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 趋势分析失败: {response.status_code}")
            return None
    
    def demo_competitive_analysis(self):
        """演示竞争分析功能。"""
        print("\n🏆 演示：竞争分析")
        print("-" * 30)
        
        competitive_query = """
        请帮我分析当前AI助手市场的竞争格局：
        1. 主要竞争对手分析（ChatGPT, Claude, Gemini等）
        2. 各家产品的技术特点和优势
        3. 市场定位和用户群体
        4. 我们的差异化机会在哪里
        
        请使用M3工作流进行全面的竞争分析。
        """
        
        print("🎯 发起竞争分析请求...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": competitive_query,
                "enable_m3": True,
                "metadata": {
                    "task_type": "competitive_analysis",
                    "market": "ai_assistants",
                    "analysis_depth": "comprehensive"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 竞争分析完成 ({duration:.1f}秒)")
            print(f"🎯 分析报告长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 竞争分析失败: {response.status_code}")
            return None
    
    def analyze_research_session(self):
        """分析研究会话的M3工作流使用情况。"""
        print("\n🔍 分析研究会话")
        print("-" * 30)
        
        # 获取所有消息
        response = requests.get(f"{self.base_url}/sessions/{self.session_id}/messages")
        all_messages = response.json()
        
        # 分析M3消息
        m3_messages = [msg for msg in all_messages if 'm3' in msg.get('tags', [])]
        user_messages = [msg for msg in all_messages if msg['role'] == 'user']
        assistant_messages = [msg for msg in all_messages if msg['role'] == 'assistant']
        workflow_messages = [msg for msg in all_messages if msg.get('workflow_id')]
        
        print(f"📊 会话统计:")
        print(f"   总消息数: {len(all_messages)}")
        print(f"   用户消息: {len(user_messages)}")
        print(f"   助手回复: {len(assistant_messages)}")
        print(f"   M3工作流消息: {len(m3_messages)}")
        print(f"   工作流步骤: {len(workflow_messages)}")
        
        # 分析工作流使用
        workflows = {}
        for msg in workflow_messages:
            wid = msg.get('workflow_id')
            if wid and wid not in workflows:
                workflows[wid] = []
            if wid:
                workflows[wid].append(msg)
        
        print(f"\n🔄 工作流分析:")
        print(f"   执行的工作流数: {len(workflows)}")
        
        for i, (wid, msgs) in enumerate(workflows.items(), 1):
            print(f"   工作流 {i}: {len(msgs)} 个步骤")
        
        return {
            "total_messages": len(all_messages),
            "m3_messages": len(m3_messages),
            "workflows_executed": len(workflows),
            "session_id": self.session_id
        }
    
    def run_complete_demo(self):
        """运行完整的研究分析demo。"""
        print("🚀 MemFuse 研究分析 Demo")
        print("=" * 50)
        
        try:
            # 1. 环境设置
            env_info = self.setup_research_environment()
            
            # 2. 文献调研
            literature_result = self.demo_literature_review()
            
            # 3. 趋势分析
            trend_result = self.demo_trend_analysis()
            
            # 4. 竞争分析
            competitive_result = self.demo_competitive_analysis()
            
            # 5. 会话分析
            session_stats = self.analyze_research_session()
            
            # 6. 总结
            print("\n🎉 研究分析Demo完成!")
            print("=" * 50)
            print(f"✅ 环境设置: 用户、智能体、会话已创建")
            print(f"✅ 文献调研: {'完成' if literature_result else '失败'}")
            print(f"✅ 趋势分析: {'完成' if trend_result else '失败'}")
            print(f"✅ 竞争分析: {'完成' if competitive_result else '失败'}")
            print(f"📊 会话统计: {session_stats['total_messages']} 条消息")
            print(f"🧠 M3工作流: {session_stats['workflows_executed']} 个工作流")
            
            print(f"\n🔗 会话链接: {self.base_url}/sessions/{self.session_id}")
            print("💡 您可以继续在这个会话中进行更多研究分析任务")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo执行失败: {e}")
            return False


def main():
    """主函数。"""
    # 检查服务器连接
    demo = ResearchAnalysisDemo()
    
    try:
        response = requests.get(f"{demo.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API服务器未正常响应")
            print("请先启动服务器: poetry run python scripts/start_api_server.py --port 8001")
            return False
    except Exception:
        print("❌ 无法连接到API服务器")
        print("请先启动服务器: poetry run python scripts/start_api_server.py --port 8001")
        return False
    
    # 运行demo
    success = demo.run_complete_demo()
    
    if success:
        print("\n🎊 研究分析Demo成功完成!")
        print("\n📖 Demo展示了以下M3工作流能力:")
        print("   • 文献调研和知识整合")
        print("   • 技术趋势分析和预测")
        print("   • 竞争格局分析")
        print("   • 结构化报告生成")
        print("   • 工作流步骤追踪")
    else:
        print("\n💥 Demo执行失败，请检查日志")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
