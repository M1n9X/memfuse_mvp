### **PRD: “认知核心”AI 记忆与智能体系统**

* **版本**: 1.0
* **日期**: 2025年8月29日
* **项目负责人**: [待定]
* **目标**: 构建一个可扩展的、具备长时程记忆和复杂任务处理能力的高级AI系统。

### 1. 项目愿景与背景

当前的大语言模型（LLM）受限于有限的上下文窗口，无法在长时程交互中保持记忆，也难以自主完成需要多步骤、多工具的复杂任务。本项目旨在通过工程化的手段，围绕**分层记忆（Layered Memory）**和**多智能体系统（Multi-Agent System）**两大核心，打造一个名为“认知核心”的AI底层系统，以突破这些限制。

最终，该系统将能够：

* **“记住”** 与用户的每一次交互，并从中学习。
* **“理解”** 对话中的事实、逻辑和决策，并用于推理。
* **“行动”** 通过规划和执行，自主解决复杂问题。
* **“进化”** 从成功经验中学习，优化未来的行为模式。

### 2. 核心架构总览

系统最终将由两大组件构成，它们协同工作：

1. **分层记忆模块 (Layered Memory)**:

   * **M1 - 情景记忆 (Episodic Memory)**: 存储原始、未经处理的对话历史和外部文档数据。
   * **M2 - 语义记忆 (Semantic Memory)**: 存储从 M1 中提取的结构化事实、实体、关系和决策链。
   * **M3 - 程序性记忆 (Procedural Memory)**: 存储解决特定问题的成功工作流（Workflows）和策略。
2. **多智能体系统 (Multi-Agent System)**:

   * **主智能体 (Master Agent / Orchestrator)**: 负责理解用户意图、任务分解、规划工作流、调用子智能体并监督执行过程。
   * **子智能体 (Sub-agents)**: 负责执行具体的、原子化的任务（如：数据库查询、代码执行、API调用、数据分析等）。

### 3. 阶段性开发计划 (Phased Development Plan)

我们将通过四个清晰的阶段来迭代实现完整系统。

---

#### **阶段一: MVP - 基于 Pgvector 的基础 RAG 系统**

* **核心目标**: 跑通长上下文解决方案的核心链路，验证通过滑动窗口和向量检索绕过LLM上下文限制的可行性。
* **用户故事**: "作为用户，我希望与AI进行超过20轮的深度对话，AI依然能够记得我们最初讨论过的关键信息，而不会‘失忆’。"

**技术规格 (Spec):**

1. **上下文管理 (Context Engineering)**:

   * 实现一个上下文控制器。
   * 硬性限制：`user_input_max_tokens = 32k`，`total_context_max_tokens = 64k`。
   * 上下文构成：`final_context = user_query + retrieved_chunks + conversation_history + system_prompt`。
2. **M1 记忆层 - 情景记忆**:

   * **技术栈**: PostgreSQL + Pgvector 扩展。
   * **数据表 `conversations`**:
     * `session_id` (TEXT, PK)
     * `round_id` (INT, PK)
     * `speaker` (ENUM: 'user', 'ai')
     * `content` (TEXT)
     * `timestamp` (TIMESTAMPTZ)
   * **数据表 `documents_chunks`**:
     * `chunk_id` (UUID, PK)
     * `document_source` (TEXT)
     * `content` (TEXT)
     * `embedding` (VECTOR)
3. **核心 RAG 流程**:

   * **输入**: 用户查询 `query`, `session_id`。
   * **步骤 1 (历史截断)**: 从 `conversations` 表中按 `session_id` 和 `timestamp` 降序获取历史对话，截断到预设的 `history_max_tokens`。
   * **步骤 2 (信息检索)**: 将 `query` 编码为向量，在 `documents_chunks` 表中进行 top-k 相似度搜索，获取 `retrieved_chunks`。
   * **步骤 3 (上下文构建)**: 按照预定模板拼接 `final_context`。
   * **步骤 4 (LLM 调用)**: 将 `final_context` 发送给 LLM。
   * **步骤 5 (记忆存储)**: 将最新的用户查询和AI响应存入 `conversations` 表。

* **成功标准**:
  * 系统能够稳定处理超过模型原生上下文长度的对话。
  * 在长对话后，能够通过提问验证系统确实检索并利用了早期的对话信息。
  * 单次请求处理延迟在可接受范围内。

---

#### **阶段二: 实现 M2 结构化记忆**

* **核心目标**: 提升系统的推理能力，使其能精确理解和回忆对话中的关键事实与决策。
* **用户故事**: "作为用户，当我问‘我们上次为什么决定不使用方案A’时，AI应该能直接回答‘因为方案A的成本超出了预算’，而不仅仅是返回我们讨论成本的那段模糊对话。"

**技术规格 (Spec):**

1. **M2 记忆层 - 语义记忆**:

   * **技术栈**: PostgreSQL (JSONB 或 独立表)。
   * **数据表 `structured_memory`**:
     * `fact_id` (UUID, PK)
     * `session_id` (TEXT, FK)
     * `source_round_id` (INT)
     * `type` (ENUM: 'Fact', 'Decision', 'Assumption', 'User_Preference')
     * `content` (TEXT)
     * `relations` (JSONB)  // e.g., `{ "based_on": ["fact_id_1"], "contradicts": "fact_id_2" }`
     * `metadata` (JSONB) // e.g., `{ "confidence": 0.95 }`
2. **记忆提取模块 (Memory Extraction Module)**:

   * **触发机制**: 在每一轮对话成功存入 M1 后，异步触发。
   * **实现方式**: 一个独立的微服务或无服务器函数 (Serverless Function)。
   * **流程**:
     1. 获取刚结束的对话回合 (`current_round`)。
     2. 调用一个轻量级、低成本的 LLM。
     3. 使用一个精心设计的 Prompt，指令 LLM 从 `current_round` 中提取事实/决策，并以 **JSON格式** 返回。
     4. 将返回的结构化数据存入 `structured_memory` 表。
3. **RAG 流程升级**:

   * 在核心 RAG 流程的步骤 2 中，增加一步：
   * **步骤 2.1 (结构化检索)**: 根据 `query` 中的实体或关键词，在 `structured_memory` 表中进行精确查询。
   * **步骤 2.2 (向量检索)**: 照常进行向量检索。
   * 将两路检索的结果合并、去重、排序后，注入最终上下文。

* **成功标准**:
  * `structured_memory` 表中能自动生成高质量的结构化数据。
  * 对于需要精确事实或决策的提问，系统的回答准确率显著提升。

---

#### **阶段三: 实现多智能体系统 (Multi-Agent System)**

* **核心目标**: 赋予系统执行复杂、多步骤任务的能力。
* **用户故事**: "作为用户，我希望能下达一个高级指令，比如‘帮我分析最新的销售数据，找出表现最好的三个产品并生成一份简报’，AI应该能自主完成这个任务，而不是让我一步步告诉它怎么做。"

**技术规格 (Spec):**

1. **主智能体 (Orchestrator)**:

   * 作为系统的新入口，负责接收所有用户请求。
   * **能力1 (意图识别)**: 判断用户请求是简单问答 (走 RAG 流程) 还是复杂任务 (启动 Agent 流程)。
   * **能力2 (任务规划)**: 调用一个 `Planner` LLM，将复杂任务分解为一系列有序的、可执行的步骤（a plan）。每个步骤包含要调用的 `Sub-agent` 名称和所需参数。
   * **能力3 (执行与调度)**: 按照计划顺序，依次调用相应的 `Sub-agent`，并将上一步的输出作为下一步的输入。
2. **子智能体 (Sub-agents)**:

   * **初期实现**: 至少实现3个基础的、工具化的 Sub-agent。
     * `RAGQueryAgent`: 封装前两个阶段的 RAG 功能，用于“知识查询”。
     * `DatabaseQueryAgent`: 能够根据自然语言请求生成 SQL 并查询数据库。
     * `ReportGenerationAgent`: 能够根据给定的数据和要点，生成格式化的报告文本。
   * **接口规范**: 每个 Sub-agent 都应有统一的 `execute(input)` 接口。

* **成功标准**:
  * 系统能成功执行一个需要至少3个步骤、调用2个以上不同 Sub-agent 的任务。
  * Orchestrator 能够正确地分解任务并传递执行结果。

---

#### **阶段四: 实现 M3 程序性记忆与学习闭环**

* **核心目标**: 让智能体系统具备学习能力，通过记忆成功的解决方案来提升未来处理相似任务的效率和准确性。
* **用户故事**: "作为用户，我发现当我第二次、第三次提出类似的复杂请求时，AI的响应速度明显变快了，结果也更稳定了。"

**技术规格 (Spec):**

1. **M3 记忆层 - 程序性记忆**:

   * **数据表 `procedural_memory`**:
     * `workflow_id` (UUID, PK)
     * `trigger_embedding` (VECTOR) // 对触发该工作流的用户请求的向量化表示
     * `trigger_pattern` (TEXT) // 可选，用于快速匹配的关键词或正则表达式
     * `successful_workflow` (JSONB) // 存储被验证为成功的、完整的任务计划
     * `usage_count` (INT)
2. **学习模块 (Learning Module)**:

   * **触发机制**: 在 Orchestrator 成功完成一个任务流后触发。
   * **流程**:
     1. 一个 `LearningAgent` 回顾整个成功的执行过程（原始请求、最终计划、最终结果）。
     2. 对原始请求进行向量化，对执行计划进行泛化和模板化。
     3. 将这对 `(trigger_embedding, successful_workflow)` 存入 `procedural_memory` 表。
3. **Orchestrator 流程升级**:

   * 在 Orchestrator 接收到新请求后，**第一步**不再是直接规划。
   * **步骤 0 (经验检索)**: 将新请求向量化，并在 `procedural_memory` 表中进行相似度搜索。
   * **决策**: 如果找到一个高相似度的、已成功的工作流，则直接加载并执行该计划，**跳过规划步骤**。否则，才启动 Planner 进行从零规划。

* **成功标准**:
  * 系统能将成功的任务执行经验自动存入 M3。
  * 对于重复性的复杂任务，系统的响应时间（尤其是规划时间）显著缩短。
  * 通过 M3 检索到的工作流执行成功率达到90%以上。
