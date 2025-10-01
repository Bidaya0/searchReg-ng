"""
资源监控器 - 监控系统资源使用情况
"""

import os
import psutil
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from logger import workflow_logger


class ResourceMonitor:
    """资源监控器 - 监控CPU、内存、磁盘等系统资源"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_memory_usage_mb = self.config.get('max_memory_usage_mb', 2048)
        self.max_disk_usage_mb = self.config.get('max_disk_usage_mb', 10240)
        self.monitor_interval = self.config.get('resource_monitor_interval_seconds', 60)
        
        # 资源历史记录
        self.resource_history: List[Dict[str, Any]] = []
        self.max_history_size = 100  # 最多保留100条记录
        
        # 警告阈值
        self.memory_warning_threshold = 0.8  # 80%内存使用率警告
        self.disk_warning_threshold = 0.8    # 80%磁盘使用率警告
        self.cpu_warning_threshold = 90.0    # 90%CPU使用率警告
    
    def check_resources(self) -> Dict[str, Any]:
        """检查系统资源使用情况"""
        try:
            # 获取系统信息
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 计算使用量
            memory_usage_mb = memory.used / 1024 / 1024
            disk_usage_mb = disk.used / 1024 / 1024
            
            # 检查进程资源使用
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            process_cpu_percent = process.cpu_percent()
            
            # 构建资源状态
            resource_status = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "memory_usage_mb": memory_usage_mb,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / 1024 / 1024,
                    "disk_usage_mb": disk_usage_mb,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "disk_available_mb": disk.free / 1024 / 1024,
                    "cpu_percent": cpu_percent
                },
                "process": {
                    "memory_usage_mb": process_memory_mb,
                    "cpu_percent": process_cpu_percent,
                    "pid": process.pid,
                    "create_time": process.create_time()
                },
                "warnings": self._check_warnings(memory_usage_mb, disk_usage_mb, cpu_percent),
                "alerts": self._check_alerts(memory_usage_mb, disk_usage_mb)
            }
            
            # 添加到历史记录
            self._add_to_history(resource_status)
            
            return resource_status
            
        except Exception as e:
            workflow_logger.log_error(f"资源监控失败: {str(e)}", "ResourceMonitor")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "system": {"memory_usage_mb": 0, "disk_usage_mb": 0, "cpu_percent": 0},
                "process": {"memory_usage_mb": 0, "cpu_percent": 0},
                "warnings": [],
                "alerts": []
            }
    
    def _check_warnings(self, memory_usage_mb: float, disk_usage_mb: float, cpu_percent: float) -> List[str]:
        """检查警告条件"""
        warnings = []
        
        try:
            # 内存警告
            if memory_usage_mb > self.max_memory_usage_mb * self.memory_warning_threshold:
                warnings.append(f"内存使用率过高: {memory_usage_mb:.1f}MB (阈值: {self.max_memory_usage_mb * self.memory_warning_threshold:.1f}MB)")
            
            # 磁盘警告
            if disk_usage_mb > self.max_disk_usage_mb * self.disk_warning_threshold:
                warnings.append(f"磁盘使用率过高: {disk_usage_mb:.1f}MB (阈值: {self.max_disk_usage_mb * self.disk_warning_threshold:.1f}MB)")
            
            # CPU警告
            if cpu_percent > self.cpu_warning_threshold:
                warnings.append(f"CPU使用率过高: {cpu_percent:.1f}% (阈值: {self.cpu_warning_threshold}%)")
            
        except Exception as e:
            workflow_logger.log_error(f"警告检查失败: {str(e)}", "ResourceMonitor")
        
        return warnings
    
    def _check_alerts(self, memory_usage_mb: float, disk_usage_mb: float) -> List[str]:
        """检查警报条件"""
        alerts = []
        
        try:
            # 内存警报
            if memory_usage_mb > self.max_memory_usage_mb:
                alerts.append(f"内存使用超限: {memory_usage_mb:.1f}MB (限制: {self.max_memory_usage_mb}MB)")
            
            # 磁盘警报
            if disk_usage_mb > self.max_disk_usage_mb:
                alerts.append(f"磁盘使用超限: {disk_usage_mb:.1f}MB (限制: {self.max_disk_usage_mb}MB)")
            
        except Exception as e:
            workflow_logger.log_error(f"警报检查失败: {str(e)}", "ResourceMonitor")
        
        return alerts
    
    def _add_to_history(self, resource_status: Dict[str, Any]):
        """添加到历史记录"""
        try:
            self.resource_history.append(resource_status)
            
            # 限制历史记录大小
            if len(self.resource_history) > self.max_history_size:
                self.resource_history = self.resource_history[-self.max_history_size:]
                
        except Exception as e:
            workflow_logger.log_error(f"添加历史记录失败: {str(e)}", "ResourceMonitor")
    
    def get_resource_trends(self, hours: int = 1) -> Dict[str, Any]:
        """获取资源使用趋势"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_data = [
                data for data in self.resource_history
                if datetime.fromisoformat(data['timestamp']) > cutoff_time
            ]
            
            if not recent_data:
                return {"error": "没有足够的历史数据"}
            
            # 计算趋势
            memory_usage = [data['system']['memory_usage_mb'] for data in recent_data]
            disk_usage = [data['system']['disk_usage_mb'] for data in recent_data]
            cpu_usage = [data['system']['cpu_percent'] for data in recent_data]
            
            trends = {
                "period_hours": hours,
                "data_points": len(recent_data),
                "memory": {
                    "current": memory_usage[-1] if memory_usage else 0,
                    "average": sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                    "max": max(memory_usage) if memory_usage else 0,
                    "min": min(memory_usage) if memory_usage else 0,
                    "trend": self._calculate_trend(memory_usage)
                },
                "disk": {
                    "current": disk_usage[-1] if disk_usage else 0,
                    "average": sum(disk_usage) / len(disk_usage) if disk_usage else 0,
                    "max": max(disk_usage) if disk_usage else 0,
                    "min": min(disk_usage) if disk_usage else 0,
                    "trend": self._calculate_trend(disk_usage)
                },
                "cpu": {
                    "current": cpu_usage[-1] if cpu_usage else 0,
                    "average": sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                    "max": max(cpu_usage) if cpu_usage else 0,
                    "min": min(cpu_usage) if cpu_usage else 0,
                    "trend": self._calculate_trend(cpu_usage)
                }
            }
            
            return trends
            
        except Exception as e:
            workflow_logger.log_error(f"获取资源趋势失败: {str(e)}", "ResourceMonitor")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势方向"""
        try:
            if len(values) < 2:
                return "stable"
            
            # 简单线性趋势计算
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
            
            if change_percent > 5:
                return "increasing"
            elif change_percent < -5:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            workflow_logger.log_error(f"趋势计算失败: {str(e)}", "ResourceMonitor")
            return "unknown"
    
    def is_resource_healthy(self) -> bool:
        """检查资源是否健康"""
        try:
            resource_status = self.check_resources()
            
            # 检查是否有警报
            if resource_status.get('alerts'):
                return False
            
            # 检查是否有严重警告
            warnings = resource_status.get('warnings', [])
            critical_warnings = [w for w in warnings if '过高' in w or '超限' in w]
            if critical_warnings:
                return False
            
            return True
            
        except Exception as e:
            workflow_logger.log_error(f"资源健康检查失败: {str(e)}", "ResourceMonitor")
            return False
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """获取资源使用摘要"""
        try:
            resource_status = self.check_resources()
            trends = self.get_resource_trends(hours=1)
            
            return {
                "current": resource_status,
                "trends": trends,
                "healthy": self.is_resource_healthy(),
                "history_size": len(self.resource_history),
                "monitor_config": {
                    "max_memory_mb": self.max_memory_usage_mb,
                    "max_disk_mb": self.max_disk_usage_mb,
                    "monitor_interval": self.monitor_interval
                }
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取资源摘要失败: {str(e)}", "ResourceMonitor")
            return {"error": str(e)}
    
    def clear_history(self):
        """清空历史记录"""
        try:
            self.resource_history.clear()
            workflow_logger.log_info("资源历史记录已清空", "ResourceMonitor")
        except Exception as e:
            workflow_logger.log_error(f"清空历史记录失败: {str(e)}", "ResourceMonitor")
    
    def save_history(self, filepath: str) -> bool:
        """保存历史记录到文件"""
        try:
            import json
            
            history_data = {
                "timestamp": datetime.now().isoformat(),
                "history": self.resource_history,
                "config": {
                    "max_memory_usage_mb": self.max_memory_usage_mb,
                    "max_disk_usage_mb": self.max_disk_usage_mb,
                    "monitor_interval": self.monitor_interval
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            workflow_logger.log_info(f"资源历史记录已保存: {filepath}", "ResourceMonitor")
            return True
            
        except Exception as e:
            workflow_logger.log_error(f"保存历史记录失败: {str(e)}", "ResourceMonitor")
            return False
