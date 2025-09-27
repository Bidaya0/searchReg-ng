#!/usr/bin/env python3
"""
记忆管理工具
提供记忆数据的查看、清理、备份等功能
"""

import argparse
import json
from datetime import datetime
from storage_utils import StorageUtils
from memory_manager import MemoryManager
from logger import workflow_logger

class MemoryTools:
    """记忆管理工具类"""
    
    def __init__(self):
        self.storage = StorageUtils()
        self.memory_manager = MemoryManager(self.storage)
    
    def show_memory_status(self):
        """显示记忆状态"""
        print("=== 记忆状态 ===")
        
        try:
            memory_data = self.memory_manager.load_memory()
            
            print(f"历史主题数量: {len(memory_data.get('historical_topics', []))}")
            print(f"知识图谱主题数: {len(memory_data.get('knowledge_graph', {}))}")
            print(f"搜索模式记录数: {len(memory_data.get('search_patterns', []))}")
            print(f"最后更新: {memory_data.get('last_updated', 'N/A')}")
            
            # 显示最近的主题
            recent_topics = memory_data.get('historical_topics', [])[-5:]
            if recent_topics:
                print(f"\n最近搜索的主题:")
                for i, topic in enumerate(recent_topics, 1):
                    print(f"  {i}. {topic}")
            
            # 显示知识图谱概览
            kg = memory_data.get('knowledge_graph', {})
            if kg:
                print(f"\n知识图谱概览:")
                for topic, data in list(kg.items())[:3]:  # 只显示前3个
                    concepts = data.get('concepts', [])
                    relationships = data.get('relationships', [])
                    search_count = data.get('search_count', 0)
                    print(f"  {topic}: {len(concepts)}个概念, {len(relationships)}个关系, {search_count}次搜索")
            
        except Exception as e:
            print(f"获取记忆状态失败: {str(e)}")
    
    def clear_memory(self, confirm=False):
        """清理记忆数据"""
        if not confirm:
            print("警告: 这将删除所有记忆数据!")
            response = input("确认删除? (yes/no): ")
            if response.lower() != 'yes':
                print("操作已取消")
                return
        
        try:
            # 创建空记忆数据
            empty_memory = self.memory_manager._init_empty_memory()
            self.memory_manager.save_memory(empty_memory)
            print("记忆数据已清理")
        except Exception as e:
            print(f"清理记忆数据失败: {str(e)}")
    
    def backup_memory(self):
        """备份记忆数据"""
        try:
            backup_path = self.storage.backup_memory()
            if backup_path:
                print(f"记忆数据已备份到: {backup_path}")
            else:
                print("备份失败: 没有找到记忆数据")
        except Exception as e:
            print(f"备份失败: {str(e)}")
    
    def show_knowledge_graph(self, topic=None):
        """显示知识图谱"""
        try:
            memory_data = self.memory_manager.load_memory()
            kg = memory_data.get('knowledge_graph', {})
            
            if not kg:
                print("知识图谱为空")
                return
            
            if topic:
                if topic in kg:
                    self._show_topic_knowledge(topic, kg[topic])
                else:
                    print(f"未找到主题 '{topic}' 的知识图谱")
            else:
                print("=== 知识图谱概览 ===")
                for topic_name, data in kg.items():
                    print(f"\n主题: {topic_name}")
                    print(f"  概念数: {len(data.get('concepts', []))}")
                    print(f"  关系数: {len(data.get('relationships', []))}")
                    print(f"  搜索次数: {data.get('search_count', 0)}")
                    print(f"  最后更新: {data.get('last_updated', 'N/A')}")
                    
                    # 显示前5个概念
                    concepts = data.get('concepts', [])[:5]
                    if concepts:
                        print(f"  主要概念: {', '.join(concepts)}")
        
        except Exception as e:
            print(f"显示知识图谱失败: {str(e)}")
    
    def _show_topic_knowledge(self, topic, data):
        """显示特定主题的知识详情"""
        print(f"=== 主题: {topic} ===")
        
        concepts = data.get('concepts', [])
        relationships = data.get('relationships', [])
        search_count = data.get('search_count', 0)
        last_updated = data.get('last_updated', 'N/A')
        
        print(f"搜索次数: {search_count}")
        print(f"最后更新: {last_updated}")
        
        print(f"\n概念 ({len(concepts)}个):")
        for i, concept in enumerate(concepts, 1):
            print(f"  {i}. {concept}")
        
        print(f"\n关系 ({len(relationships)}个):")
        for i, rel in enumerate(relationships[:10], 1):  # 只显示前10个关系
            source = rel.get('source', '')
            target = rel.get('target', '')
            rel_type = rel.get('type', '')
            print(f"  {i}. {source} -> {target} ({rel_type})")
    
    def show_search_patterns(self):
        """显示搜索模式"""
        try:
            memory_data = self.memory_manager.load_memory()
            patterns = memory_data.get('search_patterns', [])
            
            if not patterns:
                print("没有搜索模式记录")
                return
            
            print(f"=== 搜索模式 ({len(patterns)}条记录) ===")
            
            # 统计成功率
            success_count = sum(1 for p in patterns if p.get('success', False))
            success_rate = success_count / len(patterns) * 100
            
            print(f"总体成功率: {success_rate:.1f}%")
            
            # 显示最近的模式
            recent_patterns = patterns[-10:]  # 最近10条
            print(f"\n最近的搜索模式:")
            for i, pattern in enumerate(recent_patterns, 1):
                topic = pattern.get('topic', '')
                query = pattern.get('query', '')
                success = pattern.get('success', False)
                timestamp = pattern.get('timestamp', '')
                
                status = "✓" if success else "✗"
                print(f"  {i}. {status} {topic} -> {query} ({timestamp})")
        
        except Exception as e:
            print(f"显示搜索模式失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="记忆管理工具")
    parser.add_argument("--status", action="store_true", help="显示记忆状态")
    parser.add_argument("--clear", action="store_true", help="清理记忆数据")
    parser.add_argument("--backup", action="store_true", help="备份记忆数据")
    parser.add_argument("--kg", help="显示知识图谱 (可选指定主题)")
    parser.add_argument("--patterns", action="store_true", help="显示搜索模式")
    
    args = parser.parse_args()
    
    tools = MemoryTools()
    
    if args.status:
        tools.show_memory_status()
    elif args.clear:
        tools.clear_memory()
    elif args.backup:
        tools.backup_memory()
    elif args.kg is not None:
        tools.show_knowledge_graph(args.kg)
    elif args.patterns:
        tools.show_search_patterns()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
