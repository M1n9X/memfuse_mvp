# MemFuse - AI记忆系统

MemFuse是一个革命性的AI记忆系统，支持长上下文处理和M3工作流技术。

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Poetry
- Docker

### 安装和启动
```bash
# 1. 安装依赖
poetry install

# 2. 启动数据库
docker compose up -d

# 3. 启动API服务器
poetry run python scripts/start_api_server.py
```

## 🎯 核心功能

### 问题1: 长消息写入和检索
```bash
# 写入长消息
curl -X POST "http://localhost:8001/sessions/{session_id}/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "长文本内容..."}'

# 检索内容
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "搜索关键词", "top_k": 10}'
```

### 问题2: 工作流执行和经验检索
```bash
# 执行M3工作流
curl -X POST "http://localhost:8001/sessions/{session_id}/messages?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{"content": "复杂任务描述"}'

# 检索工作流经验
curl -X POST "http://localhost:8001/api/v1/users/{user_id}/query?tag=m3" \
  -H "Content-Type: application/json" \
  -d '{"query": "经验关键词", "top_k": 5}'
```

## 🧪 演示和测试

### 核心API验证
```bash
# 运行端到端验证（推荐）
poetry run python scripts/validate_core_apis.py

# 运行API验证测试
poetry run python tests/final_validation.py
```

### 演示系统
```bash
# 运行综合演示系统
poetry run python demos/demo_launcher.py

# 快速开始示例
poetry run python demos/01_quickstart.py
```

## 📚 文档

- **API参考**: `docs/API_REFERENCE.md` - 完整的API接口文档
- **统一API规范**: `docs/UNIFIED_API_SPECIFICATION.md` - 统一设计说明
- **实现总结**: `docs/API_IMPLEMENTATION_SUMMARY.md` - 技术实现细节
- **验证报告**: `docs/FINAL_VALIDATION_REPORT.md` - 功能验证结果

## 🔧 开发

### 运行测试
```bash
poetry run pytest tests/
```

### 代码格式化
```bash
poetry run black .
poetry run isort .
```

## 🏗️ 系统架构

- **Phase 1**: 基础RAG和向量搜索
- **Phase 2**: 结构化记忆提取
- **Phase 3**: M3工作流编排器
- **Phase 4**: 统一RESTful API

## 🎯 核心设计理念

1. **统一接口**: 通过`tag=m3`参数区分操作模式
2. **智能路由**: 根据tag自动选择处理策略
3. **性能优化**: 长上下文和工作流处理优化
4. **向后兼容**: 支持现有RAG系统

## 🚨 故障排除

### 常见问题
1. **数据库连接错误**: 确保PostgreSQL运行 `docker compose up -d`
2. **环境变量缺失**: 复制`.env.example`到`.env`并填写必要值
3. **端口冲突**: API服务器默认使用8001端口

### 调试
- 数据库日志: `docker compose logs postgres`
- API服务器日志: 查看终端输出
- 调试模式: 在`.env`中设置`LOG_LEVEL=DEBUG`

### 健康检查
```bash
# 检查系统状态
poetry run memfuse health --strict --check-embeddings --check-llm
```

## 📄 许可证

MIT License
