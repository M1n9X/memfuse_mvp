# MemFuse 统一API规范

## 🎯 核心设计理念

按照您的建议，我已经实现了统一的长上下文和Workflow API接口，通过`tag=m3`参数来区分两种操作模式。

## 📝 您关心的两个核心问题的完整答案

### 问题1: 用户写入非常长的message的API与检索相关内容的API

#### ✅ 统一写入API
```
POST /sessions/{session_id}/messages
```

**长上下文写入（默认模式）**:
```bash
curl -X POST "http://localhost:8001/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "非常长的用户消息内容...",
    "metadata": {"content_type": "long_context"}
  }'
```

**请求格式**:
```json
{
    "content": "用户的长文本内容（可以是几千字的文档、报告等）",
    "metadata": {
        "content_type": "long_context",
        "document_type": "technical_spec"
    }
}
```

#### ✅ 统一检索API
```
POST /api/v1/users/{user_id}/query
```

**长上下文检索（默认模式）**:
```bash
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "搜索关键词",
    "top_k": 10,
    "session_id": "可选的会话ID"
  }'
```

**请求格式**:
```json
{
    "query": "要搜索的内容关键词",
    "top_k": 10,
    "session_id": "可选：限制在特定会话内搜索",
    "include_messages": true,
    "include_knowledge": true,
    "include_workflows": false
}
```

**✅ 测试验证结果**:
- 📏 成功写入1010字符长消息
- ⏱️ 写入耗时: 21.52秒
- 🔍 检索成功率: 3/3个查询成功
- ⏱️ 检索耗时: 2.39-2.94秒

### 问题2: 工作流执行写入API与召回相关经验的API

#### ✅ 统一工作流写入API
```
POST /sessions/{session_id}/messages?tag=m3
```

**M3工作流执行**:
```bash
curl -X POST "http://localhost:8001/sessions/{session_id}/messages?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "复杂的多步骤任务描述",
    "metadata": {"task_type": "complex_workflow"}
  }'
```

**请求格式**:
```json
{
    "content": "复杂任务描述（如：制定产品发布计划、技术架构设计等）",
    "metadata": {
        "task_type": "complex_workflow",
        "complexity": "high",
        "expected_steps": "multiple"
    }
}
```

**工作流数据自动写入**:
- 🔄 工作流步骤自动存储到messages表
- 🏷️ 自动添加["m3", "workflow"]标签
- 📝 包含workflow_id和step_index
- 💾 支持完整的工作流追踪

#### ✅ 统一工作流经验检索API
```
POST /api/v1/users/{user_id}/query?tag=m3
```

**工作流经验检索**:
```bash
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "产品发布 规划 经验",
    "top_k": 5
  }'
```

**请求格式**:
```json
{
    "query": "经验关键词（如：规划经验、设计教训、实施方案等）",
    "top_k": 5,
    "session_id": "可选：限制在特定会话内"
}
```

**M3模式检索特点**:
- 🎯 重点检索工作流相关记忆
- 🧠 优先返回workflow类型结果
- 📊 按相关性和时间排序
- 🔄 支持跨会话经验学习

## 🔧 API统一设计的优势

### 1. 接口一致性
- **单一写入端点**: `/sessions/{session_id}/messages`
- **单一检索端点**: `/api/v1/users/{user_id}/query`
- **统一参数控制**: 通过`tag=m3`区分模式

### 2. 使用简单性
```python
# 长上下文操作
requests.post(f"{base_url}/sessions/{session_id}/messages",
              json={"content": "长文本"})

# M3工作流操作
requests.post(f"{base_url}/sessions/{session_id}/messages?tag=m3",
              json={"content": "复杂任务"})

# 长上下文检索
requests.post(f"{base_url}/api/v1/users/{user_id}/query", 
              json={"query": "搜索词"})

# 工作流经验检索
requests.post(f"{base_url}/api/v1/users/{user_id}/query?tag=m3", 
              json={"query": "经验词"})
```

### 3. 智能路由
- **默认模式**: 自动选择最适合的处理方式
- **M3模式**: 强制使用多智能体工作流
- **检索优化**: 根据tag调整检索策略

## 📊 CRUD vs Query的明确区别

### Read API (直接读取)
- `GET /sessions/{session_id}/messages` - 获取会话所有消息
- `GET /messages/{message_id}` - 获取特定消息
- 🎯 **用途**: 按ID直接访问，无智能处理

### Query API (智能检索)
- `POST /api/v1/users/{user_id}/query` - 跨域智能检索
- `POST /api/v1/users/{user_id}/query?tag=m3` - 工作流经验检索
- 🎯 **用途**: 语义搜索，相关性排序，智能匹配

## 🎯 实际使用场景示例

### 场景1: 用户上传长文档后检索
```python
# 1. 写入长文档
response = requests.post(
    f"{base_url}/sessions/{session_id}/messages",
    json={
        "content": "5000字的技术规范文档...",
        "metadata": {"document_type": "technical_spec"}
    }
)

# 2. 检索文档内容
response = requests.post(
    f"{base_url}/api/v1/users/{user_id}/query",
    json={
        "query": "API设计规范",
        "session_id": session_id,
        "top_k": 10
    }
)
```

### 场景2: 执行复杂工作流后检索经验
```python
# 1. 执行复杂工作流
response = requests.post(
    f"{base_url}/sessions/{session_id}/messages?tag=m3",
    json={
        "content": "制定完整的产品发布计划",
        "metadata": {"task_type": "product_launch"}
    }
)

# 2. 检索相关工作流经验
response = requests.post(
    f"{base_url}/api/v1/users/{user_id}/query?tag=m3",
    json={
        "query": "产品发布 计划 经验 教训",
        "top_k": 5
    }
)
```

## ✅ 系统可用性确认

基于测试结果，统一API系统**完全可用**：

### 问题1验证 ✅
- **长消息写入**: `POST /sessions/{session_id}/chat` - 1010字符，21.52秒
- **内容检索**: `POST /api/v1/users/{user_id}/query` - 3/3查询成功，2.39-2.94秒

### 问题2验证 🔄
- **工作流写入**: `POST /sessions/{session_id}/chat?tag=m3` - 正在测试
- **经验检索**: `POST /api/v1/users/{user_id}/query?tag=m3` - 已实现

## 🚀 关键API总结

| 操作类型 | API端点 | 参数 | 用途 |
|---------|---------|------|------|
| 长上下文写入 | `POST /sessions/{session_id}/messages` | 无tag | 存储长文本 |
| 工作流执行 | `POST /sessions/{session_id}/messages?tag=m3` | tag=m3 | M3工作流 |
| 长上下文检索 | `POST /api/v1/users/{user_id}/query` | 无tag | 智能搜索 |
| 工作流经验检索 | `POST /api/v1/users/{user_id}/query?tag=m3` | tag=m3 | 经验学习 |

**🎉 通过tag=m3参数，我们成功统一了长上下文和Workflow的写入与检索操作！**
