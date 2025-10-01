# 长时间运行工作流系统

## 概述

长时间运行工作流系统是对原有智能搜索系统的扩展，专门设计用于支持几小时甚至更长时间的持续运行任务。该系统具备智能资源管理、状态持久化、进度跟踪和自动优化等特性。

## 主要特性

### 1. 时间控制
- **灵活截止时间**：支持指定具体截止时间或持续时间
- **自适应调整**：根据剩余时间动态调整任务复杂度
- **时间警告**：在时间紧急时提供警告和优化建议

### 2. 资源管理
- **实时监控**：持续监控CPU、内存、磁盘使用情况
- **自动清理**：定期清理内存和临时文件
- **资源限制**：防止系统资源过度使用

### 3. 状态持久化
- **检查点保存**：定期保存工作流状态
- **断点续传**：支持从检查点恢复任务
- **状态恢复**：系统崩溃后可以恢复执行

### 4. 进度跟踪
- **实时进度**：显示任务完成百分比和质量分数
- **收敛检测**：自动检测质量收敛状态
- **效率分析**：分析任务执行效率

### 5. 迭代优化
- **质量评估**：每轮迭代后评估结果质量
- **改进方向**：基于质量评估确定改进方向
- **智能收敛**：达到质量阈值时自动停止

## 使用方法

### 基本使用

```bash
# 使用默认8小时运行时间
python main.py --long-running --topic "人工智能在医疗领域的应用"

# 指定持续时间（4小时）
python main.py --long-running --duration 4 --topic "量子计算研究"

# 指定具体截止时间
python main.py --long-running --deadline "2024-01-01 18:00:00" --topic "区块链技术"
```

### 高级配置

```bash
# 使用硬截止时间策略
python main.py --long-running --time-strategy hard --duration 6 --topic "深度学习"

# 使用软截止时间策略
python main.py --long-running --time-strategy soft --duration 8 --topic "机器学习"
```

### 环境变量配置

在 `.env` 文件中设置以下参数：

```env
# 长时间运行配置
MAX_DURATION_HOURS=8
CHECKPOINT_INTERVAL_MINUTES=15
MEMORY_CLEANUP_INTERVAL_MINUTES=30
MAX_MEMORY_USAGE_MB=2048
MAX_DISK_USAGE_MB=10240
LONG_RUNNING_SEARCH_TIMEOUT=300
LONG_RUNNING_MAX_CONCURRENT=3
LONG_RUNNING_MAX_ITERATIONS=100
QUALITY_CONVERGENCE_THRESHOLD=0.02
```

## 系统架构

### 核心组件

1. **LongRunningWorkflowController**: 主控制器
2. **CheckpointManager**: 检查点管理器
3. **ResourceMonitor**: 资源监控器
4. **LongRunningMemoryManager**: 内存管理器
5. **ProgressTracker**: 进度跟踪器

### 工作流节点

```
资源监控 → 问题生成 → 检查点保存 → 并行搜索 → 内存清理 → 结果处理 → 进度报告 → 总结生成 → 报告生成
     ↑                                                                                    ↓
     └─────────────────────── 条件循环 ←─────────────────────────────────────────────────┘
```

## 配置参数

### 时间控制参数
- `max_duration_hours`: 最大运行时间（小时）
- `checkpoint_interval_minutes`: 检查点保存间隔（分钟）
- `iteration_timeout_minutes`: 单轮迭代最大时间（分钟）

### 资源管理参数
- `max_memory_usage_mb`: 最大内存使用量（MB）
- `max_disk_usage_mb`: 最大磁盘使用量（MB）
- `memory_cleanup_interval_minutes`: 内存清理间隔（分钟）

### 搜索优化参数
- `search_timeout`: 搜索超时时间（秒）
- `max_concurrent_searches`: 最大并发搜索数
- `search_retry_count`: 搜索重试次数

### 质量控制参数
- `max_iterations`: 最大迭代次数
- `quality_convergence_threshold`: 质量收敛阈值
- `quality_threshold`: 质量阈值

## 监控和调试

### 进度监控

系统会定期生成进度报告，包含：
- 完成百分比
- 当前质量分数
- 资源使用情况
- 收敛状态
- 错误率

### 日志文件

- `./data/logs/workflow_*.log`: 工作流执行日志
- `./data/progress/progress_*.json`: 进度报告
- `./data/checkpoints/checkpoint_*.json`: 检查点文件

### 资源监控

```python
from resource_monitor import ResourceMonitor

monitor = ResourceMonitor()
status = monitor.check_resources()
print(f"内存使用: {status['system']['memory_usage_mb']}MB")
print(f"磁盘使用: {status['system']['disk_usage_mb']}MB")
```

## 故障恢复

### 检查点恢复

```python
from checkpoint_manager import CheckpointManager

manager = CheckpointManager()
checkpoints = manager.list_checkpoints()
latest = manager.get_latest_checkpoint()
```

### 状态恢复

系统支持从检查点恢复执行，确保长时间运行任务的连续性。

## 性能优化

### 内存优化
- 定期清理临时数据
- 限制历史记录大小
- 智能垃圾回收

### 磁盘优化
- 定期清理缓存文件
- 压缩历史日志
- 智能存储管理

### 网络优化
- 连接池复用
- 请求超时控制
- 重试机制

## 最佳实践

### 1. 时间规划
- 为复杂主题预留充足时间
- 设置合理的检查点间隔
- 监控剩余时间并及时调整

### 2. 资源管理
- 定期检查系统资源使用
- 设置合理的资源限制
- 监控内存和磁盘使用

### 3. 质量监控
- 关注质量分数变化趋势
- 及时调整搜索策略
- 利用收敛检测优化效率

### 4. 错误处理
- 定期检查日志文件
- 监控错误率变化
- 及时处理异常情况

## 示例代码

### 基本使用示例

```python
from long_running_workflow import LongRunningWorkflowController
from config import get_config
from datetime import datetime, timedelta

# 获取配置
config = get_config()

# 设置截止时间
deadline = datetime.now() + timedelta(hours=6)

# 创建控制器
controller = LongRunningWorkflowController(config, deadline)

# 处理主题
result = controller.process_topic("人工智能在医疗领域的应用")

# 检查结果
if result['status'] == 'completed':
    print(f"任务完成，运行时间: {result['long_running_stats']['elapsed_hours']:.1f}小时")
    print(f"最终质量分数: {result['long_running_stats']['final_quality_score']:.3f}")
```

### 资源监控示例

```python
from resource_monitor import ResourceMonitor

monitor = ResourceMonitor()
status = monitor.check_resources()

if status['system']['memory_usage_mb'] > 1000:
    print("内存使用过高，建议清理")
```

### 进度跟踪示例

```python
from progress_tracker import ProgressTracker

tracker = ProgressTracker()
progress = tracker.calculate_progress(state)
print(f"完成进度: {progress['completion_percentage']:.1f}%")
```

## 故障排除

### 常见问题

1. **内存不足**
   - 检查 `MAX_MEMORY_USAGE_MB` 设置
   - 增加内存清理频率
   - 减少并发搜索数量

2. **磁盘空间不足**
   - 检查 `MAX_DISK_USAGE_MB` 设置
   - 清理旧的日志和缓存文件
   - 增加检查点清理频率

3. **搜索超时**
   - 增加 `LONG_RUNNING_SEARCH_TIMEOUT` 值
   - 减少并发搜索数量
   - 检查网络连接

4. **质量不收敛**
   - 调整 `QUALITY_CONVERGENCE_THRESHOLD` 值
   - 增加最大迭代次数
   - 优化搜索策略

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **监控资源使用**
   ```python
   from resource_monitor import ResourceMonitor
   monitor = ResourceMonitor()
   status = monitor.check_resources()
   ```

3. **检查进度状态**
   ```python
   from progress_tracker import ProgressTracker
   tracker = ProgressTracker()
   progress = tracker.calculate_progress(state)
   ```

## 更新日志

### v1.0.0
- 初始版本发布
- 支持长时间运行工作流
- 实现资源监控和内存管理
- 添加检查点保存和恢复
- 支持进度跟踪和收敛检测

## 贡献指南

欢迎提交Issue和Pull Request来改进长时间运行工作流系统。

## 许可证

本项目采用MIT许可证。
