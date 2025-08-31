# MemFuse API 使用指南

## 概述

MemFuse API 提供了RESTful接口来访问MemFuse的所有核心功能，包括：
- 用户管理 (Users)
- 智能体管理 (Agents)  
- 会话管理 (Sessions)
- 消息管理 (Messages)
- 智能对话 (Chat)
- M3工作流支持

## 快速开始

### 1. 安装依赖

```bash
# 安装FastAPI相关依赖
poetry add fastapi uvicorn[standard]

# 或者更新现有依赖
poetry install
```

### 2. 启动API服务器

```bash
# 方式1: 使用启动脚本 (推荐)
python scripts/start_api_server.py

# 方式2: 直接启动
poetry run uvicorn memfuse.api_server:app --reload --host 0.0.0.0 --port 8000

# 方式3: 使用poetry脚本
poetry run memfuse-api
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# API文档
open http://localhost:8000/docs
```

## API 端点

### 基础信息
- **Base URL**: `http://localhost:8000`
- **文档**: `http://localhost:8000/docs`
- **健康检查**: `GET /health`

### Users API
```bash
# 创建用户
POST /users/
{
  "name": "john_doe",
  "email": "john@example.com",
  "metadata": {"role": "developer"}
}

# 获取用户
GET /users/{user_id}
GET /users/by-name/{name}

# 列出用户
GET /users/?name=john&limit=10

# 更新用户
PUT /users/{user_id}
{
  "email": "newemail@example.com",
  "metadata": {"role": "senior_developer"}
}

# 删除用户
DELETE /users/{user_id}
```

### Agents API
```bash
# 创建智能体
POST /agents/
{
  "name": "my_assistant",
  "type": "assistant",
  "description": "Personal AI assistant",
  "config": {"model": "gpt-4o-mini", "temperature": 0.7}
}

# 获取智能体
GET /agents/{agent_id}
GET /agents/by-name/{name}

# 列出智能体
GET /agents/?type=assistant&limit=10

# 更新智能体
PUT /agents/{agent_id}
{
  "description": "Updated description",
  "config": {"model": "gpt-4", "temperature": 0.5}
}

# 删除智能体
DELETE /agents/{agent_id}
```

### Sessions API
```bash
# 创建会话
POST /sessions/
{
  "user_id": "user-uuid",
  "agent_id": "agent-uuid",
  "name": "My Chat Session"
}

# 获取会话
GET /sessions/{session_id}

# 列出会话
GET /sessions/?user_id=user-uuid&limit=10

# 更新会话
PUT /sessions/{session_id}
{
  "name": "Updated Session Name",
  "metadata": {"topic": "AI research"}
}

# 删除会话
DELETE /sessions/{session_id}

# 会话统计
GET /sessions/{session_id}/stats
```

### Messages API
```bash
# 创建消息
POST /sessions/{session_id}/messages
{
  "role": "user",
  "content": "Hello, how are you?",
  "tags": ["greeting"],
  "metadata": {"source": "web_ui"}
}

# 列出消息
GET /sessions/{session_id}/messages?role=user&limit=50

# 获取特定消息
GET /sessions/{session_id}/messages/{message_id}

# 删除消息
DELETE /sessions/{session_id}/messages/{message_id}

# 批量创建消息 (用于工作流日志)
POST /sessions/{session_id}/messages/batch
{
  "messages": [
    {
      "role": "system",
      "content": "Workflow step 1: Planning",
      "tags": ["m3", "workflow"],
      "workflow_id": "workflow-uuid",
      "step_index": 0
    },
    {
      "role": "system", 
      "content": "Workflow step 2: Execution",
      "tags": ["m3", "workflow"],
      "workflow_id": "workflow-uuid",
      "step_index": 1
    }
  ]
}
```

### Chat API
```bash
# 基础对话
POST /sessions/{session_id}/chat
{
  "content": "What is machine learning?",
  "enable_m3": false
}

# 复杂任务 (启用M3)
POST /sessions/{session_id}/chat
{
  "content": "Help me analyze the latest AI research trends and create a report",
  "enable_m3": true,
  "metadata": {"priority": "high"}
}
```

## 高级功能

### M3 工作流支持

当 `enable_m3=true` 时，系统会：
1. 使用多智能体系统处理复杂任务
2. 自动记录工作流步骤到消息中
3. 学习成功的工作流模式
4. 在后续类似任务中复用工作流

```python
# 启用M3的复杂任务
response = client.chat(
    session_id=session_id,
    content="Research quantum computing advances and write a technical summary",
    enable_m3=True
)

# 查询工作流相关消息
m3_messages = client.list_messages(session_id, tags=["m3"])
workflow_messages = client.list_messages(session_id, workflow_id=response.get('workflow_used'))
```

### 消息标签和查询

支持灵活的消息标签和查询：

```python
# 创建带标签的消息
client.create_message(
    session_id=session_id,
    role="user",
    content="Important research question",
    tags=["research", "important", "m3"]
)

# 按标签查询
research_messages = client.list_messages(session_id, tags=["research"])
m3_messages = client.list_messages(session_id, tags=["m3"])

# 按内容搜索
ml_messages = client.list_messages(session_id, content_search="machine learning")
```

## 示例代码

### 完整工作流示例

```python
from examples.api_quickstart import MemFuseAPIClient

# 初始化客户端
client = MemFuseAPIClient("http://localhost:8000")

# 1. 创建用户和智能体
user = client.create_user("researcher", "researcher@lab.ai")
agent = client.create_agent("research_assistant", "assistant", 
                           "AI research assistant")

# 2. 创建会话
session = client.create_session(user["id"], agent["id"], "Research Session")

# 3. 基础对话
response = client.chat(session["id"], "What are the latest trends in AI?")
print(f"Response: {response['content']}")

# 4. 复杂任务 (M3)
complex_response = client.chat(
    session["id"], 
    "Research transformer architectures and create a technical comparison",
    enable_m3=True
)

# 5. 查询历史
messages = client.list_messages(session["id"])
m3_messages = client.list_messages(session["id"], tags=["m3"])
```

## 测试

### 运行测试

```bash
# 基础功能测试
python scripts/test_api_basic.py

# 端到端测试 (需要服务器运行)
python scripts/test_api_e2e.py

# 单元测试
poetry run pytest tests/test_api.py -v
```

### 手动测试

```bash
# 启动服务器
python scripts/start_api_server.py

# 在另一个终端运行快速开始示例
python examples/api_quickstart.py
```

## 配置

### 环境变量

API服务器使用与CLI相同的环境变量配置：

```bash
# 数据库配置
POSTGRES_USER=memfuse
POSTGRES_PASSWORD=memfuse
POSTGRES_DB=memfuse
PG_HOST=localhost
PG_PORT=5432

# LLM配置
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini

# 嵌入模型配置
JINA_API_KEY=your_jina_key
EMBEDDING_MODEL=jina-embeddings-v3

# M3功能开关
M3_ENABLED=true
STRUCTURED_ENABLED=true
EXTRACTOR_ENABLED=true
```

### 服务器配置

```bash
# 自定义主机和端口
python scripts/start_api_server.py --host 127.0.0.1 --port 8080

# 禁用自动重载 (生产环境)
python scripts/start_api_server.py --no-reload

# 跳过数据库迁移
python scripts/start_api_server.py --skip-migration
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查PostgreSQL是否运行
   - 验证环境变量配置
   - 确保pgvector扩展已安装

2. **API导入错误**
   - 运行 `poetry install` 安装依赖
   - 检查Python路径配置

3. **M3功能不工作**
   - 确保 `M3_ENABLED=true`
   - 检查OpenAI API密钥配置
   - 查看服务器日志获取详细错误信息

### 调试

```bash
# 查看详细日志
python scripts/start_api_server.py --log-level debug

# 检查数据库状态
python scripts/test_api_basic.py

# 验证配置
python -c "from memfuse.config import get_settings; print(get_settings())"
```

## 生产部署

### Docker部署

```bash
# 构建镜像
docker build -t memfuse-api .

# 运行容器
docker run -p 8000:8000 --env-file .env memfuse-api
```

### 性能优化

- 使用多个worker进程: `uvicorn --workers 4`
- 启用数据库连接池
- 配置适当的CORS策略
- 添加API限流和认证
