"""
基于上下文反馈的问题优化器 - 利用搜索结果和解决过程来优化问题
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from logger import workflow_logger
from contextual_reflection_analyzer import ContextualReflection, SearchContext


class ContextualQuestionOptimizer:
    """基于上下文反馈的问题优化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=0.3,  # 适中的创造性
            max_tokens=2000
        )
        
        # 优化配置
        self.optimization_config = config.get('contextual_optimization', {
            "quality_thresholds": {
                "excellent": 0.85,
                "good": 0.70,
                "fair": 0.55,
                "poor": 0.40
            },
            "context_weight": 0.7,  # 上下文权重
            "max_questions_per_iteration": 25,
            "min_questions_per_iteration": 5
        })
    
    def optimize_questions_with_context(self, questions: List[Dict[str, Any]], 
                                     reflection: ContextualReflection,
                                     search_context: SearchContext,
                                     topic: str) -> List[Dict[str, Any]]:
        """基于上下文反馈优化问题"""
        workflow_logger.log_info(f"开始基于上下文优化 {len(questions)} 个问题", "ContextualQuestionOptimizer")
        
        try:
            optimized_questions = []
            
            # 1. 分析当前问题与搜索上下文的匹配度
            question_context_analysis = self._analyze_question_context_match(questions, search_context)
            
            # 2. 基于反思结果优化问题
            for i, question in enumerate(questions):
                context_match = question_context_analysis[i]
                optimization_strategy = self._determine_contextual_optimization_strategy(
                    question, reflection, search_context, context_match
                )
                
                if optimization_strategy == "context_enhance":
                    optimized = self._enhance_question_with_context(question, reflection, search_context, topic, context_match)
                elif optimization_strategy == "context_refine":
                    optimized = self._refine_question_with_context(question, reflection, search_context, topic, context_match)
                elif optimization_strategy == "context_expand":
                    optimized = self._expand_question_with_context(question, reflection, search_context, topic, context_match)
                else:
                    optimized = question  # 保持原样
                
                optimized_questions.append(optimized)
            
            # 3. 基于知识缺口补充问题
            gap_based_questions = self._generate_gap_based_questions(reflection, search_context, topic)
            optimized_questions.extend(gap_based_questions)
            
            # 4. 基于成功模式优化问题
            pattern_based_questions = self._generate_pattern_based_questions(reflection, search_context, topic)
            optimized_questions.extend(pattern_based_questions)
            
            # 5. 限制问题数量
            max_questions = self.optimization_config.get('max_questions_per_iteration', 25)
            optimized_questions = optimized_questions[:max_questions]
            
            workflow_logger.log_info(f"上下文问题优化完成，优化后问题数: {len(optimized_questions)}", "ContextualQuestionOptimizer")
            return optimized_questions
            
        except Exception as e:
            workflow_logger.log_error(f"上下文问题优化失败: {str(e)}", "ContextualQuestionOptimizer")
            return questions  # 返回原问题
    
    def _analyze_question_context_match(self, questions: List[Dict[str, Any]], 
                                      search_context: SearchContext) -> List[Dict[str, Any]]:
        """分析问题与搜索上下文的匹配度"""
        analyses = []
        
        for question in questions:
            question_text = question.get('question', '') if isinstance(question, dict) else str(question)
            
            # 分析问题与搜索查询的匹配度
            query_match_score = self._calculate_query_match_score(question_text, search_context.search_queries)
            
            # 分析问题与搜索结果的相关性
            result_relevance_score = self._calculate_result_relevance_score(question_text, search_context.search_results)
            
            # 分析问题是否覆盖了知识缺口
            gap_coverage_score = self._calculate_gap_coverage_score(question_text, search_context.knowledge_gaps_identified)
            
            # 分析问题是否利用了成功模式
            pattern_utilization_score = self._calculate_pattern_utilization_score(question_text, search_context.successful_patterns)
            
            analysis = {
                "question": question_text,
                "query_match_score": query_match_score,
                "result_relevance_score": result_relevance_score,
                "gap_coverage_score": gap_coverage_score,
                "pattern_utilization_score": pattern_utilization_score,
                "overall_context_score": (query_match_score + result_relevance_score + gap_coverage_score + pattern_utilization_score) / 4
            }
            
            analyses.append(analysis)
        
        return analyses
    
    def _determine_contextual_optimization_strategy(self, question: Dict[str, Any], 
                                                  reflection: ContextualReflection,
                                                  search_context: SearchContext,
                                                  context_match: Dict[str, Any]) -> str:
        """确定基于上下文的优化策略"""
        overall_score = context_match.get('overall_context_score', 0.5)
        
        # 基于上下文分数决定优化策略
        if overall_score < 0.4:
            return "context_enhance"  # 需要大幅增强
        elif overall_score < 0.7:
            return "context_refine"  # 需要精细化调整
        elif overall_score < 0.9:
            return "context_expand"  # 需要扩展
        else:
            return "keep"  # 保持原样
    
    def _enhance_question_with_context(self, question: Dict[str, Any], 
                                     reflection: ContextualReflection,
                                     search_context: SearchContext,
                                     topic: str,
                                     context_match: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文增强问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            # 构建上下文增强提示
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            搜索上下文信息：
            - 成功搜索查询：{', '.join(search_context.search_queries[:3])}
            - 高质量结果模式：{', '.join(search_context.successful_patterns[:2])}
            - 知识缺口：{', '.join(search_context.knowledge_gaps_identified[:3])}
            - 搜索结果质量：{search_context.result_relevance_scores[:3]}
            
            反思分析结果：
            - 搜索效果：{reflection.search_effectiveness.get('effectiveness_score', 0):.3f}
            - 结果质量：{reflection.result_quality_assessment.get('quality_score', 0):.3f}
            - 优化建议：{', '.join(reflection.query_optimization_suggestions[:2])}
            
            请基于以上上下文信息重新设计这个问题，使其：
            1. 更好地利用成功的搜索模式
            2. 填补识别的知识缺口
            3. 提高搜索效果和质量
            4. 避免之前的失败模式
            
            只返回重新设计后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个基于上下文的问题优化专家，能够利用搜索历史和反思结果来优化问题。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            enhanced_question = response.content.strip()
            
            optimized_question = {
                "question": enhanced_question,
                "direction": question.get('direction', 'context_enhanced') if isinstance(question, dict) else 'context_enhanced',
                "optimization_type": "context_enhanced",
                "original_question": question_text,
                "optimization_reason": "基于搜索上下文和反思结果进行增强优化",
                "context_scores": {
                    "query_match": context_match.get('query_match_score', 0),
                    "result_relevance": context_match.get('result_relevance_score', 0),
                    "gap_coverage": context_match.get('gap_coverage_score', 0),
                    "pattern_utilization": context_match.get('pattern_utilization_score', 0)
                }
            }
            
            workflow_logger.log_info(f"问题上下文增强完成: {question_text} -> {enhanced_question}", "ContextualQuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题上下文增强失败: {str(e)}", "ContextualQuestionOptimizer")
            return question
    
    def _refine_question_with_context(self, question: Dict[str, Any], 
                                    reflection: ContextualReflection,
                                    search_context: SearchContext,
                                    topic: str,
                                    context_match: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文精细化问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            基于搜索上下文的精细化建议：
            - 成功查询特征：{self._extract_successful_query_features(search_context)}
            - 结果质量指标：{reflection.result_quality_assessment}
            - 搜索策略调整：{', '.join(reflection.search_strategy_adjustments[:2])}
            
            请基于以上信息精细化这个问题，使其：
            1. 更好地匹配成功的查询模式
            2. 提高搜索结果的相关性和质量
            3. 避免低效的搜索策略
            
            只返回精细化后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个问题精细化专家，能够基于搜索上下文优化问题表达。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            refined_question = response.content.strip()
            
            optimized_question = {
                "question": refined_question,
                "direction": question.get('direction', 'context_refined') if isinstance(question, dict) else 'context_refined',
                "optimization_type": "context_refined",
                "original_question": question_text,
                "optimization_reason": "基于搜索上下文进行精细化优化",
                "context_scores": {
                    "query_match": context_match.get('query_match_score', 0),
                    "result_relevance": context_match.get('result_relevance_score', 0)
                }
            }
            
            workflow_logger.log_info(f"问题上下文精细化完成: {question_text} -> {refined_question}", "ContextualQuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题上下文精细化失败: {str(e)}", "ContextualQuestionOptimizer")
            return question
    
    def _expand_question_with_context(self, question: Dict[str, Any], 
                                    reflection: ContextualReflection,
                                    search_context: SearchContext,
                                    topic: str,
                                    context_match: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文扩展问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            基于上下文的扩展信息：
            - 问题覆盖度分析：{reflection.problem_coverage_analysis}
            - 缺失角度：{reflection.knowledge_gap_analysis.get('knowledge_gaps', [])[:3]}
            - 成功策略：{', '.join(reflection.successful_strategies[:2])}
            
            请基于以上信息扩展这个问题，使其：
            1. 覆盖更多相关角度
            2. 利用成功的搜索策略
            3. 填补识别的知识缺口
            
            只返回扩展后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个问题扩展专家，能够基于上下文信息扩展问题的覆盖范围。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            expanded_question = response.content.strip()
            
            optimized_question = {
                "question": expanded_question,
                "direction": question.get('direction', 'context_expanded') if isinstance(question, dict) else 'context_expanded',
                "optimization_type": "context_expanded",
                "original_question": question_text,
                "optimization_reason": "基于搜索上下文进行扩展优化",
                "context_scores": {
                    "gap_coverage": context_match.get('gap_coverage_score', 0),
                    "pattern_utilization": context_match.get('pattern_utilization_score', 0)
                }
            }
            
            workflow_logger.log_info(f"问题上下文扩展完成: {question_text} -> {expanded_question}", "ContextualQuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题上下文扩展失败: {str(e)}", "ContextualQuestionOptimizer")
            return question
    
    def _generate_gap_based_questions(self, reflection: ContextualReflection, 
                                    search_context: SearchContext,
                                    topic: str) -> List[Dict[str, Any]]:
        """基于知识缺口生成问题"""
        try:
            knowledge_gaps = reflection.knowledge_gap_analysis.get('knowledge_gaps', [])
            if not knowledge_gaps:
                return []
            
            gap_questions = []
            
            for gap in knowledge_gaps[:3]:  # 最多生成3个缺口问题
                prompt = f"""
                主题：{topic}
                知识缺口：{gap}
                
                请基于这个知识缺口生成一个高质量的研究问题，要求：
                1. 直接针对识别的知识缺口
                2. 与主题高度相关
                3. 具有明确的搜索价值
                4. 能够产生有用的结果
                
                只返回生成的问题，不要其他解释。
                """
                
                messages = [
                    SystemMessage(content="你是一个基于知识缺口的问题生成专家。"),
                    HumanMessage(content=prompt)
                ]
                
                response = self.llm.invoke(messages)
                generated_question = response.content.strip()
                
                gap_question = {
                    "question": generated_question,
                    "direction": "knowledge_gap",
                    "optimization_type": "gap_based",
                    "original_question": None,
                    "optimization_reason": f"基于知识缺口生成: {gap}",
                    "gap_source": gap
                }
                
                gap_questions.append(gap_question)
            
            workflow_logger.log_info(f"生成 {len(gap_questions)} 个基于知识缺口的问题", "ContextualQuestionOptimizer")
            return gap_questions
            
        except Exception as e:
            workflow_logger.log_error(f"知识缺口问题生成失败: {str(e)}", "ContextualQuestionOptimizer")
            return []
    
    def _generate_pattern_based_questions(self, reflection: ContextualReflection, 
                                        search_context: SearchContext,
                                        topic: str) -> List[Dict[str, Any]]:
        """基于成功模式生成问题"""
        try:
            successful_strategies = reflection.successful_strategies
            if not successful_strategies:
                return []
            
            pattern_questions = []
            
            for strategy in successful_strategies[:2]:  # 最多生成2个模式问题
                prompt = f"""
                主题：{topic}
                成功策略：{strategy}
                
                请基于这个成功策略生成一个高质量的研究问题，要求：
                1. 充分利用识别的成功策略
                2. 与主题高度相关
                3. 具有高搜索成功率
                4. 能够产生高质量结果
                
                只返回生成的问题，不要其他解释。
                """
                
                messages = [
                    SystemMessage(content="你是一个基于成功策略的问题生成专家。"),
                    HumanMessage(content=prompt)
                ]
                
                response = self.llm.invoke(messages)
                generated_question = response.content.strip()
                
                pattern_question = {
                    "question": generated_question,
                    "direction": "successful_pattern",
                    "optimization_type": "pattern_based",
                    "original_question": None,
                    "optimization_reason": f"基于成功策略生成: {strategy}",
                    "strategy_source": strategy
                }
                
                pattern_questions.append(pattern_question)
            
            workflow_logger.log_info(f"生成 {len(pattern_questions)} 个基于成功模式的问题", "ContextualQuestionOptimizer")
            return pattern_questions
            
        except Exception as e:
            workflow_logger.log_error(f"成功模式问题生成失败: {str(e)}", "ContextualQuestionOptimizer")
            return []
    
    # 辅助方法
    def _calculate_query_match_score(self, question: str, search_queries: List[str]) -> float:
        """计算问题与搜索查询的匹配度"""
        try:
            if not search_queries:
                return 0.0
            
            question_words = set(question.lower().split())
            match_scores = []
            
            for query in search_queries:
                query_words = set(query.lower().split())
                intersection = question_words.intersection(query_words)
                union = question_words.union(query_words)
                jaccard_similarity = len(intersection) / len(union) if union else 0
                match_scores.append(jaccard_similarity)
            
            return max(match_scores) if match_scores else 0.0
            
        except Exception as e:
            return 0.0
    
    def _calculate_result_relevance_score(self, question: str, search_results: List[Dict[str, Any]]) -> float:
        """计算问题与搜索结果的相关性"""
        try:
            if not search_results:
                return 0.0
            
            question_words = set(question.lower().split())
            relevance_scores = []
            
            for result in search_results:
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                content_words = set(f"{title} {snippet}".lower().split())
                
                intersection = question_words.intersection(content_words)
                relevance_score = len(intersection) / len(question_words) if question_words else 0
                relevance_scores.append(relevance_score)
            
            return np.mean(relevance_scores) if relevance_scores else 0.0
            
        except Exception as e:
            return 0.0
    
    def _calculate_gap_coverage_score(self, question: str, knowledge_gaps: List[str]) -> float:
        """计算问题对知识缺口的覆盖度"""
        try:
            if not knowledge_gaps:
                return 0.0
            
            question_lower = question.lower()
            covered_gaps = sum(1 for gap in knowledge_gaps if any(word in question_lower for word in gap.lower().split()))
            
            return covered_gaps / len(knowledge_gaps)
            
        except Exception as e:
            return 0.0
    
    def _calculate_pattern_utilization_score(self, question: str, successful_patterns: List[str]) -> float:
        """计算问题对成功模式的利用度"""
        try:
            if not successful_patterns:
                return 0.0
            
            question_lower = question.lower()
            utilized_patterns = sum(1 for pattern in successful_patterns if any(word in question_lower for word in pattern.lower().split()))
            
            return utilized_patterns / len(successful_patterns)
            
        except Exception as e:
            return 0.0
    
    def _extract_successful_query_features(self, search_context: SearchContext) -> str:
        """提取成功查询的特征"""
        try:
            if not search_context.search_queries:
                return "无成功查询"
            
            # 分析查询长度
            query_lengths = [len(query.split()) for query in search_context.search_queries]
            avg_length = np.mean(query_lengths) if query_lengths else 0
            
            # 分析查询类型
            query_types = []
            for query in search_context.search_queries:
                if any(word in query.lower() for word in ['如何', '怎样', '方法']):
                    query_types.append('方法型')
                elif any(word in query.lower() for word in ['什么', '是', '定义']):
                    query_types.append('定义型')
                elif any(word in query.lower() for word in ['为什么', '原因', '因为']):
                    query_types.append('原因型')
                else:
                    query_types.append('其他型')
            
            return f"平均长度: {avg_length:.1f}词, 类型分布: {', '.join(set(query_types))}"
            
        except Exception as e:
            return "特征提取失败"
