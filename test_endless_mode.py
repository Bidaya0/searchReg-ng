#!/usr/bin/env python3
"""
无尽模式测试脚本
用于测试无尽模式的基本功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import get_config
from integrated_workflow import IntegratedWorkflowController
from logger import workflow_logger

def test_endless_mode():
    """测试无尽模式基本功能"""
    print("=== 无尽模式功能测试 ===")
    
    try:
        # 获取配置
        config = get_config()
        
        # 启用无尽模式
        config["endless_mode"]["enabled"] = True
        config["endless_mode"]["max_iterations"] = 2  # 测试时只运行2轮
        config["endless_mode"]["top_reports"] = 1     # 只选择前1个报告
        
        print(f"配置加载完成")
        print(f"最大迭代次数: {config['endless_mode']['max_iterations']}")
        print(f"前N个报告: {config['endless_mode']['top_reports']}")
        
        # 初始化系统
        integrated_system = IntegratedWorkflowController(config)
        print("系统初始化完成")
        
        # 测试主题
        test_topic = "人工智能在教育领域的应用"
        print(f"测试主题: {test_topic}")
        
        # 执行无尽模式
        print("开始执行无尽模式...")
        result = integrated_system.process_topic_endless(test_topic, 2)
        
        # 检查结果
        if result.get("status") == "completed":
            print("✅ 无尽模式执行成功!")
            print(f"完成迭代: {result.get('completed_iterations', 0)}")
            print(f"失败迭代: {result.get('failed_iterations', 0)}")
            print(f"前N个报告: {len(result.get('top_reports', []))}")
            print(f"摘要报告: {len(result.get('summary_reports', []))}")
            
            # 显示邮件内容预览
            email_content = result.get('final_email_content', '')
            if email_content:
                print(f"\n邮件内容预览:")
                print(email_content[:300] + "..." if len(email_content) > 300 else email_content)
        else:
            print("❌ 无尽模式执行失败!")
            print(f"错误: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_endless_mode()
