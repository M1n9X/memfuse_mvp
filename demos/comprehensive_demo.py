#!/usr/bin/env python3
"""
MemFuse Comprehensive Demo
展示M3工作流处理复杂多步骤任务的能力
"""

import requests
import time
import json
from typing import Dict, Any, List


class ComprehensiveDemo:
    """综合demo，展示M3工作流处理复杂任务的能力。"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        
    def setup_comprehensive_environment(self) -> Dict[str, str]:
        """设置综合任务环境：创建项目经理和全能助手。"""
        print("🎯 设置综合任务环境")
        print("=" * 40)
        
        timestamp = str(int(time.time()))
        
        # 创建项目经理用户
        manager_data = {
            "name": f"project_manager_{timestamp}",
            "email": f"pm_{timestamp}@company.ai",
            "metadata": {
                "role": "senior_project_manager",
                "department": "product_development",
                "specialization": ["project_planning", "team_coordination", "strategic_analysis"]
            }
        }
        
        response = requests.post(f"{self.base_url}/users/", json=manager_data)
        manager = response.json()
        print(f"✅ 项目经理创建: {manager['name']}")
        
        # 创建全能助手智能体
        assistant_data = {
            "name": f"comprehensive_assistant_{timestamp}",
            "type": "comprehensive_assistant",
            "description": "全能AI助手，能够处理复杂的多步骤任务和项目管理",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 4000,
                "comprehensive_capabilities": [
                    "project_planning",
                    "research_analysis",
                    "content_creation",
                    "data_analysis",
                    "task_coordination"
                ]
            },
            "metadata": {
                "specialization": "comprehensive_tasks",
                "complexity_level": "high"
            }
        }
        
        response = requests.post(f"{self.base_url}/agents/", json=assistant_data)
        assistant = response.json()
        print(f"✅ 全能助手创建: {assistant['name']}")
        
        # 创建综合任务会话
        session_data = {
            "user_id": manager["id"],
            "agent_id": assistant["id"],
            "name": f"综合任务会话 - {timestamp}",
            "metadata": {
                "session_type": "comprehensive_tasks",
                "complexity": "high",
                "multi_step": True
            }
        }
        
        response = requests.post(f"{self.base_url}/sessions/", json=session_data)
        session = response.json()
        self.session_id = session["id"]
        print(f"✅ 综合会话创建: {session['name']}")
        
        return {
            "manager_id": manager["id"],
            "assistant_id": assistant["id"],
            "session_id": session["id"]
        }
    
    def demo_product_launch_planning(self):
        """演示产品发布规划任务。"""
        print("\n🚀 演示：产品发布规划")
        print("-" * 30)
        
        planning_query = """
        我们需要为MemFuse AI记忆系统制定完整的产品发布计划。请帮我：
        
        1. 市场分析和定位
           - 目标用户群体识别
           - 竞争对手分析
           - 市场机会评估
        
        2. 产品策略制定
           - 核心价值主张
           - 功能优先级排序
           - 差异化策略
        
        3. 发布计划制定
           - 里程碑和时间线
           - 资源需求评估
           - 风险识别和缓解
        
        4. 营销策略设计
           - 品牌定位和消息传递
           - 渠道策略和推广计划
           - 内容营销策略
        
        请使用M3工作流进行全面的规划和分析。
        """
        
        print("📋 发起产品发布规划...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": planning_query,
                "enable_m3": True,
                "metadata": {
                    "task_type": "product_launch_planning",
                    "product": "MemFuse",
                    "planning_scope": "comprehensive"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 产品规划完成 ({duration:.1f}秒)")
            print(f"📋 规划文档长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 产品规划失败: {response.status_code}")
            return None
    
    def demo_technical_architecture_design(self):
        """演示技术架构设计任务。"""
        print("\n🏗️ 演示：技术架构设计")
        print("-" * 30)
        
        architecture_query = """
        请为MemFuse系统设计一个可扩展的云原生架构：
        
        1. 系统架构设计
           - 微服务架构规划
           - 数据库设计和分片策略
           - 缓存和存储方案
        
        2. 性能和可扩展性
           - 负载均衡和自动扩缩容
           - 性能监控和优化
           - 容错和灾备方案
        
        3. 安全和合规
           - 身份认证和授权
           - 数据加密和隐私保护
           - 审计和合规要求
        
        4. 部署和运维
           - CI/CD流水线设计
           - 容器化和编排
           - 监控和告警系统
        
        请提供详细的技术方案和实施建议。
        """
        
        print("🔧 发起架构设计任务...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": architecture_query,
                "enable_m3": True,
                "metadata": {
                    "task_type": "architecture_design",
                    "system": "MemFuse",
                    "architecture_type": "cloud_native"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 架构设计完成 ({duration:.1f}秒)")
            print(f"🏗️ 设计文档长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 架构设计失败: {response.status_code}")
            return None
    
    def analyze_comprehensive_session(self):
        """分析综合任务会话的复杂度。"""
        print("\n🔍 分析综合任务会话")
        print("-" * 30)
        
        # 获取所有消息
        response = requests.get(f"{self.base_url}/sessions/{self.session_id}/messages")
        all_messages = response.json()
        
        # 分析任务复杂度
        complex_tasks = 0
        total_chars = 0
        
        for msg in all_messages:
            if msg['role'] == 'user':
                content = msg['content']
                # 简单的复杂度评估
                if len(content) > 500 and ('请' in content or '帮我' in content):
                    complex_tasks += 1
            elif msg['role'] == 'assistant':
                total_chars += len(msg['content'])
        
        avg_response_length = total_chars // max(1, len([m for m in all_messages if m['role'] == 'assistant']))
        
        print(f"📊 综合任务会话分析:")
        print(f"   总消息数: {len(all_messages)}")
        print(f"   复杂任务数: {complex_tasks}")
        print(f"   平均回复长度: {avg_response_length} 字符")
        
        return {
            "total_messages": len(all_messages),
            "complex_tasks": complex_tasks,
            "avg_response_length": avg_response_length,
            "session_id": self.session_id
        }
    
    def run_complete_demo(self):
        """运行完整的综合任务demo。"""
        print("🚀 MemFuse 综合任务 Demo")
        print("=" * 50)
        
        try:
            # 1. 环境设置
            env_info = self.setup_comprehensive_environment()
            
            # 2. 产品发布规划
            planning_result = self.demo_product_launch_planning()
            
            # 3. 技术架构设计
            architecture_result = self.demo_technical_architecture_design()
            
            # 4. 会话分析
            session_stats = self.analyze_comprehensive_session()
            
            # 5. 总结
            print("\n🎉 综合任务Demo完成!")
            print("=" * 50)
            print(f"✅ 环境设置: 项目经理、全能助手、会话已创建")
            print(f"✅ 产品规划: {'完成' if planning_result else '失败'}")
            print(f"✅ 架构设计: {'完成' if architecture_result else '失败'}")
            print(f"📊 会话统计: {session_stats['total_messages']} 条消息")
            print(f"🎯 复杂任务: {session_stats['complex_tasks']} 个")
            
            print(f"\n🔗 会话链接: {self.base_url}/sessions/{self.session_id}")
            print("💡 您可以继续在这个会话中处理更多复杂任务")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo执行失败: {e}")
            return False


if __name__ == "__main__":
    # 检查服务器连接
    demo = ComprehensiveDemo()
    
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
