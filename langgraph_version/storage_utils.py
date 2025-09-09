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
            os.makedirs(directory, exist_ok=True)
    
    def save(self, data: Dict[str, Any], category: str, filename: str) -> str:
        """保存数据到文件"""
        file_path = f"{self.base_dir}/{category}/{filename}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
                default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o)
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
