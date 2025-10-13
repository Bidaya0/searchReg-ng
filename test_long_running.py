#!/usr/bin/env python3
"""
长时间运行工作流测试脚本
"""

import os
import sys
import time
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from long_running_workflow import LongRunningWorkflowController
from checkpoint_manager import CheckpointManager
from resource_monitor import ResourceMonitor
from long_running_memory_manager import LongRunningMemoryManager
from progress_tracker import ProgressTracker
from config import get_config


def test_components():
    """测试各个组件"""
    print("=== 测试长时间运行组件 ===")
    
    config = get_config()
    
    # 测试检查点管理器
    print("\n1. 测试检查点管理器...")
    checkpoint_manager = CheckpointManager()
    test_state = {
        'topic': '测试主题',
        'current_iteration': 1,
        'start_time': datetime.now(),
        'status': 'running'
    }
    checkpoint_path = checkpoint_manager.save_checkpoint(test_state)
    print(f"   检查点保存: {'成功' if checkpoint_path else '失败'}")
    
    # 测试资源监控器
    print("\n2. 测试资源监控器...")
    resource_monitor = ResourceMonitor(config.get('long_running', {}))
    resource_status = resource_monitor.check_resources()
    print(f"   内存使用: {resource_status.get('system', {}).get('memory_usage_mb', 0):.1f}MB")
    print(f"   磁盘使用: {resource_status.get('system', {}).get('disk_usage_mb', 0):.1f}MB")
    print(f"   资源健康: {'是' if resource_monitor.is_resource_healthy() else '否'}")
    
    # 测试内存管理器
    print("\n3. 测试内存管理器...")
    memory_manager = LongRunningMemoryManager(config.get('long_running', {}))
    memory_stats = memory_manager.get_memory_stats()
    print(f"   当前内存: {memory_stats.get('current_memory_mb', 0):.1f}MB")
    print(f"   清理次数: {memory_stats.get('cleanup_count', 0)}")
    
    # 测试进度跟踪器
    print("\n4. 测试进度跟踪器...")
    progress_tracker = ProgressTracker(config.get('long_running', {}))
    mock_state = {
        'current_iteration': 3,
        'elapsed_time': 1800,  # 30分钟
        'remaining_time': 3600,  # 60分钟
        'quality_scores': [
            {'score': 0.6, 'iteration': 1},
            {'score': 0.7, 'iteration': 2},
            {'score': 0.75, 'iteration': 3}
        ],
        'search_results': [{'query': 'test'} for _ in range(5)],
        'status': 'running'
    }
    progress = progress_tracker.calculate_progress(mock_state)
    print(f"   完成百分比: {progress.get('completion_percentage', 0):.1f}%")
    print(f"   质量分数: {progress.get('quality_metrics', {}).get('current_score', 0):.3f}")
    
    print("\n=== 组件测试完成 ===")


def test_short_running():
    """测试短时间运行（用于验证功能）"""
    print("\n=== 测试短时间运行 ===")
    
    config = get_config()
    
    # 设置短时间运行（5分钟）
    deadline = datetime.now() + timedelta(minutes=5)
    
    # 创建控制器
    controller = LongRunningWorkflowController(config, deadline)
    
    # 处理简单主题
    topic = "人工智能基础概念"
    print(f"开始处理主题: {topic}")
    print(f"截止时间: {deadline}")
    
    start_time = time.time()
    try:
        result = controller.process_topic(topic)
        end_time = time.time()
        
        print(f"\n=== 处理完成 ===")
        print(f"状态: {result.get('status')}")
        print(f"实际运行时间: {(end_time - start_time) / 60:.2f}分钟")
        
        if result.get('long_running_stats'):
            stats = result['long_running_stats']
            print(f"总迭代次数: {stats.get('total_iterations', 0)}")
            print(f"最终质量分数: {stats.get('final_quality_score', 0):.3f}")
            print(f"是否收敛: {stats.get('converged', False)}")
            print(f"内存清理次数: {stats.get('memory_cleanup_count', 0)}")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 短时间运行测试完成 ===")


def test_checkpoint_functionality():
    """测试检查点功能"""
    print("\n=== 测试检查点功能 ===")
    
    config = get_config()
    controller = LongRunningWorkflowController(config)
    
    # 列出检查点
    checkpoints = controller.checkpoint_manager.list_checkpoints()
    print(f"发现 {len(checkpoints)} 个检查点")
    
    if checkpoints:
        # 显示最新的检查点信息
        latest = checkpoints[0]
        print(f"最新检查点: {latest['checkpoint_id']}")
        print(f"创建时间: {latest['timestamp']}")
        
        # 获取检查点详细信息
        info = controller.checkpoint_manager.get_checkpoint_info(latest['checkpoint_id'])
        if info:
            print(f"文件大小: {info.get('file_size', 0)} 字节")
            print(f"元数据: {info.get('metadata', {})}")
    
    print("\n=== 检查点功能测试完成 ===")


def test_resource_monitoring():
    """测试资源监控功能"""
    print("\n=== 测试资源监控功能 ===")
    
    config = get_config()
    controller = LongRunningWorkflowController(config)
    
    # 检查当前资源状态
    resource_status = controller.resource_monitor.check_resources()
    print("当前资源状态:")
    print(f"  内存使用: {resource_status.get('system', {}).get('memory_usage_mb', 0):.1f}MB")
    print(f"  磁盘使用: {resource_status.get('system', {}).get('disk_usage_mb', 0):.1f}MB")
    print(f"  CPU使用率: {resource_status.get('system', {}).get('cpu_percent', 0):.1f}%")
    
    # 检查警告
    warnings = resource_status.get('warnings', [])
    if warnings:
        print("警告:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("无警告")
    
    # 检查警报
    alerts = resource_status.get('alerts', [])
    if alerts:
        print("警报:")
        for alert in alerts:
            print(f"  - {alert}")
    else:
        print("无警报")
    
    # 获取资源趋势
    trends = controller.resource_monitor.get_resource_trends(hours=1)
    if 'error' not in trends:
        print(f"过去1小时趋势:")
        print(f"  内存趋势: {trends.get('memory', {}).get('trend', 'unknown')}")
        print(f"  CPU趋势: {trends.get('cpu', {}).get('trend', 'unknown')}")
    else:
        print(f"趋势分析失败: {trends['error']}")
    
    print("\n=== 资源监控功能测试完成 ===")


def main():
    """主测试函数"""
    print("长时间运行工作流测试程序")
    print("=" * 50)
    
    try:
        # 测试各个组件
        test_components()
        
        # 测试检查点功能
        test_checkpoint_functionality()
        
        # 测试资源监控功能
        test_resource_monitoring()
        
        # 询问是否进行短时间运行测试
        print("\n是否进行短时间运行测试？(y/n): ", end="")
        response = input().strip().lower()
        if response in ['y', 'yes']:
            test_short_running()
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"测试执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


