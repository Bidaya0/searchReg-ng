# 无尽模式使用说明

## 概述

无尽模式(Endless Mode)是用户故事4的扩展功能，支持多轮迭代探索。系统会自动进行多轮问题生成→搜索→评分→筛选的完整流程，每轮基于上一轮的最佳方向/结果生成新问题，最终对所有轮次的报告进行评分排序，发送前3个完整报告和其余轮次的摘要。

## 功能特点

- **多轮迭代**: 支持用户指定循环次数上限(默认10次)
- **智能问题生成**: 基于上一轮最佳方向/结果生成新问题，避免重复
- **自动评分排序**: 对所有轮次报告进行多维度评分和排序
- **差异化报告**: 前3个高质量报告完整发送，其余轮次生成摘要
- **错误恢复**: 支持单轮失败继续执行，连续失败自动终止

## 使用方法

### 命令行使用

```bash
# 基本用法
python main.py --endless --topic "人工智能在教育领域的应用"

# 指定循环次数
python main.py --endless --topic "人工智能在教育领域的应用" --max-iterations 5

# 指定完整报告数量
python main.py --endless --topic "人工智能在教育领域的应用" --top-reports 2

# 组合参数
python main.py --endless --topic "人工智能在教育领域的应用" --max-iterations 8 --top-reports 3
```

### 参数说明

- `--endless`: 启用无尽模式
- `--topic`: 要探索的主题
- `--max-iterations`: 最大循环次数(默认10)
- `--top-reports`: 完整发送的报告数量(默认3)

### 编程接口使用

```python
from integrated_workflow import IntegratedWorkflowController
from config import get_config

# 获取配置
config = get_config()

# 启用无尽模式
config["endless_mode"]["enabled"] = True
config["endless_mode"]["max_iterations"] = 10
config["endless_mode"]["top_reports"] = 3

# 初始化系统
integrated_system = IntegratedWorkflowController(config)

# 执行无尽模式
result = integrated_system.process_topic_endless("人工智能在教育领域的应用", 10)

# 处理结果
if result.get("status") == "completed":
    print(f"完成迭代: {result['completed_iterations']}")
    print(f"前N个报告: {len(result['top_reports'])}")
    print(f"摘要报告: {len(result['summary_reports'])}")
```

## 配置参数

在`config.py`中的无尽模式配置：

```python
"endless_mode": {
    "enabled": False,                    # 是否启用无尽模式
    "max_iterations": 10,               # 最大循环次数
    "top_reports": 3,                   # 完整发送的报告数量
    "new_question_strategy": "best_direction_based",  # 新问题生成策略
    "early_termination": {
        "enabled": False,               # 是否启用提前终止
        "no_improvement_threshold": 3,  # 无改善轮次阈值
        "min_score_improvement": 5.0    # 最小评分改善
    },
    "error_handling": {
        "max_consecutive_failures": 3,   # 最大连续失败次数
        "continue_on_partial_failure": True  # 部分失败时是否继续
    }
}
```

## 工作流程

1. **第1轮迭代**: 基于原始主题生成5个方向和25个问题
2. **执行完整流程**: 问题生成→搜索→树状建模→内容评分→方向筛选→报告优化
3. **收集轮次报告**: 保存该轮的所有结果和评分
4. **第2-N轮迭代**: 基于上一轮最佳方向/结果生成新问题，重复完整流程
5. **最终处理**: 对所有轮次报告评分排序，筛选前N个报告
6. **生成摘要**: 为其余轮次生成摘要
7. **发送邮件**: 发送完整报告和摘要

## 评分维度

轮次报告评分包含以下维度：

- **搜索质量评分**(35%): 成功率、结果数量、摘要质量、关键点数量
- **内容深度评分**(35%): 关键发现、方向深度、报告内容丰富度
- **技术指标评分**(20%): 处理时间、问题数量、搜索轮次、成功率
- **新颖性评分**(10%): 与历史报告的差异度、独特性

## 输出格式

### 邮件结构

```
主题：[用户输入的主题]
无尽模式探索报告

=== 执行概览 ===
总迭代次数：[N]
完成迭代次数：[M]
失败迭代次数：[K]
成功率：[百分比]
平均评分：[分数]分
总耗时：[时间]分钟

=== 高质量完整报告（前N个）===
【第X轮报告】
评分：[分数]分 ([质量等级])
最佳方向：[方向名称]
关键发现：
  • [发现1]
  • [发现2]
  ...

=== 其余轮次摘要 ===
【第Y轮摘要】
[摘要内容]

=== 总结 ===
本次无尽模式探索共完成[M]轮迭代，
发现了[N]个有价值的探索方向，
平均评分[分数]分。

报告生成时间：[时间]
```

### 文件输出

- `endless_mode_report_[ID].txt`: 完整无尽模式报告
- `top_report_[N]_[ID].txt`: 前N个完整报告
- `round_summary_[N]_[ID].txt`: 轮次摘要文件

## 性能考虑

- **单轮耗时**: 约15分钟
- **10轮总耗时**: 约150分钟(2.5小时)
- **内存使用**: 随轮次增加，需要管理历史数据
- **优化建议**: 考虑增量保存轮次结果，避免内存溢出

## 错误处理

- **单轮失败**: 记录错误，继续下一轮
- **连续失败**: 超过3轮失败则终止循环
- **部分失败**: 收集已完成的轮次报告，继续最终处理
- **配置错误**: 使用默认配置参数
- **网络错误**: 实现重试机制和超时处理

## 测试验证

运行测试脚本：

```bash
python test_endless_mode.py
```

测试脚本会执行2轮迭代，验证基本功能是否正常。

## 注意事项

1. **向后兼容**: 保持现有`process_topic()`方法不变，无尽模式作为可选功能
2. **资源管理**: 长时间运行需要足够的系统资源
3. **网络依赖**: 需要稳定的网络连接进行搜索
4. **配置检查**: 确保API密钥和基础配置正确
5. **日志监控**: 建议监控日志文件，及时发现问题

## 故障排除

### 常见问题

1. **导入错误**: 确保所有依赖模块已正确安装
2. **配置错误**: 检查API密钥和基础URL配置
3. **内存不足**: 减少最大迭代次数或增加系统内存
4. **网络超时**: 检查网络连接和代理设置
5. **评分异常**: 检查评分器配置和数据格式

### 调试建议

1. 启用详细日志记录
2. 使用较小的迭代次数进行测试
3. 检查中间结果文件
4. 监控系统资源使用情况
5. 查看错误日志获取详细信息
