# 基于LangGraph的智能搜索与讨论系统

这是原autogen版本的LangGraph重构版本，使用LangGraph框架实现多智能体协作的搜索和问题生成功能。

## 主要改进

1. **使用LangGraph替代autogen**：更现代的图状态管理框架
2. **清晰的工作流定义**：通过节点和边明确定义处理流程
3. **更好的状态管理**：使用Pydantic模型管理状态
4. **简化的错误处理**：更直观的错误处理和重试机制
5. **智能记忆系统**：支持跨会话记忆、知识图谱构建和学习模式

## 功能特点

- **搜索工作流**：记忆加载 → 主题分析 → 搜索执行 → 内容记录 → 记忆更新 → 质量检查
- **问题生成工作流**：问题生成 → JSON解析 → 验证
- **智能记忆系统**：
  - 历史主题记录和关联发现
  - 知识图谱自动构建和更新
  - 学习模式支持新概念学习
  - 搜索模式分析和优化
  - 跨会话记忆持久化
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

### 记忆管理

```bash
# 查看记忆状态
python memory_tools.py --status

# 查看知识图谱
python memory_tools.py --kg

# 查看特定主题的知识图谱
python memory_tools.py --kg "人工智能"

# 查看搜索模式
python memory_tools.py --patterns

# 备份记忆数据
python memory_tools.py --backup

# 清理记忆数据
python memory_tools.py --clear
```

### 测试记忆功能

```bash
python test_memory.py
```

## 工作流说明

### 搜索工作流

1. **记忆加载节点**：加载历史记忆、知识图谱和相关概念
2. **主题分析节点**：分析主题，提取关键词，利用历史记忆
3. **搜索执行节点**：执行搜索查询，记录搜索模式
4. **内容记录节点**：总结和记录搜索结果
5. **记忆更新节点**：更新知识图谱、搜索模式和会话记忆
6. **质量检查节点**：基于记忆内容进行智能决策，检查对话质量

### 问题生成工作流

1. **问题生成节点**：基于主题生成25个问题
2. **JSON解析节点**：解析LLM返回的JSON格式
3. **验证节点**：验证问题数量和格式

## 文件结构

```
searchReg-ng2/
├── main.py                 # 主入口
├── config.py              # 配置管理
├── search_workflow.py     # 搜索工作流
├── question_workflow.py   # 问题生成工作流
├── search_tools.py        # 搜索工具
├── storage_models.py      # 数据模型
├── storage_utils.py       # 存储工具
├── memory_manager.py      # 记忆管理器
├── memory_tools.py        # 记忆管理工具
├── test_memory.py         # 记忆功能测试
├── logger.py              # 日志工具
└── requirements.txt       # 依赖包
```

## 记忆系统详解

### 记忆组件

1. **MemoryManager**: 核心记忆管理器
   - 知识图谱构建和更新
   - 概念关系发现
   - 搜索模式分析
   - 学习洞察生成

2. **SearchState扩展**: 增强的状态模型
   - 历史主题记录
   - 学习模式开关
   - 知识图谱存储
   - 相关概念关联
   - 用户偏好设置
   - 会话记忆管理

3. **记忆持久化**: 跨会话记忆保存
   - 自动备份机制
   - 知识图谱单独存储
   - 定期清理和优化

### 智能特性

- **自适应搜索阈值**: 基于历史成功率调整最小结果数
- **知识覆盖度检查**: 智能判断知识图谱完整性
- **关联发现**: 自动发现主题间的概念关联
- **学习模式**: 特别关注新概念的学习和关联
- **上下文记忆**: 提供相关的历史上下文信息
