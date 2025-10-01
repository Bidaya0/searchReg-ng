"""
问题优化器 - 基于反思结果优化和深化问题
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from logger import workflow_logger
from reflection_analyzer import ReflectionAnalysis


class QuestionOptimizer:
    """问题优化器 - 基于反思分析结果优化问题"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=0.4,  # 适中的创造性
            max_tokens=1500
        )
        
        # 优化配置
        self.optimization_config = config.get('question_optimization', {
            "quality_thresholds": {
                "excellent": 0.85,
                "good": 0.70,
                "fair": 0.55,
                "poor": 0.40
            },
            "optimization_strategies": {
                "redesign": 0.4,  # 重新设计阈值
                "deepen": 0.7,   # 深化阈值
                "refine": 0.85   # 微调阈值
            },
            "max_questions_per_iteration": 25,
            "min_questions_per_iteration": 5
        })
    
    def optimize_questions(self, questions: List[Dict[str, Any]], 
                          reflection: ReflectionAnalysis, 
                          topic: str) -> List[Dict[str, Any]]:
        """基于反思结果优化问题"""
        workflow_logger.log_info(f"开始优化 {len(questions)} 个问题", "QuestionOptimizer")
        
        try:
            optimized_questions = []
            
            # 1. 评估每个问题的质量
            question_assessments = self._assess_question_quality(questions, reflection)
            
            # 2. 根据质量决定优化策略
            for i, question in enumerate(questions):
                assessment = question_assessments[i]
                optimization_strategy = self._determine_optimization_strategy(assessment)
                
                if optimization_strategy == "redesign":
                    optimized = self._redesign_question(question, reflection, topic)
                elif optimization_strategy == "deepen":
                    optimized = self._deepen_question(question, reflection, topic)
                elif optimization_strategy == "refine":
                    optimized = self._refine_question(question, reflection, topic)
                else:
                    optimized = question  # 保持原样
                
                optimized_questions.append(optimized)
            
            # 3. 补充缺失角度的问题
            missing_angle_questions = self._generate_missing_angle_questions(reflection, topic)
            optimized_questions.extend(missing_angle_questions)
            
            # 4. 限制问题数量
            max_questions = self.optimization_config.get('max_questions_per_iteration', 25)
            optimized_questions = optimized_questions[:max_questions]
            
            workflow_logger.log_info(f"问题优化完成，优化后问题数: {len(optimized_questions)}", "QuestionOptimizer")
            return optimized_questions
            
        except Exception as e:
            workflow_logger.log_error(f"问题优化失败: {str(e)}", "QuestionOptimizer")
            return questions  # 返回原问题
    
    def _assess_question_quality(self, questions: List[Dict[str, Any]], 
                               reflection: ReflectionAnalysis) -> List[Dict[str, Any]]:
        """评估问题质量"""
        assessments = []
        
        for question in questions:
            question_text = question.get('question', '') if isinstance(question, dict) else str(question)
            
            # 基础质量评估
            quality_score = self._calculate_basic_quality_score(question_text)
            
            # 检查是否在弱问题列表中
            is_weak = question_text in reflection.weak_questions
            
            # 检查是否在强问题列表中
            is_strong = question_text in reflection.strong_questions
            
            # 计算优化潜力
            optimization_potential = self._calculate_optimization_potential(
                question_text, reflection
            )
            
            assessment = {
                "question": question_text,
                "quality_score": quality_score,
                "is_weak": is_weak,
                "is_strong": is_strong,
                "optimization_potential": optimization_potential,
                "assessment_reason": self._get_assessment_reason(quality_score, is_weak, is_strong)
            }
            
            assessments.append(assessment)
        
        return assessments
    
    def _calculate_basic_quality_score(self, question_text: str) -> float:
        """计算基础质量分数"""
        if not question_text:
            return 0.0
        
        score_factors = []
        
        # 长度评估（适中长度更好）
        length_score = min(1.0, len(question_text) / 50)  # 50字符为满分
        score_factors.append(length_score * 0.2)
        
        # 具体性评估（包含具体词汇）
        specific_words = ['如何', '什么', '为什么', '怎样', '方法', '技术', '应用', '影响', '趋势']
        specificity_score = sum(1 for word in specific_words if word in question_text) / len(specific_words)
        score_factors.append(specificity_score * 0.3)
        
        # 可执行性评估（问题是否可搜索）
        executable_words = ['研究', '发展', '应用', '技术', '方法', '案例', '现状', '趋势']
        executable_score = sum(1 for word in executable_words if word in question_text) / len(executable_words)
        score_factors.append(executable_score * 0.3)
        
        # 清晰度评估（避免模糊词汇）
        vague_words = ['一些', '很多', '大概', '可能', '也许', '一般']
        clarity_score = 1.0 - (sum(1 for word in vague_words if word in question_text) * 0.1)
        score_factors.append(max(0.0, clarity_score) * 0.2)
        
        return sum(score_factors)
    
    def _calculate_optimization_potential(self, question_text: str, 
                                        reflection: ReflectionAnalysis) -> float:
        """计算优化潜力"""
        potential = 0.0
        
        # 基于反思分析计算潜力
        if question_text in reflection.weak_questions:
            potential += 0.4
        
        if question_text in reflection.strong_questions:
            potential -= 0.2  # 强问题优化潜力较小
        
        # 基于缺失角度计算潜力
        for missing_angle in reflection.missing_angles:
            if any(word in question_text for word in missing_angle.split()):
                potential += 0.3
        
        return min(1.0, max(0.0, potential))
    
    def _get_assessment_reason(self, quality_score: float, is_weak: bool, is_strong: bool) -> str:
        """获取评估原因"""
        if is_weak:
            return "在反思分析中被识别为低效问题"
        elif is_strong:
            return "在反思分析中被识别为高效问题"
        elif quality_score < 0.4:
            return "基础质量分数较低"
        elif quality_score < 0.6:
            return "基础质量分数中等"
        else:
            return "基础质量分数较高"
    
    def _determine_optimization_strategy(self, assessment: Dict[str, Any]) -> str:
        """确定优化策略"""
        quality_score = assessment['quality_score']
        is_weak = assessment['is_weak']
        optimization_potential = assessment['optimization_potential']
        
        thresholds = self.optimization_config['optimization_strategies']
        
        # 弱问题或质量很低的问题需要重新设计
        if is_weak or quality_score < thresholds['redesign']:
            return "redesign"
        
        # 中等质量或优化潜力大的问题需要深化
        elif quality_score < thresholds['deepen'] or optimization_potential > 0.5:
            return "deepen"
        
        # 高质量问题只需要微调
        elif quality_score < thresholds['refine']:
            return "refine"
        
        # 高质量问题保持不变
        else:
            return "keep"
    
    def _redesign_question(self, question: Dict[str, Any], 
                          reflection: ReflectionAnalysis, 
                          topic: str) -> Dict[str, Any]:
        """重新设计问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            反思分析发现的问题：
            - 弱问题列表：{', '.join(reflection.weak_questions[:3])}
            - 缺失角度：{', '.join(reflection.missing_angles[:3])}
            - 优化方向：{', '.join(reflection.optimization_directions[:3])}
            
            请重新设计这个问题，使其：
            1. 更加具体和可执行
            2. 避免原问题的问题
            3. 更好地服务于主题研究
            4. 具有更高的搜索价值
            
            只返回重新设计后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个问题设计专家，能够重新设计低质量的问题，使其更加具体、可执行和有价值。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            redesigned_question = response.content.strip()
            
            # 创建优化后的问题对象
            optimized_question = {
                "question": redesigned_question,
                "direction": question.get('direction', 'optimized') if isinstance(question, dict) else 'optimized',
                "optimization_type": "redesigned",
                "original_question": question_text,
                "optimization_reason": "问题质量较低，需要重新设计"
            }
            
            workflow_logger.log_info(f"问题重新设计完成: {question_text} -> {redesigned_question}", "QuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题重新设计失败: {str(e)}", "QuestionOptimizer")
            return question
    
    def _deepen_question(self, question: Dict[str, Any], 
                        reflection: ReflectionAnalysis, 
                        topic: str) -> Dict[str, Any]:
        """深化问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            反思分析发现的改进方向：
            - 优化方向：{', '.join(reflection.optimization_directions[:3])}
            - 信息缺口：{', '.join(reflection.information_gaps[:3])}
            - 缺失角度：{', '.join(reflection.missing_angles[:3])}
            
            请深化这个问题，使其：
            1. 更加深入和具体
            2. 包含更多技术细节
            3. 更好地填补信息缺口
            4. 具有更高的研究价值
            
            只返回深化后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个研究问题专家，能够深化问题，使其更加深入、具体和有研究价值。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            deepened_question = response.content.strip()
            
            optimized_question = {
                "question": deepened_question,
                "direction": question.get('direction', 'deepened') if isinstance(question, dict) else 'deepened',
                "optimization_type": "deepened",
                "original_question": question_text,
                "optimization_reason": "问题需要深化，提高研究深度"
            }
            
            workflow_logger.log_info(f"问题深化完成: {question_text} -> {deepened_question}", "QuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题深化失败: {str(e)}", "QuestionOptimizer")
            return question
    
    def _refine_question(self, question: Dict[str, Any], 
                        reflection: ReflectionAnalysis, 
                        topic: str) -> Dict[str, Any]:
        """微调问题"""
        question_text = question.get('question', '') if isinstance(question, dict) else str(question)
        
        try:
            prompt = f"""
            原问题：{question_text}
            主题：{topic}
            
            反思分析发现的微调方向：
            - 优化方向：{', '.join(reflection.optimization_directions[:2])}
            
            请微调这个问题，使其：
            1. 表达更加精准
            2. 避免歧义
            3. 提高搜索效果
            4. 保持原有核心内容
            
            只返回微调后的问题，不要其他解释。
            """
            
            messages = [
                SystemMessage(content="你是一个问题优化专家，能够微调问题，使其表达更加精准和有效。"),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            refined_question = response.content.strip()
            
            optimized_question = {
                "question": refined_question,
                "direction": question.get('direction', 'refined') if isinstance(question, dict) else 'refined',
                "optimization_type": "refined",
                "original_question": question_text,
                "optimization_reason": "问题质量较高，进行微调优化"
            }
            
            workflow_logger.log_info(f"问题微调完成: {question_text} -> {refined_question}", "QuestionOptimizer")
            return optimized_question
            
        except Exception as e:
            workflow_logger.log_error(f"问题微调失败: {str(e)}", "QuestionOptimizer")
            return question
    
    def _generate_missing_angle_questions(self, reflection: ReflectionAnalysis, 
                                        topic: str) -> List[Dict[str, Any]]:
        """生成缺失角度的问题"""
        if not reflection.missing_angles:
            return []
        
        try:
            missing_questions = []
            
            for angle in reflection.missing_angles[:3]:  # 最多生成3个缺失角度的问题
                prompt = f"""
                主题：{topic}
                缺失角度：{angle}
                
                请基于这个缺失角度生成一个高质量的研究问题，要求：
                1. 问题具体、可执行
                2. 与主题高度相关
                3. 能够填补研究空白
                4. 具有搜索价值
                
                只返回生成的问题，不要其他解释。
                """
                
                messages = [
                    SystemMessage(content="你是一个研究问题生成专家，能够基于缺失的研究角度生成高质量的问题。"),
                    HumanMessage(content=prompt)
                ]
                
                response = self.llm.invoke(messages)
                generated_question = response.content.strip()
                
                missing_question = {
                    "question": generated_question,
                    "direction": "missing_angle",
                    "optimization_type": "generated",
                    "original_question": None,
                    "optimization_reason": f"补充缺失角度: {angle}"
                }
                
                missing_questions.append(missing_question)
            
            workflow_logger.log_info(f"生成 {len(missing_questions)} 个缺失角度问题", "QuestionOptimizer")
            return missing_questions
            
        except Exception as e:
            workflow_logger.log_error(f"缺失角度问题生成失败: {str(e)}", "QuestionOptimizer")
            return []
    
    def analyze_optimization_effectiveness(self, original_questions: List[Dict[str, Any]], 
                                         optimized_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析优化效果"""
        try:
            analysis = {
                "total_questions": len(optimized_questions),
                "optimization_types": {},
                "quality_improvements": [],
                "effectiveness_score": 0.0
            }
            
            # 统计优化类型
            for question in optimized_questions:
                opt_type = question.get('optimization_type', 'unknown')
                analysis["optimization_types"][opt_type] = analysis["optimization_types"].get(opt_type, 0) + 1
            
            # 分析质量改进
            for i, opt_question in enumerate(optimized_questions):
                if i < len(original_questions):
                    orig_question = original_questions[i]
                    orig_text = orig_question.get('question', '') if isinstance(orig_question, dict) else str(orig_question)
                    opt_text = opt_question.get('question', '')
                    
                    # 简单的质量改进评估
                    orig_quality = self._calculate_basic_quality_score(orig_text)
                    opt_quality = self._calculate_basic_quality_score(opt_text)
                    
                    improvement = opt_quality - orig_quality
                    analysis["quality_improvements"].append({
                        "original": orig_text,
                        "optimized": opt_text,
                        "improvement": improvement,
                        "optimization_type": opt_question.get('optimization_type', 'unknown')
                    })
            
            # 计算整体效果分数
            if analysis["quality_improvements"]:
                avg_improvement = sum(imp["improvement"] for imp in analysis["quality_improvements"]) / len(analysis["quality_improvements"])
                analysis["effectiveness_score"] = max(0.0, min(1.0, avg_improvement + 0.5))
            
            return analysis
            
        except Exception as e:
            workflow_logger.log_error(f"优化效果分析失败: {str(e)}", "QuestionOptimizer")
            return {"effectiveness_score": 0.0, "error": str(e)}
