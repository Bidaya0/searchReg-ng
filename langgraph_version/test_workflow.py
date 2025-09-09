#!/usr/bin/env python3
"""
测试LangGraph工作流的简单脚本
"""

import os
import sys
from config import get_config
from search_workflow import SearchWorkflow
from question_workflow import QuestionWorkflow

def test_config():
    """测试配置加载"""
    print("测试配置加载...")
    config = get_config()
    print(f"配置加载成功: {list(config.keys())}")
    return config

def test_question_workflow(config):
    """测试问题生成工作流"""
    print("\n测试问题生成工作流...")
    
    try:
        workflow = QuestionWorkflow(config)
        result = workflow.generate_questions("人工智能的发展趋势")
        
        print(f"问题生成结果: {result.get('status', 'unknown')}")
        if result.get('status') == 'completed':
            print(f"总问题数: {result.get('total_questions', 0)}")
            print(f"方向数: {len(result.get('directions', []))}")
        else:
            print(f"错误: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"问题生成工作流测试失败: {e}")

def test_search_workflow(config):
    """测试搜索工作流（需要Searx服务）"""
    print("\n测试搜索工作流...")
    
    try:
        workflow = SearchWorkflow(config)
        result = workflow.process_topic("人工智能的发展趋势")
        
        print(f"搜索结果: {result.get('status', 'unknown')}")
        if result.get('status') == 'completed':
            print(f"搜索次数: {len(result.get('search_results', []))}")
            print(f"总结数: {len(result.get('summaries', []))}")
        else:
            print(f"错误: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"搜索工作流测试失败: {e}")

def main():
    """主测试函数"""
    print("开始测试LangGraph工作流...")
    
    # 测试配置
    config = test_config()
    
    # 检查必要的环境变量
    if not config.get('api_key'):
        print("警告: 未设置API_KEY环境变量")
    
    if not config.get('base_url'):
        print("警告: 未设置BASE_URL环境变量")
    
    # 测试问题生成工作流（不需要外部服务）
    test_question_workflow(config)
    
    # 测试搜索工作流（需要Searx服务）
    test_search_workflow(config)
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()
