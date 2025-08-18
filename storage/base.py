from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import os
from pathlib import Path

class StorageInterface(ABC):
    """存储接口基类"""
    
    @abstractmethod
    def save(self, data: Any, file_type: str, filename: str) -> bool:
        """保存数据
        
        Args:
            data: 要保存的数据
            file_type: 文件类型（cache/results/logs）
            filename: 文件名
            
        Returns:
            bool: 是否保存成功
        """
        pass
    
    @abstractmethod
    def load(self, file_type: str, filename: str) -> Optional[Any]:
        """加载数据
        
        Args:
            file_type: 文件类型（cache/results/logs）
            filename: 文件名
            
        Returns:
            Optional[Any]: 加载的数据，如果不存在则返回 None
        """
        pass
    
    @abstractmethod
    def list_files(self, file_type: str) -> List[str]:
        """获取文件列表
        
        Args:
            file_type: 文件类型（cache/results/logs）
            
        Returns:
            List[str]: 文件名列表
        """
        pass
    
    @abstractmethod
    def delete(self, file_type: str, filename: str) -> bool:
        """删除文件
        
        Args:
            file_type: 文件类型（cache/results/logs）
            filename: 文件名
            
        Returns:
            bool: 是否删除成功
        """
        pass 