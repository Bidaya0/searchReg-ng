"""
最佳方向筛选器
负责从多个方向中选择最有价值的方向，为优化报告生成提供筛选结果
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from logger import workflow_logger


class SelectionCriteria:
    """筛选标准"""
    
    def __init__(self, config: Dict[str, Any]):
        self.min_comprehensive_score = config.get("min_comprehensive_score", 60.0)
        self.min_quality_level = config.get("min_quality_level", "中")
        self.max_detailed_directions = config.get("max_detailed_directions", 1)
        self.max_summary_directions = config.get("max_summary_directions", 4)
        self.complementary_threshold = config.get("complementary_threshold", 0.3)
        self.enable_quality_filtering = config.get("enable_quality_filtering", True)
        self.enable_complementary_analysis = config.get("enable_complementary_analysis", True)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "min_comprehensive_score": self.min_comprehensive_score,
            "min_quality_level": self.min_quality_level,
            "max_detailed_directions": self.max_detailed_directions,
            "max_summary_directions": self.max_summary_directions,
            "complementary_threshold": self.complementary_threshold,
            "enable_quality_filtering": self.enable_quality_filtering,
            "enable_complementary_analysis": self.enable_complementary_analysis
        }


class SelectionResult:
    """筛选结果"""
    
    def __init__(self):
        self.best_direction = ""
        self.best_direction_score = 0.0
        self.detailed_directions = []
        self.summary_directions = []
        self.excluded_directions = []
        self.selection_reasoning = ""
        self.complementary_analysis = {}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "best_direction": self.best_direction,
            "best_direction_score": self.best_direction_score,
            "detailed_directions": self.detailed_directions,
            "summary_directions": self.summary_directions,
            "excluded_directions": self.excluded_directions,
            "selection_reasoning": self.selection_reasoning,
            "complementary_analysis": self.complementary_analysis,
            "created_at": self.created_at.isoformat()
        }


class BestDirectionSelector:
    """最佳方向筛选器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 筛选标准配置
        self.criteria = SelectionCriteria(config)
    
    def select_best_directions(self, scoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """筛选最佳方向"""
        try:
            self.logger.log_info("开始筛选最佳方向")
            
            # 提取方向评分数据
            direction_scores = self._extract_direction_scores(scoring_result)
            
            if not direction_scores:
                return self._get_default_selection()
            
            # 1. 质量筛选
            qualified_directions = self._filter_by_quality(direction_scores)
            
            # 2. 评分排序
            sorted_directions = self._sort_by_score(qualified_directions)
            
            # 3. 选择最佳方向
            best_direction = self._select_best_direction(sorted_directions)
            
            # 4. 选择详细展示方向
            detailed_directions = self._select_detailed_directions(sorted_directions)
            
            # 5. 选择简略展示方向
            summary_directions = self._select_summary_directions(sorted_directions, detailed_directions)
            
            # 6. 确定排除的方向
            excluded_directions = self._identify_excluded_directions(direction_scores, detailed_directions, summary_directions)
            
            # 7. 互补性分析
            complementary_analysis = self._analyze_complementarity(sorted_directions) if self.criteria.enable_complementary_analysis else {}
            
            # 8. 生成筛选理由
            reasoning = self._generate_selection_reasoning(best_direction, detailed_directions, summary_directions, excluded_directions)
            
            # 构建筛选结果
            result = SelectionResult()
            result.best_direction = best_direction["direction"]
            result.best_direction_score = best_direction["comprehensive_score"]
            result.detailed_directions = [d["direction"] for d in detailed_directions]
            result.summary_directions = [d["direction"] for d in summary_directions]
            result.excluded_directions = excluded_directions
            result.selection_reasoning = reasoning
            result.complementary_analysis = complementary_analysis
            
            self.logger.log_info(f"最佳方向筛选完成: {result.best_direction} ({result.best_direction_score:.1f}分)")
            
            return {
                "status": "completed",
                "selection_result": result.to_dict(),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.log_error(f"筛选最佳方向失败: {str(e)}")
            return self._get_default_selection()
    
    def _extract_direction_scores(self, scoring_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取方向评分数据"""
        try:
            if "scoring_result" not in scoring_result:
                return []
            
            scoring_data = scoring_result["scoring_result"]
            if "direction_scores" not in scoring_data:
                return []
            
            return scoring_data["direction_scores"]
            
        except Exception as e:
            self.logger.log_error(f"提取方向评分数据失败: {str(e)}")
            return []
    
    def _filter_by_quality(self, direction_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于质量筛选方向"""
        if not self.criteria.enable_quality_filtering:
            return direction_scores
        
        qualified_directions = []
        
        for score in direction_scores:
            # 检查综合评分
            if score.get("comprehensive_score", 0) >= self.criteria.min_comprehensive_score:
                # 检查质量等级
                if self._is_quality_level_acceptable(score.get("quality_level", "低")):
                    qualified_directions.append(score)
                else:
                    self.logger.log_info(f"方向 '{score.get('direction', 'unknown')}' 质量等级不符合要求: {score.get('quality_level', '低')}")
            else:
                self.logger.log_info(f"方向 '{score.get('direction', 'unknown')}' 评分不符合要求: {score.get('comprehensive_score', 0):.1f}分")
        
        self.logger.log_info(f"质量筛选完成，{len(qualified_directions)}/{len(direction_scores)} 个方向符合要求")
        return qualified_directions
    
    def _is_quality_level_acceptable(self, quality_level: str) -> bool:
        """检查质量等级是否可接受"""
        quality_hierarchy = {"低": 1, "中": 2, "高": 3}
        min_level = quality_hierarchy.get(self.criteria.min_quality_level, 2)
        current_level = quality_hierarchy.get(quality_level, 1)
        
        return current_level >= min_level
    
    def _sort_by_score(self, direction_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按评分排序"""
        return sorted(direction_scores, key=lambda x: x.get("comprehensive_score", 0), reverse=True)
    
    def _select_best_direction(self, sorted_directions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最佳方向"""
        if not sorted_directions:
            raise ValueError("没有可用的方向")
        
        best_direction = sorted_directions[0]
        self.logger.log_info(f"选择最佳方向: {best_direction.get('direction', 'unknown')} ({best_direction.get('comprehensive_score', 0):.1f}分)")
        return best_direction
    
    def _select_detailed_directions(self, sorted_directions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择详细展示方向"""
        detailed_directions = []
        
        # 选择最佳方向作为详细展示
        if sorted_directions:
            detailed_directions.append(sorted_directions[0])
        
        # 如果配置允许多个详细展示方向，选择其他高质量方向
        if self.criteria.max_detailed_directions > 1 and len(sorted_directions) > 1:
            additional_count = min(
                self.criteria.max_detailed_directions - 1,
                len(sorted_directions) - 1
            )
            
            for i in range(1, additional_count + 1):
                if sorted_directions[i].get("comprehensive_score", 0) >= 70.0:  # 高质量阈值
                    detailed_directions.append(sorted_directions[i])
        
        self.logger.log_info(f"选择 {len(detailed_directions)} 个详细展示方向")
        return detailed_directions
    
    def _select_summary_directions(self, sorted_directions: List[Dict[str, Any]], detailed_directions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择简略展示方向"""
        detailed_direction_names = {d.get("direction", "") for d in detailed_directions}
        summary_directions = []
        
        # 从剩余方向中选择
        for direction in sorted_directions:
            if direction.get("direction", "") not in detailed_direction_names:
                if len(summary_directions) < self.criteria.max_summary_directions:
                    summary_directions.append(direction)
                else:
                    break
        
        self.logger.log_info(f"选择 {len(summary_directions)} 个简略展示方向")
        return summary_directions
    
    def _identify_excluded_directions(self, all_directions: List[Dict[str, Any]], 
                                    detailed_directions: List[Dict[str, Any]],
                                    summary_directions: List[Dict[str, Any]]) -> List[str]:
        """识别排除的方向"""
        included_direction_names = set()
        included_direction_names.update(d.get("direction", "") for d in detailed_directions)
        included_direction_names.update(d.get("direction", "") for d in summary_directions)
        
        excluded_directions = []
        for direction in all_directions:
            if direction.get("direction", "") not in included_direction_names:
                excluded_directions.append(direction.get("direction", ""))
        
        self.logger.log_info(f"排除 {len(excluded_directions)} 个方向")
        return excluded_directions
    
    def _analyze_complementarity(self, sorted_directions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析互补性"""
        if len(sorted_directions) < 2:
            return {}
        
        complementary_pairs = []
        complementary_score = 0.0
        
        # 分析方向间的互补性
        for i, direction1 in enumerate(sorted_directions):
            for j, direction2 in enumerate(sorted_directions[i+1:], i+1):
                complementarity = self._calculate_complementarity(direction1, direction2)
                if complementarity >= self.criteria.complementary_threshold:
                    complementary_pairs.append({
                        "direction1": direction1.get("direction", ""),
                        "direction2": direction2.get("direction", ""),
                        "complementarity_score": complementarity
                    })
                    complementary_score += complementarity
        
        avg_complementary_score = complementary_score / len(complementary_pairs) if complementary_pairs else 0.0
        
        return {
            "complementary_pairs": complementary_pairs,
            "avg_complementary_score": avg_complementary_score,
            "total_complementary_pairs": len(complementary_pairs)
        }
    
    def _calculate_complementarity(self, direction1: Dict[str, Any], direction2: Dict[str, Any]) -> float:
        """计算两个方向的互补性"""
        # 基于评分差异和内容特征计算互补性
        score1 = direction1.get("comprehensive_score", 0)
        score2 = direction2.get("comprehensive_score", 0)
        score_diff = abs(score1 - score2)
        
        # 评分差异越大，互补性越高
        complementarity = min(score_diff / 100.0, 1.0)
        
        return complementarity
    
    def _generate_selection_reasoning(self, best_direction: Dict[str, Any],
                                   detailed_directions: List[Dict[str, Any]],
                                   summary_directions: List[Dict[str, Any]],
                                   excluded_directions: List[str]) -> str:
        """生成筛选理由"""
        reasoning_parts = []
        
        # 最佳方向理由
        best_dir_name = best_direction.get("direction", "unknown")
        best_score = best_direction.get("comprehensive_score", 0)
        best_quality = best_direction.get("quality_level", "低")
        reasoning_parts.append(f"选择 '{best_dir_name}' 作为最佳方向，综合评分 {best_score:.1f}分，质量等级 {best_quality}。")
        
        # 详细展示理由
        if len(detailed_directions) > 1:
            detailed_names = [d.get("direction", "") for d in detailed_directions[1:]]
            reasoning_parts.append(f"同时选择 {', '.join(detailed_names)} 进行详细展示，这些方向评分较高且内容质量优秀。")
        
        # 简略展示理由
        if summary_directions:
            summary_names = [d.get("direction", "") for d in summary_directions]
            reasoning_parts.append(f"选择 {', '.join(summary_names)} 进行简略展示，提供补充信息和不同视角。")
        
        # 排除理由
        if excluded_directions:
            reasoning_parts.append(f"排除 {', '.join(excluded_directions)}，这些方向评分较低或内容质量不足。")
        
        return " ".join(reasoning_parts)
    
    def _get_default_selection(self) -> Dict[str, Any]:
        """获取默认选择"""
        result = SelectionResult()
        result.best_direction = "unknown"
        result.best_direction_score = 0.0
        result.detailed_directions = []
        result.summary_directions = []
        result.excluded_directions = []
        result.selection_reasoning = "没有可用的方向进行筛选"
        
        return {
            "status": "error",
            "selection_result": result.to_dict(),
            "error": "没有可用的方向进行筛选",
            "created_at": datetime.now().isoformat()
        }
    
    def get_selection_summary(self, selection_result: Dict[str, Any]) -> str:
        """获取筛选摘要"""
        result_data = selection_result.get("selection_result", {})
        
        summary_lines = [
            f"# 最佳方向筛选摘要",
            f"",
            f"**最佳方向**: {result_data.get('best_direction', 'unknown')}",
            f"**最佳评分**: {result_data.get('best_direction_score', 0):.1f}分",
            f"**详细展示方向**: {len(result_data.get('detailed_directions', []))}个",
            f"**简略展示方向**: {len(result_data.get('summary_directions', []))}个",
            f"**排除方向**: {len(result_data.get('excluded_directions', []))}个",
            f"",
            f"## 筛选理由",
            f"{result_data.get('selection_reasoning', '无')}",
            f"",
            f"## 互补性分析",
            f"互补性分析结果: {result_data.get('complementary_analysis', {})}"
        ]
        
        return "\n".join(summary_lines)
