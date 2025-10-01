"""
基于上下文反馈的反思机制 - 利用搜索结果和解决过程来优化策略
"""

import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from logger import workflow_logger


@dataclass
class SearchContext:
    """搜索上下文信息"""
    # 搜索过程信息
    search_queries: List[str]
    search_results: List[Dict[str, Any]]
    search_errors: List[str]
    search_timing: Dict[str, float]
    
    # 结果质量信息
    result_relevance_scores: List[float]
    result_diversity_score: float
    result_completeness_score: float
    
    # 问题解决过程
    problem_solving_steps: List[str]
    knowledge_gaps_identified: List[str]
    successful_patterns: List[str]
    failed_attempts: List[str]
    
    # 上下文元数据
    iteration_number: int
    topic: str
    timestamp: datetime


@dataclass
class ContextualReflection:
    """基于上下文的反思结果"""
    # 搜索效果分析
    search_effectiveness: Dict[str, Any]
    result_quality_assessment: Dict[str, Any]
    problem_coverage_analysis: Dict[str, Any]
    
    # 解决过程分析
    solving_process_analysis: Dict[str, Any]
    knowledge_gap_analysis: Dict[str, Any]
    pattern_recognition: Dict[str, Any]
    
    # 优化建议
    query_optimization_suggestions: List[str]
    search_strategy_adjustments: List[str]
    problem_refinement_suggestions: List[str]
    next_iteration_strategy: Dict[str, Any]
    
    # 学习收获
    learned_patterns: List[str]
    successful_strategies: List[str]
    avoid_patterns: List[str]
    
    # 元数据
    confidence_score: float
    analysis_timestamp: datetime


class ContextualReflectionAnalyzer:
    """基于上下文反馈的反思分析器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=0.2,  # 较低温度确保分析的一致性
            max_tokens=3000
        )
        
        # 反思配置
        self.reflection_config = config.get('contextual_reflection', {
            "min_results_for_analysis": 3,
            "quality_thresholds": {
                "excellent": 0.85,
                "good": 0.70,
                "fair": 0.55,
                "poor": 0.40
            },
            "context_extraction_depth": 3,
            "pattern_recognition_threshold": 0.7
        })
    
    def analyze_with_context(self, state: Dict[str, Any]) -> ContextualReflection:
        """基于上下文进行反思分析"""
        workflow_logger.log_info("开始基于上下文的反思分析", "ContextualReflectionAnalyzer")
        
        try:
            # 1. 提取搜索上下文
            search_context = self._extract_search_context(state)
            
            # 2. 分析搜索效果
            search_effectiveness = self._analyze_search_effectiveness(search_context)
            
            # 3. 分析结果质量
            result_quality = self._analyze_result_quality(search_context)
            
            # 4. 分析问题覆盖度
            coverage_analysis = self._analyze_problem_coverage(search_context)
            
            # 5. 分析解决过程
            solving_process = self._analyze_solving_process(search_context)
            
            # 6. 识别知识缺口
            knowledge_gaps = self._identify_knowledge_gaps(search_context)
            
            # 7. 识别成功模式
            patterns = self._recognize_patterns(search_context)
            
            # 8. 生成优化建议
            optimization_suggestions = self._generate_contextual_optimization_suggestions(
                search_context, search_effectiveness, result_quality, coverage_analysis
            )
            
            # 9. 构建反思结果
            reflection = ContextualReflection(
                search_effectiveness=search_effectiveness,
                result_quality_assessment=result_quality,
                problem_coverage_analysis=coverage_analysis,
                solving_process_analysis=solving_process,
                knowledge_gap_analysis=knowledge_gaps,
                pattern_recognition=patterns,
                query_optimization_suggestions=optimization_suggestions['query_optimizations'],
                search_strategy_adjustments=optimization_suggestions['strategy_adjustments'],
                problem_refinement_suggestions=optimization_suggestions['problem_refinements'],
                next_iteration_strategy=optimization_suggestions['next_strategy'],
                learned_patterns=patterns['successful_patterns'],
                successful_strategies=patterns['successful_strategies'],
                avoid_patterns=patterns['avoid_patterns'],
                confidence_score=self._calculate_confidence_score(search_context),
                analysis_timestamp=datetime.now()
            )
            
            workflow_logger.log_info(f"上下文反思分析完成，置信度: {reflection.confidence_score:.3f}", "ContextualReflectionAnalyzer")
            return reflection
            
        except Exception as e:
            workflow_logger.log_error(f"上下文反思分析失败: {str(e)}", "ContextualReflectionAnalyzer")
            return self._create_default_reflection(state)
    
    def _extract_search_context(self, state: Dict[str, Any]) -> SearchContext:
        """提取搜索上下文信息"""
        try:
            # 提取搜索查询
            search_queries = []
            search_results = []
            search_errors = []
            
            # 从搜索结果中提取信息
            for result in state.get('search_results', []):
                if isinstance(result, dict):
                    search_queries.append(result.get('query', ''))
                    search_results.append(result)
                    if result.get('error'):
                        search_errors.append(result.get('error'))
            
            # 计算结果质量分数
            result_relevance_scores = []
            for result in search_results:
                relevance_score = self._calculate_result_relevance(result, state.get('topic', ''))
                result_relevance_scores.append(relevance_score)
            
            # 分析问题解决过程
            problem_solving_steps = self._extract_problem_solving_steps(state)
            knowledge_gaps = self._extract_knowledge_gaps(state)
            successful_patterns = self._extract_successful_patterns(state)
            failed_attempts = self._extract_failed_attempts(state)
            
            return SearchContext(
                search_queries=search_queries,
                search_results=search_results,
                search_errors=search_errors,
                search_timing=self._extract_search_timing(state),
                result_relevance_scores=result_relevance_scores,
                result_diversity_score=self._calculate_diversity_score(search_results),
                result_completeness_score=self._calculate_completeness_score(search_results, state.get('topic', '')),
                problem_solving_steps=problem_solving_steps,
                knowledge_gaps_identified=knowledge_gaps,
                successful_patterns=successful_patterns,
                failed_attempts=failed_attempts,
                iteration_number=state.get('current_iteration', 0),
                topic=state.get('topic', ''),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            workflow_logger.log_error(f"搜索上下文提取失败: {str(e)}")
            return SearchContext(
                search_queries=[], search_results=[], search_errors=[],
                search_timing={}, result_relevance_scores=[], result_diversity_score=0.0,
                result_completeness_score=0.0, problem_solving_steps=[], knowledge_gaps_identified=[],
                successful_patterns=[], failed_attempts=[], iteration_number=0, topic="", timestamp=datetime.now()
            )
    
    def _analyze_search_effectiveness(self, context: SearchContext) -> Dict[str, Any]:
        """分析搜索效果"""
        try:
            # 计算搜索成功率
            total_searches = len(context.search_queries)
            successful_searches = len(context.search_results)
            error_rate = len(context.search_errors) / max(total_searches, 1)
            
            # 分析查询质量
            query_quality_scores = []
            for query in context.search_queries:
                quality_score = self._evaluate_query_quality(query, context.topic)
                query_quality_scores.append(quality_score)
            
            avg_query_quality = np.mean(query_quality_scores) if query_quality_scores else 0.0
            
            # 分析搜索效率
            search_efficiency = successful_searches / max(total_searches, 1)
            
            return {
                "total_searches": total_searches,
                "successful_searches": successful_searches,
                "error_rate": error_rate,
                "search_efficiency": search_efficiency,
                "avg_query_quality": avg_query_quality,
                "query_quality_scores": query_quality_scores,
                "effectiveness_score": (search_efficiency + avg_query_quality) / 2
            }
            
        except Exception as e:
            workflow_logger.log_error(f"搜索效果分析失败: {str(e)}")
            return {"effectiveness_score": 0.0}
    
    def _analyze_result_quality(self, context: SearchContext) -> Dict[str, Any]:
        """分析结果质量"""
        try:
            if not context.search_results:
                return {"quality_score": 0.0, "relevance_score": 0.0, "diversity_score": 0.0}
            
            # 计算平均相关性
            avg_relevance = np.mean(context.result_relevance_scores) if context.result_relevance_scores else 0.0
            
            # 计算多样性
            diversity_score = context.result_diversity_score
            
            # 计算完整性
            completeness_score = context.result_completeness_score
            
            # 综合质量分数
            overall_quality = (avg_relevance + diversity_score + completeness_score) / 3
            
            return {
                "quality_score": overall_quality,
                "relevance_score": avg_relevance,
                "diversity_score": diversity_score,
                "completeness_score": completeness_score,
                "result_count": len(context.search_results),
                "high_quality_results": sum(1 for score in context.result_relevance_scores if score > 0.8),
                "low_quality_results": sum(1 for score in context.result_relevance_scores if score < 0.4)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"结果质量分析失败: {str(e)}")
            return {"quality_score": 0.0}
    
    def _analyze_problem_coverage(self, context: SearchContext) -> Dict[str, Any]:
        """分析问题覆盖度"""
        try:
            # 使用LLM分析问题覆盖度
            prompt = f"""
            基于以下搜索上下文，分析问题覆盖度：
            
            主题：{context.topic}
            搜索查询：{', '.join(context.search_queries[:5])}
            搜索结果摘要：{self._get_results_summary(context.search_results[:3])}
            
            请分析：
            1. 当前搜索覆盖了主题的哪些方面？
            2. 还有哪些重要方面没有被覆盖？
            3. 搜索深度如何？
            4. 是否存在重复或冗余的搜索？
            
            请用JSON格式返回分析结果。
            """
            
            messages = [
                SystemMessage(content="你是一个搜索分析专家，能够评估搜索的覆盖度和完整性。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            coverage_analysis = self._parse_coverage_analysis(response.content)
            
            return coverage_analysis
            
        except Exception as e:
            workflow_logger.log_error(f"问题覆盖度分析失败: {str(e)}")
            return {"coverage_score": 0.0, "missing_aspects": [], "redundancy_score": 0.0}
    
    def _analyze_solving_process(self, context: SearchContext) -> Dict[str, Any]:
        """分析解决过程"""
        try:
            # 分析问题解决步骤的有效性
            step_effectiveness = []
            for step in context.problem_solving_steps:
                effectiveness = self._evaluate_step_effectiveness(step, context)
                step_effectiveness.append(effectiveness)
            
            # 分析成功模式
            successful_patterns = context.successful_patterns
            failed_patterns = context.failed_attempts
            
            # 计算解决过程质量
            process_quality = np.mean(step_effectiveness) if step_effectiveness else 0.0
            
            return {
                "process_quality": process_quality,
                "step_effectiveness": step_effectiveness,
                "successful_patterns": successful_patterns,
                "failed_patterns": failed_patterns,
                "problem_solving_steps": context.problem_solving_steps,
                "learning_efficiency": len(successful_patterns) / max(len(failed_patterns) + len(successful_patterns), 1)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"解决过程分析失败: {str(e)}")
            return {"process_quality": 0.0}
    
    def _identify_knowledge_gaps(self, context: SearchContext) -> Dict[str, Any]:
        """识别知识缺口"""
        try:
            # 使用LLM分析知识缺口
            prompt = f"""
            基于以下搜索上下文，识别知识缺口：
            
            主题：{context.topic}
            搜索结果：{self._get_results_summary(context.search_results)}
            已识别的缺口：{', '.join(context.knowledge_gaps_identified)}
            
            请分析：
            1. 当前搜索在哪些方面存在知识缺口？
            2. 哪些关键信息缺失？
            3. 需要补充哪些角度的搜索？
            4. 哪些概念需要进一步澄清？
            
            请用JSON格式返回分析结果。
            """
            
            messages = [
                SystemMessage(content="你是一个知识分析专家，能够识别研究中的知识缺口和盲点。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            gap_analysis = self._parse_gap_analysis(response.content)
            
            return gap_analysis
            
        except Exception as e:
            workflow_logger.log_error(f"知识缺口识别失败: {str(e)}")
            return {"knowledge_gaps": [], "gap_severity": 0.0}
    
    def _recognize_patterns(self, context: SearchContext) -> Dict[str, Any]:
        """识别成功和失败模式"""
        try:
            # 分析成功模式
            successful_patterns = []
            failed_patterns = []
            
            # 基于搜索结果质量识别模式
            for i, result in enumerate(context.search_results):
                if i < len(context.result_relevance_scores):
                    relevance_score = context.result_relevance_scores[i]
                    if relevance_score > 0.8:
                        # 高质量结果，分析成功模式
                        pattern = self._extract_success_pattern(result, context.search_queries[i])
                        if pattern:
                            successful_patterns.append(pattern)
                    elif relevance_score < 0.4:
                        # 低质量结果，分析失败模式
                        pattern = self._extract_failure_pattern(result, context.search_queries[i])
                        if pattern:
                            failed_patterns.append(pattern)
            
            return {
                "successful_patterns": successful_patterns,
                "failed_patterns": failed_patterns,
                "pattern_confidence": min(1.0, len(successful_patterns) / 3.0),
                "successful_strategies": self._extract_successful_strategies(successful_patterns),
                "avoid_patterns": self._extract_avoid_patterns(failed_patterns)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"模式识别失败: {str(e)}")
            return {"successful_patterns": [], "failed_patterns": []}
    
    def _generate_contextual_optimization_suggestions(self, context: SearchContext, 
                                                    search_effectiveness: Dict[str, Any],
                                                    result_quality: Dict[str, Any],
                                                    coverage_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文生成优化建议"""
        try:
            suggestions = {
                "query_optimizations": [],
                "strategy_adjustments": [],
                "problem_refinements": [],
                "next_strategy": {}
            }
            
            # 基于搜索效果生成查询优化建议
            if search_effectiveness.get('error_rate', 0) > 0.3:
                suggestions["query_optimizations"].append("减少搜索错误，优化查询表达")
            
            if search_effectiveness.get('avg_query_quality', 0) < 0.6:
                suggestions["query_optimizations"].append("提高查询质量，使用更具体的术语")
            
            # 基于结果质量生成策略调整建议
            if result_quality.get('diversity_score', 0) < 0.5:
                suggestions["strategy_adjustments"].append("增加搜索多样性，探索不同角度")
            
            if result_quality.get('completeness_score', 0) < 0.6:
                suggestions["strategy_adjustments"].append("提高搜索完整性，补充缺失信息")
            
            # 基于覆盖度分析生成问题优化建议
            missing_aspects = coverage_analysis.get('missing_aspects', [])
            if missing_aspects:
                suggestions["problem_refinements"].extend([
                    f"补充缺失角度: {aspect}" for aspect in missing_aspects[:3]
                ])
            
            # 生成下一轮策略
            suggestions["next_strategy"] = self._generate_next_iteration_strategy(
                context, search_effectiveness, result_quality, coverage_analysis
            )
            
            return suggestions
            
        except Exception as e:
            workflow_logger.log_error(f"优化建议生成失败: {str(e)}")
            return {"query_optimizations": [], "strategy_adjustments": [], "problem_refinements": [], "next_strategy": {}}
    
    # 辅助方法
    def _calculate_result_relevance(self, result: Dict[str, Any], topic: str) -> float:
        """计算结果相关性"""
        try:
            # 简单的相关性计算
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            content = f"{title} {snippet}".lower()
            
            topic_words = topic.lower().split()
            relevance_score = sum(1 for word in topic_words if word in content) / len(topic_words)
            
            return min(1.0, relevance_score)
            
        except Exception as e:
            return 0.0
    
    def _calculate_diversity_score(self, results: List[Dict[str, Any]]) -> float:
        """计算结果多样性"""
        try:
            if len(results) < 2:
                return 0.0
            
            # 基于URL域名的多样性
            domains = set()
            for result in results:
                url = result.get('url', '')
                if url:
                    domain = url.split('/')[2] if '/' in url else url
                    domains.add(domain)
            
            diversity_score = len(domains) / len(results)
            return min(1.0, diversity_score)
            
        except Exception as e:
            return 0.0
    
    def _calculate_completeness_score(self, results: List[Dict[str, Any]], topic: str) -> float:
        """计算结果完整性"""
        try:
            if not results:
                return 0.0
            
            # 基于结果数量和内容长度
            total_content_length = sum(len(str(result.get('snippet', ''))) for result in results)
            avg_content_length = total_content_length / len(results)
            
            # 简单的完整性评估
            completeness_score = min(1.0, avg_content_length / 200)  # 200字符为满分
            
            return completeness_score
            
        except Exception as e:
            return 0.0
    
    def _extract_problem_solving_steps(self, state: Dict[str, Any]) -> List[str]:
        """提取问题解决步骤"""
        # 从状态中提取问题解决步骤
        steps = []
        
        # 基于迭代历史提取步骤
        iteration_history = state.get('iteration_history', [])
        for iteration in iteration_history:
            if iteration.get('questions'):
                steps.append(f"生成问题: {len(iteration['questions'])}个")
            if iteration.get('search_results'):
                steps.append(f"执行搜索: {len(iteration['search_results'])}个结果")
            if iteration.get('quality_score'):
                steps.append(f"质量评估: {iteration['quality_score']:.3f}")
        
        return steps
    
    def _extract_knowledge_gaps(self, state: Dict[str, Any]) -> List[str]:
        """提取知识缺口"""
        gaps = []
        
        # 从反思历史中提取知识缺口
        reflection_history = state.get('reflection_history', [])
        for reflection in reflection_history:
            analysis = reflection.get('analysis')
            if analysis and hasattr(analysis, 'missing_angles'):
                gaps.extend(analysis.missing_angles)
        
        return list(set(gaps))  # 去重
    
    def _extract_successful_patterns(self, state: Dict[str, Any]) -> List[str]:
        """提取成功模式"""
        patterns = []
        
        # 基于高质量结果识别成功模式
        quality_scores = state.get('quality_scores', [])
        for score_data in quality_scores:
            if score_data.get('score', 0) > 0.8:
                patterns.append(f"高质量迭代: {score_data.get('iteration', 0)}")
        
        return patterns
    
    def _extract_failed_attempts(self, state: Dict[str, Any]) -> List[str]:
        """提取失败尝试"""
        failures = []
        
        # 基于搜索错误识别失败模式
        search_errors = state.get('search_errors', [])
        for error in search_errors:
            failures.append(f"搜索错误: {error}")
        
        return failures
    
    def _extract_search_timing(self, state: Dict[str, Any]) -> Dict[str, float]:
        """提取搜索时间信息"""
        return {
            "total_time": state.get('elapsed_time', 0),
            "avg_iteration_time": state.get('elapsed_time', 0) / max(state.get('current_iteration', 1), 1)
        }
    
    def _evaluate_query_quality(self, query: str, topic: str) -> float:
        """评估查询质量"""
        try:
            # 简单的查询质量评估
            quality_factors = []
            
            # 长度评估
            length_score = min(1.0, len(query) / 50)
            quality_factors.append(length_score * 0.3)
            
            # 相关性评估
            topic_words = topic.lower().split()
            query_words = query.lower().split()
            relevance_score = sum(1 for word in topic_words if word in query_words) / len(topic_words)
            quality_factors.append(relevance_score * 0.4)
            
            # 具体性评估
            specific_words = ['如何', '什么', '为什么', '怎样', '方法', '技术', '应用']
            specificity_score = sum(1 for word in specific_words if word in query) / len(specific_words)
            quality_factors.append(specificity_score * 0.3)
            
            return sum(quality_factors)
            
        except Exception as e:
            return 0.0
    
    def _get_results_summary(self, results: List[Dict[str, Any]]) -> str:
        """获取搜索结果摘要"""
        try:
            summaries = []
            for result in results[:3]:  # 只取前3个结果
                title = result.get('title', '')
                snippet = result.get('snippet', '')[:100]  # 限制长度
                summaries.append(f"{title}: {snippet}")
            
            return '; '.join(summaries)
            
        except Exception as e:
            return ""
    
    def _parse_coverage_analysis(self, content: str) -> Dict[str, Any]:
        """解析覆盖度分析结果"""
        try:
            # 尝试解析JSON
            if content.strip().startswith('{'):
                return json.loads(content)
            
            # 如果不是JSON，返回默认结果
            return {
                "coverage_score": 0.7,
                "missing_aspects": ["需要更多具体案例", "缺少技术细节"],
                "redundancy_score": 0.3
            }
            
        except Exception as e:
            return {"coverage_score": 0.5, "missing_aspects": [], "redundancy_score": 0.0}
    
    def _parse_gap_analysis(self, content: str) -> Dict[str, Any]:
        """解析缺口分析结果"""
        try:
            if content.strip().startswith('{'):
                return json.loads(content)
            
            return {
                "knowledge_gaps": ["技术实现细节", "实际应用案例"],
                "gap_severity": 0.6
            }
            
        except Exception as e:
            return {"knowledge_gaps": [], "gap_severity": 0.0}
    
    def _evaluate_step_effectiveness(self, step: str, context: SearchContext) -> float:
        """评估步骤有效性"""
        # 简单的步骤有效性评估
        if "高质量" in step:
            return 0.9
        elif "搜索错误" in step:
            return 0.2
        else:
            return 0.6
    
    def _extract_success_pattern(self, result: Dict[str, Any], query: str) -> str:
        """提取成功模式"""
        return f"查询'{query}'产生了高质量结果"
    
    def _extract_failure_pattern(self, result: Dict[str, Any], query: str) -> str:
        """提取失败模式"""
        return f"查询'{query}'产生了低质量结果"
    
    def _extract_successful_strategies(self, patterns: List[str]) -> List[str]:
        """提取成功策略"""
        strategies = []
        for pattern in patterns:
            if "高质量" in pattern:
                strategies.append("使用具体查询词")
        return strategies
    
    def _extract_avoid_patterns(self, patterns: List[str]) -> List[str]:
        """提取避免模式"""
        avoid_patterns = []
        for pattern in patterns:
            if "低质量" in pattern:
                avoid_patterns.append("避免模糊查询")
        return avoid_patterns
    
    def _generate_next_iteration_strategy(self, context: SearchContext, 
                                        search_effectiveness: Dict[str, Any],
                                        result_quality: Dict[str, Any],
                                        coverage_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成下一轮策略"""
        strategy = {
            "focus_areas": [],
            "search_adjustments": {},
            "query_optimization": {},
            "problem_expansion": []
        }
        
        # 基于分析结果调整策略
        if search_effectiveness.get('error_rate', 0) > 0.3:
            strategy["search_adjustments"]["reduce_errors"] = True
        
        if result_quality.get('diversity_score', 0) < 0.5:
            strategy["focus_areas"].append("increase_diversity")
        
        missing_aspects = coverage_analysis.get('missing_aspects', [])
        if missing_aspects:
            strategy["problem_expansion"] = missing_aspects[:3]
        
        return strategy
    
    def _calculate_confidence_score(self, context: SearchContext) -> float:
        """计算分析置信度"""
        confidence_factors = []
        
        # 基于数据完整性
        if context.search_results:
            confidence_factors.append(0.4)
        if context.search_queries:
            confidence_factors.append(0.3)
        if context.problem_solving_steps:
            confidence_factors.append(0.2)
        if context.knowledge_gaps_identified:
            confidence_factors.append(0.1)
        
        return sum(confidence_factors)
    
    def _create_default_reflection(self, state: Dict[str, Any]) -> ContextualReflection:
        """创建默认反思结果"""
        return ContextualReflection(
            search_effectiveness={"effectiveness_score": 0.5},
            result_quality_assessment={"quality_score": 0.5},
            problem_coverage_analysis={"coverage_score": 0.5},
            solving_process_analysis={"process_quality": 0.5},
            knowledge_gap_analysis={"knowledge_gaps": []},
            pattern_recognition={"successful_patterns": []},
            query_optimization_suggestions=["需要更多数据进行分析"],
            search_strategy_adjustments=["收集更多搜索结果"],
            problem_refinement_suggestions=["优化问题表达"],
            next_iteration_strategy={"focus_areas": []},
            learned_patterns=[],
            successful_strategies=[],
            avoid_patterns=[],
            confidence_score=0.3,
            analysis_timestamp=datetime.now()
        )
