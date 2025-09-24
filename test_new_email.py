#!/usr/bin/env python3
"""
测试新的邮件格式输出
"""

import json
from email_formatter import EmailFormatter
from storage_models import SearchRoundRecord
from datetime import datetime

def test_email_format():
    """测试新的邮件格式"""
    
    # 创建测试数据 - 基于您提供的实际数据
    test_data = {
        "topic": "如何让人开始学习新技能",
        "questions": [
            {"question": "如何激发学习新技能的内在动机？"},
            {"question": "学习新技能需要哪些基础条件？"},
            {"question": "如何选择合适的学习新技能？"},
            {"question": "学习新技能的最佳时机是什么时候？"},
            {"question": "如何制定学习新技能的具体计划？"}
        ],
        "search_rounds": [
            SearchRoundRecord(
                round_number=1,
                question="如何激发学习新技能的内在动机？",
                direction="动机激发",
                search_query="如何激发学习新技能的内在动机？",
                search_results=[],
                summary="学习动机是推动人们开始学习新技能的关键因素。内在动机比外在动机更持久，包括兴趣、好奇心、成就感等。",
                key_points=["内在动机比外在动机更持久", "兴趣是学习的最佳驱动力", "成就感能增强学习动力"],
                success=True,
                processing_time=2.5
            ),
            SearchRoundRecord(
                round_number=2,
                question="学习新技能需要哪些基础条件？",
                direction="基础准备",
                search_query="学习新技能需要哪些基础条件？",
                search_results=[],
                summary="学习新技能需要时间、精力、资源、环境等基础条件。合理规划这些条件是学习成功的前提。",
                key_points=["充足的学习时间", "必要的学习资源", "良好的学习环境", "持续的学习精力"],
                success=True,
                processing_time=3.2
            ),
            SearchRoundRecord(
                round_number=3,
                question="如何选择合适的学习新技能？",
                direction="技能选择",
                search_query="如何选择合适的学习新技能？",
                search_results=[],
                summary="选择学习新技能需要考虑个人兴趣、职业发展、市场需求、学习难度等因素。",
                key_points=["结合个人兴趣", "考虑职业发展", "分析市场需求", "评估学习难度"],
                success=True,
                processing_time=2.8
            )
        ],
        "comprehensive_summary": {
            "executive_summary": "学习新技能是一个系统性的过程，需要从动机激发、基础准备、技能选择等多个维度进行规划和实施。",
            "key_insights": [
                "内在动机是学习成功的关键",
                "基础条件准备充分很重要",
                "技能选择需要综合考虑多个因素"
            ],
            "recommendations": [
                "帮助学习者找到内在动机",
                "提供必要的学习资源和支持",
                "指导学习者做出明智的技能选择"
            ]
        },
        "workflow_id": "test_workflow_001"
    }
    
    # 创建邮件格式化器
    formatter = EmailFormatter()
    
    # 生成邮件内容
    email_content = formatter.format_workflow_result(test_data, "测试用户")
    
    print("=== 新邮件格式测试结果 ===")
    print(email_content)
    print("\n=== 测试完成 ===")
    
    # 保存到文件
    with open("./data/results/test_email_output.txt", "w", encoding="utf-8") as f:
        f.write(email_content)
    
    print("邮件内容已保存到 ./data/results/test_email_output.txt")

if __name__ == "__main__":
    test_email_format()
