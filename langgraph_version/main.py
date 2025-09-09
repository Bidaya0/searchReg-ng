from search_workflow import SearchWorkflow
from question_workflow import QuestionWorkflow
from config import get_config
import argparse

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="基于LangGraph的智能搜索与讨论系统")
    parser.add_argument("--topic", type=str, help="要搜索的主题")
    parser.add_argument("--max_results", type=int, default=20, help="最大结果数量")
    parser.add_argument("--interactive", action="store_true", help="交互式模式，从标准输入获取主题")
    parser.add_argument("--questions", action="store_true", help="启用问题生成模式：基于5个方向生成25个问题")
    args = parser.parse_args()
    
    # 获取配置
    config = get_config()
    
    # 初始化系统
    search_system = SearchWorkflow(config)
    question_system = QuestionWorkflow(config)
    
    # 获取主题
    if args.interactive:
        print("请输入要搜索的主题（输入完成后按回车）：")
        topic = input().strip()
    else:
        if not args.topic:
            print("错误：请提供要搜索的主题（使用 --topic 参数或 --interactive 模式）")
            return
        topic = args.topic
    
    # 分支：问题生成模式 or 搜索模式
    if args.questions:
        print(f"正在为主题 '{topic}' 生成问题...")
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
            print(f"问题生成失败：{result.get('error', '未知错误')}")
    else:
        print(f"正在处理主题 '{topic}'...")
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

if __name__ == "__main__":
    main()
