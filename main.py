from search_workflow import SearchWorkflow
from question_workflow import QuestionWorkflow
from integrated_workflow import IntegratedWorkflowController
from config import get_config
from logger import workflow_logger
import argparse
import sys

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="基于LangGraph的智能搜索与讨论系统")
    parser.add_argument("--topic", type=str, help="要搜索的主题")
    parser.add_argument("--max_results", type=int, default=20, help="最大结果数量")
    parser.add_argument("--interactive", action="store_true", help="交互式模式，从标准输入获取主题")
    parser.add_argument("--questions", action="store_true", help="启用问题生成模式：基于5个方向生成25个问题")
    parser.add_argument("--integrated", action="store_true", help="启用集成工作流模式：问题生成+搜索+汇总")
    args = parser.parse_args()
    
    try:
        # 获取配置
        workflow_logger.log_info("正在加载配置...")
        config = get_config()
        workflow_logger.log_info("配置加载完成")
        
        # 检查必要的配置
        if not config.get('api_key'):
            workflow_logger.log_error("未设置API_KEY环境变量")
            print("错误：未设置API_KEY环境变量")
            sys.exit(1)
        
        if not config.get('base_url'):
            workflow_logger.log_warning("未设置BASE_URL环境变量，使用默认值")
        
        # 初始化系统
        workflow_logger.log_info("正在初始化系统...")
        search_system = SearchWorkflow(config)
        question_system = QuestionWorkflow(config)
        integrated_system = IntegratedWorkflowController(config)
        workflow_logger.log_info("系统初始化完成")
        
    except Exception as e:
        workflow_logger.log_error(f"系统初始化失败: {str(e)}")
        print(f"错误：系统初始化失败 - {str(e)}")
        sys.exit(1)
    
    # 获取主题
    try:
        if args.interactive:
            print("请输入要搜索的主题（输入完成后按回车）：")
            topic = input().strip()
            if not topic:
                print("错误：主题不能为空")
                sys.exit(1)
        else:
            if not args.topic:
                print("错误：请提供要搜索的主题（使用 --topic 参数或 --interactive 模式）")
                sys.exit(1)
            topic = args.topic
        
        workflow_logger.log_info(f"开始处理主题: {topic}")
        
    except KeyboardInterrupt:
        workflow_logger.log_info("用户中断操作")
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        workflow_logger.log_error(f"获取主题失败: {str(e)}")
        print(f"错误：获取主题失败 - {str(e)}")
        sys.exit(1)
    
    # 分支：问题生成模式 or 搜索模式 or 集成工作流模式
    try:
        if args.integrated:
            print(f"正在为主题 '{topic}' 执行集成工作流...")
            workflow_logger.log_info("启动集成工作流模式")
            result = integrated_system.process_topic(topic)
            
            if result.get("status") == "completed":
                print(f"\n=== 集成工作流结果 ===")
                print(f"主题：{result['topic']}")
                print(f"生成问题数：{len(result.get('questions', []))}")
                print(f"搜索结果数：{len(result.get('search_results', []))}")
                print(f"处理时间：{result.get('execution_stats', {}).get('total_time', 'N/A')}秒")
                
                # 显示综合总结
                if result.get('comprehensive_summary'):
                    summary = result['comprehensive_summary']
                    print(f"\n=== 综合总结 ===")
                    if summary.get('executive_summary'):
                        print(f"执行摘要：\n{summary['executive_summary']}")
                    
                    if summary.get('key_insights'):
                        print(f"\n关键洞察：")
                        for i, insight in enumerate(summary['key_insights'], 1):
                            print(f"  {i}. {insight}")
                    
                    if summary.get('recommendations'):
                        print(f"\n建议和后续行动：")
                        for i, rec in enumerate(summary['recommendations'], 1):
                            print(f"  {i}. {rec}")
                
                # 显示执行统计
                if result.get('execution_stats'):
                    stats = result['execution_stats']
                    print(f"\n=== 执行统计 ===")
                    print(f"总处理时间：{stats.get('total_time', 'N/A')}秒")
                    print(f"问题生成数：{stats.get('questions_generated', 0)}")
                    print(f"搜索完成数：{stats.get('searches_completed', 0)}")
                    print(f"搜索错误数：{stats.get('search_errors', 0)}")
                    print(f"成功率：{stats.get('success_rate', 0):.2%}")
            else:
                print(f"集成工作流失败：{result.get('error', '未知错误')}")
                workflow_logger.log_error(f"集成工作流失败: {result.get('error', '未知错误')}")
        elif args.questions:
            print(f"正在为主题 '{topic}' 生成问题...")
            workflow_logger.log_info("启动问题生成模式")
            result = question_system.generate_questions(topic)
            
            if result.get("status") == "completed":
                print(f"\n=== 问题生成结果 ===")
                print(f"主题：{result['topic']}")
                print(f"总问题数：{result['total_questions']}")
                print("\n各方向问题：")
                
                for i, direction in enumerate(result['directions'], 1):
                    print(f"\n{i}. {direction['direction']}")
                    if direction.get('rationale'):
                        print(f"   设计动机：{direction['rationale']}")
                    print("   问题：")
                    for j, question in enumerate(direction['questions'], 1):
                        print(f"   {j}) {question['question']}")
            else:
                error_msg = result.get('error', '未知错误')
                error_details = result.get('error_details', '')
                print(f"问题生成失败：{error_msg}")
                if error_details:
                    print(f"详细错误信息：\n{error_details}")
                workflow_logger.log_error(f"问题生成失败: {error_msg}")
                if error_details:
                    workflow_logger.log_error(f"详细错误信息:\n{error_details}")
        else:
            print(f"正在处理主题 '{topic}'...")
            workflow_logger.log_info("启动搜索模式")
            result = search_system.process_topic(topic)
            
            if result.get("status") == "completed":
                print(f"\n=== 搜索结果 ===")
                print(f"状态：{result['status']}")
                print(f"终止原因：{result.get('termination_reason', 'N/A')}")
                print(f"搜索次数：{len(result.get('search_results', []))}")
                print(f"总结数量：{len(result.get('summaries', []))}")
                print(f"关键点数量：{len(result.get('key_points', []))}")
                
                # 显示搜索结果
                if result.get('search_results'):
                    print("\n=== 搜索结果详情 ===")
                    for i, search_result in enumerate(result['search_results'], 1):
                        print(f"\n搜索 {i}：{search_result['query']}")
                        print(f"结果数量：{len(search_result['results'])}")
                        for j, item in enumerate(search_result['results'][:3], 1):  # 只显示前3个结果
                            print(f"  {j}. {item['title']}")
                            print(f"     {item['snippet'][:100]}...")
                
                # 显示总结
                if result.get('summaries'):
                    print("\n=== 内容总结 ===")
                    for i, summary in enumerate(result['summaries'], 1):
                        print(f"\n总结 {i}：")
                        print(summary[:200] + "..." if len(summary) > 200 else summary)
                
                # 显示关键点
                if result.get('key_points'):
                    print("\n=== 关键点 ===")
                    for i, key_point in enumerate(result['key_points'], 1):
                        print(f"{i}. {key_point}")
            else:
                print(f"处理失败：{result.get('error', '未知错误')}")
                workflow_logger.log_error(f"搜索处理失败: {result.get('error', '未知错误')}")
                
    except KeyboardInterrupt:
        workflow_logger.log_info("用户中断操作")
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        workflow_logger.log_error(f"处理过程中发生错误: {str(e)}")
        print(f"错误：处理过程中发生错误 - {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
