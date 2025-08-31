#!/usr/bin/env python3
"""
MemFuse Content Creation Demo
展示M3工作流在内容创作任务中的应用
"""

import requests
import time
import json
from typing import Dict, Any, List


class ContentCreationDemo:
    """内容创作demo，展示M3工作流的创作能力。"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        
    def setup_creative_environment(self) -> Dict[str, str]:
        """设置创作环境：创建内容创作者和创作助手。"""
        print("✍️ 设置内容创作环境")
        print("=" * 40)
        
        timestamp = str(int(time.time()))
        
        # 创建内容创作者用户
        creator_data = {
            "name": f"content_creator_{timestamp}",
            "email": f"creator_{timestamp}@studio.ai",
            "metadata": {
                "role": "content_creator",
                "department": "creative_studio",
                "specialization": ["technical_writing", "marketing", "storytelling"]
            }
        }
        
        response = requests.post(f"{self.base_url}/users/", json=creator_data)
        creator = response.json()
        print(f"✅ 内容创作者创建: {creator['name']}")
        
        # 创建创作助手智能体
        assistant_data = {
            "name": f"creative_assistant_{timestamp}",
            "type": "creative_assistant",
            "description": "AI创作助手，专门用于内容策划、写作和编辑",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "creative_capabilities": [
                    "content_planning",
                    "writing_assistance",
                    "editing_suggestions",
                    "style_adaptation"
                ]
            },
            "metadata": {
                "specialization": "content_creation",
                "creativity_level": "high"
            }
        }
        
        response = requests.post(f"{self.base_url}/agents/", json=assistant_data)
        assistant = response.json()
        print(f"✅ 创作助手创建: {assistant['name']}")
        
        # 创建创作会话
        session_data = {
            "user_id": creator["id"],
            "agent_id": assistant["id"],
            "name": f"内容创作会话 - {timestamp}",
            "metadata": {
                "session_type": "content_creation",
                "creative_domain": "technical_content"
            }
        }
        
        response = requests.post(f"{self.base_url}/sessions/", json=session_data)
        session = response.json()
        self.session_id = session["id"]
        print(f"✅ 创作会话创建: {session['name']}")
        
        return {
            "creator_id": creator["id"],
            "assistant_id": assistant["id"],
            "session_id": session["id"]
        }
    
    def demo_blog_post_creation(self):
        """演示博客文章创作。"""
        print("\n📝 演示：技术博客创作")
        print("-" * 30)
        
        blog_request = """
        请帮我创作一篇关于"MemFuse：下一代AI记忆系统"的技术博客文章。
        
        要求：
        1. 目标读者：技术开发者和AI研究者
        2. 文章长度：1500-2000字
        3. 包含技术架构图的描述
        4. 突出创新点和应用场景
        5. 提供代码示例
        
        请使用M3工作流进行内容策划、写作和优化。
        """
        
        print("✍️ 发起博客创作请求...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": blog_request,
                "enable_m3": True,
                "metadata": {
                    "content_type": "blog_post",
                    "target_audience": "developers",
                    "word_count": "1500-2000"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 博客文章创作完成 ({duration:.1f}秒)")
            print(f"📄 文章长度: {len(result['content'])} 字符")
            
            # 显示文章开头
            content = result['content']
            lines = content.split('\n')
            print(f"📖 文章开头预览:")
            for line in lines[:8]:
                if line.strip():
                    print(f"   {line}")
            
            return result
        else:
            print(f"❌ 博客创作失败: {response.status_code}")
            return None
    
    def demo_marketing_copy(self):
        """演示营销文案创作。"""
        print("\n🎯 演示：营销文案创作")
        print("-" * 30)
        
        marketing_request = """
        为MemFuse AI记忆系统创作一套营销文案，包括：
        1. 产品slogan（朗朗上口，体现核心价值）
        2. 产品介绍（200字以内，突出差异化）
        3. 功能特点列表（5-7个核心特点）
        4. 用户证言模板（3个不同角色）
        5. 社交媒体推广文案（Twitter, LinkedIn）
        
        请使用M3工作流确保文案的一致性和吸引力。
        """
        
        print("🎨 发起营销文案创作...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": marketing_request,
                "enable_m3": True,
                "metadata": {
                    "content_type": "marketing_copy",
                    "brand": "MemFuse",
                    "tone": "professional_friendly"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 营销文案创作完成 ({duration:.1f}秒)")
            print(f"🎯 文案长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 营销文案创作失败: {response.status_code}")
            return None
    
    def demo_documentation_writing(self):
        """演示技术文档写作。"""
        print("\n📚 演示：技术文档写作")
        print("-" * 30)
        
        doc_request = """
        请为MemFuse API创建完整的开发者文档，包括：
        1. 快速开始指南
        2. API参考文档
        3. 代码示例和最佳实践
        4. 故障排除指南
        5. 高级用法和集成案例
        
        请使用M3工作流确保文档的完整性和实用性。
        """
        
        print("📖 发起技术文档写作...")
        start_time = time.time()
        
        response = requests.post(
            f"{self.base_url}/sessions/{self.session_id}/chat",
            json={
                "content": doc_request,
                "enable_m3": True,
                "metadata": {
                    "content_type": "technical_documentation",
                    "product": "MemFuse_API",
                    "audience": "developers"
                }
            }
        )
        
        duration = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 技术文档完成 ({duration:.1f}秒)")
            print(f"📚 文档长度: {len(result['content'])} 字符")
            return result
        else:
            print(f"❌ 技术文档写作失败: {response.status_code}")
            return None
    
    def run_complete_demo(self):
        """运行完整的内容创作demo。"""
        print("🚀 MemFuse 内容创作 Demo")
        print("=" * 50)
        
        try:
            # 1. 环境设置
            env_info = self.setup_creative_environment()
            
            # 2. 博客文章创作
            blog_result = self.demo_blog_post_creation()
            
            # 3. 营销文案创作
            marketing_result = self.demo_marketing_copy()
            
            # 4. 技术文档写作
            doc_result = self.demo_documentation_writing()
            
            # 5. 会话分析
            session_stats = self.analyze_research_session()
            
            # 6. 总结
            print("\n🎉 内容创作Demo完成!")
            print("=" * 50)
            print(f"✅ 环境设置: 创作者、助手、会话已创建")
            print(f"✅ 博客创作: {'完成' if blog_result else '失败'}")
            print(f"✅ 营销文案: {'完成' if marketing_result else '失败'}")
            print(f"✅ 技术文档: {'完成' if doc_result else '失败'}")
            print(f"📊 会话统计: {session_stats['total_messages']} 条消息")
            print(f"🧠 M3工作流: {session_stats['workflows_executed']} 个工作流")
            
            print(f"\n🔗 会话链接: {self.base_url}/sessions/{self.session_id}")
            print("💡 您可以继续在这个会话中进行更多内容创作任务")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Demo执行失败: {e}")
            return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
