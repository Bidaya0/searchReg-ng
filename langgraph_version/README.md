# 基于LangGraph的智能搜索与讨论系统

这是原autogen版本的LangGraph重构版本，使用LangGraph框架实现多智能体协作的搜索和问题生成功能。

## 主要改进

1. **使用LangGraph替代autogen**：更现代的图状态管理框架
2. **清晰的工作流定义**：通过节点和边明确定义处理流程
3. **更好的状态管理**：使用Pydantic模型管理状态
4. **简化的错误处理**：更直观的错误处理和重试机制

## 功能特点

- **搜索工作流**：主题分析 → 搜索执行 → 内容记录 → 质量检查
- **问题生成工作流**：问题生成 → JSON解析 → 验证
- **状态持久化**：自动保存搜索结果和生成的问题
- **错误恢复**：自动重试和错误处理

## 安装要求

```bash
pip install -r requirements.txt
```

## 环境配置

创建 `.env` 文件：

```
API_KEY=your_api_key
BASE_URL=your_base_url
MODEL=your_model_name
SEARX_HOST=http://127.0.0.1:8080
```

## 使用方法

### 搜索模式

```bash
python main.py --topic "人工智能的发展趋势"
```

### 问题生成模式

```bash
python main.py --questions --topic "人工智能的发展趋势"
```

### 交互式模式

```bash
python main.py --interactive
```

## 工作流说明

### 搜索工作流

1. **主题分析节点**：分析主题，提取关键词
2. **搜索执行节点**：执行搜索查询
3. **内容记录节点**：总结和记录搜索结果
4. **质量检查节点**：检查对话质量，决定是否继续

### 问题生成工作流

1. **问题生成节点**：基于主题生成25个问题
2. **JSON解析节点**：解析LLM返回的JSON格式
3. **验证节点**：验证问题数量和格式

## 文件结构

```
langgraph_version/
├── main.py                 # 主入口
├── config.py              # 配置管理
├── search_workflow.py     # 搜索工作流
├── question_workflow.py   # 问题生成工作流
├── search_tools.py        # 搜索工具
├── storage_models.py      # 数据模型
├── storage_utils.py       # 存储工具
└── requirements.txt       # 依赖包
```
