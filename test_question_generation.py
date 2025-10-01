#!/usr/bin/env python3
"""
简单的问题生成测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from question_workflow import QuestionWorkflow
from config import get_config

def test_question_generation():
    """测试问题生成"""
    print("=== 测试问题生成 ===")
    
    # 获取配置
    config = get_config()
    
    # 创建问题生成工作流
    workflow = QuestionWorkflow(config)
    
    # 测试主题
    topic = "测试主题"
    print(f"测试主题: {topic}")
    
    try:
        # 生成问题
        result = workflow.generate_questions(topic)
        
        print(f"结果状态: {result.get('status')}")
        print(f"错误信息: {result.get('error')}")
        print(f"总问题数: {result.get('total_questions', 0)}")
        
        if result.get('directions'):
            print(f"方向数量: {len(result['directions'])}")
            for i, direction in enumerate(result['directions'], 1):
                print(f"  方向{i}: {direction.get('direction', 'unknown')}")
                print(f"    问题数: {len(direction.get('questions', []))}")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_question_generation()
