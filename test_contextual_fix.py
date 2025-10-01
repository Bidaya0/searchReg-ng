#!/usr/bin/env python3
"""
测试上下文反馈机制修复
"""

import sys
import os
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contextual_question_optimizer import ContextualQuestionOptimizer
from contextual_reflection_analyzer import ContextualReflection, SearchContext
from config import get_config


def test_contextual_question_optimizer():
    """测试上下文问题优化器"""
    print("=== 测试上下文问题优化器修复 ===")
    
    try:
        config = get_config()
        optimizer = ContextualQuestionOptimizer(config)
        
        # 模拟问题
        questions = [
            {"question": "AI在医疗中的应用"},
            {"question": "机器学习如何改善医疗诊断？"}
        ]
        
        # 模拟上下文反思结果
        contextual_reflection = ContextualReflection(
            search_effectiveness={"effectiveness_score": 0.7},
            result_quality_assessment={"quality_score": 0.8},
            problem_coverage_analysis={"coverage_score": 0.6},
            solving_process_analysis={"process_quality": 0.7},
            knowledge_gap_analysis={"knowledge_gaps": ["技术细节", "实际案例"]},
            pattern_recognition={"successful_patterns": ["具体查询"], "failed_patterns": []},
            query_optimization_suggestions=["使用更具体的术语"],
            search_strategy_adjustments=["增加搜索深度"],
            problem_refinement_suggestions=["补充技术细节"],
            next_iteration_strategy={"focus_areas": ["技术实现"]},
            learned_patterns=["具体查询效果好"],
            successful_strategies=["使用技术术语"],
            avoid_patterns=["模糊查询"],
            confidence_score=0.8,
            analysis_timestamp=None
        )
        
        # 模拟搜索上下文
        search_context = SearchContext(
            search_queries=["AI医疗诊断", "机器学习医疗应用"],
            search_results=[
                {"title": "AI医疗研究", "snippet": "人工智能在医疗诊断中的应用..."},
                {"title": "机器学习医疗", "snippet": "机器学习技术在医疗领域的应用..."}
            ],
            search_errors=[],
            search_timing={"total_time": 120, "avg_iteration_time": 60},
            result_relevance_scores=[0.8, 0.7],
            result_diversity_score=0.6,
            result_completeness_score=0.7,
            problem_solving_steps=["生成问题", "执行搜索", "质量评估"],
            knowledge_gaps_identified=["技术细节", "实际案例"],
            successful_patterns=["具体查询", "技术术语"],
            failed_attempts=["模糊查询"],
            iteration_number=2,
            topic="AI医疗应用",
            timestamp=None
        )
        
        topic = "人工智能在医疗领域的应用"
        
        # 测试问题优化（使用模拟LLM）
        with patch.object(optimizer.llm, 'invoke') as mock_llm:
            mock_response = Mock()
            mock_response.content = "人工智能在医疗诊断中的具体技术实现方法和临床应用案例是什么？"
            mock_llm.return_value = mock_response
            
            optimized_questions = optimizer.optimize_questions_with_context(
                questions, contextual_reflection, search_context, topic
            )
            
            print(f"优化结果:")
            print(f"  原始问题数: {len(questions)}")
            print(f"  优化后问题数: {len(optimized_questions)}")
            
            for i, opt_question in enumerate(optimized_questions[:2]):
                print(f"  问题 {i+1}: {opt_question.get('question', '')}")
                print(f"    优化类型: {opt_question.get('optimization_type', 'unknown')}")
                print(f"    优化原因: {opt_question.get('optimization_reason', '')}")
            
            print("✅ 上下文问题优化器测试通过")
            
    except Exception as e:
        print(f"❌ 上下文问题优化器测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("开始测试上下文反馈机制修复...")
    
    test_contextual_question_optimizer()
    
    print("\n=== 测试完成 ===")
    print("如果测试通过，说明 context_match 错误已修复。")


if __name__ == "__main__":
    main()
