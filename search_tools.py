from typing import List, Dict, Any
import yaml
from datetime import datetime
from langchain_community.utilities import SearxSearchWrapper
from storage_models import SearchResult, SearchItem
from storage_utils import StorageUtils

class SearchTools:
    """搜索工具类"""
    
    def __init__(self, searx_host: str, storage: StorageUtils):
        self.search = SearxSearchWrapper(searx_host=searx_host)
        self.storage = storage
    
    def search_query(self, query: str, max_results: int = 20) -> SearchResult:
        """执行搜索查询"""
        try:
            results = self.search.results(
                query,
                engines=['presearch'],
                num_results=max_results
            )
            
            if len(results) <= 1:
                raise Exception("搜索结果为空或过少")
            
            # 格式化搜索结果
            search_result = SearchResult(
                query=query,
                results=[
                    SearchItem(
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        link=item.get("link", "")
                    ) for item in results
                ]
            )
            
            # 保存搜索结果
            self.storage.save_search_result(search_result)
            
            return search_result
            
        except Exception as e:
            raise Exception(f"搜索执行失败: {str(e)}")
    
    def format_search_results(self, search_result: SearchResult) -> str:
        """格式化搜索结果用于LLM"""
        return yaml.dump(search_result.dict(), allow_unicode=True)
