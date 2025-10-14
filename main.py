from search_workflow import SearchWorkflow
from question_workflow import QuestionWorkflow
from integrated_workflow import IntegratedWorkflowController
from config import get_config
from logger import workflow_logger
import argparse
import sys

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="基于LangGraph的智能搜索与讨论系统 - 支持优化工作流模式")
    parser.add_argument("--topic", type=str, help="要搜索的主题")
    parser.add_argument("--max_results", type=int, default=20, help="最大结果数量")
    parser.add_argument("--interactive", action="store_true", help="交互式模式，从标准输入获取主题")
    parser.add_argument("--questions", action="store_true", help="启用问题生成模式：基于5个方向生成25个问题")
    parser.add_argument("--integrated", action="store_true", help="启用集成工作流模式：问题生成+搜索+汇总")
    parser.add_argument("--optimized", action="store_true", help="启用优化工作流模式：问题生成+搜索+评分+优化报告")
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
    
    # 获取主题和模式
    try:
        if args.interactive:
            # 交互式模式：显示菜单让用户选择
            print("\n" + "="*60)
            print("🚀 智能搜索与讨论系统")
            print("="*60)
            print("请选择运行模式：")
            print("1. 基础搜索模式 - 对单个主题进行深度搜索")
            print("2. 问题生成模式 - 基于5个方向生成25个问题")
            print("3. 集成工作流模式 - 问题生成+搜索+汇总")
            print("4. 优化工作流模式 - 问题生成+搜索+评分+优化报告 (推荐)")
            print("5. 退出")
            print("-"*60)
            
            while True:
                try:
                    choice = input("请输入选择 (1-5): ").strip()
                    if choice == "1":
                        mode = "search"
                        break
                    elif choice == "2":
                        mode = "questions"
                        break
                    elif choice == "3":
                        mode = "integrated"
                        break
                    elif choice == "4":
                        mode = "optimized"
                        break
                    elif choice == "5":
                        print("感谢使用，再见！")
                        sys.exit(0)
                    else:
                        print("无效选择，请输入 1-5")
                except KeyboardInterrupt:
                    print("\n操作已取消")
                    sys.exit(0)
            
            print(f"\n已选择模式: {mode}")
            print("请输入要处理的主题（输入完成后按回车）：")
            topic = input().strip()
            if not topic:
                print("错误：主题不能为空")
                sys.exit(1)
        else:
            # 命令行模式：根据参数确定模式
            if args.optimized:
                mode = "optimized"
            elif args.integrated:
                mode = "integrated"
            elif args.questions:
                mode = "questions"
            else:
                mode = "search"
            
            if not args.topic:
                print("错误：请提供要搜索的主题（使用 --topic 参数或 --interactive 模式）")
                sys.exit(1)
            topic = args.topic
        
        workflow_logger.log_info(f"开始处理主题: {topic}, 模式: {mode}")
        
    except KeyboardInterrupt:
        workflow_logger.log_info("用户中断操作")
        print("\n操作已取消")
        sys.exit(0)
    except Exception as e:
        workflow_logger.log_error(f"获取主题失败: {str(e)}")
        print(f"错误：获取主题失败 - {str(e)}")
        sys.exit(1)
    
    # 分支：根据模式执行相应的处理
    try:
        if mode == "optimized":
            print(f"正在为主题 '{topic}' 执行优化工作流...")
            workflow_logger.log_info("启动优化工作流模式")
            result = integrated_system.process_topic(topic)
            
            if result.get("status") == "completed":
                print(f"\n=== 优化工作流结果 ===")
                print(f"主题：{result['topic']}")
                print(f"工作流ID：{result.get('workflow_id', 'N/A')}")
                print(f"最佳方向：{result.get('best_direction', 'N/A')}")
                print(f"邮件发送状态：{'✅ 成功' if result.get('email_sent', False) else '❌ 失败'}")
                
                # 显示方向评分
                if result.get('direction_scores'):
                    print(f"\n=== 方向评分结果 ===")
                    for i, score in enumerate(result['direction_scores'], 1):
                        print(f"{i}. {score.direction}: {score.overall_score:.1f}分")
                        print(f"   - 搜索质量: {score.search_quality_score:.1f}分")
                        print(f"   - 内容深度: {score.content_depth_score:.1f}分")
                        print(f"   - 技术指标: {score.technical_score:.1f}分")
                
                # 显示优化报告
                if result.get('optimized_report'):
                    report = result['optimized_report']
                    print(f"\n=== 优化报告概览 ===")
                    print(f"最佳方向：{report.best_direction} ({report.best_direction_score:.1f}分)")
                    print(f"执行摘要长度：{len(report.executive_summary)}字符")
                    print(f"详细分析问题数：{len(report.detailed_analysis.get('questions_analysis', []))}")
                    print(f"简要分析方向数：{len(report.brief_analyses)}")
                    print(f"综合建议数：{len(report.comprehensive_recommendations)}")
                    
                    # 显示执行摘要预览
                    print(f"\n=== 执行摘要预览 ===")
                    summary_preview = report.executive_summary[:300] + "..." if len(report.executive_summary) > 300 else report.executive_summary
                    print(summary_preview)
                    
                    # 显示最佳方向的关键发现
                    if report.detailed_analysis.get('key_findings'):
                        print(f"\n=== 最佳方向关键发现 ===")
                        for i, finding in enumerate(report.detailed_analysis['key_findings'][:5], 1):
                            print(f"{i}. {finding}")
                    
                    # 显示综合建议
                    if report.comprehensive_recommendations:
                        print(f"\n=== 综合建议 ===")
                        for i, rec in enumerate(report.comprehensive_recommendations[:5], 1):
                            print(f"{i}. {rec}")
                
                # 显示执行统计
                if result.get('execution_stats'):
                    stats = result['execution_stats']
                    print(f"\n=== 执行统计 ===")
                    print(f"总处理时间：{stats.get('total_time', 'N/A')}秒")
                    print(f"问题生成数：{stats.get('questions_generated', 0)}")
                    print(f"搜索完成数：{stats.get('searches_completed', 0)}")
                    print(f"搜索错误数：{stats.get('search_errors', 0)}")
                    print(f"评分方向数：{stats.get('directions_scored', 0)}")
                    print(f"成功率：{stats.get('success_rate', 0):.2%}")
                
                # 显示邮件内容预览
                if result.get('final_email'):
                    print(f"\n=== 邮件内容预览 ===")
                    email_preview = result['final_email'][:500]
                    print(f"{email_preview}...")
                    print(f"\n📧 完整邮件内容已生成，邮件发送状态：{'✅ 成功' if result.get('email_sent', False) else '❌ 失败'}")
                
                print(f"\n🎉 优化工作流完成！")
                print(f"📋 系统特点：")
                print(f"   - 智能评分：基于搜索质量、内容深度、技术指标的综合评分")
                print(f"   - 重点突出：详细展示最佳方向，简略展示其他方向")
                print(f"   - 结构优化：降低用户阅读负担，提高信息获取效率")
                print(f"   - 统一报告：生成一份综合邮件，包含所有重要信息")
            else:
                print(f"优化工作流失败：{result.get('error', '未知错误')}")
                workflow_logger.log_error(f"优化工作流失败: {result.get('error', '未知错误')}")
        elif mode == "integrated":
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
        elif mode == "questions":
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
        else:  # mode == "search"
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
