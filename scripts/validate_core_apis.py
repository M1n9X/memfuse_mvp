#!/usr/bin/env python3
"""
MemFuse 核心API验证工具
验证长上下文和工作流的完整功能
"""

import requests
import time


class MemFuseCoreValidator:
    """MemFuse核心API验证器。"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.user = None
        self.agent = None
        self.session = None
    
    def setup_environment(self):
        """设置验证环境。"""
        print("🔧 设置MemFuse验证环境")
        print("=" * 40)
        
        timestamp = str(int(time.time()))
        
        # 创建用户
        user_data = {"name": f"demo_user_{timestamp}", "email": f"demo_{timestamp}@memfuse.com"}
        self.user = requests.post(f"{self.base_url}/users/", json=user_data).json()
        print(f"✅ 用户创建: {self.user['name']}")
        
        # 创建智能体
        agent_data = {"name": f"demo_agent_{timestamp}", "type": "assistant"}
        self.agent = requests.post(f"{self.base_url}/agents/", json=agent_data).json()
        print(f"✅ 智能体创建: {self.agent['name']}")
        
        # 创建会话
        session_data = {
            "user_id": self.user["id"],
            "agent_id": self.agent["id"],
            "name": "核心API验证"
        }
        self.session = requests.post(f"{self.base_url}/sessions/", json=session_data).json()
        print(f"✅ 会话创建: {self.session['id']}")
        
        return True
    
    def demo_long_context(self):
        """演示长上下文处理。"""
        print(f"\n📝 演示1: 长上下文处理")
        print("-" * 30)
        
        # 模拟长文档内容
        long_document = """
        MemFuse系统架构文档
        
        MemFuse是一个革命性的AI记忆系统，采用先进的M3工作流技术。
        系统核心特性包括：
        1. 长上下文处理能力 - 支持超长文本的智能存储和检索
        2. M3工作流引擎 - 复杂任务的多步骤自动化处理
        3. 统一API接口 - 通过tag参数区分不同操作模式
        4. 智能检索系统 - 基于语义的相关性搜索
        5. 经验学习机制 - 从工作流执行中积累经验
        
        技术架构：
        - 前端：FastAPI RESTful接口
        - 后端：PostgreSQL数据库 + RAG检索
        - AI引擎：OpenAI GPT模型 + 自研M3工作流
        - 存储：向量数据库 + 关系数据库混合架构
        
        应用场景：
        - 知识管理：长文档的智能存储和检索
        - 任务自动化：复杂工作流的自动执行
        - 经验积累：从历史任务中学习最佳实践
        """ * 3  # 重复3次模拟长文档
        
        # 写入长文档
        print("📤 写入长文档...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session['id']}/messages",
            json={
                "content": long_document,
                "metadata": {"document_type": "architecture_spec"}
            }
        )
        
        write_duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 长文档写入成功 ({write_duration:.1f}秒)")
            print(f"📄 AI回复: {result.get('content', '')[:100]}...")
        else:
            print(f"❌ 长文档写入失败: {response.status_code}")
            return False
        
        # 检索文档内容
        print("\n🔍 检索文档内容...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/api/v1/users/{self.user['id']}/query",
            json={
                "query": "MemFuse 系统架构 技术特性",
                "top_k": 5,
                "session_id": self.session['id']
            }
        )
        
        search_duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            results = result.get("data", {}).get("results", [])
            print(f"✅ 内容检索成功 ({search_duration:.2f}秒)")
            print(f"📊 找到 {len(results)} 个相关结果")
            
            for i, res in enumerate(results[:2], 1):
                print(f"   {i}. {res.get('content', '')[:80]}...")
        else:
            print(f"❌ 内容检索失败: {response.status_code}")
            return False
        
        return True
    
    def demo_m3_workflow(self):
        """演示M3工作流处理。"""
        print(f"\n🔄 演示2: M3工作流处理")
        print("-" * 30)
        
        # 复杂任务描述
        complex_task = """
        请为MemFuse系统制定一个技术改进计划，包括：
        1. 性能优化方案
        2. 新功能开发建议
        3. 用户体验改进
        4. 系统架构升级
        请提供具体的实施步骤和时间规划。
        """
        
        # 执行M3工作流
        print("🚀 执行M3工作流...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session['id']}/messages?tag=m3",
            json={
                "content": complex_task,
                "metadata": {"task_type": "improvement_planning"}
            }
        )
        
        workflow_duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ M3工作流执行成功 ({workflow_duration:.1f}秒)")
            print(f"🔄 工作流ID: {result.get('workflow_used', 'N/A')}")
            print(f"📄 工作流结果: {result.get('content', '')[:150]}...")
        else:
            print(f"❌ M3工作流执行失败: {response.status_code}")
            return False
        
        # 检索工作流经验
        print("\n🧠 检索工作流经验...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/api/v1/users/{self.user['id']}/query?tag=m3",
            json={
                "query": "技术改进 计划 优化",
                "top_k": 3
            }
        )
        
        search_duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            results = result.get("data", {}).get("results", [])
            workflow_results = [r for r in results if 'workflow' in r.get('type', '')]
            print(f"✅ 工作流经验检索成功 ({search_duration:.2f}秒)")
            print(f"🧠 找到 {len(results)} 个结果，{len(workflow_results)} 个工作流相关")
        else:
            print(f"❌ 工作流经验检索失败: {response.status_code}")
            return False
        
        return True
    
    def run_validation(self):
        """运行完整验证。"""
        print("🎯 MemFuse 核心API端到端验证")
        print("=" * 50)
        
        # 检查服务器
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print("❌ API服务器未响应")
                return False
        except Exception:
            print("❌ 无法连接API服务器")
            print("💡 请先运行: poetry run python scripts/start_api_server.py")
            return False
        
        # 设置环境
        if not self.setup_environment():
            return False
        
        # 演示长上下文
        if not self.demo_long_context():
            return False
        
        # 演示M3工作流
        if not self.demo_m3_workflow():
            return False
        
        # 总结
        print(f"\n🎉 核心API验证完成!")
        print("=" * 50)
        print("✅ 验证的核心功能:")
        print("   📝 长上下文写入和检索")
        print("   🔄 M3工作流执行和经验学习")
        print("   🔍 统一API接口设计")
        
        print(f"\n📋 核心API总结:")
        print(f"   📝 长消息: POST /sessions/{{session_id}}/messages")
        print(f"   🔄 工作流: POST /sessions/{{session_id}}/messages?tag=m3")
        print(f"   🔍 检索: POST /api/v1/users/{{user_id}}/query")
        print(f"   🧠 经验: POST /api/v1/users/{{user_id}}/query?tag=m3")
        
        print(f"\n🔗 验证会话: {self.session['id']}")
        print("🚀 MemFuse系统完全就绪！")

        return True


def main():
    """主函数。"""
    validator = MemFuseCoreValidator()
    success = validator.run_validation()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
