from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import QuestionState, QuestionDirection, QuestionItem, QuestionsResult
from storage_utils import StorageUtils
from config import get_config
from logger import workflow_logger
import json

import re

class QuestionWorkflow:
    
    """基于LangGraph的问题生成工作流"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage = StorageUtils()
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1500)
        )
        
        # 创建状态图
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """创建LangGraph工作流"""
        workflow = StateGraph(QuestionState)
        
        # 添加节点
        workflow.add_node("question_generator", self._question_generator_node)
        workflow.add_node("json_parser", self._json_parser_node)
        workflow.add_node("validator", self._validator_node)
        
        # 设置入口点
        workflow.set_entry_point("question_generator")
        
        # 添加边
        workflow.add_edge("question_generator", "json_parser")
        workflow.add_edge("json_parser", "validator")
        
        # 条件边
        workflow.add_conditional_edges(
            "validator",
            self._should_retry,
            {
                "retry": "question_generator",
                "complete": END
            }
        )
        
        return workflow.compile()
    
    def _question_generator_node(self, state: QuestionState) -> QuestionState:
        """问题生成节点"""
        workflow_logger.log_node_start("question_generator", state)
        
        system_prompt = """你是一名问题设计专家。
        - 输入：用户给定的主题
        - 任务：围绕该主题，从5个互补且覆盖全面的方向提出共计25个高质量问题（每个方向5个）。
        - 输出：用严格的JSON返回，包含5个方向的名称、每个方向的设计动机（rationale）、以及5条清晰、可执行的问题。
        - 约束：
          1) 问题要具体、可回答，避免空泛；
          2) 5个方向之间应有区分度，覆盖视角包括但不限于：背景/现状、目标/价值、方案/实现、风险/挑战、评估/指标 等；
          3) 严格输出为JSON，不要自然语言解释；
          4) 禁止使用任何代码围栏（例如 ```json 或 ```），直接输出纯JSON文本；
          5) 问题使用中文。
        - JSON模式：
        {
          "directions": [
            {
              "direction": "方向名称",
              "rationale": "该方向为何重要的简述",
              "questions": [
                {"question": "问题1"},
                {"question": "问题2"},
                {"question": "问题3"},
                {"question": "问题4"},
                {"question": "问题5"}
              ]
            }, ... 共5个方向
          ]
        }"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"主题：{state['topic']}\n请基于该主题生成5个方向、共25个问题，严格遵守系统消息中的JSON格式返回。")
        ]
        
        workflow_logger.log_llm_request(f"生成问题: {state['topic']}", self.config.get("model"))
        
        try:
            response = self.llm.invoke(messages)
            workflow_logger.log_llm_response(response.content, self.config.get("model"))
            
            # 将响应内容存储到状态中（用于JSON解析）
            state['raw_response'] = response.content
            
            workflow_logger.log_conversation("assistant", f"生成问题响应: {response.content[:200]}...", "question_generator")
            workflow_logger.log_node_end("question_generator", {"response_generated": True})
            
        except Exception as e:
            workflow_logger.log_error(f"问题生成失败: {str(e)}", "question_generator")
            state['error'] = f"问题生成失败: {str(e)}"
        
        return state
    
    def _json_parser_node(self, state: QuestionState) -> QuestionState:
        """JSON解析节点"""
        workflow_logger.log_node_start("json_parser", state)
        
        if not state.get('raw_response'):
            state['error'] = "没有原始响应内容"
            workflow_logger.log_error("没有原始响应内容", "json_parser")
            return state
        
        try:
            # 提取JSON
            json_content = self._extract_json_from_text(state['raw_response'])
            
            if not json_content:
                state['error'] = "无法从响应中提取JSON"
                workflow_logger.log_error("无法从响应中提取JSON", "json_parser")
                return state
            
            # 解析方向
            directions_raw = json_content.get("directions", [])
            directions = []
            total_questions = 0
            
            for d in directions_raw:
                direction_name = d.get("direction", "未命名方向")
                rationale = d.get("rationale", "")
                questions_list = d.get("questions", [])
                
                items = []
                for q in questions_list[:5]:  # 限制每个方向最多5个问题
                    if isinstance(q, dict):
                        q_text = q.get("question", "")
                    else:
                        q_text = str(q)
                    
                    if q_text:
                        items.append(QuestionItem(question=q_text))
                
                total_questions += len(items)
                directions.append(QuestionDirection(
                    direction=direction_name,
                    rationale=rationale,
                    questions=items
                ))
            
            state['directions'] = directions
            state['total_questions'] = total_questions
            state['parsed_json'] = json_content
            
            workflow_logger.log_info(f"JSON解析成功: {len(directions)}个方向, {total_questions}个问题", "json_parser")
            workflow_logger.log_node_end("json_parser", {"directions_count": len(directions), "questions_count": total_questions})
            
        except Exception as e:
            state['error'] = f"JSON解析失败: {str(e)}"
            workflow_logger.log_error(f"JSON解析失败: {str(e)}", "json_parser")
        
        return state
    
    def _validator_node(self, state: QuestionState) -> QuestionState:
        """验证节点"""
        workflow_logger.log_node_start("validator", state)
        
        # 检查是否有错误
        if state.get('error'):
            state['status'] = "error"
            workflow_logger.log_error(f"验证失败: {state['error']}", "validator")
            workflow_logger.log_node_end("validator", {"status": "error", "error": state['error']})
            return state
        
        # 验证方向数量
        if len(state.get('directions', [])) != 5:
            state['error'] = f"方向数量不正确，期望5个，实际{len(state.get('directions', []))}个"
            state['status'] = "error"
            workflow_logger.log_error(f"方向数量不正确: {len(state.get('directions', []))}", "validator")
            workflow_logger.log_node_end("validator", {"status": "error", "error": state['error']})
            return state
        
        # 验证问题数量
        if state.get('total_questions', 0) != 25:
            state['error'] = f"问题数量不正确，期望25个，实际{state.get('total_questions', 0)}个"
            state['status'] = "error"
            workflow_logger.log_error(f"问题数量不正确: {state.get('total_questions', 0)}", "validator")
            workflow_logger.log_node_end("validator", {"status": "error", "error": state['error']})
            return state
        
        # 验证每个方向的问题数量
        for i, direction in enumerate(state.get('directions', [])):
            if len(direction.questions) != 5:
                state['error'] = f"方向{i+1}的问题数量不正确，期望5个，实际{len(direction.questions)}个"
                state['status'] = "error"
                workflow_logger.log_error(f"方向{i+1}问题数量不正确: {len(direction.questions)}", "validator")
                workflow_logger.log_node_end("validator", {"status": "error", "error": state['error']})
                return state
        
        # 验证通过
        state['status'] = "completed"
        workflow_logger.log_info("验证通过", "validator")
        workflow_logger.log_node_end("validator", {"status": "completed"})
        
        return state
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON"""
        if not text:
            return {}
        
        # 去除常见代码围栏 ```json ... ``` 或 ``` ... ```
        fenced_match = re.search(r"```[a-zA-Z]*\n([\s\S]*?)```", text)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass
        
        # 直接尝试整体解析
        try:
            return json.loads(text)
        except Exception:
            pass
        
        # 兜底：提取第一个以 { 开头到对应 } 的片段
        start = text.find("{")
        if start != -1:
            brace = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    brace += 1
                elif text[i] == '}':
                    brace -= 1
                    if brace == 0:
                        fragment = text[start : i + 1]
                        try:
                            return json.loads(fragment)
                        except Exception:
                            break
        
        return {}
    
    def _should_retry(self, state: QuestionState) -> str:
        """决定是否重试"""
        if state.get('status') == "error":
            # 检查重试次数
            if 'retry_count' not in state:
                state['retry_count'] = 0
            
            state['retry_count'] += 1
            
            if state['retry_count'] < 3:  # 最多重试3次
                workflow_logger.log_warning(f"重试第{state['retry_count']}次", "should_retry")
                return "retry"
            else:
                workflow_logger.log_error("达到最大重试次数", "should_retry")
                return "complete"
        else:
            workflow_logger.log_info("验证通过，工作流完成", "should_retry")
            return "complete"
    
    def generate_questions(self, topic: str) -> Dict[str, Any]:
        """生成问题的主流程"""
        workflow_logger.log_workflow_start("QuestionWorkflow", topic)
        
        try:
            # 初始化状态
            initial_state: QuestionState = {
                "topic": topic,
                "directions": [],
                "total_questions": 0,
                "status": "running",
                "error": None,
                "raw_response": None,
                "parsed_json": None,
                "retry_count": 0
            }
            
            workflow_logger.log_debug("初始化状态完成", initial_state)
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            workflow_logger.log_debug("工作流执行完成", final_state)
            
            # 构建结果
            if final_state.get('status') == "completed":
                result = QuestionsResult(
                    topic=topic,
                    directions=final_state.get('directions', []),
                    total_questions=final_state.get('total_questions', 0)
                )
                
                # 保存结果
                self.storage.save_questions_result(result)
                
                result_dict = result.dict()
                workflow_logger.log_workflow_end("QuestionWorkflow", "completed", result_dict)
                
                return result_dict
            else:
                # 返回错误信息
                error_result = {
                    "topic": topic,
                    "status": "error",
                    "error": final_state.get('error', '未知错误'),
                    "total_questions": 0
                }
                workflow_logger.log_workflow_end("QuestionWorkflow", "error", error_result)
                return error_result
                
        except Exception as e:
            error_result = {
                "topic": topic,
                "status": "error",
                "error": str(e),
                "total_questions": 0
            }
            workflow_logger.log_error(f"工作流执行失败: {str(e)}", "generate_questions")
            workflow_logger.log_workflow_end("QuestionWorkflow", "error", error_result)
            return error_result