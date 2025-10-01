from search_workflow import SearchWorkflow
from question_workflow import QuestionWorkflow
from integrated_workflow import IntegratedWorkflowController
from long_running_workflow import LongRunningWorkflowController
from config import get_config
from logger import workflow_logger
import argparse
import sys
from datetime import datetime, timedelta

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="基于LangGraph的智能搜索与讨论系统")
    parser.add_argument("--topic", type=str, help="要搜索的主题")
    parser.add_argument("--max_results", type=int, default=20, help="最大结果数量")
    parser.add_argument("--interactive", action="store_true", help="交互式模式，从标准输入获取主题")
    parser.add_argument("--questions", action="store_true", help="启用问题生成模式：基于5个方向生成25个问题")
    parser.add_argument("--integrated", action="store_true", help="启用集成工作流模式：问题生成+搜索+汇总")
    parser.add_argument("--long-running", action="store_true", help="启用长时间运行模式：支持几小时运行的智能搜索")
    parser.add_argument("--deadline", type=str, help="截止时间 (格式: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--duration", type=int, help="任务持续时间（小时）")
    parser.add_argument("--time-strategy", choices=["hard", "soft", "adaptive"], 
                       default="adaptive", help="时间控制策略")
    parser.add_argument("--time-iterations", action="store_true", 
                       help="启用时间迭代搜索模式：在指定时间内持续迭代搜索")
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
        
        # 计算截止时间
        deadline = None
        if args.deadline:
            deadline = datetime.strptime(args.deadline, "%Y-%m-%d %H:%M:%S")
        elif args.duration:
            deadline = datetime.now() + timedelta(hours=args.duration)
        elif args.long_running or args.time_iterations:
            # 长时间运行模式或时间迭代模式默认8小时
            deadline = datetime.now() + timedelta(hours=config.get('long_running', {}).get('max_duration_hours', 8))
        
        # 初始化长时间运行系统（如果需要）
        long_running_system = None
        if args.long_running or args.time_iterations:
            long_running_system = LongRunningWorkflowController(config, deadline, args.time_strategy)
            workflow_logger.log_info(f"长时间运行系统已初始化，截止时间: {deadline}，时间策略: {args.time_strategy}")
        
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
    
    # 分支：问题生成模式 or 搜索模式 or 集成工作流模式 or 长时间运行模式 or 时间迭代搜索模式
    try:
        if args.time_iterations:
            print(f"正在为主题 '{topic}' 执行时间迭代搜索...")
            workflow_logger.log_info("启动时间迭代搜索模式")
            
            # 使用时间迭代搜索
            duration_hours = args.duration or 2  # 默认2小时
            result = long_running_system.execute_time_based_iterations(topic, duration_hours)
            
            if result.get("status") == "completed":
                print(f"\n=== 时间迭代搜索结果 ===")
                print(f"主题：{result['topic']}")
                print(f"总迭代次数：{result.get('total_iterations', 0)}")
                print(f"总运行时间：{result.get('elapsed_time', 0)/3600:.1f}小时")
                print(f"总搜索结果数：{result.get('total_results', 0)}")
                print(f"最终质量分数：{result.get('final_quality_score', 0):.3f}")
                print(f"时间策略：{result.get('time_strategy', 'adaptive')}")
                
                # 显示质量分数历史
                if result.get('quality_scores'):
                    print(f"\n=== 质量分数历史 ===")
                    for i, score_data in enumerate(result['quality_scores'], 1):
                        print(f"第{i}轮迭代：质量分数 {score_data.get('score', 0):.3f}")
                
                # 显示执行统计
                print(f"\n=== 执行统计 ===")
                print(f"平均每轮迭代时间：{result.get('elapsed_time', 0)/max(result.get('total_iterations', 1), 1)/60:.1f}分钟")
                print(f"迭代效率：{result.get('total_iterations', 0)/max(result.get('elapsed_time', 1)/3600, 1):.1f}轮/小时")
                
                # 显示基于上下文反馈的反思机制统计
                if result.get('contextual_feedback_enabled'):
                    print(f"\n=== 基于上下文反馈的反思机制统计 ===")
                    contextual_reflection_stats = result.get('contextual_reflection_stats', {})
                    print(f"上下文反思分析次数：{contextual_reflection_stats.get('contextual_reflection_count', 0)}")
                    print(f"平均置信度分数：{contextual_reflection_stats.get('avg_confidence_score', 0):.3f}")
                    print(f"平均搜索效果：{contextual_reflection_stats.get('avg_search_effectiveness', 0):.3f}")
                    print(f"平均结果质量：{contextual_reflection_stats.get('avg_result_quality', 0):.3f}")
                    print(f"识别知识缺口总数：{contextual_reflection_stats.get('total_knowledge_gaps_identified', 0)}")
                    print(f"上下文学习效率：{contextual_reflection_stats.get('contextual_learning_efficiency', 0):.3f}")
                    
                    contextual_optimization_stats = result.get('contextual_optimization_stats', {})
                    print(f"上下文问题优化次数：{contextual_optimization_stats.get('contextual_optimization_count', 0)}")
                    print(f"平均上下文丰富度：{contextual_optimization_stats.get('avg_context_richness', 0):.1f}")
                    print(f"平均优化置信度：{contextual_optimization_stats.get('avg_optimization_confidence', 0):.3f}")
                    print(f"上下文优化问题总数：{contextual_optimization_stats.get('total_questions_contextually_optimized', 0)}")
                    print(f"上下文优化效率：{contextual_optimization_stats.get('contextual_optimization_efficiency', 0):.3f}")
                    
                    print("\n=== 上下文反馈机制说明 ===")
                    print("✅ 基于搜索结果质量分析优化问题")
                    print("✅ 利用搜索过程上下文指导策略调整")
                    print("✅ 识别知识缺口并生成针对性问题")
                    print("✅ 学习成功模式并避免失败模式")
                    print("✅ 在时间满足前持续打磨和优化子问题")
            else:
                print(f"时间迭代搜索失败：{result.get('error', '未知错误')}")
                workflow_logger.log_error(f"时间迭代搜索失败: {result.get('error', '未知错误')}")
        elif args.long_running:
            print(f"正在为主题 '{topic}' 执行长时间运行工作流...")
            workflow_logger.log_info("启动长时间运行模式")
            result = long_running_system.process_topic(topic)
            
            if result.get("status") == "completed":
                print(f"\n=== 长时间运行工作流结果 ===")
                print(f"主题：{result['topic']}")
                print(f"总运行时间：{result.get('long_running_stats', {}).get('elapsed_hours', 0):.1f}小时")
                print(f"总迭代次数：{result.get('long_running_stats', {}).get('total_iterations', 0)}")
                print(f"最终质量分数：{result.get('long_running_stats', {}).get('final_quality_score', 0):.3f}")
                print(f"是否收敛：{result.get('long_running_stats', {}).get('converged', False)}")
                print(f"内存清理次数：{result.get('long_running_stats', {}).get('memory_cleanup_count', 0)}")
                print(f"检查点数量：{result.get('long_running_stats', {}).get('checkpoint_count', 0)}")
                
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
                
                # 显示邮件格式报告
                if result.get('email_content'):
                    print(f"\n=== 邮件格式报告 ===")
                    print("邮件内容已生成并保存到文件。")
                    if result.get('email_filepath'):
                        print(f"邮件文件路径：{result['email_filepath']}")
                    
                    # 显示邮件内容的前500个字符作为预览
                    email_preview = result['email_content'][:500]
                    print(f"\n邮件内容预览：\n{email_preview}...")
                    print(f"\n完整邮件内容请查看文件：{result.get('email_filepath', 'N/A')}")
            else:
                print(f"长时间运行工作流失败：{result.get('error', '未知错误')}")
                workflow_logger.log_error(f"长时间运行工作流失败: {result.get('error', '未知错误')}")
        elif args.integrated:
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
                
                # 显示邮件格式报告
                if result.get('email_content'):
                    print(f"\n=== 邮件格式报告 ===")
                    print("邮件内容已生成并保存到文件。")
                    if result.get('email_filepath'):
                        print(f"邮件文件路径：{result['email_filepath']}")
                    
                    # 显示邮件内容的前500个字符作为预览
                    email_preview = result['email_content'][:500]
                    print(f"\n邮件内容预览：\n{email_preview}...")
                    print(f"\n完整邮件内容请查看文件：{result.get('email_filepath', 'N/A')}")
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
