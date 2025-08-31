# MemFuse API 参考文档

## 🎯 核心API概述

MemFuse提供统一的API接口，通过`tag=m3`参数区分长上下文和工作流操作。

### 两个核心问题的API解决方案

#### 问题1: 长消息写入和检索
- **写入**: `POST /sessions/{session_id}/messages`
- **检索**: `POST /api/v1/users/{user_id}/query`

#### 问题2: 工作流执行和经验检索  
- **执行**: `POST /sessions/{session_id}/messages?tag=m3`
- **检索**: `POST /api/v1/users/{user_id}/query?tag=m3`

## 📝 消息API (Messages)

### 统一消息写入
```
POST /sessions/{session_id}/messages
```

**长上下文模式（默认）**:
```bash
curl -X POST "http://localhost:8001/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "用户的长文本内容...",
    "metadata": {"content_type": "long_context"}
  }'
```

**M3工作流模式**:
```bash
curl -X POST "http://localhost:8001/sessions/{session_id}/messages?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "复杂的多步骤任务描述",
    "metadata": {"task_type": "complex_workflow"}
  }'
```

**请求参数**:
- `session_id` (string, required): 会话ID
- `tag` (string, optional): 使用"m3"启用工作流模式
- `content` (string, required): 消息内容
- `role` (string, optional): 消息角色，默认"user"
- `metadata` (object, optional): 附加元数据

**响应格式**:
```json
{
  "message_id": "uuid",
  "content": "AI回复内容",
  "metadata": {},
  "workflow_used": "uuid或null",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 消息列表获取
```
GET /sessions/{session_id}/messages
```

**参数**:
- `role` (string, optional): 按角色过滤
- `workflow_id` (string, optional): 按工作流ID过滤
- `limit` (int, optional): 限制数量，默认50
- `offset` (int, optional): 偏移量，默认0

## 🔍 查询API (Query)

### 统一内容检索
```
POST /api/v1/users/{user_id}/query
```

**长上下文检索（默认）**:
```bash
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "搜索关键词",
    "top_k": 10,
    "session_id": "可选的会话ID"
  }'
```

**工作流经验检索**:
```bash
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "经验关键词",
    "top_k": 5
  }'
```

**请求参数**:
- `user_id` (string, required): 用户ID
- `tag` (string, optional): 使用"m3"检索工作流经验
- `query` (string, required): 搜索查询
- `top_k` (int, optional): 返回结果数量，默认10
- `session_id` (string, optional): 限制在特定会话

**响应格式**:
```json
{
  "data": {
    "results": [
      {
        "content": "匹配的内容",
        "metadata": {},
        "score": 0.95,
        "type": "message|workflow"
      }
    ]
  }
}
```

## 👤 用户管理API

### 创建用户
```
POST /users/
```

### 获取用户
```
GET /users/{user_id}
```

## 🤖 智能体管理API

### 创建智能体
```
POST /agents/
```

### 获取智能体
```
GET /agents/{agent_id}
```

## 💬 会话管理API

### 创建会话
```
POST /sessions/
```

### 获取会话
```
GET /sessions/{session_id}
```

## 🔧 系统API

### 健康检查
```
GET /health
```

## 📊 API使用模式

### 长上下文处理流程
1. 创建用户和智能体
2. 创建会话
3. 写入长消息: `POST /sessions/{session_id}/messages`
4. 检索内容: `POST /api/v1/users/{user_id}/query`

### M3工作流处理流程
1. 创建用户和智能体
2. 创建会话
3. 执行工作流: `POST /sessions/{session_id}/messages?tag=m3`
4. 检索经验: `POST /api/v1/users/{user_id}/query?tag=m3`

## 🎯 关键设计原则

1. **统一接口**: 通过tag参数区分操作模式
2. **智能路由**: 根据tag自动选择处理策略
3. **向后兼容**: 支持现有RAG系统
4. **性能优化**: M3工作流和长上下文处理优化

## 🚀 快速开始

参见 `demos/01_quickstart.py` 获取完整的使用示例。

运行API服务器:
```bash
poetry run python scripts/start_api_server.py
```

运行核心验证:
```bash
poetry run python scripts/validate_core_apis.py
```

运行详细测试:
```bash
poetry run python tests/final_validation.py
```
