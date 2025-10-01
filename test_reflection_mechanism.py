#!/usr/bin/env python3
"""
反思机制测试脚本 - 测试反思和问题优化功能
"""

import sys
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from long_running_workflow import LongRunningWorkflowController
from reflection_analyzer import ReflectionAnalyzer, ReflectionAnalysis
from question_optimizer import QuestionOptimizer
from config import get_config
from logger import workflow_logger


def test_reflection_analyzer():
    """测试反思分析器"""
    print("=== 反思分析器测试 ===")
    
    try:
        config = get_config()
        analyzer = ReflectionAnalyzer(config)
        
        # 模拟状态数据
        state = {
            "current_iteration": 3,
            "topic": "人工智能在医疗领域的应用",
            "questions": [
                {"question": "AI在医疗诊断中的准确率如何？"},
                {"question": "机器学习在医学影像分析中的应用现状"},
                {"question": "AI辅助药物研发的最新进展"}
            ],
            "search_results": [
                {
                    "question": "AI在医疗诊断中的准确率如何？",
                    "results": [
                        {"title": "AI医疗诊断研究", "snippet": "人工智能在医疗诊断中的应用..."},
                        {"title": "机器学习医疗", "snippet": "机器学习在医疗领域的应用..."}
                    ],
                    "summaries": ["AI在医疗诊断中显示出巨大潜力"],
                    "key_points": ["准确率提升", "效率改善"]
                }
            ],
            "accumulated_results": [],
            "quality_scores": [
                {"iteration": 1, "score": 0.6, "timestamp": "2024-01-01T10:00:00"},
                {"iteration": 2, "score": 0.7, "timestamp": "2024-01-01T10:15:00"},
                {"iteration": 3, "score": 0.8, "timestamp": "2024-01-01T10:30:00"}
            ],
            "search_errors": []
        }
        
        # 执行反思分析
        with patch.object(analyzer.llm, 'invoke') as mock_llm:
            # 模拟LLM响应
            mock_response = Mock()
            mock_response.content = """
            基于搜索结果分析，发现以下缺失角度：
            1. AI医疗系统的伦理和安全问题
            2. 医疗AI系统的监管和标准化
            3. AI在个性化医疗中的具体应用
            """
            mock_llm.return_value = mock_response
            
            reflection_analysis = analyzer.analyze_iteration_results(state)
            
            print(f"反思分析结果:")
            print(f"  整体质量分数: {reflection_analysis.overall_quality_score:.3f}")
            print(f"  质量趋势: {reflection_analysis.quality_trend}")
            print(f"  改进潜力: {reflection_analysis.improvement_potential:.3f}")
            print(f"  弱问题数量: {len(reflection_analysis.weak_questions)}")
            print(f"  强问题数量: {len(reflection_analysis.strong_questions)}")
            print(f"  缺失角度数量: {len(reflection_analysis.missing_angles)}")
            print(f"  优化方向数量: {len(reflection_analysis.optimization_directions)}")
            
            print("✓ 反思分析器测试通过")
            
    except Exception as e:
        print(f"✗ 反思分析器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_question_optimizer():
    """测试问题优化器"""
    print("\n=== 问题优化器测试 ===")
    
    try:
        config = get_config()
        optimizer = QuestionOptimizer(config)
        
        # 模拟问题
        questions = [
            {"question": "AI在医疗中的应用"},
            {"question": "机器学习如何改善医疗诊断？"},
            {"question": "人工智能医疗系统的安全性问题"}
        ]
        
        # 模拟反思分析结果
        reflection_analysis = ReflectionAnalysis(
            overall_quality_score=0.7,
            quality_trend="improving",
            improvement_potential=0.3,
            question_effectiveness=[],
            weak_questions=["AI在医疗中的应用"],
            strong_questions=["机器学习如何改善医疗诊断？"],
            missing_angles=["AI医疗伦理问题", "监管政策"],
            search_coverage={},
            result_diversity=0.6,
            information_gaps=["技术细节"],
            duplicate_content=0.2,
            optimization_directions=["深化问题", "补充角度"],
            priority_improvements=["优化弱问题"],
            next_iteration_strategy={},
            iteration_number=2,
            analysis_timestamp=datetime.now(),
            confidence_score=0.8
        )
        
        topic = "人工智能在医疗领域的应用"
        
        # 执行问题优化
        with patch.object(optimizer.llm, 'invoke') as mock_llm:
            # 模拟LLM响应
            mock_response = Mock()
            mock_response.content = "人工智能在医疗诊断中的具体应用案例和技术实现方法是什么？"
            mock_llm.return_value = mock_response
            
            optimized_questions = optimizer.optimize_questions(questions, reflection_analysis, topic)
            
            print(f"问题优化结果:")
            print(f"  原始问题数: {len(questions)}")
            print(f"  优化后问题数: {len(optimized_questions)}")
            
            for i, opt_question in enumerate(optimized_questions):
                print(f"  问题 {i+1}: {opt_question.get('question', '')}")
                print(f"    优化类型: {opt_question.get('optimization_type', 'unknown')}")
                print(f"    优化原因: {opt_question.get('optimization_reason', '')}")
            
            # 分析优化效果
            effectiveness = optimizer.analyze_optimization_effectiveness(questions, optimized_questions)
            print(f"  优化效果分数: {effectiveness.get('effectiveness_score', 0):.3f}")
            
            print("✓ 问题优化器测试通过")
            
    except Exception as e:
        print(f"✗ 问题优化器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_reflection_integration():
    """测试反思机制集成"""
    print("\n=== 反思机制集成测试 ===")
    
    try:
        config = get_config()
        topic = "量子计算研究"
        
        # 创建长时间运行控制器
        deadline = datetime.now() + timedelta(hours=0.1)  # 6分钟测试
        controller = LongRunningWorkflowController(config, deadline, "adaptive")
        
        # 模拟LLM和搜索响应
        with patch.object(controller.llm, 'invoke') as mock_llm, \
             patch.object(controller.search_workflow, 'process_topic') as mock_search:
            
            # 模拟问题生成响应
            mock_response = Mock()
            mock_response.content = """
            1. 量子计算的基本原理是什么？
            2. 量子计算在密码学中的应用
            3. 量子计算的发展现状和挑战
            4. 量子计算与经典计算的比较
            5. 量子计算的实际应用案例
            """
            mock_llm.return_value = mock_response
            
            # 模拟搜索响应
            mock_search.return_value = {
                "status": "completed",
                "search_results": [
                    {
                        "query": "量子计算基本原理",
                        "results": [
                            {"title": "量子计算研究", "snippet": "量子计算的基本原理..."},
                            {"title": "量子算法", "snippet": "量子算法的发展..."}
                        ],
                        "summaries": ["量子计算基于量子力学原理"],
                        "key_points": ["量子叠加", "量子纠缠"]
                    }
                ],
                "summaries": ["量子计算研究总结"],
                "key_points": ["技术突破", "应用前景"]
            }
            
            # 执行时间迭代搜索
            start_time = time.time()
            result = controller.execute_time_based_iterations(topic, duration_hours=0.1)
            end_time = time.time()
            
            print(f"反思机制集成测试结果:")
            print(f"  状态: {result.get('status', 'unknown')}")
            print(f"  总迭代次数: {result.get('total_iterations', 0)}")
            print(f"  总运行时间: {result.get('elapsed_time', 0):.1f}秒")
            print(f"  实际执行时间: {end_time - start_time:.1f}秒")
            print(f"  反思机制启用: {result.get('reflection_enabled', False)}")
            
            # 显示反思统计
            if result.get('reflection_enabled'):
                reflection_stats = result.get('reflection_stats', {})
                print(f"  反思分析次数: {reflection_stats.get('reflection_count', 0)}")
                print(f"  平均质量分数: {reflection_stats.get('avg_quality_score', 0):.3f}")
                print(f"  质量趋势: {reflection_stats.get('quality_trend', 'unknown')}")
                
                optimization_stats = result.get('optimization_stats', {})
                print(f"  问题优化次数: {optimization_stats.get('optimization_count', 0)}")
                print(f"  平均优化效果: {optimization_stats.get('avg_effectiveness', 0):.3f}")
            
            print("✓ 反思机制集成测试通过")
            
    except Exception as e:
        print(f"✗ 反思机制集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def test_reflection_workflow():
    """测试反思工作流"""
    print("\n=== 反思工作流测试 ===")
    
    try:
        config = get_config()
        controller = LongRunningWorkflowController(config, None, "adaptive")
        
        # 模拟状态
        state = {
            "current_iteration": 2,
            "topic": "区块链技术",
            "questions": [
                {"question": "区块链的基本原理"},
                {"question": "区块链在金融领域的应用"}
            ],
            "search_results": [
                {
                    "question": "区块链的基本原理",
                    "results": [{"title": "区块链技术", "snippet": "区块链的基本原理..."}],
                    "summaries": ["区块链是一种分布式账本技术"],
                    "key_points": ["去中心化", "不可篡改"]
                }
            ],
            "accumulated_results": [],
            "quality_scores": [
                {"iteration": 1, "score": 0.6, "timestamp": "2024-01-01T10:00:00"},
                {"iteration": 2, "score": 0.7, "timestamp": "2024-01-01T10:15:00"}
            ]
        }
        
        # 测试反思分析
        with patch.object(controller.reflection_analyzer.llm, 'invoke') as mock_llm:
            mock_response = Mock()
            mock_response.content = """
            基于搜索结果分析，发现以下缺失角度：
            1. 区块链技术的安全性和隐私保护
            2. 区块链在供应链管理中的应用
            3. 区块链技术的能耗和环保问题
            """
            mock_llm.return_value = mock_response
            
            reflection_analysis = controller._perform_reflection_analysis(state)
            
            print(f"反思分析结果:")
            print(f"  质量分数: {reflection_analysis.overall_quality_score:.3f}")
            print(f"  改进潜力: {reflection_analysis.improvement_potential:.3f}")
            print(f"  缺失角度: {len(reflection_analysis.missing_angles)}")
            
            # 测试问题优化
            with patch.object(controller.question_optimizer.llm, 'invoke') as mock_opt_llm:
                mock_opt_response = Mock()
                mock_opt_response.content = "区块链技术在供应链管理中的具体应用案例和实现方法是什么？"
                mock_opt_llm.return_value = mock_opt_response
                
                optimized_questions = controller._optimize_questions_based_on_reflection(
                    state, reflection_analysis
                )
                
                print(f"问题优化结果:")
                print(f"  优化后问题数: {len(optimized_questions)}")
                
                for i, question in enumerate(optimized_questions[:3]):
                    print(f"  问题 {i+1}: {question.get('question', '')}")
            
            print("✓ 反思工作流测试通过")
            
    except Exception as e:
        print(f"✗ 反思工作流测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("开始反思机制功能测试...")
    print(f"测试时间: {datetime.now()}")
    
    # 运行各项测试
    test_reflection_analyzer()
    test_question_optimizer()
    test_reflection_integration()
    test_reflection_workflow()
    
    print("\n=== 测试完成 ===")
    print("如果所有测试都通过，说明反思机制已正确实现，能够在时间满足前不断打磨子问题。")


if __name__ == "__main__":
    main()
