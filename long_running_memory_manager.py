"""
长时间运行内存管理器 - 优化长时间运行任务的内存使用
"""

import gc
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from logger import workflow_logger


class LongRunningMemoryManager:
    """长时间运行内存管理器 - 负责内存优化和清理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_memory_usage_mb = self.config.get('max_memory_usage_mb', 2048)
        self.cleanup_interval_minutes = self.config.get('memory_cleanup_interval_minutes', 30)
        
        # 内存清理统计
        self.cleanup_count = 0
        self.total_freed_mb = 0
        self.last_cleanup_time = None
        
        # 内存使用历史
        self.memory_history: List[Dict[str, Any]] = []
        self.max_history_size = 50
    
    def cleanup_memory(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行内存清理"""
        try:
            cleanup_start_time = datetime.now()
            
            # 记录清理前的内存使用
            before_memory = self._get_memory_usage()
            
            # 执行清理操作
            cleanup_result = {
                "freed_objects": 0,
                "cleaned_items": [],
                "freed_mb": 0,
                "cleanup_time": 0,
                "before_memory_mb": before_memory,
                "after_memory_mb": 0
            }
            
            # 1. 清理状态中的临时数据
            cleaned_items = self._cleanup_state_data(state)
            cleanup_result["cleaned_items"] = cleaned_items
            
            # 2. 清理Python垃圾回收
            freed_objects = gc.collect()
            cleanup_result["freed_objects"] = freed_objects
            
            # 3. 清理缓存文件
            cache_cleaned = self._cleanup_cache_files()
            cleanup_result["cleaned_items"].extend(cache_cleaned)
            
            # 4. 清理日志文件
            log_cleaned = self._cleanup_log_files()
            cleanup_result["cleaned_items"].extend(log_cleaned)
            
            # 记录清理后的内存使用
            after_memory = self._get_memory_usage()
            cleanup_result["after_memory_mb"] = after_memory
            cleanup_result["freed_mb"] = max(0, before_memory - after_memory)
            
            # 计算清理时间
            cleanup_end_time = datetime.now()
            cleanup_result["cleanup_time"] = (cleanup_end_time - cleanup_start_time).total_seconds()
            
            # 更新统计信息
            self.cleanup_count += 1
            self.total_freed_mb += cleanup_result["freed_mb"]
            self.last_cleanup_time = cleanup_end_time
            
            # 记录内存使用历史
            self._record_memory_usage(after_memory, cleanup_result)
            
            workflow_logger.log_info(
                f"内存清理完成: 释放 {cleanup_result['freed_mb']:.1f}MB, "
                f"清理对象 {freed_objects} 个, 用时 {cleanup_result['cleanup_time']:.2f}秒",
                "LongRunningMemoryManager"
            )
            
            return cleanup_result
            
        except Exception as e:
            workflow_logger.log_error(f"内存清理失败: {str(e)}", "LongRunningMemoryManager")
            return {
                "freed_objects": 0,
                "cleaned_items": [],
                "freed_mb": 0,
                "cleanup_time": 0,
                "error": str(e)
            }
    
    def _cleanup_state_data(self, state: Dict[str, Any]) -> List[str]:
        """清理状态数据"""
        cleaned_items = []
        
        try:
            # 清理搜索结果（保留最近10轮）
            if 'search_results' in state and isinstance(state['search_results'], list):
                original_count = len(state['search_results'])
                if original_count > 10:
                    state['search_results'] = state['search_results'][-10:]
                    cleaned_items.append(f"search_results: {original_count - 10} items")
            
            # 清理摘要（保留最近5轮）
            if 'summaries' in state and isinstance(state['summaries'], list):
                original_count = len(state['summaries'])
                if original_count > 5:
                    state['summaries'] = state['summaries'][-5:]
                    cleaned_items.append(f"summaries: {original_count - 5} items")
            
            # 清理关键点（保留最近5轮）
            if 'key_points' in state and isinstance(state['key_points'], list):
                original_count = len(state['key_points'])
                if original_count > 5:
                    state['key_points'] = state['key_points'][-5:]
                    cleaned_items.append(f"key_points: {original_count - 5} items")
            
            # 清理质量分数历史（保留最近20条）
            if 'quality_scores' in state and isinstance(state['quality_scores'], list):
                original_count = len(state['quality_scores'])
                if original_count > 20:
                    state['quality_scores'] = state['quality_scores'][-20:]
                    cleaned_items.append(f"quality_scores: {original_count - 20} items")
            
            # 清理改进历史（保留最近10条）
            if 'improvement_history' in state and isinstance(state['improvement_history'], list):
                original_count = len(state['improvement_history'])
                if original_count > 10:
                    state['improvement_history'] = state['improvement_history'][-10:]
                    cleaned_items.append(f"improvement_history: {original_count - 10} items")
            
            # 清理累积结果（保留最近5轮）
            if 'accumulated_results' in state and isinstance(state['accumulated_results'], list):
                original_count = len(state['accumulated_results'])
                if original_count > 5:
                    state['accumulated_results'] = state['accumulated_results'][-5:]
                    cleaned_items.append(f"accumulated_results: {original_count - 5} items")
            
            # 清理搜索轮次记录（保留最近20条）
            if 'search_rounds' in state and isinstance(state['search_rounds'], list):
                original_count = len(state['search_rounds'])
                if original_count > 20:
                    state['search_rounds'] = state['search_rounds'][-20:]
                    cleaned_items.append(f"search_rounds: {original_count - 20} items")
            
        except Exception as e:
            workflow_logger.log_error(f"状态数据清理失败: {str(e)}", "LongRunningMemoryManager")
        
        return cleaned_items
    
    def _cleanup_cache_files(self) -> List[str]:
        """清理缓存文件"""
        cleaned_items = []
        
        try:
            cache_dir = "./data/cache"
            if not os.path.exists(cache_dir):
                return cleaned_items
            
            # 清理超过7天的缓存文件
            cutoff_time = datetime.now() - timedelta(days=7)
            cleaned_count = 0
            
            for filename in os.listdir(cache_dir):
                filepath = os.path.join(cache_dir, filename)
                if os.path.isfile(filepath):
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_mtime < cutoff_time:
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                        except Exception as e:
                            workflow_logger.log_warning(f"删除缓存文件失败: {filepath} - {str(e)}")
            
            if cleaned_count > 0:
                cleaned_items.append(f"cache_files: {cleaned_count} files")
            
        except Exception as e:
            workflow_logger.log_error(f"缓存文件清理失败: {str(e)}", "LongRunningMemoryManager")
        
        return cleaned_items
    
    def _cleanup_log_files(self) -> List[str]:
        """清理日志文件"""
        cleaned_items = []
        
        try:
            logs_dir = "./data/logs"
            if not os.path.exists(logs_dir):
                return cleaned_items
            
            # 清理超过30天的日志文件
            cutoff_time = datetime.now() - timedelta(days=30)
            cleaned_count = 0
            
            for filename in os.listdir(logs_dir):
                if filename.endswith('.log') or filename.endswith('.json'):
                    filepath = os.path.join(logs_dir, filename)
                    if os.path.isfile(filepath):
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_mtime < cutoff_time:
                            try:
                                os.remove(filepath)
                                cleaned_count += 1
                            except Exception as e:
                                workflow_logger.log_warning(f"删除日志文件失败: {filepath} - {str(e)}")
            
            if cleaned_count > 0:
                cleaned_items.append(f"log_files: {cleaned_count} files")
            
        except Exception as e:
            workflow_logger.log_error(f"日志文件清理失败: {str(e)}", "LongRunningMemoryManager")
        
        return cleaned_items
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception as e:
            workflow_logger.log_error(f"获取内存使用量失败: {str(e)}", "LongRunningMemoryManager")
            return 0.0
    
    def _record_memory_usage(self, memory_mb: float, cleanup_result: Dict[str, Any]):
        """记录内存使用情况"""
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "memory_mb": memory_mb,
                "freed_mb": cleanup_result.get("freed_mb", 0),
                "cleanup_count": self.cleanup_count
            }
            
            self.memory_history.append(record)
            
            # 限制历史记录大小
            if len(self.memory_history) > self.max_history_size:
                self.memory_history = self.memory_history[-self.max_history_size:]
                
        except Exception as e:
            workflow_logger.log_error(f"记录内存使用失败: {str(e)}", "LongRunningMemoryManager")
    
    def should_cleanup(self, state: Dict[str, Any]) -> bool:
        """判断是否应该执行内存清理"""
        try:
            # 检查内存使用量
            current_memory = self._get_memory_usage()
            if current_memory > self.max_memory_usage_mb * 0.8:  # 超过80%阈值
                return True
            
            # 检查距离上次清理的时间
            if self.last_cleanup_time:
                time_since_cleanup = (datetime.now() - self.last_cleanup_time).total_seconds()
                if time_since_cleanup > self.cleanup_interval_minutes * 60:
                    return True
            else:
                return True  # 首次运行
            
            # 检查状态数据大小
            state_size = self._estimate_state_size(state)
            if state_size > 100:  # 状态数据超过100MB
                return True
            
            return False
            
        except Exception as e:
            workflow_logger.log_error(f"清理判断失败: {str(e)}", "LongRunningMemoryManager")
            return True  # 出错时默认清理
    
    def _estimate_state_size(self, state: Dict[str, Any]) -> float:
        """估算状态数据大小（MB）"""
        try:
            import sys
            
            # 计算状态对象的内存使用
            state_size = sys.getsizeof(state)
            
            # 递归计算嵌套对象的大小
            def get_size(obj):
                size = sys.getsizeof(obj)
                if isinstance(obj, dict):
                    size += sum(get_size(v) for v in obj.values())
                elif isinstance(obj, list):
                    size += sum(get_size(item) for item in obj)
                return size
            
            total_size = get_size(state)
            return total_size / 1024 / 1024  # 转换为MB
            
        except Exception as e:
            workflow_logger.log_error(f"状态大小估算失败: {str(e)}", "LongRunningMemoryManager")
            return 0.0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        try:
            current_memory = self._get_memory_usage()
            
            return {
                "current_memory_mb": current_memory,
                "max_memory_mb": self.max_memory_usage_mb,
                "memory_usage_percent": (current_memory / self.max_memory_usage_mb) * 100,
                "cleanup_count": self.cleanup_count,
                "total_freed_mb": self.total_freed_mb,
                "last_cleanup_time": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
                "history_size": len(self.memory_history),
                "should_cleanup": self.should_cleanup({})
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取内存统计失败: {str(e)}", "LongRunningMemoryManager")
            return {"error": str(e)}
    
    def get_memory_trends(self, hours: int = 1) -> Dict[str, Any]:
        """获取内存使用趋势"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = [
                data for data in self.memory_history
                if datetime.fromisoformat(data['timestamp']) > cutoff_time
            ]
            
            if not recent_data:
                return {"error": "没有足够的历史数据"}
            
            memory_values = [data['memory_mb'] for data in recent_data]
            freed_values = [data['freed_mb'] for data in recent_data]
            
            return {
                "period_hours": hours,
                "data_points": len(recent_data),
                "memory": {
                    "current": memory_values[-1] if memory_values else 0,
                    "average": sum(memory_values) / len(memory_values) if memory_values else 0,
                    "max": max(memory_values) if memory_values else 0,
                    "min": min(memory_values) if memory_values else 0
                },
                "freed": {
                    "total": sum(freed_values) if freed_values else 0,
                    "average": sum(freed_values) / len(freed_values) if freed_values else 0,
                    "max": max(freed_values) if freed_values else 0
                }
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取内存趋势失败: {str(e)}", "LongRunningMemoryManager")
            return {"error": str(e)}
    
    def force_cleanup(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """强制内存清理"""
        try:
            workflow_logger.log_info("执行强制内存清理", "LongRunningMemoryManager")
            
            # 执行完整的垃圾回收
            collected = gc.collect()
            
            # 清理状态数据
            cleaned_items = self._cleanup_state_data(state)
            
            # 清理所有缓存和日志文件
            cache_cleaned = self._cleanup_cache_files()
            log_cleaned = self._cleanup_log_files()
            
            # 记录结果
            before_memory = self._get_memory_usage()
            after_memory = self._get_memory_usage()
            
            result = {
                "freed_objects": collected,
                "cleaned_items": cleaned_items + cache_cleaned + log_cleaned,
                "freed_mb": max(0, before_memory - after_memory),
                "before_memory_mb": before_memory,
                "after_memory_mb": after_memory,
                "force_cleanup": True
            }
            
            self.cleanup_count += 1
            self.total_freed_mb += result["freed_mb"]
            self.last_cleanup_time = datetime.now()
            
            workflow_logger.log_info(f"强制清理完成: 释放 {result['freed_mb']:.1f}MB", "LongRunningMemoryManager")
            
            return result
            
        except Exception as e:
            workflow_logger.log_error(f"强制清理失败: {str(e)}", "LongRunningMemoryManager")
            return {"error": str(e)}
    
    def clear_history(self):
        """清空历史记录"""
        try:
            self.memory_history.clear()
            workflow_logger.log_info("内存历史记录已清空", "LongRunningMemoryManager")
        except Exception as e:
            workflow_logger.log_error(f"清空历史记录失败: {str(e)}", "LongRunningMemoryManager")


