from search_agent import SearchAgentSystem
from question_agent import QuestionAgentSystem
from config import get_config
import argparse

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="智能搜索与讨论系统")
    parser.add_argument("--topic", type=str, help="要搜索的主题")
    parser.add_argument("--max_results", type=int, default=20, help="最大结果数量")
    parser.add_argument("--interactive", action="store_true", help="交互式模式，从标准输入获取主题")
    parser.add_argument("--questions", action="store_true", help="启用问题生成模式：基于5个方向生成25个问题")
    args = parser.parse_args()
    
    # 获取配置
    config = get_config()
    
    # 初始化系统
    search_system = SearchAgentSystem(config)
    question_system = QuestionAgentSystem(config)
    
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
        result = question_system.generate_questions(topic)
    else:
        result = search_system.process_topic(topic)
    
    # 输出结果
    if result.get("status") == "completed" or result.get("total_questions"):
        print("\n=== 对话历史结果 ===")
        print(result)

    else:
        print(f"处理过程中出现错误：{result}")

if __name__ == "__main__":
    main() 