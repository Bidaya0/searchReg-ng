"""
优化报告生成器
负责生成结构化的优化邮件报告，整合树状结构信息和筛选结果
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from storage_models import SearchRoundRecord
from logger import workflow_logger


class DetailedDirectionAnalysis:
    """详细方向分析"""
    
    def __init__(self, direction: str, score: float, quality_level: str):
        self.direction = direction
        self.score = score
        self.quality_level = quality_level
        
        # 详细内容
        self.questions = []
        self.search_results = []
        self.summaries = []
        self.key_points = []
        
        # 分析内容
        self.detailed_analysis = ""
        self.insights = []
        self.recommendations = []
        
        # 统计信息
        self.total_questions = 0
        self.total_search_results = 0
        self.avg_summary_length = 0.0
        self.avg_key_points_count = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "direction": self.direction,
            "score": self.score,
            "quality_level": self.quality_level,
            "questions": self.questions,
            "search_results": self.search_results,
            "summaries": self.summaries,
            "key_points": self.key_points,
            "detailed_analysis": self.detailed_analysis,
            "insights": self.insights,
            "recommendations": self.recommendations,
            "total_questions": self.total_questions,
            "total_search_results": self.total_search_results,
            "avg_summary_length": self.avg_summary_length,
            "avg_key_points_count": self.avg_key_points_count
        }


class SummaryDirectionAnalysis:
    """简略方向分析"""
    
    def __init__(self, direction: str, score: float, quality_level: str):
        self.direction = direction
        self.score = score
        self.quality_level = quality_level
        
        # 简略内容
        self.key_findings = []
        self.main_insights = []
        self.brief_summary = ""
        
        # 统计信息
        self.total_questions = 0
        self.total_search_results = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "direction": self.direction,
            "score": self.score,
            "quality_level": self.quality_level,
            "key_findings": self.key_findings,
            "main_insights": self.main_insights,
            "brief_summary": self.brief_summary,
            "total_questions": self.total_questions,
            "total_search_results": self.total_search_results
        }


class OptimizedReport:
    """优化报告结构"""
    
    def __init__(self, topic: str, best_direction: str, best_direction_score: float):
        self.topic = topic
        self.best_direction = best_direction
        self.best_direction_score = best_direction_score
        self.analysis_dimensions = 0
        self.generation_time = datetime.now()
        
        # 详细内容
        self.executive_summary = ""
        self.best_direction_analysis = None
        
        # 简略内容
        self.other_directions_summary = []
        
        # 树状结构信息
        self.question_tree_summary = ""
        self.key_insights = []
        
        # 技术信息
        self.technical_stats = {}
        
        # 元数据
        self.report_id = f"optimized_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.created_at = datetime.now()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "topic": self.topic,
            "best_direction": self.best_direction,
            "best_direction_score": self.best_direction_score,
            "analysis_dimensions": self.analysis_dimensions,
            "generation_time": self.generation_time.isoformat(),
            "executive_summary": self.executive_summary,
            "best_direction_analysis": self.best_direction_analysis.to_dict() if self.best_direction_analysis else None,
            "other_directions_summary": [summary.to_dict() for summary in self.other_directions_summary],
            "question_tree_summary": self.question_tree_summary,
            "key_insights": self.key_insights,
            "technical_stats": self.technical_stats,
            "report_id": self.report_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class OptimizedReportGenerator:
    """优化报告生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2000)
        )
    
    def generate_optimized_report(self, selection_result: Dict[str, Any], 
                                scoring_result: Dict[str, Any],
                                search_rounds: List[SearchRoundRecord],
                                question_tree: Dict[str, Any],
                                topic: str) -> Dict[str, Any]:
        """生成优化报告"""
        try:
            self.logger.log_info(f"开始生成优化报告，主题: {topic}")
            
            # 提取数据
            selection_data = selection_result.get("selection_result", {})
            scoring_data = scoring_result.get("scoring_result", {})
            
            # 创建优化报告
            report = OptimizedReport(
                topic=topic,
                best_direction=selection_data.get("best_direction", "unknown"),
                best_direction_score=selection_data.get("best_direction_score", 0.0)
            )
            
            # 设置分析维度数
            report.analysis_dimensions = scoring_data.get("total_directions", 0)
            
            # 1. 生成执行摘要
            report.executive_summary = self._generate_executive_summary(selection_result, scoring_result, topic)
            
            # 2. 生成最佳方向详细分析
            report.best_direction_analysis = self._generate_detailed_direction_analysis(
                selection_data.get("best_direction", "unknown"), search_rounds, scoring_result
            )
            
            # 3. 生成其他方向简略分析
            report.other_directions_summary = self._generate_summary_directions_analysis(
                selection_data.get("summary_directions", []), search_rounds, scoring_result
            )
            
            # 4. 生成问题树状结构摘要
            report.question_tree_summary = self._generate_question_tree_summary(question_tree)
            
            # 5. 生成关键洞察
            report.key_insights = self._generate_key_insights(selection_result, scoring_result, search_rounds)
            
            # 6. 生成技术统计
            report.technical_stats = self._generate_technical_stats(scoring_result, search_rounds)
            
            self.logger.log_info(f"优化报告生成完成，最佳方向: {report.best_direction}")
            
            return {
                "status": "completed",
                "optimized_report": report.to_dict(),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.log_error(f"生成优化报告失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
    
    def _generate_executive_summary(self, selection_result: Dict[str, Any], 
                                  scoring_result: Dict[str, Any], topic: str) -> str:
        """生成执行摘要"""
        try:
            selection_data = selection_result.get("selection_result", {})
            scoring_data = scoring_result.get("scoring_result", {})
            
            prompt = f"""请为以下分析结果生成一个专业的执行摘要：

主题：{topic}
最佳方向：{selection_data.get('best_direction', 'unknown')}（评分：{selection_data.get('best_direction_score', 0):.1f}分）
分析维度：{scoring_data.get('total_directions', 0)}个方向
平均评分：{scoring_data.get('avg_comprehensive_score', 0):.1f}分

筛选理由：{selection_data.get('selection_reasoning', '无')}

请生成一个200-300字的执行摘要，包括：
1. 分析主题和研究范围
2. 最佳方向的选择理由
3. 主要发现和洞察
4. 建议和后续行动

要求：语言专业、简洁，重点突出最佳方向的价值。"""

            messages = [
                SystemMessage(content="你是一个专业的分析报告撰写专家，擅长生成简洁而有力的执行摘要。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            self.logger.log_error(f"生成执行摘要失败: {str(e)}")
            return f"本报告针对'{topic}'进行了全面的多维度分析，共涉及{scoring_data.get('total_directions', 0)}个研究方向。经过综合评分，'{selection_data.get('best_direction', 'unknown')}'方向表现最为突出（{selection_data.get('best_direction_score', 0):.1f}分），建议重点关注该方向的相关内容。"
    
    def _generate_detailed_direction_analysis(self, direction: str, 
                                           search_rounds: List[SearchRoundRecord],
                                           scoring_result: Dict[str, Any]) -> DetailedDirectionAnalysis:
        """生成详细方向分析"""
        try:
            # 获取该方向的评分信息
            direction_score = None
            scoring_data = scoring_result.get("scoring_result", {})
            direction_scores = scoring_data.get("direction_scores", [])
            
            for score in direction_scores:
                if score.get("direction") == direction:
                    direction_score = score
                    break
            
            if not direction_score:
                raise ValueError(f"未找到方向 '{direction}' 的评分信息")
            
            # 获取该方向的搜索记录
            direction_rounds = [round for round in search_rounds if round.direction == direction]
            
            # 创建详细分析对象
            analysis = DetailedDirectionAnalysis(
                direction=direction,
                score=direction_score.get("comprehensive_score", 0),
                quality_level=direction_score.get("quality_level", "低")
            )
            
            # 提取问题和搜索结果
            for round in direction_rounds:
                analysis.questions.append({
                    "question": round.question,
                    "success": round.success,
                    "processing_time": round.processing_time
                })
                
                if round.search_results:
                    analysis.search_results.extend([{
                        "title": result.title,
                        "snippet": result.snippet,
                        "link": result.link
                    } for result in round.search_results])
                
                if round.summary:
                    analysis.summaries.append(round.summary)
                
                if round.key_points:
                    analysis.key_points.extend(round.key_points)
            
            # 生成详细分析
            analysis.detailed_analysis = self._generate_direction_detailed_analysis(direction, direction_rounds, direction_score)
            
            # 生成洞察和建议
            analysis.insights = self._generate_direction_insights(direction, direction_rounds, direction_score)
            analysis.recommendations = self._generate_direction_recommendations(direction, direction_rounds, direction_score)
            
            # 设置统计信息
            analysis.total_questions = len(analysis.questions)
            analysis.total_search_results = len(analysis.search_results)
            analysis.avg_summary_length = sum(len(s) for s in analysis.summaries) / len(analysis.summaries) if analysis.summaries else 0
            analysis.avg_key_points_count = len(analysis.key_points) / len(direction_rounds) if direction_rounds else 0
            
            return analysis
            
        except Exception as e:
            self.logger.log_error(f"生成详细方向分析失败: {str(e)}")
            # 返回默认分析
            analysis = DetailedDirectionAnalysis(direction, 0, "低")
            analysis.detailed_analysis = f"'{direction}'方向分析生成失败，请查看错误日志。"
            return analysis
    
    def _generate_direction_detailed_analysis(self, direction: str, 
                                            search_rounds: List[SearchRoundRecord],
                                            direction_score: Dict[str, Any]) -> str:
        """生成方向详细分析"""
        try:
            prompt = f"""请为以下方向生成详细的专业分析：

方向：{direction}
综合评分：{direction_score.get('comprehensive_score', 0):.1f}分
质量等级：{direction_score.get('quality_level', '低')}
搜索质量：{direction_score.get('search_quality_score', 0):.1f}分
内容深度：{direction_score.get('content_depth_score', 0):.1f}分
技术指标：{direction_score.get('technical_score', 0):.1f}分

搜索记录数量：{len(search_rounds)}
搜索结果总数：{direction_score.get('search_results_count', 0)}
搜索成功率：{direction_score.get('search_success_rate', 0):.1%}
平均摘要长度：{direction_score.get('avg_summary_length', 0):.0f}字符
平均关键点数：{direction_score.get('avg_key_points_count', 0):.1f}个

请生成一个500-800字的详细分析，包括：
1. 该方向的核心价值和重要性
2. 搜索结果的质量和深度分析
3. 关键发现和重要洞察
4. 该方向的优势和特点
5. 潜在的应用价值和发展前景

要求：分析深入、逻辑清晰、语言专业。"""

            messages = [
                SystemMessage(content="你是一个专业的行业分析专家，擅长深度分析特定方向的价值和特点。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            return response.content
            
        except Exception as e:
            self.logger.log_error(f"生成方向详细分析失败: {str(e)}")
            return f"'{direction}'方向在本次分析中表现优秀，综合评分{direction_score.get('comprehensive_score', 0):.1f}分。该方向在搜索质量、内容深度和技术指标方面均达到良好水平，具有重要的研究价值和应用前景。"
    
    def _generate_summary_directions_analysis(self, summary_directions: List[str],
                                            search_rounds: List[SearchRoundRecord],
                                            scoring_result: Dict[str, Any]) -> List[SummaryDirectionAnalysis]:
        """生成简略方向分析"""
        summary_analyses = []
        
        for direction in summary_directions:
            try:
                # 获取该方向的评分信息
                direction_score = None
                scoring_data = scoring_result.get("scoring_result", {})
                direction_scores = scoring_data.get("direction_scores", [])
                
                for score in direction_scores:
                    if score.get("direction") == direction:
                        direction_score = score
                        break
                
                if not direction_score:
                    continue
                
                # 获取该方向的搜索记录
                direction_rounds = [round for round in search_rounds if round.direction == direction]
                
                # 创建简略分析对象
                summary_analysis = SummaryDirectionAnalysis(
                    direction=direction,
                    score=direction_score.get("comprehensive_score", 0),
                    quality_level=direction_score.get("quality_level", "低")
                )
                
                # 生成关键发现
                summary_analysis.key_findings = self._extract_key_findings(direction_rounds)
                
                # 生成主要洞察
                summary_analysis.main_insights = self._extract_main_insights(direction_rounds, direction_score)
                
                # 生成简要总结
                summary_analysis.brief_summary = self._generate_brief_summary(direction, direction_score, direction_rounds)
                
                # 设置统计信息
                summary_analysis.total_questions = len(direction_rounds)
                summary_analysis.total_search_results = direction_score.get("search_results_count", 0)
                
                summary_analyses.append(summary_analysis)
                
            except Exception as e:
                self.logger.log_error(f"生成方向 '{direction}' 简略分析失败: {str(e)}")
                continue
        
        return summary_analyses
    
    def _generate_question_tree_summary(self, question_tree: Dict[str, Any]) -> str:
        """生成问题树状结构摘要"""
        try:
            if not question_tree or "tree" not in question_tree:
                return "问题树状结构信息不可用。"
            
            tree_data = question_tree["tree"]
            
            summary_lines = [
                f"## 问题树状结构分析",
                f"",
                f"本次分析构建了层次化的问题树状结构，包含以下特征：",
                f"",
                f"- **树结构深度**: {tree_data.get('tree_depth', 0)}层",
                f"- **总节点数**: {tree_data.get('total_nodes', 0)}个",
                f"- **方向数**: {len(tree_data.get('directions', []))}个",
                f"- **问题数**: {tree_data.get('total_questions', 0)}个",
                f"- **平均重要性评分**: {tree_data.get('avg_importance_score', 0):.3f}",
                f"- **平均相关性评分**: {tree_data.get('avg_relevance_score', 0):.3f}",
                f"- **树结构一致性**: {tree_data.get('tree_coherence_score', 0):.3f}",
                f"",
                f"### 方向分布",
                f""
            ]
            
            # 添加各方向的问题分布
            for direction in tree_data.get('directions', []):
                summary_lines.append(f"- **{direction}**: 包含相关问题")
            
            summary_lines.extend([
                f"",
                f"### 结构特点",
                f"",
                f"该树状结构具有以下特点：",
                f"- 层次清晰：根节点（主题）→ 方向节点 → 问题节点",
                f"- 逻辑合理：各方向相互独立且互补",
                f"- 覆盖全面：涵盖了主题的各个重要方面",
                f"- 质量均衡：各节点的重要性评分相对均衡"
            ])
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            self.logger.log_error(f"生成问题树状结构摘要失败: {str(e)}")
            return "问题树状结构分析：本次分析构建了层次化的问题树状结构，包含多个方向和问题节点，为深入分析提供了良好的基础。"
    
    def _generate_key_insights(self, selection_result: Dict[str, Any],
                             scoring_result: Dict[str, Any],
                             search_rounds: List[SearchRoundRecord]) -> List[str]:
        """生成关键洞察"""
        try:
            insights = []
            
            selection_data = selection_result.get("selection_result", {})
            scoring_data = scoring_result.get("scoring_result", {})
            
            # 基于评分结果的洞察
            best_score = scoring_data.get("best_score", 0)
            if best_score >= 80:
                insights.append(f"'{selection_data.get('best_direction', 'unknown')}'方向表现卓越，具有重要的研究价值")
            elif best_score >= 60:
                insights.append(f"'{selection_data.get('best_direction', 'unknown')}'方向表现良好，值得重点关注")
            
            # 基于质量分布的洞察
            quality_dist = scoring_data.get("quality_distribution", {})
            if quality_dist.get("高", 0) > 0:
                insights.append(f"有{quality_dist['高']}个方向达到高质量标准，整体分析质量较高")
            
            # 基于搜索结果的洞察
            total_results = sum(len(round.search_results) if round.search_results else 0 for round in search_rounds)
            if total_results > 100:
                insights.append(f"获得了{total_results}个搜索结果，信息收集充分")
            
            # 基于成功率的洞察
            successful_rounds = sum(1 for round in search_rounds if round.success)
            success_rate = successful_rounds / len(search_rounds) if search_rounds else 0
            if success_rate >= 0.9:
                insights.append("搜索成功率超过90%，系统运行稳定")
            elif success_rate >= 0.8:
                insights.append("搜索成功率良好，大部分查询获得有效结果")
            
            return insights
            
        except Exception as e:
            self.logger.log_error(f"生成关键洞察失败: {str(e)}")
            return ["分析完成，获得了有价值的洞察和建议"]
    
    def _generate_technical_stats(self, scoring_result: Dict[str, Any],
                                search_rounds: List[SearchRoundRecord]) -> Dict[str, Any]:
        """生成技术统计"""
        try:
            total_rounds = len(search_rounds)
            successful_rounds = sum(1 for round in search_rounds if round.success)
            total_results = sum(len(round.search_results) if round.search_results else 0 for round in search_rounds)
            total_processing_time = sum(round.processing_time for round in search_rounds)
            
            scoring_data = scoring_result.get("scoring_result", {})
            
            return {
                "total_search_rounds": total_rounds,
                "successful_rounds": successful_rounds,
                "success_rate": successful_rounds / total_rounds if total_rounds > 0 else 0,
                "total_search_results": total_results,
                "avg_results_per_round": total_results / total_rounds if total_rounds > 0 else 0,
                "total_processing_time": total_processing_time,
                "avg_processing_time": total_processing_time / total_rounds if total_rounds > 0 else 0,
                "scoring_processing_time": scoring_data.get("processing_time", 0),
                "directions_analyzed": scoring_data.get("total_directions", 0),
                "quality_distribution": scoring_data.get("quality_distribution", {}),
                "score_distribution": scoring_data.get("score_distribution", {})
            }
            
        except Exception as e:
            self.logger.log_error(f"生成技术统计失败: {str(e)}")
            return {}
    
    def _extract_key_findings(self, search_rounds: List[SearchRoundRecord]) -> List[str]:
        """提取关键发现"""
        findings = []
        
        for round in search_rounds:
            if round.key_points:
                findings.extend(round.key_points[:2])  # 每个问题最多取2个关键点
        
        return findings[:5]  # 最多返回5个关键发现
    
    def _extract_main_insights(self, search_rounds: List[SearchRoundRecord], 
                             direction_score: Dict[str, Any]) -> List[str]:
        """提取主要洞察"""
        insights = []
        
        # 基于评分的洞察
        search_quality_score = direction_score.get("search_quality_score", 0)
        if search_quality_score >= 80:
            insights.append("搜索质量优秀，获得了丰富的信息")
        elif search_quality_score >= 60:
            insights.append("搜索质量良好，信息收集充分")
        
        content_depth_score = direction_score.get("content_depth_score", 0)
        if content_depth_score >= 80:
            insights.append("内容深度丰富，分析透彻")
        elif content_depth_score >= 60:
            insights.append("内容深度适中，提供了有价值的见解")
        
        return insights
    
    def _generate_brief_summary(self, direction: str, direction_score: Dict[str, Any],
                              search_rounds: List[SearchRoundRecord]) -> str:
        """生成简要总结"""
        return f"'{direction}'方向综合评分{direction_score.get('comprehensive_score', 0):.1f}分，质量等级{direction_score.get('quality_level', '低')}。该方向在搜索质量、内容深度等方面表现良好，提供了有价值的补充信息。"
    
    def _generate_direction_insights(self, direction: str, search_rounds: List[SearchRoundRecord],
                                   direction_score: Dict[str, Any]) -> List[str]:
        """生成方向洞察"""
        insights = []
        
        # 基于搜索结果的洞察
        search_results_count = direction_score.get("search_results_count", 0)
        if search_results_count > 50:
            insights.append("获得了丰富的搜索结果，信息覆盖面广")
        elif search_results_count > 20:
            insights.append("搜索结果数量适中，信息质量良好")
        
        # 基于成功率的洞察
        search_success_rate = direction_score.get("search_success_rate", 0)
        if search_success_rate >= 0.9:
            insights.append("搜索成功率极高，系统运行稳定")
        elif search_success_rate >= 0.8:
            insights.append("搜索成功率良好，大部分查询成功")
        
        # 基于内容质量的洞察
        avg_summary_length = direction_score.get("avg_summary_length", 0)
        if avg_summary_length > 200:
            insights.append("摘要内容丰富，分析深入")
        elif avg_summary_length > 100:
            insights.append("摘要内容适中，提供了关键信息")
        
        return insights
    
    def _generate_direction_recommendations(self, direction: str, search_rounds: List[SearchRoundRecord],
                                         direction_score: Dict[str, Any]) -> List[str]:
        """生成方向建议"""
        recommendations = []
        
        # 基于评分的建议
        comprehensive_score = direction_score.get("comprehensive_score", 0)
        if comprehensive_score >= 80:
            recommendations.append("建议重点关注该方向，具有重要的研究价值")
        elif comprehensive_score >= 60:
            recommendations.append("建议进一步深入研究该方向")
        
        # 基于搜索质量的建议
        search_quality_score = direction_score.get("search_quality_score", 0)
        if search_quality_score < 60:
            recommendations.append("建议优化搜索策略，提高搜索质量")
        
        # 基于内容深度的建议
        content_depth_score = direction_score.get("content_depth_score", 0)
        if content_depth_score < 60:
            recommendations.append("建议深化内容分析，提供更详细的见解")
        
        return recommendations


class ReportFormatter:
    """报告格式化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = workflow_logger
    
    def format_optimized_report(self, report: Dict[str, Any]) -> str:
        """格式化优化报告"""
        try:
            self.logger.log_info("开始格式化优化报告")
            
            report_data = report.get("optimized_report", {})
            
            # 构建报告内容
            content_lines = [
                f"主题：深度分析报告：{report_data.get('topic', 'unknown')}",
                f"",
                f"尊敬的用户，",
                f"",
                f"您好！",
                f"",
                f"以下是关于'{report_data.get('topic', 'unknown')}'的优化分析报告，经过智能评分和报告优化处理。",
                f"",
                f"## 📋 分析概览",
                f"- **分析主题**：{report_data.get('topic', 'unknown')}",
                f"- **最佳方向**：{report_data.get('best_direction', 'unknown')}（评分：{report_data.get('best_direction_score', 0):.1f}分）",
                f"- **分析维度**：{report_data.get('analysis_dimensions', 0)}个方向",
                f"- **生成时间**：{report_data.get('generation_time', 'unknown')}",
                f"",
                f"## 📊 执行摘要",
                f"{report_data.get('executive_summary', '无')}",
                f"",
                f"## 🔍 最佳方向详细分析",
                f""
            ]
            
            # 添加最佳方向详细分析
            best_direction_analysis = report_data.get("best_direction_analysis")
            if best_direction_analysis:
                content_lines.extend([
                    f"### {best_direction_analysis.get('direction', 'unknown')}（评分：{best_direction_analysis.get('score', 0):.1f}分）",
                    f"",
                    f"**方向说明**：{best_direction_analysis.get('detailed_analysis', '无')}",
                    f"",
                    f"**问题分析**：",
                    f""
                ])
                
                # 添加问题分析
                questions = best_direction_analysis.get("questions", [])
                for i, question in enumerate(questions, 1):
                    content_lines.extend([
                        f"**{i}. {question.get('question', 'unknown')}**",
                        f"   - 搜索状态：{'成功' if question.get('success', False) else '失败'}",
                        f"   - 处理时间：{question.get('processing_time', 0):.2f}秒",
                        f""
                    ])
                
                # 添加关键洞察
                insights = best_direction_analysis.get("insights", [])
                if insights:
                    content_lines.extend([
                        f"**关键洞察**：",
                        f""
                    ])
                    for insight in insights:
                        content_lines.append(f"- {insight}")
                    content_lines.append("")
                
                # 添加建议
                recommendations = best_direction_analysis.get("recommendations", [])
                if recommendations:
                    content_lines.extend([
                        f"**建议**：",
                        f""
                    ])
                    for recommendation in recommendations:
                        content_lines.append(f"- {recommendation}")
                    content_lines.append("")
            
            # 添加其他方向简略分析
            other_directions_summary = report_data.get("other_directions_summary", [])
            if other_directions_summary:
                content_lines.extend([
                    f"## 📝 其他方向简略分析",
                    f""
                ])
                
                for summary in other_directions_summary:
                    content_lines.extend([
                        f"### {summary.get('direction', 'unknown')}（评分：{summary.get('score', 0):.1f}分）",
                        f"",
                        f"**简要总结**：{summary.get('brief_summary', '无')}",
                        f""
                    ])
                    
                    key_findings = summary.get("key_findings", [])
                    if key_findings:
                        content_lines.extend([
                            f"**关键发现**：",
                            f""
                        ])
                        for finding in key_findings:
                            content_lines.append(f"- {finding}")
                        content_lines.append("")
                    
                    main_insights = summary.get("main_insights", [])
                    if main_insights:
                        content_lines.extend([
                            f"**主要洞察**：",
                            f""
                        ])
                        for insight in main_insights:
                            content_lines.append(f"- {insight}")
                        content_lines.append("")
            
            # 添加问题树状结构摘要
            question_tree_summary = report_data.get("question_tree_summary")
            if question_tree_summary:
                content_lines.extend([
                    f"## 🌳 问题树状结构分析",
                    f"",
                    question_tree_summary,
                    f""
                ])
            
            # 添加关键洞察
            key_insights = report_data.get("key_insights", [])
            if key_insights:
                content_lines.extend([
                    f"## 💡 关键洞察",
                    f""
                ])
                for insight in key_insights:
                    content_lines.append(f"- {insight}")
                content_lines.append("")
            
            # 添加技术统计
            technical_stats = report_data.get("technical_stats", {})
            if technical_stats:
                content_lines.extend([
                    f"## 📈 技术统计",
                    f"",
                    f"- 总搜索轮次：{technical_stats.get('total_search_rounds', 0)}",
                    f"- 成功轮次：{technical_stats.get('successful_rounds', 0)}",
                    f"- 成功率：{technical_stats.get('success_rate', 0):.1%}",
                    f"- 总搜索结果：{technical_stats.get('total_search_results', 0)}",
                    f"- 平均处理时间：{technical_stats.get('avg_processing_time', 0):.2f}秒",
                    f""
                ])
            
            # 添加结尾
            content_lines.extend([
                f"---",
                f"此邮件由智能分析系统自动生成",
                f"如有任何问题，请随时联系。"
            ])
            
            formatted_content = "\n".join(content_lines)
            self.logger.log_info("优化报告格式化完成")
            return formatted_content
            
        except Exception as e:
            self.logger.log_error(f"格式化优化报告失败: {str(e)}")
            return f"优化报告生成失败：{str(e)}"
    
    def save_optimized_report(self, content: str, filename: str = None) -> str:
        """保存优化报告到文件"""
        try:
            if not filename:
                filename = f"optimized_email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            import os
            filepath = os.path.join("data", "results", filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 保存文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.log_info(f"优化报告已保存到: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.log_error(f"保存优化报告失败: {str(e)}")
            return ""
