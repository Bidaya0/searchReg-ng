from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from storage_models import SearchResult, SearchState
from storage_utils import StorageUtils
from logger import workflow_logger
import json
import re
from collections import defaultdict, Counter

class MemoryManager:
    """知识记忆管理器"""
    
    def __init__(self, storage: StorageUtils):
        self.storage = storage
        self.memory_file = "memory_data.json"
        self.knowledge_graph_file = "knowledge_graph.json"
        
    def load_memory(self) -> Dict[str, Any]:
        """加载记忆数据"""
        try:
            memory_data = self.storage.load_memory_data()
            if not memory_data:
                return self._init_empty_memory()
            return memory_data
        except Exception as e:
            workflow_logger.log_error(f"加载记忆数据失败: {str(e)}", "MemoryManager")
            return self._init_empty_memory()
    
    def save_memory(self, memory_data: Dict[str, Any]) -> str:
        """保存记忆数据"""
        try:
            # 更新最后修改时间
            memory_data["last_updated"] = datetime.now().isoformat()
            
            # 保存记忆数据
            memory_path = self.storage.save_memory_data(memory_data)
            
            # 单独保存知识图谱
            if "knowledge_graph" in memory_data:
                self.storage.save_knowledge_graph(memory_data["knowledge_graph"])
            
            # 定期备份
            if self._should_backup(memory_data):
                backup_path = self.storage.backup_memory()
                workflow_logger.log_info(f"记忆数据已备份: {backup_path}", "MemoryManager")
            
            return memory_path
        except Exception as e:
            workflow_logger.log_error(f"保存记忆数据失败: {str(e)}", "MemoryManager")
            return ""
    
    def _should_backup(self, memory_data: Dict[str, Any]) -> bool:
        """判断是否需要备份"""
        last_updated = memory_data.get("last_updated")
        if not last_updated:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_updated)
            # 如果距离上次备份超过1小时，则备份
            return (datetime.now() - last_time).total_seconds() > 3600
        except:
            return True
    
    def _init_empty_memory(self) -> Dict[str, Any]:
        """初始化空记忆"""
        return {
            "historical_topics": [],
            "knowledge_graph": {},
            "user_preferences": {},
            "search_patterns": [],
            "concept_relationships": {},
            "learning_insights": [],
            "session_history": [],
            "last_updated": datetime.now().isoformat()
        }
    
    def add_topic_to_history(self, topic: str, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加主题到历史记录"""
        if topic not in memory_data.get("historical_topics", []):
            memory_data["historical_topics"].append(topic)
            # 保持历史记录在合理范围内
            if len(memory_data["historical_topics"]) > 50:
                memory_data["historical_topics"] = memory_data["historical_topics"][-50:]
        
        workflow_logger.log_info(f"添加主题到历史: {topic}", "MemoryManager")
        return memory_data
    
    def update_knowledge_graph(self, topic: str, search_results: List[SearchResult], 
                             memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识图谱"""
        if "knowledge_graph" not in memory_data:
            memory_data["knowledge_graph"] = {}
        
        # 从搜索结果中提取概念和关系
        concepts = self._extract_concepts_from_results(search_results)
        relationships = self._find_concept_relationships(concepts, search_results)
        
        # 更新知识图谱
        if topic not in memory_data["knowledge_graph"]:
            memory_data["knowledge_graph"][topic] = {
                "concepts": [],
                "relationships": [],
                "last_updated": datetime.now().isoformat(),
                "search_count": 0
            }
        
        memory_data["knowledge_graph"][topic]["concepts"].extend(concepts)
        memory_data["knowledge_graph"][topic]["relationships"].extend(relationships)
        memory_data["knowledge_graph"][topic]["search_count"] += 1
        memory_data["knowledge_graph"][topic]["last_updated"] = datetime.now().isoformat()
        
        # 去重
        memory_data["knowledge_graph"][topic]["concepts"] = list(set(
            memory_data["knowledge_graph"][topic]["concepts"]
        ))
        
        workflow_logger.log_info(f"更新知识图谱: {topic}, 概念数: {len(concepts)}", "MemoryManager")
        return memory_data
    
    def _extract_concepts_from_results(self, search_results: List[SearchResult]) -> List[str]:
        """从搜索结果中提取概念"""
        concepts = set()
        
        for search_result in search_results:
            for item in search_result.results:
                # 从标题和摘要中提取关键词
                text = f"{item.title} {item.snippet}"
                # 简单的关键词提取（可以后续优化为更复杂的NLP方法）
                words = re.findall(r'\b[A-Za-z\u4e00-\u9fff]{2,}\b', text)
                # 过滤常见停用词
                stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were'}
                concepts.update([word for word in words if word.lower() not in stop_words])
        
        return list(concepts)[:20]  # 限制概念数量
    
    def _find_concept_relationships(self, concepts: List[str], search_results: List[SearchResult]) -> List[Dict[str, str]]:
        """发现概念之间的关系"""
        relationships = []
        
        # 简单的共现关系检测
        for search_result in search_results:
            text = " ".join([f"{item.title} {item.snippet}" for item in search_result.results])
            for i, concept1 in enumerate(concepts):
                for concept2 in concepts[i+1:]:
                    if concept1 in text and concept2 in text:
                        relationships.append({
                            "source": concept1,
                            "target": concept2,
                            "type": "co_occurrence",
                            "strength": 1
                        })
        
        return relationships
    
    def get_related_concepts(self, topic: str, memory_data: Dict[str, Any]) -> List[str]:
        """获取相关概念"""
        related = []
        
        # 从知识图谱中获取相关概念
        if topic in memory_data.get("knowledge_graph", {}):
            topic_data = memory_data["knowledge_graph"][topic]
            related.extend(topic_data.get("concepts", [])[:10])
        
        # 从历史主题中寻找相似主题
        for hist_topic in memory_data.get("historical_topics", []):
            if hist_topic != topic and self._calculate_topic_similarity(topic, hist_topic) > 0.3:
                if hist_topic in memory_data.get("knowledge_graph", {}):
                    hist_concepts = memory_data["knowledge_graph"][hist_topic].get("concepts", [])
                    related.extend(hist_concepts[:5])
        
        return list(set(related))[:15]  # 去重并限制数量
    
    def _calculate_topic_similarity(self, topic1: str, topic2: str) -> float:
        """计算主题相似度"""
        words1 = set(topic1.lower().split())
        words2 = set(topic2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def update_search_patterns(self, topic: str, query: str, success: bool, 
                             memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新搜索模式"""
        if "search_patterns" not in memory_data:
            memory_data["search_patterns"] = []
        
        pattern = {
            "topic": topic,
            "query": query,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        memory_data["search_patterns"].append(pattern)
        
        # 保持模式记录在合理范围内
        if len(memory_data["search_patterns"]) > 100:
            memory_data["search_patterns"] = memory_data["search_patterns"][-100:]
        
        workflow_logger.log_debug(f"更新搜索模式: {topic} -> {query} ({success})", "MemoryManager")
        return memory_data
    
    def get_learning_insights(self, memory_data: Dict[str, Any]) -> List[str]:
        """获取学习洞察"""
        insights = []
        
        # 分析搜索模式
        patterns = memory_data.get("search_patterns", [])
        if patterns:
            success_rate = sum(1 for p in patterns if p.get("success", False)) / len(patterns)
            insights.append(f"整体搜索成功率: {success_rate:.1%}")
            
            # 分析最成功的查询类型
            successful_queries = [p["query"] for p in patterns if p.get("success", False)]
            if successful_queries:
                query_lengths = [len(q.split()) for q in successful_queries]
                avg_length = sum(query_lengths) / len(query_lengths)
                insights.append(f"成功查询平均长度: {avg_length:.1f} 词")
        
        # 分析知识图谱
        kg = memory_data.get("knowledge_graph", {})
        if kg:
            total_concepts = sum(len(topic_data.get("concepts", [])) for topic_data in kg.values())
            insights.append(f"知识图谱包含 {len(kg)} 个主题，{total_concepts} 个概念")
        
        return insights
    
    def get_context_memory(self, topic: str, memory_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取上下文记忆"""
        context = []
        
        # 获取相关历史主题
        related_topics = []
        for hist_topic in memory_data.get("historical_topics", []):
            if hist_topic != topic and self._calculate_topic_similarity(topic, hist_topic) > 0.2:
                related_topics.append(hist_topic)
        
        if related_topics:
            context.append({
                "type": "related_topics",
                "content": related_topics[:5],
                "relevance": "high"
            })
        
        # 获取相关概念
        related_concepts = self.get_related_concepts(topic, memory_data)
        if related_concepts:
            context.append({
                "type": "related_concepts", 
                "content": related_concepts[:10],
                "relevance": "medium"
            })
        
        # 获取学习洞察
        insights = self.get_learning_insights(memory_data)
        if insights:
            context.append({
                "type": "learning_insights",
                "content": insights,
                "relevance": "low"
            })
        
        return context
    
    def update_session_memory(self, session_data: Dict[str, Any], memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新会话记忆"""
        if "session_history" not in memory_data:
            memory_data["session_history"] = []
        
        session_entry = {
            "timestamp": datetime.now().isoformat(),
            "data": session_data
        }
        
        memory_data["session_history"].append(session_entry)
        
        # 保持会话历史在合理范围内
        if len(memory_data["session_history"]) > 20:
            memory_data["session_history"] = memory_data["session_history"][-20:]
        
        return memory_data
