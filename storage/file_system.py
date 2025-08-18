from typing import Any, List, Optional
import json
import os
from pathlib import Path
from .base import StorageInterface

class FileSystemStorage(StorageInterface):
    """文件系统存储实现"""
    
    def __init__(self, base_dir: str):
        """初始化文件系统存储
        
        Args:
            base_dir: 基础目录路径
        """
        self.base_dir = Path(base_dir)
        self._init_storage()
    
    def _init_storage(self):
        """初始化存储目录"""
        storage_dirs = [
            self.base_dir / "cache",
            self.base_dir / "results",
            self.base_dir / "logs"
        ]
        
        for dir_path in storage_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, file_type: str, filename: str) -> Path:
        """获取文件完整路径
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            Path: 文件完整路径
        """
        return self.base_dir / file_type / f"{filename}.json"
    
    def save(self, data: Any, file_type: str, filename: str) -> bool:
        """保存数据到文件
        
        Args:
            data: 要保存的数据
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            bool: 是否保存成功
        """
        try:
            file_path = self._get_file_path(file_type, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存文件失败: {str(e)}")
            return False
    
    def load(self, file_type: str, filename: str) -> Optional[Any]:
        """从文件加载数据
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            Optional[Any]: 加载的数据，如果文件不存在则返回 None
        """
        try:
            file_path = self._get_file_path(file_type, filename)
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载文件失败: {str(e)}")
            return None
    
    def list_files(self, file_type: str) -> List[str]:
        """获取指定类型的文件列表
        
        Args:
            file_type: 文件类型
            
        Returns:
            List[str]: 文件名列表（不含扩展名）
        """
        try:
            dir_path = self.base_dir / file_type
            if not dir_path.exists():
                return []
                
            return [f.stem for f in dir_path.glob("*.json")]
        except Exception as e:
            print(f"获取文件列表失败: {str(e)}")
            return []
    
    def delete(self, file_type: str, filename: str) -> bool:
        """删除文件
        
        Args:
            file_type: 文件类型
            filename: 文件名
            
        Returns:
            bool: 是否删除成功
        """
        try:
            file_path = self._get_file_path(file_type, filename)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"删除文件失败: {str(e)}")
            return False 