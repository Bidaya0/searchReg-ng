"""
进度跟踪器 - 跟踪长时间运行任务的进度和状态
"""

import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from logger import workflow_logger


class ProgressTracker:
    """进度跟踪器 - 跟踪任务进度、质量变化和收敛状态"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.progress_dir = self.config.get('progress_dir', './data/progress')
        self.max_iterations = self.config.get('max_iterations', 100)
        self.quality_convergence_threshold = self.config.get('quality_convergence_threshold', 0.02)
        
        # 进度历史记录
        self.progress_history: List[Dict[str, Any]] = []
        self.max_history_size = 200
        
        # 确保进度目录存在
        self._ensure_progress_dir()
    
    def _ensure_progress_dir(self):
        """确保进度目录存在"""
        try:
            os.makedirs(self.progress_dir, exist_ok=True)
        except Exception as e:
            workflow_logger.log_error(f"创建进度目录失败: {str(e)}", "ProgressTracker")
    
    def calculate_progress(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """计算当前进度"""
        try:
            # 基础进度信息
            current_iteration = state.get('current_iteration', 0)
            elapsed_time = state.get('elapsed_time', 0)
            remaining_time = state.get('remaining_time', 0)
            time_strategy = state.get('time_strategy', 'adaptive')
            
            # 计算迭代进度
            iteration_progress = min(1.0, current_iteration / self.max_iterations) if self.max_iterations > 0 else 0
            
            # 计算时间进度
            total_time = elapsed_time + remaining_time
            time_progress = min(1.0, elapsed_time / total_time) if total_time > 0 else 0
            
            # 综合完成百分比
            completion_percentage = (iteration_progress + time_progress) / 2 * 100
            
            # 计算质量相关指标
            quality_metrics = self._calculate_quality_metrics(state)
            
            # 计算收敛状态
            convergence_status = self._check_convergence(state)
            
            # 计算错误率
            error_rate = self._calculate_error_rate(state)
            
            # 计算效率指标
            efficiency_metrics = self._calculate_efficiency_metrics(state)
            
            # 计算时间策略相关指标
            time_strategy_metrics = self._calculate_time_strategy_metrics(state, time_strategy)
            
            # 构建进度信息
            progress = {
                "timestamp": datetime.now().isoformat(),
                "iteration": current_iteration,
                "completion_percentage": completion_percentage,
                "iteration_progress": iteration_progress,
                "time_progress": time_progress,
                "elapsed_hours": elapsed_time / 3600,
                "remaining_hours": remaining_time / 3600,
                "quality_metrics": quality_metrics,
                "convergence_status": convergence_status,
                "error_rate": error_rate,
                "efficiency_metrics": efficiency_metrics,
                "time_strategy_metrics": time_strategy_metrics,
                "time_strategy": time_strategy,
                "status": state.get('status', 'unknown')
            }
            
            # 添加到历史记录
            self._add_to_history(progress)
            
            return progress
            
        except Exception as e:
            workflow_logger.log_error(f"进度计算失败: {str(e)}", "ProgressTracker")
            return {
                "timestamp": datetime.now().isoformat(),
                "completion_percentage": 0,
                "error": str(e)
            }
    
    def _calculate_quality_metrics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """计算质量指标"""
        try:
            quality_scores = state.get('quality_scores', [])
            
            if not quality_scores:
                return {
                    "current_score": 0.0,
                    "average_score": 0.0,
                    "max_score": 0.0,
                    "min_score": 0.0,
                    "score_trend": "unknown",
                    "score_variance": 0.0
                }
            
            scores = [score['score'] for score in quality_scores]
            current_score = scores[-1] if scores else 0.0
            
            # 计算统计指标
            average_score = np.mean(scores) if scores else 0.0
            max_score = np.max(scores) if scores else 0.0
            min_score = np.min(scores) if scores else 0.0
            score_variance = np.var(scores) if len(scores) > 1 else 0.0
            
            # 计算趋势
            score_trend = self._calculate_trend(scores)
            
            return {
                "current_score": current_score,
                "average_score": average_score,
                "max_score": max_score,
                "min_score": min_score,
                "score_trend": score_trend,
                "score_variance": score_variance,
                "total_measurements": len(scores)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"质量指标计算失败: {str(e)}", "ProgressTracker")
            return {"error": str(e)}
    
    def _check_convergence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """检查收敛状态"""
        try:
            quality_scores = state.get('quality_scores', [])
            
            if len(quality_scores) < 3:
                return {
                    "converged": False,
                    "reason": "insufficient_data",
                    "variance": 0.0,
                    "trend": 0.0
                }
            
            # 获取最近的质量分数
            recent_scores = [score['score'] for score in quality_scores[-5:]]  # 最近5个分数
            
            # 计算方差和趋势
            variance = np.var(recent_scores) if len(recent_scores) > 1 else 0.0
            trend = self._calculate_trend_value(recent_scores)
            
            # 判断是否收敛
            converged = (variance < self.quality_convergence_threshold and 
                        abs(trend) < self.quality_convergence_threshold)
            
            return {
                "converged": converged,
                "variance": variance,
                "trend": trend,
                "threshold": self.quality_convergence_threshold,
                "recent_scores": recent_scores,
                "reason": "converged" if converged else "still_improving"
            }
            
        except Exception as e:
            workflow_logger.log_error(f"收敛检查失败: {str(e)}", "ProgressTracker")
            return {"converged": False, "error": str(e)}
    
    def _calculate_error_rate(self, state: Dict[str, Any]) -> float:
        """计算错误率"""
        try:
            # 统计各种错误
            search_errors = state.get('search_errors', [])
            question_errors = state.get('question_generation_error', [])
            processing_errors = state.get('result_processing_error', [])
            summary_errors = state.get('summary_error', [])
            
            # 计算总错误数
            total_errors = len(search_errors)
            if question_errors:
                total_errors += 1
            if processing_errors:
                total_errors += 1
            if summary_errors:
                total_errors += 1
            
            # 计算总操作数
            total_operations = state.get('current_iteration', 0) * 5  # 假设每轮迭代有5个主要操作
            if total_operations == 0:
                return 0.0
            
            error_rate = total_errors / total_operations
            return min(1.0, error_rate)  # 限制在0-1之间
            
        except Exception as e:
            workflow_logger.log_error(f"错误率计算失败: {str(e)}", "ProgressTracker")
            return 0.0
    
    def _calculate_efficiency_metrics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """计算效率指标"""
        try:
            current_iteration = state.get('current_iteration', 0)
            elapsed_time = state.get('elapsed_time', 0)
            
            if current_iteration == 0 or elapsed_time == 0:
                return {
                    "iterations_per_hour": 0.0,
                    "avg_iteration_time": 0.0,
                    "efficiency_score": 0.0
                }
            
            # 计算每小时迭代数
            iterations_per_hour = current_iteration / (elapsed_time / 3600)
            
            # 计算平均每轮迭代时间
            avg_iteration_time = elapsed_time / current_iteration
            
            # 计算效率分数（基于迭代速度和稳定性）
            efficiency_score = min(1.0, iterations_per_hour / 10.0)  # 假设10轮/小时为满分
            
            return {
                "iterations_per_hour": iterations_per_hour,
                "avg_iteration_time": avg_iteration_time,
                "efficiency_score": efficiency_score
            }
            
        except Exception as e:
            workflow_logger.log_error(f"效率指标计算失败: {str(e)}", "ProgressTracker")
            return {"error": str(e)}
    
    def _calculate_time_strategy_metrics(self, state: Dict[str, Any], time_strategy: str) -> Dict[str, Any]:
        """计算时间策略相关指标"""
        try:
            remaining_time = state.get('remaining_time', 0)
            current_iteration = state.get('current_iteration', 0)
            quality_scores = state.get('quality_scores', [])
            current_quality = quality_scores[-1].get('score', 0) if quality_scores else 0
            
            metrics = {
                "strategy": time_strategy,
                "remaining_time_hours": remaining_time / 3600,
                "current_iteration": current_iteration,
                "current_quality": current_quality
            }
            
            if time_strategy == "hard":
                # 硬截止时间策略指标
                buffer_time = 300  # 5分钟缓冲
                metrics.update({
                    "buffer_time_remaining": max(0, remaining_time - buffer_time),
                    "in_buffer_zone": remaining_time <= buffer_time,
                    "strategy_status": "strict_deadline"
                })
                
            elif time_strategy == "soft":
                # 软截止时间策略指标
                buffer_time = 1800  # 30分钟缓冲
                reduction_factor = 2
                metrics.update({
                    "buffer_time_remaining": max(0, remaining_time - buffer_time),
                    "in_buffer_zone": remaining_time <= buffer_time,
                    "iteration_reduction_factor": reduction_factor,
                    "next_iteration_allowed": current_iteration % reduction_factor == 0,
                    "strategy_status": "gradual_reduction"
                })
                
            else:  # adaptive
                # 自适应策略指标
                high_quality_threshold = 0.8
                low_quality_threshold = 0.5
                high_quality_factor = 3
                
                if current_quality > high_quality_threshold:
                    strategy_status = "high_quality_reduction"
                    next_iteration_allowed = current_iteration % high_quality_factor == 0
                elif current_quality < low_quality_threshold:
                    strategy_status = "low_quality_acceleration"
                    next_iteration_allowed = True
                else:
                    strategy_status = "normal_iteration"
                    next_iteration_allowed = True
                
                metrics.update({
                    "high_quality_threshold": high_quality_threshold,
                    "low_quality_threshold": low_quality_threshold,
                    "high_quality_factor": high_quality_factor,
                    "strategy_status": strategy_status,
                    "next_iteration_allowed": next_iteration_allowed,
                    "quality_based_adjustment": True
                })
            
            return metrics
            
        except Exception as e:
            workflow_logger.log_error(f"时间策略指标计算失败: {str(e)}", "ProgressTracker")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势方向"""
        try:
            if len(values) < 2:
                return "unknown"
            
            trend_value = self._calculate_trend_value(values)
            
            if trend_value > 0.05:
                return "increasing"
            elif trend_value < -0.05:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            workflow_logger.log_error(f"趋势计算失败: {str(e)}", "ProgressTracker")
            return "unknown"
    
    def _calculate_trend_value(self, values: List[float]) -> float:
        """计算趋势数值"""
        try:
            if len(values) < 2:
                return 0.0
            
            # 简单线性回归计算趋势
            x = np.arange(len(values))
            y = np.array(values)
            
            # 计算斜率
            slope = np.polyfit(x, y, 1)[0]
            
            # 归一化到-1到1之间
            if len(values) > 0:
                value_range = max(values) - min(values)
                if value_range > 0:
                    normalized_slope = slope / value_range
                    return normalized_slope
            
            return 0.0
            
        except Exception as e:
            workflow_logger.log_error(f"趋势值计算失败: {str(e)}", "ProgressTracker")
            return 0.0
    
    def _add_to_history(self, progress: Dict[str, Any]):
        """添加到历史记录"""
        try:
            self.progress_history.append(progress)
            
            # 限制历史记录大小
            if len(self.progress_history) > self.max_history_size:
                self.progress_history = self.progress_history[-self.max_history_size:]
                
        except Exception as e:
            workflow_logger.log_error(f"添加历史记录失败: {str(e)}", "ProgressTracker")
    
    def save_progress_report(self, progress_report: Dict[str, Any]) -> str:
        """保存进度报告"""
        try:
            report_file = os.path.join(
                self.progress_dir, 
                f"progress_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(progress_report, f, ensure_ascii=False, indent=2)
            
            workflow_logger.log_info(f"进度报告已保存: {report_file}", "ProgressTracker")
            return report_file
            
        except Exception as e:
            workflow_logger.log_error(f"进度报告保存失败: {str(e)}", "ProgressTracker")
            return ""
    
    def get_progress_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取进度摘要"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_progress = [
                p for p in self.progress_history
                if datetime.fromisoformat(p['timestamp']) > cutoff_time
            ]
            
            if not recent_progress:
                return {"error": "没有足够的历史数据"}
            
            # 计算摘要统计
            completion_percentages = [p['completion_percentage'] for p in recent_progress]
            quality_scores = [p['quality_metrics'].get('current_score', 0) for p in recent_progress]
            error_rates = [p['error_rate'] for p in recent_progress]
            
            return {
                "period_hours": hours,
                "data_points": len(recent_progress),
                "completion": {
                    "current": completion_percentages[-1] if completion_percentages else 0,
                    "average": np.mean(completion_percentages) if completion_percentages else 0,
                    "max": np.max(completion_percentages) if completion_percentages else 0,
                    "trend": self._calculate_trend(completion_percentages)
                },
                "quality": {
                    "current": quality_scores[-1] if quality_scores else 0,
                    "average": np.mean(quality_scores) if quality_scores else 0,
                    "max": np.max(quality_scores) if quality_scores else 0,
                    "trend": self._calculate_trend(quality_scores)
                },
                "errors": {
                    "current": error_rates[-1] if error_rates else 0,
                    "average": np.mean(error_rates) if error_rates else 0,
                    "max": np.max(error_rates) if error_rates else 0,
                    "trend": self._calculate_trend(error_rates)
                }
            }
            
        except Exception as e:
            workflow_logger.log_error(f"获取进度摘要失败: {str(e)}", "ProgressTracker")
            return {"error": str(e)}
    
    def get_convergence_analysis(self) -> Dict[str, Any]:
        """获取收敛分析"""
        try:
            if len(self.progress_history) < 5:
                return {"error": "需要至少5个数据点进行收敛分析"}
            
            # 获取质量分数历史
            quality_scores = []
            for progress in self.progress_history:
                if 'quality_metrics' in progress and 'current_score' in progress['quality_metrics']:
                    quality_scores.append(progress['quality_metrics']['current_score'])
            
            if len(quality_scores) < 5:
                return {"error": "质量分数数据不足"}
            
            # 分析收敛模式
            recent_scores = quality_scores[-10:]  # 最近10个分数
            variance = np.var(recent_scores)
            trend = self._calculate_trend_value(recent_scores)
            
            # 判断收敛状态
            converged = (variance < self.quality_convergence_threshold and 
                        abs(trend) < self.quality_convergence_threshold)
            
            # 计算收敛速度
            convergence_speed = self._calculate_convergence_speed(quality_scores)
            
            return {
                "converged": converged,
                "variance": variance,
                "trend": trend,
                "convergence_speed": convergence_speed,
                "threshold": self.quality_convergence_threshold,
                "recent_scores": recent_scores,
                "total_measurements": len(quality_scores)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"收敛分析失败: {str(e)}", "ProgressTracker")
            return {"error": str(e)}
    
    def _calculate_convergence_speed(self, quality_scores: List[float]) -> float:
        """计算收敛速度"""
        try:
            if len(quality_scores) < 3:
                return 0.0
            
            # 计算质量分数的变化率
            changes = []
            for i in range(1, len(quality_scores)):
                change = abs(quality_scores[i] - quality_scores[i-1])
                changes.append(change)
            
            # 计算平均变化率
            avg_change = np.mean(changes) if changes else 0.0
            
            # 计算收敛速度（变化率越小，收敛越快）
            convergence_speed = max(0.0, 1.0 - avg_change)
            
            return convergence_speed
            
        except Exception as e:
            workflow_logger.log_error(f"收敛速度计算失败: {str(e)}", "ProgressTracker")
            return 0.0
    
    def clear_history(self):
        """清空历史记录"""
        try:
            self.progress_history.clear()
            workflow_logger.log_info("进度历史记录已清空", "ProgressTracker")
        except Exception as e:
            workflow_logger.log_error(f"清空历史记录失败: {str(e)}", "ProgressTracker")
    
    def export_progress_data(self, filepath: str) -> bool:
        """导出进度数据"""
        try:
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "history": self.progress_history,
                "summary": self.get_progress_summary(hours=24)
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            workflow_logger.log_info(f"进度数据已导出: {filepath}", "ProgressTracker")
            return True
            
        except Exception as e:
            workflow_logger.log_error(f"导出进度数据失败: {str(e)}", "ProgressTracker")
            return False
