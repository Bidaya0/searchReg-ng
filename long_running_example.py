#!/usr/bin/env python3
"""
长时间运行工作流使用示例
"""

from long_running_workflow import LongRunningWorkflowController
from config import get_config
from datetime import datetime, timedelta
import time


def example_basic_usage():
    """基本使用示例"""
    print("=== 长时间运行工作流基本使用示例 ===")
    
    # 获取配置
    config = get_config()
    
    # 设置8小时后截止
    deadline = datetime.now() + timedelta(hours=8)
    
    # 创建长时间运行控制器
    controller = LongRunningWorkflowController(config, deadline)
    
    # 处理主题
    topic = "人工智能在医疗领域的深度应用研究"
    print(f"开始处理主题: {topic}")
    print(f"截止时间: {deadline}")
    
    start_time = time.time()
    result = controller.process_topic(topic)
    end_time = time.time()
    
    # 显示结果
    print(f"\n=== 处理完成 ===")
    print(f"状态: {result.get('status')}")
    print(f"实际运行时间: {(end_time - start_time) / 3600:.2f}小时")
    
    if result.get('long_running_stats'):
        stats = result['long_running_stats']
        print(f"总迭代次数: {stats.get('total_iterations', 0)}")
        print(f"最终质量分数: {stats.get('final_quality_score', 0):.3f}")
        print(f"是否收敛: {stats.get('converged', False)}")
        print(f"内存清理次数: {stats.get('memory_cleanup_count', 0)}")
        print(f"检查点数量: {stats.get('checkpoint_count', 0)}")


def example_with_custom_duration():
    """自定义持续时间示例"""
    print("\n=== 自定义持续时间示例 ===")
    
    config = get_config()
    
    # 设置2小时后截止
    deadline = datetime.now() + timedelta(hours=2)
    
    controller = LongRunningWorkflowController(config, deadline)
    
    topic = "量子计算在密码学中的应用"
    print(f"开始处理主题: {topic}")
    print(f"截止时间: {deadline}")
    
    result = controller.process_topic(topic)
    
    print(f"\n=== 处理完成 ===")
    print(f"状态: {result.get('status')}")
    if result.get('long_running_stats'):
        stats = result['long_running_stats']
        print(f"运行时间: {stats.get('elapsed_hours', 0):.2f}小时")
        print(f"迭代次数: {stats.get('total_iterations', 0)}")


def example_checkpoint_recovery():
    """检查点恢复示例"""
    print("\n=== 检查点恢复示例 ===")
    
    config = get_config()
    
    # 创建控制器
    controller = LongRunningWorkflowController(config)
    
    # 列出所有检查点
    checkpoints = controller.checkpoint_manager.list_checkpoints()
    print(f"发现 {len(checkpoints)} 个检查点:")
    
    for i, checkpoint in enumerate(checkpoints[:5], 1):  # 只显示前5个
        print(f"  {i}. {checkpoint['checkpoint_id']} - {checkpoint['timestamp']}")
    
    # 如果有检查点，尝试恢复最新的
    if checkpoints:
        latest_checkpoint = checkpoints[0]
        print(f"\n尝试恢复检查点: {latest_checkpoint['checkpoint_id']}")
        
        # 这里可以添加恢复逻辑
        # recovered_state = controller.checkpoint_manager.load_checkpoint(latest_checkpoint['checkpoint_id'])
        print("检查点恢复功能需要在实际工作流中实现")


def example_resource_monitoring():
    """资源监控示例"""
    print("\n=== 资源监控示例 ===")
    
    config = get_config()
    controller = LongRunningWorkflowController(config)
    
    # 检查当前资源状态
    resource_status = controller.resource_monitor.check_resources()
    print("当前资源状态:")
    print(f"  内存使用: {resource_status.get('system', {}).get('memory_usage_mb', 0):.1f}MB")
    print(f"  磁盘使用: {resource_status.get('system', {}).get('disk_usage_mb', 0):.1f}MB")
    print(f"  CPU使用率: {resource_status.get('system', {}).get('cpu_percent', 0):.1f}%")
    
    # 检查资源健康状态
    is_healthy = controller.resource_monitor.is_resource_healthy()
    print(f"资源健康状态: {'健康' if is_healthy else '不健康'}")
    
    # 获取资源趋势
    trends = controller.resource_monitor.get_resource_trends(hours=1)
    if 'error' not in trends:
        print(f"过去1小时资源趋势:")
        print(f"  内存趋势: {trends.get('memory', {}).get('trend', 'unknown')}")
        print(f"  CPU趋势: {trends.get('cpu', {}).get('trend', 'unknown')}")


def example_progress_tracking():
    """进度跟踪示例"""
    print("\n=== 进度跟踪示例 ===")
    
    config = get_config()
    controller = LongRunningWorkflowController(config)
    
    # 模拟一些进度数据
    mock_state = {
        'current_iteration': 5,
        'elapsed_time': 3600,  # 1小时
        'remaining_time': 7200,  # 2小时
        'quality_scores': [
            {'score': 0.6, 'iteration': 1},
            {'score': 0.7, 'iteration': 2},
            {'score': 0.75, 'iteration': 3},
            {'score': 0.8, 'iteration': 4},
            {'score': 0.82, 'iteration': 5}
        ],
        'search_results': [{'query': 'test'} for _ in range(10)],
        'status': 'running'
    }
    
    # 计算进度
    progress = controller.progress_tracker.calculate_progress(mock_state)
    print("进度信息:")
    print(f"  完成百分比: {progress.get('completion_percentage', 0):.1f}%")
    print(f"  当前质量分数: {progress.get('quality_metrics', {}).get('current_score', 0):.3f}")
    print(f"  是否收敛: {progress.get('convergence_status', {}).get('converged', False)}")
    print(f"  错误率: {progress.get('error_rate', 0):.2%}")
    
    # 获取收敛分析
    convergence = controller.progress_tracker.get_convergence_analysis()
    if 'error' not in convergence:
        print(f"收敛分析:")
        print(f"  是否收敛: {convergence.get('converged', False)}")
        print(f"  方差: {convergence.get('variance', 0):.4f}")
        print(f"  趋势: {convergence.get('trend', 0):.4f}")


def main():
    """主函数"""
    print("长时间运行工作流示例程序")
    print("=" * 50)
    
    try:
        # 基本使用示例
        example_basic_usage()
        
        # 自定义持续时间示例
        example_with_custom_duration()
        
        # 检查点恢复示例
        example_checkpoint_recovery()
        
        # 资源监控示例
        example_resource_monitoring()
        
        # 进度跟踪示例
        example_progress_tracking()
        
        print("\n=== 所有示例完成 ===")
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


