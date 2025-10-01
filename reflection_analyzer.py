"""
反思机制 - 在时间满足前不断打磨和优化子问题
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
class ReflectionAnalysis:
    """反思分析结果"""
    # 质量分析
    overall_quality_score: float
    quality_trend: str  # "improving", "stable", "declining"
    improvement_potential: float
    
    # 问题分析
    question_effectiveness: List[Dict[str, Any]]
    weak_questions: List[str]
    strong_questions: List[str]
    missing_angles: List[str]
    
    # 搜索分析
    search_coverage: Dict[str, Any]
    result_diversity: float
    information_gaps: List[str]
    duplicate_content: float
    
    # 改进建议
    optimization_directions: List[str]
    priority_improvements: List[str]
    next_iteration_strategy: Dict[str, Any]
    
    # 元数据
    iteration_number: int
    analysis_timestamp: datetime
    confidence_score: float


class ReflectionAnalyzer:
    """反思分析器 - 分析当前迭代结果并生成改进建议"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=0.3,  # 较低温度确保分析的一致性
            max_tokens=2000
        )
        
        # 反思配置
        self.reflection_config = config.get('reflection', {
            "quality_thresholds": {
                "excellent": 0.85,
                "good": 0.70,
                "fair": 0.55,
                "poor": 0.40
            },
            "improvement_threshold": 0.05,
            "diversity_threshold": 0.7,
            "max_analysis_depth": 3
        })
    
    def analyze_iteration_results(self, state: Dict[str, Any]) -> ReflectionAnalysis:
        """分析当前迭代结果"""
        workflow_logger.log_info("开始反思分析", "ReflectionAnalyzer")
        
        try:
            # 1. 收集分析数据
            analysis_data = self._collect_analysis_data(state)
            
            # 2. 执行质量分析
            quality_analysis = self._analyze_quality(analysis_data)
            
            # 3. 执行问题分析
            question_analysis = self._analyze_questions(analysis_data)
            
            # 4. 执行搜索分析
            search_analysis = self._analyze_search_results(analysis_data)
            
            # 5. 生成改进建议
            improvement_suggestions = self._generate_improvement_suggestions(
                quality_analysis, question_analysis, search_analysis
            )
            
            # 6. 构建反思分析结果
            reflection_analysis = ReflectionAnalysis(
                overall_quality_score=quality_analysis['overall_score'],
                quality_trend=quality_analysis['trend'],
                improvement_potential=quality_analysis['improvement_potential'],
                
                question_effectiveness=question_analysis['effectiveness'],
                weak_questions=question_analysis['weak_questions'],
                strong_questions=question_analysis['strong_questions'],
                missing_angles=question_analysis['missing_angles'],
                
                search_coverage=search_analysis['coverage'],
                result_diversity=search_analysis['diversity'],
                information_gaps=search_analysis['gaps'],
                duplicate_content=search_analysis['duplicate_rate'],
                
                optimization_directions=improvement_suggestions['directions'],
                priority_improvements=improvement_suggestions['priorities'],
                next_iteration_strategy=improvement_suggestions['strategy'],
                
                iteration_number=state.get('current_iteration', 0),
                analysis_timestamp=datetime.now(),
                confidence_score=self._calculate_confidence_score(analysis_data)
            )
            
            workflow_logger.log_info(f"反思分析完成，质量分数: {reflection_analysis.overall_quality_score:.3f}", "ReflectionAnalyzer")
            return reflection_analysis
            
        except Exception as e:
            workflow_logger.log_error(f"反思分析失败: {str(e)}", "ReflectionAnalyzer")
            # 返回默认分析结果
            return self._create_default_analysis(state)
    
    def _collect_analysis_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """收集分析数据"""
        return {
            "current_iteration": state.get('current_iteration', 0),
            "total_iterations": state.get('max_iterations', 100),
            "elapsed_time": state.get('elapsed_time', 0),
            "remaining_time": state.get('remaining_time', 0),
            
            "questions": state.get('questions', []),
            "search_results": state.get('search_results', []),
            "accumulated_results": state.get('accumulated_results', []),
            
            "quality_scores": state.get('quality_scores', []),
            "search_errors": state.get('search_errors', []),
            
            "topic": state.get('topic', ''),
            "time_strategy": state.get('time_strategy', 'adaptive')
        }
    
    def _analyze_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析质量趋势"""
        quality_scores = data.get('quality_scores', [])
        
        if not quality_scores:
            return {
                "overall_score": 0.0,
                "trend": "unknown",
                "improvement_potential": 1.0,
                "score_history": []
            }
        
        scores = [score['score'] for score in quality_scores]
        current_score = scores[-1] if scores else 0.0
        
        # 计算趋势
        if len(scores) >= 3:
            recent_scores = scores[-3:]
            trend_value = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            if trend_value > 0.02:
                trend = "improving"
            elif trend_value < -0.02:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # 计算改进潜力
        max_possible_score = 1.0
        improvement_potential = max(0.0, max_possible_score - current_score)
        
        return {
            "overall_score": current_score,
            "trend": trend,
            "improvement_potential": improvement_potential,
            "score_history": scores
        }
    
    def _analyze_questions(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析问题效果"""
        questions = data.get('questions', [])
        search_results = data.get('search_results', [])
        
        if not questions:
            return {
                "effectiveness": [],
                "weak_questions": [],
                "strong_questions": [],
                "missing_angles": []
            }
        
        # 分析每个问题的效果
        effectiveness = []
        weak_questions = []
        strong_questions = []
        
        for question in questions:
            question_text = question.get('question', '') if isinstance(question, dict) else str(question)
            
            # 找到对应的搜索结果
            question_results = []
            for result in search_results:
                if result.get('question', '') == question_text:
                    question_results.append(result)
            
            # 评估问题效果
            effectiveness_score = self._evaluate_question_effectiveness(question_text, question_results)
            
            effectiveness.append({
                "question": question_text,
                "effectiveness_score": effectiveness_score,
                "result_count": len(question_results),
                "quality_indicators": self._extract_quality_indicators(question_results)
            })
            
            if effectiveness_score < 0.5:
                weak_questions.append(question_text)
            elif effectiveness_score > 0.8:
                strong_questions.append(question_text)
        
        # 识别缺失角度
        missing_angles = self._identify_missing_angles(questions, search_results)
        
        return {
            "effectiveness": effectiveness,
            "weak_questions": weak_questions,
            "strong_questions": strong_questions,
            "missing_angles": missing_angles
        }
    
    def _analyze_search_results(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析搜索结果"""
        search_results = data.get('search_results', [])
        accumulated_results = data.get('accumulated_results', [])
        
        if not search_results:
            return {
                "coverage": {},
                "diversity": 0.0,
                "gaps": [],
                "duplicate_rate": 0.0
            }
        
        # 分析覆盖度
        coverage = self._analyze_coverage(search_results)
        
        # 分析多样性
        diversity = self._calculate_diversity(search_results)
        
        # 识别信息缺口
        gaps = self._identify_information_gaps(search_results, data.get('topic', ''))
        
        # 计算重复率
        duplicate_rate = self._calculate_duplicate_rate(search_results, accumulated_results)
        
        return {
            "coverage": coverage,
            "diversity": diversity,
            "gaps": gaps,
            "duplicate_rate": duplicate_rate
        }
    
    def _evaluate_question_effectiveness(self, question: str, results: List[Dict[str, Any]]) -> float:
        """评估问题效果"""
        if not results:
            return 0.0
        
        # 基于结果数量和质量评估
        result_count_score = min(1.0, len(results) / 5.0)  # 5个结果为满分
        
        # 基于结果质量评估
        quality_scores = []
        for result in results:
            summaries = result.get('summaries', [])
            key_points = result.get('key_points', [])
            
            # 简单质量评估
            summary_quality = len(summaries) > 0 and len(summaries[0]) > 50
            key_points_quality = len(key_points) > 0
            
            quality_score = (summary_quality + key_points_quality) / 2
            quality_scores.append(quality_score)
        
        avg_quality_score = np.mean(quality_scores) if quality_scores else 0.0
        
        # 综合评分
        effectiveness_score = (result_count_score + avg_quality_score) / 2
        
        return effectiveness_score
    
    def _extract_quality_indicators(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取质量指标"""
        if not results:
            return {}
        
        total_results = len(results)
        total_summaries = sum(len(result.get('summaries', [])) for result in results)
        total_key_points = sum(len(result.get('key_points', [])) for result in results)
        
        return {
            "total_results": total_results,
            "total_summaries": total_summaries,
            "total_key_points": total_key_points,
            "avg_summaries_per_result": total_summaries / total_results if total_results > 0 else 0,
            "avg_key_points_per_result": total_key_points / total_results if total_results > 0 else 0
        }
    
    def _identify_missing_angles(self, questions: List[Any], results: List[Dict[str, Any]]) -> List[str]:
        """识别缺失的研究角度"""
        # 使用LLM分析缺失角度
        try:
            question_texts = []
            for q in questions:
                if isinstance(q, dict):
                    question_texts.append(q.get('question', ''))
                else:
                    question_texts.append(str(q))
            
            result_summaries = []
            for result in results:
                summaries = result.get('summaries', [])
                if summaries:
                    result_summaries.append(summaries[0][:200])  # 取前200字符
            
            prompt = f"""
            基于以下问题和搜索结果，分析还缺少哪些重要的研究角度：
            
            已研究的问题：
            {chr(10).join(f"- {q}" for q in question_texts[:10])}
            
            搜索结果摘要：
            {chr(10).join(f"- {s}" for s in result_summaries[:5])}
            
            请识别3-5个缺失的重要研究角度，每个角度用一句话描述。
            """
            
            messages = [
                SystemMessage(content="你是一个研究分析专家，能够识别研究中的盲点和缺失角度。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            missing_angles_text = response.content.strip()
            
            # 解析缺失角度
            missing_angles = []
            lines = missing_angles_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('-', '•', '1.', '2.', '3.', '4.', '5.'))):
                    # 清理格式
                    angle = line.lstrip('-•123456789. ').strip()
                    if angle:
                        missing_angles.append(angle)
            
            return missing_angles[:5]  # 最多返回5个
            
        except Exception as e:
            workflow_logger.log_error(f"缺失角度识别失败: {str(e)}")
            return []
    
    def _analyze_coverage(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析搜索覆盖度"""
        if not results:
            return {}
        
        # 分析不同维度的覆盖情况
        topics_covered = set()
        sources_covered = set()
        
        for result in results:
            # 提取主题
            question = result.get('question', '')
            topics_covered.add(question)
            
            # 提取来源
            search_results = result.get('results', [])
            for sr in search_results:
                url = sr.get('url', '')
                if url:
                    domain = url.split('/')[2] if '/' in url else url
                    sources_covered.add(domain)
        
        return {
            "topics_covered": len(topics_covered),
            "sources_covered": len(sources_covered),
            "coverage_diversity": len(sources_covered) / max(len(topics_covered), 1)
        }
    
    def _calculate_diversity(self, results: List[Dict[str, Any]]) -> float:
        """计算结果多样性"""
        if not results:
            return 0.0
        
        # 基于问题类型的多样性
        question_types = set()
        for result in results:
            question = result.get('question', '')
            # 简单分类
            if any(word in question.lower() for word in ['什么', '如何', '为什么', '怎样']):
                question_types.add('what')
            elif any(word in question.lower() for word in ['如何', '怎样', '方法']):
                question_types.add('how')
            elif any(word in question.lower() for word in ['为什么', '原因', '因为']):
                question_types.add('why')
            else:
                question_types.add('other')
        
        diversity_score = len(question_types) / 4.0  # 4种类型为满分
        return min(1.0, diversity_score)
    
    def _identify_information_gaps(self, results: List[Dict[str, Any]], topic: str) -> List[str]:
        """识别信息缺口"""
        # 使用LLM分析信息缺口
        try:
            result_summaries = []
            for result in results[:5]:  # 只分析前5个结果
                summaries = result.get('summaries', [])
                if summaries:
                    result_summaries.append(summaries[0][:300])
            
            prompt = f"""
            基于主题"{topic}"和以下搜索结果，分析还缺少哪些重要信息：
            
            搜索结果摘要：
            {chr(10).join(f"- {s}" for s in result_summaries)}
            
            请识别3-5个重要的信息缺口，每个缺口用一句话描述。
            """
            
            messages = [
                SystemMessage(content="你是一个信息分析专家，能够识别研究中的信息缺口。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            gaps_text = response.content.strip()
            
            # 解析信息缺口
            gaps = []
            lines = gaps_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('-', '•', '1.', '2.', '3.', '4.', '5.'))):
                    gap = line.lstrip('-•123456789. ').strip()
                    if gap:
                        gaps.append(gap)
            
            return gaps[:5]
            
        except Exception as e:
            workflow_logger.log_error(f"信息缺口识别失败: {str(e)}")
            return []
    
    def _calculate_duplicate_rate(self, current_results: List[Dict[str, Any]], 
                                accumulated_results: List[Dict[str, Any]]) -> float:
        """计算重复率"""
        if not current_results or not accumulated_results:
            return 0.0
        
        # 简单的重复检测：基于问题文本
        current_questions = set()
        for result in current_results:
            question = result.get('question', '')
            current_questions.add(question)
        
        accumulated_questions = set()
        for result in accumulated_results:
            question = result.get('question', '')
            accumulated_questions.add(question)
        
        # 计算重复率
        duplicates = current_questions.intersection(accumulated_questions)
        duplicate_rate = len(duplicates) / len(current_questions) if current_questions else 0.0
        
        return duplicate_rate
    
    def _generate_improvement_suggestions(self, quality_analysis: Dict[str, Any], 
                                       question_analysis: Dict[str, Any], 
                                       search_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成改进建议"""
        suggestions = {
            "directions": [],
            "priorities": [],
            "strategy": {}
        }
        
        # 基于质量分析生成建议
        if quality_analysis['trend'] == 'declining':
            suggestions["priorities"].append("质量下降，需要调整搜索策略")
            suggestions["directions"].append("优化问题表达，提高搜索精准度")
        
        if quality_analysis['improvement_potential'] > 0.3:
            suggestions["priorities"].append("存在较大改进空间")
            suggestions["directions"].append("深化问题研究，增加搜索深度")
        
        # 基于问题分析生成建议
        if question_analysis['weak_questions']:
            suggestions["priorities"].append(f"发现{len(question_analysis['weak_questions'])}个低效问题")
            suggestions["directions"].append("重新设计低效问题，提高问题质量")
        
        if question_analysis['missing_angles']:
            suggestions["priorities"].append("发现研究盲点")
            suggestions["directions"].append("补充缺失的研究角度")
        
        # 基于搜索分析生成建议
        if search_analysis['diversity'] < 0.5:
            suggestions["directions"].append("提高搜索多样性")
        
        if search_analysis['duplicate_rate'] > 0.3:
            suggestions["directions"].append("减少重复搜索，提高效率")
        
        # 生成下一轮策略
        suggestions["strategy"] = self._generate_next_strategy(
            quality_analysis, question_analysis, search_analysis
        )
        
        return suggestions
    
    def _generate_next_strategy(self, quality_analysis: Dict[str, Any], 
                              question_analysis: Dict[str, Any], 
                              search_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成下一轮策略"""
        strategy = {
            "focus_areas": [],
            "optimization_priorities": [],
            "search_adjustments": {},
            "question_count": 15,  # 默认问题数量
            "search_depth": "medium"
        }
        
        # 基于质量趋势调整策略
        if quality_analysis['trend'] == 'improving':
            strategy["search_depth"] = "deep"
            strategy["question_count"] = 20
        elif quality_analysis['trend'] == 'declining':
            strategy["search_depth"] = "focused"
            strategy["question_count"] = 10
        
        # 基于问题分析调整策略
        if question_analysis['weak_questions']:
            strategy["focus_areas"].append("question_optimization")
            strategy["optimization_priorities"].append("improve_weak_questions")
        
        if question_analysis['missing_angles']:
            strategy["focus_areas"].append("angle_expansion")
            strategy["optimization_priorities"].append("add_missing_angles")
        
        # 基于搜索分析调整策略
        if search_analysis['diversity'] < 0.5:
            strategy["search_adjustments"]["increase_diversity"] = True
        
        if search_analysis['duplicate_rate'] > 0.3:
            strategy["search_adjustments"]["reduce_duplicates"] = True
        
        return strategy
    
    def _calculate_confidence_score(self, data: Dict[str, Any]) -> float:
        """计算分析置信度"""
        # 基于数据完整性和质量计算置信度
        confidence_factors = []
        
        # 数据完整性
        if data.get('questions'):
            confidence_factors.append(0.3)
        if data.get('search_results'):
            confidence_factors.append(0.3)
        if data.get('quality_scores'):
            confidence_factors.append(0.2)
        if data.get('accumulated_results'):
            confidence_factors.append(0.2)
        
        confidence_score = sum(confidence_factors)
        return min(1.0, confidence_score)
    
    def _create_default_analysis(self, state: Dict[str, Any]) -> ReflectionAnalysis:
        """创建默认分析结果"""
        return ReflectionAnalysis(
            overall_quality_score=0.5,
            quality_trend="unknown",
            improvement_potential=0.5,
            
            question_effectiveness=[],
            weak_questions=[],
            strong_questions=[],
            missing_angles=[],
            
            search_coverage={},
            result_diversity=0.5,
            information_gaps=[],
            duplicate_content=0.0,
            
            optimization_directions=["需要更多数据进行分析"],
            priority_improvements=["收集更多搜索结果"],
            next_iteration_strategy={"question_count": 15, "search_depth": "medium"},
            
            iteration_number=state.get('current_iteration', 0),
            analysis_timestamp=datetime.now(),
            confidence_score=0.3
        )
