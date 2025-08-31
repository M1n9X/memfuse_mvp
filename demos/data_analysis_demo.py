#!/usr/bin/env python3
"""
MemFuse Data Analysis Demo
展示M3工作流在数据分析任务中的应用
"""

import requests
import time
import json
from typing import Dict, Any, List


class DataAnalysisDemo:
    """数据分析demo，展示M3工作流的数据处理能力。"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        
    def setup_analysis_environment(self) -> Dict[str, str]:
        """设置数据分析环境：创建数据分析师和分析助手。"""
        print("📊 设置数据分析环境")
        print("=" * 40)
        
        timestamp = str(int(time.time()))
        
        # 创建数据分析师用户
        analyst_data = {
            "name": f"data_analyst_{timestamp}",
            "email": f"analyst_{timestamp}@data.ai",
            "metadata": {
                "role": "senior_data_analyst",
                "department": "data_science",
                "specialization": ["statistical_analysis", "machine_learning", "visualization"]
            }
        }
        
        response = requests.post(f"{self.base_url}/users/", json=analyst_data)
        analyst = response.json()
        print(f"✅ 数据分析师创建: {analyst['name']}")
        
        # 创建数据分析助手智能体
        assistant_data = {
            "name": f"data_assistant_{timestamp}",
            "type": "data_analyst",
            "description": "AI数据分析助手，专门用于数据处理、统计分析和洞察发现",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 4000,
                "analysis_capabilities": [
                    "statistical_analysis",
                    "pattern_recognition",
                    "data_visualization",
                    "insight_generation"
                ]
            },
            "metadata": {
                "specialization": "data_analysis",
                "analysis_depth": "comprehensive"
            }
        }
        
        response = requests.post(f"{self.base_url}/agents/", json=assistant_data)
        assistant = response.json()
        print(f"✅ 数据分析助手创建: {assistant['name']}")
        
        # 创建分析会话
        session_data = {
            "user_id": analyst["id"],
            "agent_id": assistant["id"],
            "name": f"数据分析会话 - {timestamp}",
            "metadata": {
                "session_type": "data_analysis",
                "analysis_domain": "conversation_data"
            }
        }
        
        response = requests.post(f"{self.base_url}/sessions/", json=session_data)
        session = response.json()
        self.session_id = session["id"]
        print(f"✅ 分析会话创建: {session['name']}")
        
        return {
            "analyst_id": analyst["id"],
            "assistant_id": assistant["id"],
            "session_id": session["id"]
        }
    
    def demo_conversation_analysis(self):
        """演示对话数据分析。"""
        print("\n💬 演示：对话数据分析")
        print("-" * 30)
        
        analysis_query = """
        请分析我们系统中的对话数据，重点关注：
        1. 用户查询的类型分布和频率
        2. 对话长度和复杂度趋势
        3. M3工作流的使用模式
        4. 用户满意度指标
        5. 系统性能瓶颈识别
        
        请使用M3工作流进行深度数据挖掘和模式识别。
        """
        
        print("🔍 发起对话数据分析...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": analysis_query,
                "enable_m3": True,
                "metadata": {
                    "analysis_type": "conversation_analysis",
                    "data_source": "message_database",
                    "metrics": ["frequency", "complexity", "satisfaction"]
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 对话分析完成 ({duration:.1f}秒)")
            print(f"📊 分析报告长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 对话分析失败: {response.status_code}")
            return None
    
    def demo_performance_metrics(self):
        """演示性能指标分析。"""
        print("\n⚡ 演示：性能指标分析")
        print("-" * 30)
        
        metrics_query = """
        请分析MemFuse系统的性能指标：
        1. API响应时间分布
        2. M3工作流执行效率
        3. 数据库查询性能
        4. 内存使用模式
        5. 错误率和故障模式
        
        基于分析结果提供性能优化建议。
        """
        
        print("📈 发起性能指标分析...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": metrics_query,
                "enable_m3": True,
                "metadata": {
                    "analysis_type": "performance_metrics",
                    "system": "memfuse_api",
                    "optimization_focus": "response_time"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 性能分析完成 ({duration:.1f}秒)")
            print(f"📊 分析报告长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 性能分析失败: {response.status_code}")
            return None
    
    def demo_user_behavior_analysis(self):
        """演示用户行为分析。"""
        print("\n👥 演示：用户行为分析")
        print("-" * 30)
        
        behavior_query = """
        分析用户在MemFuse系统中的行为模式：
        1. 用户活跃度和使用频率
        2. 功能使用偏好（RAG vs M3）
        3. 会话持续时间和深度
        4. 用户流失和留存模式
        5. 个性化推荐机会
        
        请提供数据驱动的用户洞察和产品改进建议。
        """
        
        print("👤 发起用户行为分析...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": behavior_query,
                "enable_m3": True,
                "metadata": {
                    "analysis_type": "user_behavior",
                    "data_scope": "all_users",
                    "insights_focus": "engagement_optimization"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 用户行为分析完成 ({duration:.1f}秒)")
            print(f"👥 分析报告长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 用户行为分析失败: {response.status_code}")
            return None
    
    def analyze_data_session(self):
        """分析数据分析会话的工作流使用。"""
        print("\n🔍 分析数据分析会话")
        print("-" * 30)
        
        # 获取所有消息
        response = requests.get(f"{self.base_url}/sessions/{self.session_id}/messages")
        all_messages = response.json()
        
        # 分析不同类型的消息
        analysis_messages = [msg for msg in all_messages if 'analysis' in msg.get('content', '').lower()]
        m3_messages = [msg for msg in all_messages if 'm3' in msg.get('tags', [])]
        
        print(f"📊 数据分析会话统计:")
        print(f"   总消息数: {len(all_messages)}")
        print(f"   分析相关消息: {len(analysis_messages)}")
        print(f"   M3工作流消息: {len(m3_messages)}")
        
        # 分析任务类型
        task_types = {}
        for msg in all_messages:
            if msg['role'] == 'user':
                content = msg['content'].lower()
                if '分析' in content:
                    if '对话' in content:
                        task_types['conversation_analysis'] = task_types.get('conversation_analysis', 0) + 1
                    elif '性能' in content:
                        task_types['performance_analysis'] = task_types.get('performance_analysis', 0) + 1
                    elif '用户' in content:
                        task_types['user_behavior'] = task_types.get('user_behavior', 0) + 1
        
        print(f"\n📈 分析任务类型分布:")
        for task_type, count in task_types.items():
            print(f"   {task_type}: {count} 次")
        
        return {
            "total_messages": len(all_messages),
            "analysis_messages": len(analysis_messages),
            "m3_messages": len(m3_messages),
            "task_distribution": task_types,
            "session_id": self.session_id
        }
    
    def run_complete_demo(self):
        """运行完整的数据分析demo。"""
        print("🚀 MemFuse 数据分析 Demo")
        print("=" * 50)
        
        try:
            # 1. 环境设置
            env_info = self.setup_analysis_environment()
            
            # 2. 对话数据分析
            conversation_result = self.demo_conversation_analysis()
            
            # 3. 性能指标分析
            performance_result = self.demo_performance_metrics()
            
            # 4. 用户行为分析
            behavior_result = self.demo_user_behavior_analysis()
            
            # 5. 会话分析
            session_stats = self.analyze_data_session()
            
            # 6. 总结
            print("\n🎉 数据分析Demo完成!")
            print("=" * 50)
            print(f"✅ 环境设置: 分析师、助手、会话已创建")
            print(f"✅ 对话分析: {'完成' if conversation_result else '失败'}")
            print(f"✅ 性能分析: {'完成' if performance_result else '失败'}")
            print(f"✅ 行为分析: {'完成' if behavior_result else '失败'}")
            print(f"📊 会话统计: {session_stats['total_messages']} 条消息")
            print(f"🧠 M3工作流: {session_stats['m3_messages']} 个M3消息")
            
            print(f"\n🔗 会话链接: {self.base_url}/sessions/{self.session_id}")
            print("💡 您可以继续在这个会话中进行更多数据分析任务")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo执行失败: {e}")
            return False


if __name__ == "__main__":
    # 检查服务器连接
    demo = DataAnalysisDemo()
    
    try:
        response = requests.get(f"{demo.base_url}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API服务器未正常响应")
            print("请先启动服务器: poetry run python scripts/start_api_server.py --port 8001")
            exit(1)
    except Exception:
        print("❌ 无法连接到API服务器")
        print("请先启动服务器: poetry run python scripts/start_api_server.py --port 8001")
        exit(1)
    
    success = demo.run_complete_demo()
    exit(0 if success else 1)
