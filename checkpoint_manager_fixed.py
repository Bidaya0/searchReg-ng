"""
检查点管理器 - 修复版本，避免与LangGraph保留字段冲突
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from logger import workflow_logger


class CheckpointManager:
    """检查点管理器 - 支持长时间运行工作流的状态保存和恢复"""
    
    def __init__(self, checkpoint_dir: str = "./data/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.max_checkpoints = 10  # 最大检查点数量
        
        # 确保检查点目录存在
        try:
            os.makedirs(self.checkpoint_dir, exist_ok=True)
            workflow_logger.log_info(f"检查点目录已创建: {self.checkpoint_dir}")
        except Exception as e:
            workflow_logger.log_error(f"创建检查点目录失败: {str(e)}")
            raise
    
    def save_checkpoint(self, state: Dict[str, Any], custom_checkpoint_id: str = None) -> str:
        """保存检查点"""
        try:
            if custom_checkpoint_id is None:
                custom_checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 准备检查点数据
            checkpoint_data = {
                "custom_checkpoint_id": custom_checkpoint_id,
                "timestamp": datetime.now().isoformat(),
                "state": self._serialize_state(state),
                "metadata": {
                    "iteration": state.get('current_iteration', 0),
                    "elapsed_time": state.get('elapsed_time', 0),
                    "quality_score": state.get('progress', {}).get('current_quality_score', 0),
                    "topic": state.get('topic', ''),
                    "status": state.get('status', 'running')
                }
            }
            
            # 保存检查点文件
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{custom_checkpoint_id}.json")
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # 清理旧检查点
            self._cleanup_old_checkpoints()
            
            workflow_logger.log_info(f"检查点已保存: {checkpoint_path}", "CheckpointManager")
            return checkpoint_path
            
        except Exception as e:
            workflow_logger.log_error(f"检查点保存失败: {str(e)}", "CheckpointManager")
            return ""
    
    def load_checkpoint(self, custom_checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{custom_checkpoint_id}.json")
            
            if not os.path.exists(checkpoint_path):
                workflow_logger.log_warning(f"检查点文件不存在: {checkpoint_path}", "CheckpointManager")
                return None
            
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # 恢复状态
            state = self._deserialize_state(checkpoint_data.get('state', {}))
            
            workflow_logger.log_info(f"检查点已加载: {custom_checkpoint_id}", "CheckpointManager")
            return state
            
        except Exception as e:
            workflow_logger.log_error(f"检查点加载失败: {str(e)}", "CheckpointManager")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有检查点"""
        try:
            checkpoints = []
            
            if not os.path.exists(self.checkpoint_dir):
                return checkpoints
            
            for filename in os.listdir(self.checkpoint_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.checkpoint_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            checkpoint_data = json.load(f)
                        
                        checkpoints.append({
                            "custom_checkpoint_id": checkpoint_data.get('custom_checkpoint_id', filename[:-5]),
                            "timestamp": checkpoint_data.get('timestamp', ''),
                            "metadata": checkpoint_data.get('metadata', {}),
                            "filepath": filepath
                        })
                    except Exception as e:
                        workflow_logger.log_warning(f"读取检查点文件失败: {filepath}, {str(e)}")
                        continue
            
            # 按时间排序
            checkpoints.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return checkpoints
            
        except Exception as e:
            workflow_logger.log_error(f"列出检查点失败: {str(e)}", "CheckpointManager")
            return []
    
    def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """获取最新检查点"""
        try:
            checkpoints = self.list_checkpoints()
            if checkpoints:
                latest = checkpoints[0]
                return self.load_checkpoint(latest['custom_checkpoint_id'])
            return None
            
        except Exception as e:
            workflow_logger.log_error(f"获取最新检查点失败: {str(e)}", "CheckpointManager")
            return None
    
    def delete_checkpoint(self, custom_checkpoint_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{custom_checkpoint_id}.json")
            
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
                workflow_logger.log_info(f"检查点已删除: {custom_checkpoint_id}", "CheckpointManager")
                return True
            else:
                workflow_logger.log_warning(f"检查点文件不存在: {checkpoint_path}", "CheckpointManager")
                return False
                
        except Exception as e:
            workflow_logger.log_error(f"删除检查点失败: {str(e)}", "CheckpointManager")
            return False
    
    def cleanup_old_checkpoints(self, keep_count: int = None) -> int:
        """清理旧检查点"""
        try:
            if keep_count is None:
                keep_count = self.max_checkpoints
            
            checkpoints = self.list_checkpoints()
            
            if len(checkpoints) <= keep_count:
                return 0
            
            deleted_count = 0
            for checkpoint in checkpoints[keep_count:]:
                if self.delete_checkpoint(checkpoint['custom_checkpoint_id']):
                    deleted_count += 1
            
            workflow_logger.log_info(f"已清理 {deleted_count} 个旧检查点", "CheckpointManager")
            return deleted_count
            
        except Exception as e:
            workflow_logger.log_error(f"清理旧检查点失败: {str(e)}", "CheckpointManager")
            return 0
    
    def _cleanup_old_checkpoints(self):
        """内部方法：清理旧检查点"""
        self.cleanup_old_checkpoints()
    
    def get_checkpoint_info(self, custom_checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点信息"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{custom_checkpoint_id}.json")
            
            if not os.path.exists(checkpoint_path):
                return None
            
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            return {
                "custom_checkpoint_id": checkpoint_data.get('custom_checkpoint_id'),
                "timestamp": checkpoint_data.get('timestamp'),
                "metadata": checkpoint_data.get('metadata', {}),
                "filepath": checkpoint_path
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取检查点信息失败: {str(e)}", "CheckpointManager")
            return None
    
    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """序列化状态数据"""
        try:
            # 处理datetime对象
            serialized_state = {}
            for key, value in state.items():
                if isinstance(value, datetime):
                    serialized_state[key] = value.isoformat()
                elif isinstance(value, dict):
                    serialized_state[key] = self._serialize_state(value)
                elif isinstance(value, list):
                    serialized_state[key] = [
                        self._serialize_state(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    serialized_state[key] = value
            
            return serialized_state
            
        except Exception as e:
            workflow_logger.log_error(f"状态序列化失败: {str(e)}", "CheckpointManager")
            return state
    
    def _deserialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化状态数据"""
        try:
            # 处理datetime字符串
            deserialized_state = {}
            for key, value in state.items():
                if isinstance(value, str) and key.endswith('_time'):
                    try:
                        deserialized_state[key] = datetime.fromisoformat(value)
                    except ValueError:
                        deserialized_state[key] = value
                elif isinstance(value, dict):
                    deserialized_state[key] = self._deserialize_state(value)
                elif isinstance(value, list):
                    deserialized_state[key] = [
                        self._deserialize_state(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    deserialized_state[key] = value
            
            return deserialized_state
            
        except Exception as e:
            workflow_logger.log_error(f"状态反序列化失败: {str(e)}", "CheckpointManager")
            return state
