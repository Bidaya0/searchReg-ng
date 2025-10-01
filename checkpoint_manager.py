"""
检查点管理器 - 支持长时间运行工作流的状态持久化
"""

import os
import json
import pickle
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from logger import workflow_logger


class CheckpointManager:
    """检查点管理器 - 负责工作流状态的保存和恢复"""
    
    def __init__(self, checkpoint_dir: str = "./data/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        self.max_checkpoints = 10  # 最多保留10个检查点
        self._ensure_checkpoint_dir()
    
    def _ensure_checkpoint_dir(self):
        """确保检查点目录存在"""
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
                    "status": state.get('status', 'unknown'),
                    "topic": state.get('topic', 'unknown'),
                    "workflow_id": state.get('workflow_id', 'unknown')
                }
            }
            
            # 保存检查点文件
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # 清理旧检查点
            self._cleanup_old_checkpoints()
            
            workflow_logger.log_info(f"检查点已保存: {checkpoint_path}", "CheckpointManager")
            return checkpoint_path
            
        except Exception as e:
            workflow_logger.log_error(f"检查点保存失败: {str(e)}", "CheckpointManager")
            return ""
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
            if not os.path.exists(checkpoint_path):
                workflow_logger.log_warning(f"检查点文件不存在: {checkpoint_path}", "CheckpointManager")
                return None
            
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            state = self._deserialize_state(checkpoint_data['state'])
            workflow_logger.log_info(f"检查点已加载: {checkpoint_id}", "CheckpointManager")
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
                    checkpoint_path = os.path.join(self.checkpoint_dir, filename)
                    try:
                        with open(checkpoint_path, 'r', encoding='utf-8') as f:
                            checkpoint_data = json.load(f)
                        
                        checkpoints.append({
                            "checkpoint_id": checkpoint_data.get('checkpoint_id', filename[:-5]),
                            "timestamp": checkpoint_data.get('timestamp', ''),
                            "metadata": checkpoint_data.get('metadata', {}),
                            "file_path": checkpoint_path
                        })
                    except Exception as e:
                        workflow_logger.log_warning(f"读取检查点文件失败: {filename} - {str(e)}")
                        continue
            
            # 按时间排序
            checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
            return checkpoints
            
        except Exception as e:
            workflow_logger.log_error(f"列出检查点失败: {str(e)}", "CheckpointManager")
            return []
    
    def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """获取最新的检查点"""
        try:
            checkpoints = self.list_checkpoints()
            if not checkpoints:
                return None
            
            latest = checkpoints[0]
            return self.load_checkpoint(latest['checkpoint_id'])
            
        except Exception as e:
            workflow_logger.log_error(f"获取最新检查点失败: {str(e)}", "CheckpointManager")
            return None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
                workflow_logger.log_info(f"检查点已删除: {checkpoint_id}", "CheckpointManager")
                return True
            else:
                workflow_logger.log_warning(f"检查点文件不存在: {checkpoint_path}", "CheckpointManager")
                return False
                
        except Exception as e:
            workflow_logger.log_error(f"删除检查点失败: {str(e)}", "CheckpointManager")
            return False
    
    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """序列化状态数据"""
        try:
            # 创建状态副本
            serialized_state = state.copy()
            
            # 处理不可序列化的对象
            for key, value in serialized_state.items():
                if hasattr(value, '__dict__'):
                    # 如果是对象，转换为字典
                    serialized_state[key] = value.__dict__ if hasattr(value, '__dict__') else str(value)
                elif isinstance(value, (set, frozenset)):
                    # 集合转换为列表
                    serialized_state[key] = list(value)
                elif hasattr(value, 'isoformat'):
                    # 日期时间对象转换为字符串
                    serialized_state[key] = value.isoformat()
            
            return serialized_state
            
        except Exception as e:
            workflow_logger.log_error(f"状态序列化失败: {str(e)}", "CheckpointManager")
            return {}
    
    def _deserialize_state(self, serialized_state: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化状态数据"""
        try:
            # 创建状态副本
            state = serialized_state.copy()
            
            # 处理特殊字段的反序列化
            if 'start_time' in state and isinstance(state['start_time'], str):
                state['start_time'] = datetime.fromisoformat(state['start_time'])
            
            if 'end_time' in state and isinstance(state['end_time'], str):
                state['end_time'] = datetime.fromisoformat(state['end_time'])
            
            if 'last_checkpoint_time' in state and isinstance(state['last_checkpoint_time'], str):
                state['last_checkpoint_time'] = datetime.fromisoformat(state['last_checkpoint_time'])
            
            if 'last_memory_cleanup' in state and isinstance(state['last_memory_cleanup'], str):
                state['last_memory_cleanup'] = datetime.fromisoformat(state['last_memory_cleanup'])
            
            return state
            
        except Exception as e:
            workflow_logger.log_error(f"状态反序列化失败: {str(e)}", "CheckpointManager")
            return serialized_state
    
    def _cleanup_old_checkpoints(self):
        """清理旧检查点"""
        try:
            checkpoints = self.list_checkpoints()
            if len(checkpoints) <= self.max_checkpoints:
                return
            
            # 删除多余的检查点
            checkpoints_to_delete = checkpoints[self.max_checkpoints:]
            for checkpoint in checkpoints_to_delete:
                self.delete_checkpoint(checkpoint['checkpoint_id'])
            
            workflow_logger.log_info(f"已清理 {len(checkpoints_to_delete)} 个旧检查点", "CheckpointManager")
            
        except Exception as e:
            workflow_logger.log_error(f"清理旧检查点失败: {str(e)}", "CheckpointManager")
    
    def cleanup_all_checkpoints(self):
        """清理所有检查点"""
        try:
            if os.path.exists(self.checkpoint_dir):
                shutil.rmtree(self.checkpoint_dir)
                self._ensure_checkpoint_dir()
                workflow_logger.log_info("所有检查点已清理", "CheckpointManager")
                return True
            return False
            
        except Exception as e:
            workflow_logger.log_error(f"清理所有检查点失败: {str(e)}", "CheckpointManager")
            return False
    
    def get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点信息"""
        try:
            checkpoint_path = os.path.join(self.checkpoint_dir, f"{checkpoint_id}.json")
            if not os.path.exists(checkpoint_path):
                return None
            
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            return {
                "checkpoint_id": checkpoint_data.get('checkpoint_id'),
                "timestamp": checkpoint_data.get('timestamp'),
                "metadata": checkpoint_data.get('metadata', {}),
                "file_size": os.path.getsize(checkpoint_path),
                "file_path": checkpoint_path
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取检查点信息失败: {str(e)}", "CheckpointManager")
            return None
