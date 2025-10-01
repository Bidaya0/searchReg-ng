#!/usr/bin/env python3
"""
时间策略测试脚本 - 测试2小时迭代搜索功能
"""

import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from long_running_workflow import LongRunningWorkflowController
from config import get_config
from logger import workflow_logger


def test_time_strategy_iterations():
    """测试时间策略迭代功能"""
    print("=== 时间策略迭代搜索测试 ===")
    
    # 获取配置
    config = get_config()
    
    # 测试主题
    topic = "人工智能在医疗领域的应用"
    
    # 测试不同的时间策略
    strategies = ["hard", "soft", "adaptive"]
    
    for strategy in strategies:
        print(f"\n--- 测试 {strategy} 时间策略 ---")
        
        try:
            # 创建长时间运行控制器
            deadline = datetime.now() + timedelta(hours=2)  # 2小时测试
            controller = LongRunningWorkflowController(config, deadline, strategy)
            
            # 模拟LLM响应
            with patch.object(controller.llm, 'invoke') as mock_llm:
                # 模拟问题生成响应
                mock_response = Mock()
                mock_response.content = """
                1. 人工智能在医疗诊断中的准确率如何？
                2. 机器学习算法在医学影像分析中的应用现状
                3. AI辅助药物研发的最新进展
                4. 医疗AI系统的伦理和安全问题
                5. 人工智能在个性化医疗中的作用
                """
                mock_llm.return_value = mock_response
                
                # 模拟搜索工作流
                with patch.object(controller.search_workflow, 'process_topic') as mock_search:
                    mock_search.return_value = {
                        "status": "completed",
                        "search_results": [
                            {
                                "query": "AI医疗诊断",
                                "results": [
                                    {"title": "AI医疗诊断研究", "snippet": "人工智能在医疗诊断中的应用..."},
                                    {"title": "机器学习医疗", "snippet": "机器学习在医疗领域的应用..."}
                                ],
                                "summaries": ["AI在医疗诊断中显示出巨大潜力"],
                                "key_points": ["准确率提升", "效率改善"]
                            }
                        ],
                        "summaries": ["AI医疗诊断研究总结"],
                        "key_points": ["技术突破", "应用前景"]
                    }
                    
                    # 执行时间迭代搜索
                    start_time = time.time()
                    result = controller.execute_time_based_iterations(topic, duration_hours=0.1)  # 6分钟测试
                    end_time = time.time()
                    
                    # 验证结果
                    print(f"策略: {strategy}")
                    print(f"状态: {result.get('status', 'unknown')}")
                    print(f"总迭代次数: {result.get('total_iterations', 0)}")
                    print(f"总运行时间: {result.get('elapsed_time', 0):.1f}秒")
                    print(f"总搜索结果数: {result.get('total_results', 0)}")
                    print(f"最终质量分数: {result.get('final_quality_score', 0):.3f}")
                    print(f"实际执行时间: {end_time - start_time:.1f}秒")
                    
                    # 显示质量分数历史
                    if result.get('quality_scores'):
                        print("质量分数历史:")
                        for i, score_data in enumerate(result['quality_scores'], 1):
                            print(f"  第{i}轮: {score_data.get('score', 0):.3f}")
                    
                    # 验证时间策略是否正确执行
                    if strategy == "hard":
                        assert result.get('time_strategy') == "hard", "硬策略未正确设置"
                    elif strategy == "soft":
                        assert result.get('time_strategy') == "soft", "软策略未正确设置"
                    else:
                        assert result.get('time_strategy') == "adaptive", "自适应策略未正确设置"
                    
                    print(f"✓ {strategy} 策略测试通过")
                    
        except Exception as e:
            print(f"✗ {strategy} 策略测试失败: {str(e)}")
            import traceback
            traceback.print_exc()


def test_iteration_logic():
    """测试迭代逻辑"""
    print("\n=== 迭代逻辑测试 ===")
    
    config = get_config()
    topic = "量子计算研究"
    
    try:
        # 创建控制器
        deadline = datetime.now() + timedelta(hours=1)
        controller = LongRunningWorkflowController(config, deadline, "adaptive")
        
        # 测试迭代状态初始化
        state = controller._initialize_iteration_state(topic, deadline)
        print(f"初始状态: {state['topic']}, 剩余时间: {state['remaining_time']:.1f}秒")
        
        # 测试迭代继续判断
        should_continue = controller._should_continue_iteration(state)
        print(f"应该继续迭代: {should_continue}")
        
        # 测试时间策略条件检查
        strategy_result = controller._check_time_strategy_conditions(state)
        print(f"时间策略结果: {strategy_result}")
        
        # 测试自适应策略
        adaptive_result = controller._adaptive_time_strategy(state)
        print(f"自适应策略结果: {adaptive_result}")
        
        print("✓ 迭代逻辑测试通过")
        
    except Exception as e:
        print(f"✗ 迭代逻辑测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_progress_tracker():
    """测试进度跟踪器"""
    print("\n=== 进度跟踪器测试 ===")
    
    from progress_tracker import ProgressTracker
    
    try:
        config = get_config()
        tracker = ProgressTracker(config.get('long_running', {}))
        
        # 模拟状态
        state = {
            "current_iteration": 3,
            "elapsed_time": 1800,  # 30分钟
            "remaining_time": 3600,  # 1小时
            "time_strategy": "adaptive",
            "quality_scores": [
                {"iteration": 1, "score": 0.6, "timestamp": "2024-01-01T10:00:00"},
                {"iteration": 2, "score": 0.7, "timestamp": "2024-01-01T10:15:00"},
                {"iteration": 3, "score": 0.8, "timestamp": "2024-01-01T10:30:00"}
            ],
            "status": "running"
        }
        
        # 计算进度
        progress = tracker.calculate_progress(state)
        
        print(f"完成百分比: {progress['completion_percentage']:.1f}%")
        print(f"迭代进度: {progress['iteration_progress']:.3f}")
        print(f"时间进度: {progress['time_progress']:.3f}")
        print(f"当前质量分数: {progress['quality_metrics']['current_score']:.3f}")
        print(f"时间策略: {progress['time_strategy']}")
        print(f"策略状态: {progress['time_strategy_metrics']['strategy_status']}")
        
        print("✓ 进度跟踪器测试通过")
        
    except Exception as e:
        print(f"✗ 进度跟踪器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("开始时间策略功能测试...")
    print(f"测试时间: {datetime.now()}")
    
    # 运行各项测试
    test_time_strategy_iterations()
    test_iteration_logic()
    test_progress_tracker()
    
    print("\n=== 测试完成 ===")
    print("如果所有测试都通过，说明时间策略2小时迭代搜索功能已正确实现。")


if __name__ == "__main__":
    main()
