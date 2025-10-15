"""
邮件内容评分系统
负责对邮件内容进行多维度量化评分，为最佳方向筛选提供科学依据
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

from storage_models import SearchRoundRecord
from logger import workflow_logger


class QualityLevel(str, Enum):
    """质量等级枚举"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class DirectionScore:
    """方向评分结果"""
    
    def __init__(self, direction: str):
        self.direction = direction
        
        # 各维度评分（0-100）
        self.search_quality_score = 0.0
        self.content_depth_score = 0.0
        self.technical_score = 0.0
        self.comprehensive_score = 0.0
        
        # 质量等级和排名
        self.quality_level = QualityLevel.LOW
        self.ranking = 0
        
        # 详细指标
        self.search_results_count = 0
        self.search_success_rate = 0.0
        self.avg_summary_length = 0.0
        self.avg_key_points_count = 0.0
        self.avg_processing_time = 0.0
        
        # 时间信息
        self.calculated_at = datetime.now()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "direction": self.direction,
            "search_quality_score": self.search_quality_score,
            "content_depth_score": self.content_depth_score,
            "technical_score": self.technical_score,
            "comprehensive_score": self.comprehensive_score,
            "quality_level": self.quality_level.value,
            "ranking": self.ranking,
            "search_results_count": self.search_results_count,
            "search_success_rate": self.search_success_rate,
            "avg_summary_length": self.avg_summary_length,
            "avg_key_points_count": self.avg_key_points_count,
            "avg_processing_time": self.avg_processing_time,
            "calculated_at": self.calculated_at.isoformat(),
            "metadata": self.metadata
        }


class ScoringResult:
    """评分结果"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.total_directions = 0
        self.scored_directions = 0
        
        # 评分结果
        self.direction_scores = []
        self.best_direction = None
        self.best_score = 0.0
        
        # 统计信息
        self.avg_comprehensive_score = 0.0
        self.score_distribution = {}
        self.quality_distribution = {}
        
        # 时间信息
        self.calculated_at = datetime.now()
        self.processing_time = 0.0
    
    def add_direction_score(self, direction_score: DirectionScore):
        """添加方向评分"""
        self.direction_scores.append(direction_score)
        self.scored_directions += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "topic": self.topic,
            "total_directions": self.total_directions,
            "scored_directions": self.scored_directions,
            "direction_scores": [score.to_dict() for score in self.direction_scores],
            "best_direction": self.best_direction,
            "best_score": self.best_score,
            "avg_comprehensive_score": self.avg_comprehensive_score,
            "score_distribution": self.score_distribution,
            "quality_distribution": self.quality_distribution,
            "calculated_at": self.calculated_at.isoformat(),
            "processing_time": self.processing_time
        }


class SearchQualityScorer:
    """搜索质量评分器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 评分权重配置
        self.weights = {
            "results_count_weight": 0.3,      # 搜索结果数量权重
            "success_rate_weight": 0.4,       # 搜索成功率权重
            "relevance_weight": 0.3          # 结果相关性权重
        }
        
        # 评分阈值配置
        self.thresholds = {
            "min_results_count": 3,           # 最小结果数量
            "max_results_count": 20,          # 最大结果数量
            "min_success_rate": 0.6,          # 最小成功率
            "min_relevance_score": 0.5        # 最小相关性评分
        }
    
    def calculate_search_quality_score(self, direction: str, search_rounds: List[SearchRoundRecord]) -> float:
        """计算搜索质量评分"""
        try:
            # 筛选该方向的搜索记录
            direction_rounds = [round for round in search_rounds if round.direction == direction]
            
            if not direction_rounds:
                self.logger.log_warning(f"方向 '{direction}' 没有搜索记录")
                return 0.0
            
            # 1. 计算搜索结果数量评分
            results_count_score = self._calculate_results_count_score(direction_rounds)
            
            # 2. 计算搜索成功率评分
            success_rate_score = self._calculate_success_rate_score(direction_rounds)
            
            # 3. 计算结果相关性评分
            relevance_score = self._calculate_relevance_score(direction_rounds)
            
            # 4. 计算综合评分
            comprehensive_score = (
                results_count_score * self.weights["results_count_weight"] +
                success_rate_score * self.weights["success_rate_weight"] +
                relevance_score * self.weights["relevance_weight"]
            )
            
            return min(comprehensive_score * 100, 100.0)  # 转换为0-100分
            
        except Exception as e:
            self.logger.log_error(f"计算搜索质量评分失败: {str(e)}")
            return 0.0
    
    def _calculate_results_count_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算搜索结果数量评分"""
        total_results = sum(len(round.search_results) if round.search_results else 0 for round in search_rounds)
        avg_results = total_results / len(search_rounds)
        
        # 标准化到0-1范围
        if avg_results <= self.thresholds["min_results_count"]:
            return 0.0
        elif avg_results >= self.thresholds["max_results_count"]:
            return 1.0
        else:
            return (avg_results - self.thresholds["min_results_count"]) / (
                self.thresholds["max_results_count"] - self.thresholds["min_results_count"]
            )
    
    def _calculate_success_rate_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算搜索成功率评分"""
        successful_rounds = sum(1 for round in search_rounds if round.success)
        success_rate = successful_rounds / len(search_rounds)
        
        # 标准化到0-1范围
        if success_rate <= self.thresholds["min_success_rate"]:
            return 0.0
        else:
            return min(success_rate, 1.0)
    
    def _calculate_relevance_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算结果相关性评分"""
        # 基于搜索结果的质量和相关性
        relevance_scores = []
        
        for round in search_rounds:
            if round.search_results:
                # 简单的相关性评分：基于结果数量和质量
                result_count = len(round.search_results)
                quality_score = 1.0 if round.success else 0.5
                
                # 综合评分
                relevance_score = min(result_count / 10.0, 1.0) * quality_score
                relevance_scores.append(relevance_score)
        
        if not relevance_scores:
            return 0.0
        
        return sum(relevance_scores) / len(relevance_scores)


class ContentDepthScorer:
    """内容深度评分器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 评分权重配置
        self.weights = {
            "summary_length_weight": 0.4,     # 摘要长度权重
            "key_points_weight": 0.35,        # 关键点权重
            "completeness_weight": 0.25       # 完整性权重
        }
        
        # 评分阈值配置
        self.thresholds = {
            "min_summary_length": 50,         # 最小摘要长度
            "max_summary_length": 500,        # 最大摘要长度
            "min_key_points": 2,              # 最小关键点数
            "max_key_points": 10              # 最大关键点数
        }
    
    def calculate_content_depth_score(self, direction: str, search_rounds: List[SearchRoundRecord]) -> float:
        """计算内容深度评分"""
        try:
            # 筛选该方向的搜索记录
            direction_rounds = [round for round in search_rounds if round.direction == direction]
            
            if not direction_rounds:
                self.logger.log_warning(f"方向 '{direction}' 没有搜索记录")
                return 0.0
            
            # 1. 计算摘要长度评分
            summary_length_score = self._calculate_summary_length_score(direction_rounds)
            
            # 2. 计算关键点数量评分
            key_points_score = self._calculate_key_points_score(direction_rounds)
            
            # 3. 计算内容完整性评分
            completeness_score = self._calculate_completeness_score(direction_rounds)
            
            # 4. 计算综合评分
            comprehensive_score = (
                summary_length_score * self.weights["summary_length_weight"] +
                key_points_score * self.weights["key_points_weight"] +
                completeness_score * self.weights["completeness_weight"]
            )
            
            return min(comprehensive_score * 100, 100.0)  # 转换为0-100分
            
        except Exception as e:
            self.logger.log_error(f"计算内容深度评分失败: {str(e)}")
            return 0.0
    
    def _calculate_summary_length_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算摘要长度评分"""
        total_length = sum(len(round.summary) if round.summary else 0 for round in search_rounds)
        avg_length = total_length / len(search_rounds)
        
        # 标准化到0-1范围
        if avg_length <= self.thresholds["min_summary_length"]:
            return 0.0
        elif avg_length >= self.thresholds["max_summary_length"]:
            return 1.0
        else:
            return (avg_length - self.thresholds["min_summary_length"]) / (
                self.thresholds["max_summary_length"] - self.thresholds["min_summary_length"]
            )
    
    def _calculate_key_points_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算关键点数量评分"""
        total_key_points = sum(len(round.key_points) if round.key_points else 0 for round in search_rounds)
        avg_key_points = total_key_points / len(search_rounds)
        
        # 标准化到0-1范围
        if avg_key_points <= self.thresholds["min_key_points"]:
            return 0.0
        elif avg_key_points >= self.thresholds["max_key_points"]:
            return 1.0
        else:
            return (avg_key_points - self.thresholds["min_key_points"]) / (
                self.thresholds["max_key_points"] - self.thresholds["min_key_points"]
            )
    
    def _calculate_completeness_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算内容完整性评分"""
        completeness_scores = []
        
        for round in search_rounds:
            completeness = 0.0
            
            # 有摘要（权重40%）
            if round.summary and len(round.summary.strip()) > 0:
                completeness += 0.4
            
            # 有关键点（权重30%）
            if round.key_points and len(round.key_points) > 0:
                completeness += 0.3
            
            # 有搜索结果（权重30%）
            if round.search_results and len(round.search_results) > 0:
                completeness += 0.3
            
            completeness_scores.append(completeness)
        
        return sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0


class TechnicalMetricsScorer:
    """技术指标评分器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 评分权重配置
        self.weights = {
            "processing_time_weight": 0.5,    # 处理时间权重
            "stability_weight": 0.5           # 稳定性权重
        }
        
        # 评分阈值配置
        self.thresholds = {
            "min_processing_time": 1.0,       # 最小处理时间（秒）
            "max_processing_time": 30.0,      # 最大处理时间（秒）
            "min_stability_rate": 0.8         # 最小稳定性率
        }
    
    def calculate_technical_score(self, direction: str, search_rounds: List[SearchRoundRecord]) -> float:
        """计算技术指标评分"""
        try:
            # 筛选该方向的搜索记录
            direction_rounds = [round for round in search_rounds if round.direction == direction]
            
            if not direction_rounds:
                self.logger.log_warning(f"方向 '{direction}' 没有搜索记录")
                return 0.0
            
            # 1. 计算处理时间效率评分
            processing_time_score = self._calculate_processing_time_score(direction_rounds)
            
            # 2. 计算系统稳定性评分
            stability_score = self._calculate_stability_score(direction_rounds)
            
            # 3. 计算综合评分
            comprehensive_score = (
                processing_time_score * self.weights["processing_time_weight"] +
                stability_score * self.weights["stability_weight"]
            )
            
            return min(comprehensive_score * 100, 100.0)  # 转换为0-100分
            
        except Exception as e:
            self.logger.log_error(f"计算技术指标评分失败: {str(e)}")
            return 0.0
    
    def _calculate_processing_time_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算处理时间效率评分"""
        total_time = sum(round.processing_time for round in search_rounds)
        avg_time = total_time / len(search_rounds)
        
        # 标准化到0-1范围（时间越短，评分越高）
        if avg_time <= self.thresholds["min_processing_time"]:
            return 1.0
        elif avg_time >= self.thresholds["max_processing_time"]:
            return 0.0
        else:
            return 1.0 - (avg_time - self.thresholds["min_processing_time"]) / (
                self.thresholds["max_processing_time"] - self.thresholds["min_processing_time"]
            )
    
    def _calculate_stability_score(self, search_rounds: List[SearchRoundRecord]) -> float:
        """计算系统稳定性评分"""
        successful_rounds = sum(1 for round in search_rounds if round.success)
        stability_rate = successful_rounds / len(search_rounds)
        
        # 标准化到0-1范围
        if stability_rate <= self.thresholds["min_stability_rate"]:
            return 0.0
        else:
            return min(stability_rate, 1.0)


class ComprehensiveScorer:
    """综合评分器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 评分权重配置
        self.weights = {
            "search_quality_weight": 0.4,     # 搜索质量权重
            "content_depth_weight": 0.4,      # 内容深度权重
            "technical_metrics_weight": 0.2   # 技术指标权重
        }
    
    def calculate_comprehensive_score(self, search_quality_score: float, 
                                    content_depth_score: float, 
                                    technical_score: float) -> float:
        """计算综合评分"""
        try:
            comprehensive_score = (
                search_quality_score * self.weights["search_quality_weight"] +
                content_depth_score * self.weights["content_depth_weight"] +
                technical_score * self.weights["technical_metrics_weight"]
            )
            
            return min(comprehensive_score, 100.0)
            
        except Exception as e:
            self.logger.log_error(f"计算综合评分失败: {str(e)}")
            return 0.0
    
    def determine_quality_level(self, comprehensive_score: float) -> QualityLevel:
        """确定质量等级"""
        if comprehensive_score >= 80:
            return QualityLevel.HIGH
        elif comprehensive_score >= 60:
            return QualityLevel.MEDIUM
        else:
            return QualityLevel.LOW


class ScoreAnalyzer:
    """评分结果分析器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
    
    def analyze_scoring_result(self, scoring_result: ScoringResult) -> Dict[str, Any]:
        """分析评分结果"""
        try:
            # 计算统计信息
            self._calculate_statistics(scoring_result)
            
            # 确定最佳方向
            self._determine_best_direction(scoring_result)
            
            # 计算分布信息
            self._calculate_distributions(scoring_result)
            
            # 生成分析报告
            analysis_report = self._generate_analysis_report(scoring_result)
            
            return analysis_report
            
        except Exception as e:
            self.logger.log_error(f"分析评分结果失败: {str(e)}")
            return {}
    
    def _calculate_statistics(self, scoring_result: ScoringResult):
        """计算统计信息"""
        if not scoring_result.direction_scores:
            return
        
        # 计算平均综合评分
        total_score = sum(score.comprehensive_score for score in scoring_result.direction_scores)
        scoring_result.avg_comprehensive_score = total_score / len(scoring_result.direction_scores)
        
        # 设置总方向数
        scoring_result.total_directions = len(scoring_result.direction_scores)
    
    def _determine_best_direction(self, scoring_result: ScoringResult):
        """确定最佳方向"""
        if not scoring_result.direction_scores:
            return
        
        # 按综合评分排序
        sorted_scores = sorted(scoring_result.direction_scores, 
                             key=lambda x: x.comprehensive_score, reverse=True)
        
        # 设置最佳方向
        best_score = sorted_scores[0]
        scoring_result.best_direction = best_score.direction
        scoring_result.best_score = best_score.comprehensive_score
        
        # 设置排名
        for i, score in enumerate(sorted_scores):
            score.ranking = i + 1
    
    def _calculate_distributions(self, scoring_result: ScoringResult):
        """计算分布信息"""
        if not scoring_result.direction_scores:
            return
        
        # 计算评分分布
        score_ranges = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "0-59": 0
        }
        
        for score in scoring_result.direction_scores:
            if score.comprehensive_score >= 90:
                score_ranges["90-100"] += 1
            elif score.comprehensive_score >= 80:
                score_ranges["80-89"] += 1
            elif score.comprehensive_score >= 70:
                score_ranges["70-79"] += 1
            elif score.comprehensive_score >= 60:
                score_ranges["60-69"] += 1
            else:
                score_ranges["0-59"] += 1
        
        scoring_result.score_distribution = score_ranges
        
        # 计算质量分布
        quality_distribution = {
            "高": 0,
            "中": 0,
            "低": 0
        }
        
        for score in scoring_result.direction_scores:
            quality_distribution[score.quality_level.value] += 1
        
        scoring_result.quality_distribution = quality_distribution
    
    def _generate_analysis_report(self, scoring_result: ScoringResult) -> Dict[str, Any]:
        """生成分析报告"""
        return {
            "analysis_summary": {
                "total_directions": scoring_result.total_directions,
                "scored_directions": scoring_result.scored_directions,
                "best_direction": scoring_result.best_direction,
                "best_score": scoring_result.best_score,
                "avg_score": scoring_result.avg_comprehensive_score
            },
            "score_distribution": scoring_result.score_distribution,
            "quality_distribution": scoring_result.quality_distribution,
            "top_directions": [
                {
                    "direction": score.direction,
                    "score": score.comprehensive_score,
                    "quality_level": score.quality_level.value,
                    "ranking": score.ranking
                }
                for score in sorted(scoring_result.direction_scores, 
                                  key=lambda x: x.comprehensive_score, reverse=True)[:3]
            ],
            "analysis_insights": self._generate_insights(scoring_result)
        }
    
    def _generate_insights(self, scoring_result: ScoringResult) -> List[str]:
        """生成分析洞察"""
        insights = []
        
        # 基于最佳评分的洞察
        if scoring_result.best_score >= 80:
            insights.append(f"'{scoring_result.best_direction}'方向表现卓越，具有重要的研究价值")
        elif scoring_result.best_score >= 60:
            insights.append(f"'{scoring_result.best_direction}'方向表现良好，值得重点关注")
        
        # 基于质量分布的洞察
        quality_dist = scoring_result.quality_distribution
        if quality_dist.get("高", 0) > 0:
            insights.append(f"有{quality_dist['高']}个方向达到高质量标准，整体分析质量较高")
        
        # 基于平均评分的洞察
        if scoring_result.avg_comprehensive_score >= 70:
            insights.append("整体评分较高，各方向质量均衡")
        elif scoring_result.avg_comprehensive_score >= 50:
            insights.append("整体评分中等，存在改进空间")
        else:
            insights.append("整体评分较低，需要优化搜索和分析策略")
        
        return insights


class EmailContentScorer:
    """邮件内容评分器主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 初始化子组件
        self.search_quality_scorer = SearchQualityScorer(config)
        self.content_depth_scorer = ContentDepthScorer(config)
        self.technical_metrics_scorer = TechnicalMetricsScorer(config)
        self.comprehensive_scorer = ComprehensiveScorer(config)
        self.score_analyzer = ScoreAnalyzer(config)
    
    def score_directions(self, search_rounds: List[SearchRoundRecord], topic: str) -> Dict[str, Any]:
        """对各个方向进行评分"""
        try:
            start_time = datetime.now()
            self.logger.log_info(f"开始对方向进行评分，主题: {topic}")
            
            # 创建评分结果
            scoring_result = ScoringResult(topic)
            
            # 获取所有方向
            directions = list(set(round.direction for round in search_rounds))
            scoring_result.total_directions = len(directions)
            
            # 对每个方向进行评分
            for direction in directions:
                direction_score = self._score_single_direction(direction, search_rounds)
                if direction_score:
                    scoring_result.add_direction_score(direction_score)
            
            # 分析评分结果
            analysis_report = self.score_analyzer.analyze_scoring_result(scoring_result)
            
            # 计算处理时间
            end_time = datetime.now()
            scoring_result.processing_time = (end_time - start_time).total_seconds()
            
            # 构建返回结果
            result = {
                "status": "completed",
                "scoring_result": scoring_result.to_dict(),
                "analysis_report": analysis_report,
                "created_at": datetime.now().isoformat()
            }
            
            self.logger.log_info(f"方向评分完成，共{scoring_result.scored_directions}个方向")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
            self.logger.log_error(f"方向评分失败: {str(e)}")
            return error_result
    
    def _score_single_direction(self, direction: str, search_rounds: List[SearchRoundRecord]) -> Optional[DirectionScore]:
        """对单个方向进行评分"""
        try:
            # 创建方向评分对象
            direction_score = DirectionScore(direction)
            
            # 计算各维度评分
            search_quality_score = self.search_quality_scorer.calculate_search_quality_score(direction, search_rounds)
            content_depth_score = self.content_depth_scorer.calculate_content_depth_score(direction, search_rounds)
            technical_score = self.technical_metrics_scorer.calculate_technical_score(direction, search_rounds)
            
            # 计算综合评分
            comprehensive_score = self.comprehensive_scorer.calculate_comprehensive_score(
                search_quality_score, content_depth_score, technical_score
            )
            
            # 设置评分结果
            direction_score.search_quality_score = search_quality_score
            direction_score.content_depth_score = content_depth_score
            direction_score.technical_score = technical_score
            direction_score.comprehensive_score = comprehensive_score
            
            # 确定质量等级
            direction_score.quality_level = self.comprehensive_scorer.determine_quality_level(comprehensive_score)
            
            # 设置详细指标
            self._set_detailed_metrics(direction_score, direction, search_rounds)
            
            return direction_score
            
        except Exception as e:
            self.logger.log_error(f"评分方向 '{direction}' 失败: {str(e)}")
            return None
    
    def _set_detailed_metrics(self, direction_score: DirectionScore, direction: str, search_rounds: List[SearchRoundRecord]):
        """设置详细指标"""
        direction_rounds = [round for round in search_rounds if round.direction == direction]
        
        if not direction_rounds:
            return
        
        # 搜索结果数量
        total_results = sum(len(round.search_results) if round.search_results else 0 for round in direction_rounds)
        direction_score.search_results_count = total_results
        
        # 搜索成功率
        successful_rounds = sum(1 for round in direction_rounds if round.success)
        direction_score.search_success_rate = successful_rounds / len(direction_rounds)
        
        # 平均摘要长度
        total_summary_length = sum(len(round.summary) if round.summary else 0 for round in direction_rounds)
        direction_score.avg_summary_length = total_summary_length / len(direction_rounds)
        
        # 平均关键点数量
        total_key_points = sum(len(round.key_points) if round.key_points else 0 for round in direction_rounds)
        direction_score.avg_key_points_count = total_key_points / len(direction_rounds)
        
        # 平均处理时间
        total_processing_time = sum(round.processing_time for round in direction_rounds)
        direction_score.avg_processing_time = total_processing_time / len(direction_rounds)
    
    def get_scoring_summary(self, scoring_result: ScoringResult) -> str:
        """获取评分摘要"""
        summary_lines = [
            f"# 邮件内容评分摘要",
            f"",
            f"**主题**: {scoring_result.topic}",
            f"**总方向数**: {scoring_result.total_directions}",
            f"**已评分方向数**: {scoring_result.scored_directions}",
            f"**最佳方向**: {scoring_result.best_direction}",
            f"**最佳评分**: {scoring_result.best_score:.1f}分",
            f"**平均评分**: {scoring_result.avg_comprehensive_score:.1f}分",
            f"",
            f"## 评分分布",
            f"- 90-100分: {scoring_result.score_distribution.get('90-100', 0)}个方向",
            f"- 80-89分: {scoring_result.score_distribution.get('80-89', 0)}个方向",
            f"- 70-79分: {scoring_result.score_distribution.get('70-79', 0)}个方向",
            f"- 60-69分: {scoring_result.score_distribution.get('60-69', 0)}个方向",
            f"- 0-59分: {scoring_result.score_distribution.get('0-59', 0)}个方向",
            f"",
            f"## 质量分布",
            f"- 高质量: {scoring_result.quality_distribution.get('高', 0)}个方向",
            f"- 中等质量: {scoring_result.quality_distribution.get('中', 0)}个方向",
            f"- 低质量: {scoring_result.quality_distribution.get('低', 0)}个方向"
        ]
        
        return "\n".join(summary_lines)
