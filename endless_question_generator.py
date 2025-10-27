"""
无尽模式新问题生成器
基于上一轮的最佳方向/结果生成新问题，避免重复并深入挖掘未覆盖领域
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import QuestionDirection, QuestionItem, RoundReport
from logger import workflow_logger
import json
import re
from datetime import datetime


class EndlessQuestionGenerator:
    """无尽模式新问题生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2000)
        )
        
        # 无尽模式配置
        self.endless_config = config.get("endless_mode", {})
        self.new_question_strategy = self.endless_config.get("new_question_strategy", "best_direction_based")
    
    def generate_next_questions(self, 
                              topic: str, 
                              previous_round_report: Optional[RoundReport] = None,
                              all_previous_reports: List[RoundReport] = None) -> Dict[str, Any]:
        """
        基于上一轮结果生成新问题
        
        Args:
            topic: 原始主题
            previous_round_report: 上一轮的报告
            all_previous_reports: 所有之前的报告列表
            
        Returns:
            包含新问题生成结果的字典
        """
        workflow_logger.log_info(f"开始生成第{len(all_previous_reports or []) + 1}轮新问题")
        
        try:
            # 构建生成提示词
            prompt = self._build_generation_prompt(topic, previous_round_report, all_previous_reports)
            
            # 调用LLM生成新问题
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            workflow_logger.log_llm_request(f"生成新问题: {topic}", self.config.get("model"))
            
            response = self.llm.invoke(messages)
            response_content = response.content
            
            # 解析响应
            parsed_result = self._parse_response(response_content)
            
            if parsed_result.get("status") == "success":
                workflow_logger.log_info(f"新问题生成成功: {len(parsed_result.get('directions', []))}个方向")
                return parsed_result
            else:
                workflow_logger.log_error(f"新问题生成失败: {parsed_result.get('error', '未知错误')}")
                return parsed_result
                
        except Exception as e:
            error_msg = f"新问题生成异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "directions": [],
                "total_questions": 0
            }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一名问题设计专家，专门负责基于已有探索结果生成新的深入问题。

你的任务：
1. 分析用户已经完成的探索轮次和结果
2. 识别已探索的内容和未覆盖的领域
3. 基于最佳方向和关键发现，设计5个新的互补方向
4. 为每个方向生成5个深入、具体、可执行的问题
5. 确保新问题与已有问题不重复，且能深入挖掘未覆盖领域

要求：
- 问题要具体、可回答，避免空泛
- 5个方向之间应有区分度，覆盖不同视角
- 基于已有发现提出更深入或相关的新问题
- 保持5个方向的互补性和覆盖面
- 严格输出为JSON格式，不要自然语言解释
- 禁止使用任何代码围栏（例如 ```json 或 ```），直接输出纯JSON文本
- 问题使用中文

JSON格式：
{
  "directions": [
    {
      "direction": "方向名称",
      "rationale": "该方向为何重要的简述，说明与已有探索的关系",
      "questions": [
        {"question": "问题1"},
        {"question": "问题2"},
        {"question": "问题3"},
        {"question": "问题4"},
        {"question": "问题5"}
      ]
    }
  ]
}"""
    
    def _build_generation_prompt(self, 
                                topic: str, 
                                previous_round_report: Optional[RoundReport],
                                all_previous_reports: List[RoundReport]) -> str:
        """构建生成提示词"""
        prompt_parts = [
            f"主题：{topic}",
            f"",
            f"用户已经完成了 {len(all_previous_reports or [])} 轮探索，现在需要基于已有结果生成新的问题。"
        ]
        
        if previous_round_report:
            prompt_parts.extend([
                f"",
                f"=== 上一轮探索结果 ===",
                f"轮次：{previous_round_report.round_number}",
                f"最佳方向：{previous_round_report.best_direction}",
                f"综合评分：{previous_round_report.comprehensive_score:.1f}",
                f"质量等级：{previous_round_report.quality_level}",
                f"关键发现："
            ])
            
            for i, finding in enumerate(previous_round_report.key_findings[:5], 1):
                prompt_parts.append(f"  {i}. {finding}")
        
        if all_previous_reports and len(all_previous_reports) > 1:
            prompt_parts.extend([
                f"",
                f"=== 历史探索概览 ===",
                f"已完成轮次：{len(all_previous_reports)}",
                f"已探索的主要方向："
            ])
            
            # 收集所有已探索的方向
            explored_directions = set()
            for report in all_previous_reports:
                if report.best_direction:
                    explored_directions.add(report.best_direction)
            
            for i, direction in enumerate(list(explored_directions)[:10], 1):
                prompt_parts.append(f"  {i}. {direction}")
        
        prompt_parts.extend([
            f"",
            f"=== 任务要求 ===",
            f"请基于以上探索结果，设计5个新的互补方向和25个新问题：",
            f"1. 避免重复已探索的问题和方向",
            f"2. 基于已有发现，提出更深入或相关的新问题",
            f"3. 挖掘未覆盖的领域和视角",
            f"4. 保持5个方向的互补性和覆盖面",
            f"5. 确保问题具体、可执行",
            f"",
            f"请严格按照系统消息中的JSON格式返回结果。"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 清理响应内容
            cleaned_content = self._clean_response_content(response_content)
            
            # 尝试解析JSON
            try:
                parsed_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                workflow_logger.log_error(f"JSON解析失败: {str(e)}")
                return {
                    "status": "error",
                    "error": f"JSON解析失败: {str(e)}",
                    "directions": [],
                    "total_questions": 0
                }
            
            # 验证数据结构
            if not isinstance(parsed_data, dict) or "directions" not in parsed_data:
                return {
                    "status": "error",
                    "error": "响应格式不正确：缺少directions字段",
                    "directions": [],
                    "total_questions": 0
                }
            
            directions_data = parsed_data["directions"]
            if not isinstance(directions_data, list):
                return {
                    "status": "error",
                    "error": "响应格式不正确：directions不是列表",
                    "directions": [],
                    "total_questions": 0
                }
            
            # 转换为QuestionDirection对象
            directions = []
            total_questions = 0
            
            for direction_data in directions_data:
                if not isinstance(direction_data, dict):
                    continue
                
                direction_name = direction_data.get("direction", "")
                rationale = direction_data.get("rationale", "")
                questions_data = direction_data.get("questions", [])
                
                if not direction_name or not questions_data:
                    continue
                
                # 创建QuestionItem列表
                questions = []
                for question_data in questions_data:
                    if isinstance(question_data, dict) and "question" in question_data:
                        question_text = question_data["question"].strip()
                        if question_text:
                            questions.append(QuestionItem(question=question_text))
                
                if len(questions) >= 3:  # 至少需要3个问题
                    direction = QuestionDirection(
                        direction=direction_name,
                        rationale=rationale,
                        questions=questions
                    )
                    directions.append(direction)
                    total_questions += len(questions)
            
            if len(directions) < 3:  # 至少需要3个方向
                return {
                    "status": "error",
                    "error": f"生成的方向数量不足：{len(directions)}个，需要至少3个",
                    "directions": directions,
                    "total_questions": total_questions
                }
            
            return {
                "status": "success",
                "directions": directions,
                "total_questions": total_questions,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"解析响应异常: {str(e)}",
                "directions": [],
                "total_questions": 0
            }
    
    def _clean_response_content(self, content: str) -> str:
        """清理响应内容"""
        # 移除代码围栏
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        content = re.sub(r'^```\s*', '', content)
        
        # 移除多余的空白字符
        content = content.strip()
        
        # 查找JSON开始和结束位置
        start_pos = content.find('{')
        end_pos = content.rfind('}')
        
        if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
            content = content[start_pos:end_pos + 1]
        
        return content
    
    def analyze_exploration_coverage(self, all_reports: List[RoundReport]) -> Dict[str, Any]:
        """
        分析探索覆盖度，识别未覆盖的领域
        
        Args:
            all_reports: 所有历史报告
            
        Returns:
            探索覆盖度分析结果
        """
        if not all_reports:
            return {
                "coverage_analysis": "无历史数据",
                "explored_directions": [],
                "suggested_directions": [],
                "coverage_score": 0.0
            }
        
        # 收集已探索的方向
        explored_directions = set()
        direction_scores = {}
        
        for report in all_reports:
            if report.best_direction:
                explored_directions.add(report.best_direction)
                direction_scores[report.best_direction] = report.comprehensive_score
        
        # 分析覆盖度
        total_directions = len(explored_directions)
        avg_score = sum(direction_scores.values()) / len(direction_scores) if direction_scores else 0
        
        # 生成建议方向（这里可以基于领域知识扩展）
        suggested_directions = self._generate_suggested_directions(explored_directions)
        
        return {
            "coverage_analysis": f"已探索{total_directions}个方向，平均评分{avg_score:.1f}",
            "explored_directions": list(explored_directions),
            "suggested_directions": suggested_directions,
            "coverage_score": min(total_directions / 10.0, 1.0),  # 假设10个方向为完全覆盖
            "avg_score": avg_score
        }
    
    def _generate_suggested_directions(self, explored_directions: set) -> List[str]:
        """基于已探索方向生成建议的新方向"""
        # 这里可以根据具体领域知识扩展
        common_directions = [
            "技术实现方案", "商业模式分析", "风险评估", "市场调研", 
            "用户需求分析", "竞争分析", "成本效益分析", "时间规划",
            "资源需求", "成功指标", "失败应对", "创新机会",
            "政策法规", "环境影响", "社会影响", "伦理考量"
        ]
        
        # 过滤掉已探索的方向
        suggested = []
        for direction in common_directions:
            if not any(explored.lower() in direction.lower() or direction.lower() in explored.lower() 
                      for explored in explored_directions):
                suggested.append(direction)
        
        return suggested[:5]  # 返回前5个建议
