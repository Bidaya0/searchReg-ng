from typing import Dict, Any
from .base import StorageInterface
from .file_system import FileSystemStorage

class StorageFactory:
    """存储工厂类"""
    
    @staticmethod
    def create_storage(storage_type: str, config: Dict[str, Any]) -> StorageInterface:
        """创建存储实例
        
        Args:
            storage_type: 存储类型
            config: 配置信息
            
        Returns:
            StorageInterface: 存储实例
            
        Raises:
            ValueError: 不支持的存储类型
        """
        if storage_type == "file_system":
            return FileSystemStorage(config["base_dir"])
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}") 