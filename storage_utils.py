import json
import os
from typing import Dict, Any
from datetime import datetime
from storage_models import SearchResult, FinalResult, ErrorLog, QuestionsResult

class StorageUtils:
    """存储工具类"""
    
    def __init__(self, base_dir: str = "./data"):
        self.base_dir = base_dir
        self._init_directories()
    
    def _init_directories(self):
        """初始化存储目录"""
        directories = [
            f"{self.base_dir}/cache",
            f"{self.base_dir}/results", 
            f"{self.base_dir}/logs"
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                print(f"警告：无法创建目录 {directory}: {e}")
    
    def save(self, data: Dict[str, Any], category: str, filename: str) -> str:
        """保存数据到文件"""
        file_path = f"{self.base_dir}/{category}/{filename}.json"
        
        def json_serializer(obj):
            """自定义JSON序列化器"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, 'dict'):
                return obj.dict()
            else:
                return str(obj)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
                default=json_serializer
            )
        
        return file_path
    
    def load(self, category: str, filename: str) -> Dict[str, Any]:
        """从文件加载数据"""
        file_path = f"{self.base_dir}/{category}/{filename}.json"
        
        if not os.path.exists(file_path):
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_search_result(self, search_result: SearchResult) -> str:
        """保存搜索结果"""
        filename = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.save(search_result.dict(), "cache", filename)
    
    def save_final_result(self, final_result: FinalResult) -> str:
        """保存最终结果"""
        filename = f"final_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.save(final_result.dict(), "results", filename)
    
    def save_questions_result(self, questions_result: QuestionsResult) -> str:
        """保存问题生成结果"""
        filename = f"questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.save(questions_result.dict(), "results", filename)
    
    def save_error_log(self, error_log: ErrorLog) -> str:
        """保存错误日志"""
        filename = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self.save(error_log.dict(), "logs", filename)
    
    def save_memory_data(self, memory_data: Dict[str, Any]) -> str:
        """保存记忆数据"""
        filename = "memory_data"
        return self.save(memory_data, "cache", filename)
    
    def load_memory_data(self) -> Dict[str, Any]:
        """加载记忆数据"""
        return self.load("cache", "memory_data")
    
    def save_knowledge_graph(self, knowledge_graph: Dict[str, Any]) -> str:
        """保存知识图谱"""
        filename = "knowledge_graph"
        return self.save(knowledge_graph, "cache", filename)
    
    def load_knowledge_graph(self) -> Dict[str, Any]:
        """加载知识图谱"""
        return self.load("cache", "knowledge_graph")
    
    def backup_memory(self) -> str:
        """备份记忆数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        memory_data = self.load_memory_data()
        if memory_data:
            filename = f"memory_backup_{timestamp}"
            return self.save(memory_data, "cache", filename)
        return ""
    
    def restore_memory(self, backup_filename: str) -> bool:
        """从备份恢复记忆数据"""
        try:
            backup_data = self.load("cache", backup_filename)
            if backup_data:
                self.save_memory_data(backup_data)
                return True
        except Exception as e:
            print(f"恢复记忆数据失败: {e}")
        return False