"""
轮次报告评分器
实现对单轮报告的评分逻辑，支持跨轮次的报告排序
"""

from typing import Dict, Any, List, Optional
from storage_models import RoundReport
from email_content_scorer import EmailContentScorer
from logger import workflow_logger
from datetime import datetime
import json


class RoundReportScorer:
    """轮次报告评分器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化内容评分器
        self.content_scorer = EmailContentScorer(config)
        
        # 无尽模式配置
        self.endless_config = config.get("endless_mode", {})
        
        # 评分权重配置
        self.scoring_weights = {
            "search_quality_weight": 0.35,
            "content_depth_weight": 0.35,
            "technical_metrics_weight": 0.20,
            "novelty_weight": 0.10  # 新颖性权重
        }
    
    def score_round_report(self, round_report: RoundReport) -> Dict[str, Any]:
        """
        对单轮报告进行评分
        
        Args:
            round_report: 单轮报告
            
        Returns:
            评分结果
        """
        workflow_logger.log_info(f"开始评分第{round_report.round_number}轮报告")
        
        try:
            # 基础评分维度
            search_quality_score = self._calculate_search_quality_score(round_report)
            content_depth_score = self._calculate_content_depth_score(round_report)
            technical_metrics_score = self._calculate_technical_metrics_score(round_report)
            
            # 新颖性评分（基于与历史报告的差异）
            novelty_score = self._calculate_novelty_score(round_report)
            
            # 计算综合评分
            comprehensive_score = (
                search_quality_score * self.scoring_weights["search_quality_weight"] +
                content_depth_score * self.scoring_weights["content_depth_weight"] +
                technical_metrics_score * self.scoring_weights["technical_metrics_weight"] +
                novelty_score * self.scoring_weights["novelty_weight"]
            )
            
            # 确定质量等级
            quality_level = self._determine_quality_level(comprehensive_score)
            
            scoring_result = {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "scores": {
                    "search_quality_score": search_quality_score,
                    "content_depth_score": content_depth_score,
                    "technical_metrics_score": technical_metrics_score,
                    "novelty_score": novelty_score,
                    "comprehensive_score": comprehensive_score
                },
                "quality_level": quality_level,
                "best_direction": round_report.best_direction,
                "key_findings": round_report.key_findings,
                "scoring_timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            workflow_logger.log_info(f"第{round_report.round_number}轮报告评分完成: {comprehensive_score:.1f}分 ({quality_level})")
            
            return scoring_result
            
        except Exception as e:
            error_msg = f"评分第{round_report.round_number}轮报告异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "scores": {
                    "search_quality_score": 0.0,
                    "content_depth_score": 0.0,
                    "technical_metrics_score": 0.0,
                    "novelty_score": 0.0,
                    "comprehensive_score": 0.0
                },
                "quality_level": "低",
                "best_direction": "",
                "key_findings": [],
                "scoring_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": error_msg
            }
    
    def score_all_round_reports(self, round_reports: List[RoundReport]) -> Dict[str, Any]:
        """
        对所有轮次报告进行评分和排序
        
        Args:
            round_reports: 所有轮次报告列表
            
        Returns:
            评分和排序结果
        """
        workflow_logger.log_info(f"开始评分{len(round_reports)}个轮次报告")
        
        try:
            scored_reports = []
            
            # 为每个报告评分
            for round_report in round_reports:
                scoring_result = self.score_round_report(round_report)
                scored_reports.append(scoring_result)
            
            # 按综合评分排序
            sorted_reports = sorted(scored_reports, 
                                 key=lambda x: x["scores"]["comprehensive_score"], 
                                 reverse=True)
            
            # 统计信息
            total_reports = len(scored_reports)
            high_quality_count = len([r for r in scored_reports if r["quality_level"] == "高"])
            medium_quality_count = len([r for r in scored_reports if r["quality_level"] == "中"])
            low_quality_count = len([r for r in scored_reports if r["quality_level"] == "低"])
            
            avg_score = sum(r["scores"]["comprehensive_score"] for r in scored_reports) / total_reports if total_reports > 0 else 0
            
            result = {
                "total_reports": total_reports,
                "scored_reports": scored_reports,
                "sorted_reports": sorted_reports,
                "statistics": {
                    "average_score": avg_score,
                    "high_quality_count": high_quality_count,
                    "medium_quality_count": medium_quality_count,
                    "low_quality_count": low_quality_count,
                    "score_distribution": {
                        "high": high_quality_count / total_reports if total_reports > 0 else 0,
                        "medium": medium_quality_count / total_reports if total_reports > 0 else 0,
                        "low": low_quality_count / total_reports if total_reports > 0 else 0
                    }
                },
                "scoring_timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            workflow_logger.log_info(f"所有轮次报告评分完成: 平均{avg_score:.1f}分, 高质量{high_quality_count}个")
            
            return result
            
        except Exception as e:
            error_msg = f"评分所有轮次报告异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "total_reports": 0,
                "scored_reports": [],
                "sorted_reports": [],
                "statistics": {},
                "scoring_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": error_msg
            }
    
    def _calculate_search_quality_score(self, round_report: RoundReport) -> float:
        """计算搜索质量评分"""
        try:
            search_rounds = round_report.search_rounds
            if not search_rounds:
                return 0.0
            
            # 成功率
            successful_rounds = [r for r in search_rounds if r.success]
            success_rate = len(successful_rounds) / len(search_rounds)
            
            # 结果数量
            total_results = sum(len(r.search_results) for r in successful_rounds)
            avg_results_per_round = total_results / len(successful_rounds) if successful_rounds else 0
            
            # 结果质量（基于摘要长度和关键点数量）
            total_summary_length = sum(len(r.summary) for r in successful_rounds)
            total_key_points = sum(len(r.key_points) for r in successful_rounds)
            
            # 综合评分
            score = (
                success_rate * 40 +  # 成功率权重40%
                min(avg_results_per_round / 10, 1.0) * 30 +  # 结果数量权重30%
                min(total_summary_length / 1000, 1.0) * 20 +  # 摘要质量权重20%
                min(total_key_points / 20, 1.0) * 10  # 关键点数量权重10%
            )
            
            return min(score, 100.0)
            
        except Exception as e:
            workflow_logger.log_error(f"计算搜索质量评分异常: {str(e)}")
            return 0.0
    
    def _calculate_content_depth_score(self, round_report: RoundReport) -> float:
        """计算内容深度评分"""
        try:
            # 基于关键发现数量和质量
            key_findings = round_report.key_findings
            findings_score = min(len(key_findings) * 10, 50)  # 每个发现10分，最多50分
            
            # 基于最佳方向的深度
            best_direction = round_report.best_direction
            direction_depth_score = len(best_direction) / 10 if best_direction else 0  # 方向名称长度反映深度
            direction_depth_score = min(direction_depth_score * 20, 30)  # 最多30分
            
            # 基于优化报告的内容
            optimized_report = round_report.optimized_report
            report_depth_score = 0
            if optimized_report and isinstance(optimized_report, dict):
                # 检查报告内容的丰富程度
                content_keys = ["executive_summary", "detailed_analysis", "key_insights", "recommendations"]
                for key in content_keys:
                    if key in optimized_report and optimized_report[key]:
                        report_depth_score += 5
                report_depth_score = min(report_depth_score, 20)  # 最多20分
            
            total_score = findings_score + direction_depth_score + report_depth_score
            return min(total_score, 100.0)
            
        except Exception as e:
            workflow_logger.log_error(f"计算内容深度评分异常: {str(e)}")
            return 0.0
    
    def _calculate_technical_metrics_score(self, round_report: RoundReport) -> float:
        """计算技术指标评分"""
        try:
            # 处理时间效率
            processing_time = round_report.processing_time
            time_score = max(0, 30 - processing_time / 60) if processing_time > 0 else 30  # 15分钟内满分
            
            # 问题数量
            questions_count = len(round_report.questions)
            questions_score = min(questions_count * 2, 20)  # 每个问题2分，最多20分
            
            # 搜索轮次数量
            search_rounds_count = len(round_report.search_rounds)
            rounds_score = min(search_rounds_count * 3, 25)  # 每个轮次3分，最多25分
            
            # 成功率
            successful_rounds = [r for r in round_report.search_rounds if r.success]
            success_rate = len(successful_rounds) / len(round_report.search_rounds) if round_report.search_rounds else 0
            success_score = success_rate * 25  # 成功率权重25分
            
            total_score = time_score + questions_score + rounds_score + success_score
            return min(total_score, 100.0)
            
        except Exception as e:
            workflow_logger.log_error(f"计算技术指标评分异常: {str(e)}")
            return 0.0
    
    def _calculate_novelty_score(self, round_report: RoundReport) -> float:
        """计算新颖性评分（基于与历史报告的差异）"""
        try:
            # 这里简化实现，实际可以基于更复杂的相似度计算
            # 基于最佳方向的独特性
            best_direction = round_report.best_direction
            if not best_direction:
                return 0.0
            
            # 基于关键发现的独特性
            key_findings = round_report.key_findings
            findings_novelty = min(len(key_findings) * 15, 60)  # 每个发现15分，最多60分
            
            # 基于问题的新颖性（简化：基于问题数量）
            questions_count = len(round_report.questions)
            questions_novelty = min(questions_count * 2, 40)  # 每个问题2分，最多40分
            
            total_score = findings_novelty + questions_novelty
            return min(total_score, 100.0)
            
        except Exception as e:
            workflow_logger.log_error(f"计算新颖性评分异常: {str(e)}")
            return 0.0
    
    def _determine_quality_level(self, comprehensive_score: float) -> str:
        """确定质量等级"""
        if comprehensive_score >= 80:
            return "高"
        elif comprehensive_score >= 60:
            return "中"
        else:
            return "低"
    
    def select_top_reports(self, sorted_reports: List[Dict[str, Any]], top_count: int = 3) -> Dict[str, Any]:
        """
        筛选前N个报告
        
        Args:
            sorted_reports: 已排序的报告列表
            top_count: 要选择的数量
            
        Returns:
            筛选结果
        """
        try:
            if not sorted_reports:
                return {
                    "top_reports": [],
                    "remaining_reports": [],
                    "selection_timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }
            
            # 选择前N个报告
            top_reports = sorted_reports[:top_count]
            remaining_reports = sorted_reports[top_count:]
            
            result = {
                "top_reports": top_reports,
                "remaining_reports": remaining_reports,
                "top_count": len(top_reports),
                "remaining_count": len(remaining_reports),
                "selection_timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            workflow_logger.log_info(f"报告筛选完成: 前{len(top_reports)}个完整报告, {len(remaining_reports)}个摘要报告")
            
            return result
            
        except Exception as e:
            error_msg = f"筛选前N个报告异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "top_reports": [],
                "remaining_reports": sorted_reports,
                "selection_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": error_msg
            }
