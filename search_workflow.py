from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import SearchState, SearchResult, ChatMessage, FinalResult, ErrorLog
from search_tools import SearchTools
from storage_utils import StorageUtils
from config import get_config
from logger import workflow_logger
import json
from datetime import datetime

class SearchWorkflow:
    """基于LangGraph的搜索工作流"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage = StorageUtils()
        self.search_tools = SearchTools(config.get("searx_host"), self.storage)
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1000)
        )
        
        # 创建状态图
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """创建LangGraph工作流"""
        workflow = StateGraph(SearchState)
        
        # 添加节点
        workflow.add_node("topic_analyzer", self._topic_analyzer_node)
        workflow.add_node("search_executor", self._search_executor_node)
        workflow.add_node("content_recorder", self._content_recorder_node)
        workflow.add_node("quality_checker", self._quality_checker_node)
        
        # 设置入口点
        workflow.set_entry_point("topic_analyzer")
        
        # 添加边
        workflow.add_edge("topic_analyzer", "search_executor")
        workflow.add_edge("search_executor", "content_recorder")
        workflow.add_edge("content_recorder", "quality_checker")
        
        # 条件边
        workflow.add_conditional_edges(
            "quality_checker",
            self._should_continue,
            {
                "continue": "topic_analyzer",
                "end": END
            }
        )
        
        return workflow.compile()
    
    def _topic_analyzer_node(self, state: SearchState) -> SearchState:
        """主题分析节点"""
        workflow_logger.log_node_start("topic_analyzer", state)
        
        system_prompt = """你是一个主题分析专家，负责分析用户输入的主题，提取关键词和生成搜索建议。
        你需要：
        1. 分析主题的核心概念，并进行扩展性陈述。
        2. 评估主题的搜索难度。
        3. 根据已有搜索结果，生成新的搜索建议。
        4. 给搜索执行器提供具体的搜索查询建议。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析主题：{state['topic']}")
        ]
        
        # 如果有历史消息，添加到上下文中
        for msg in state.get('messages', [])[-5:]:  # 只取最近5条消息
            if hasattr(msg, 'content'):
                # 如果已经是BaseMessage类型，直接添加
                messages.append(msg)
            elif hasattr(msg, 'role'):
                # 如果是ChatMessage类型，转换为BaseMessage
                if msg.role == "assistant":
                    messages.append(AIMessage(content=msg.content))
                else:
                    messages.append(HumanMessage(content=msg.content))
        
        workflow_logger.log_llm_request(f"分析主题: {state['topic']}", self.config.get("model"))
        
        try:
            response = self.llm.invoke(messages)
            workflow_logger.log_llm_response(response.content, self.config.get("model"))
            
            # 更新状态 - 直接使用LangChain消息
            new_message = AIMessage(content=response.content)
            
            # 确保messages列表存在
            if 'messages' not in state:
                state['messages'] = []
            
            state['messages'].append(new_message)
            
            workflow_logger.log_conversation("assistant", response.content, "topic_analyzer")
            workflow_logger.log_node_end("topic_analyzer", {"message_added": True})
            
        except Exception as e:
            workflow_logger.log_error(f"主题分析失败: {str(e)}", "topic_analyzer")
            error_message = AIMessage(content=f"主题分析失败: {str(e)}")
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(error_message)
        
        return state
    
    def _search_executor_node(self, state: SearchState) -> SearchState:
        """搜索执行节点"""
        workflow_logger.log_node_start("search_executor", state)
        
        # 构建搜索查询
        if not state.get('current_query'):
            # 基于主题生成搜索查询
            query_prompt = f"基于主题 '{state['topic']}' 生成一个具体的搜索查询词"
            query_response = self.llm.invoke([
                SystemMessage(content="你是一个搜索查询生成专家，根据主题生成具体的搜索查询词。"),
                HumanMessage(content=query_prompt)
            ])
            state['current_query'] = query_response.content.strip()
            workflow_logger.log_conversation("assistant", f"生成搜索查询: {state['current_query']}", "search_executor")
        
        try:
            # 执行搜索
            workflow_logger.log_search_query(state['current_query'], self.config.get("max_results", 20))
            
            search_result = self.search_tools.search_query(
                state['current_query'],
                self.config.get("max_results", 20)
            )
            
            # 确保search_results列表存在
            if 'search_results' not in state:
                state['search_results'] = []
            
            state['search_results'].append(search_result)
            
            # 生成搜索总结
            search_summary = f"搜索查询：{state['current_query']}\n搜索结果：{len(search_result.results)}条\n"
            search_summary += self.search_tools.format_search_results(search_result)
            
            summary_message = AIMessage(content=f"搜索完成：\n{search_summary}")
            
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(summary_message)
            
            workflow_logger.log_conversation("assistant", f"搜索完成，获得{len(search_result.results)}条结果", "search_executor")
            workflow_logger.log_node_end("search_executor", {"search_completed": True, "results_count": len(search_result.results)})
            
        except Exception as e:
            error_msg = f"搜索失败：{str(e)}"
            workflow_logger.log_error(f"搜索执行失败: {str(e)}", "search_executor")
            
            error_message = AIMessage(content=error_msg)
            
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(error_message)
        
        return state
    
    def _content_recorder_node(self, state: SearchState) -> SearchState:
        """内容记录节点"""
        workflow_logger.log_node_start("content_recorder", state)
        
        if not state.get('search_results'):
            workflow_logger.log_warning("没有搜索结果可记录", "content_recorder")
            return state
        
        system_prompt = """你是一个内容记录专家，负责记录和总结搜索结果。
        搜索结果可能会有多语言场景，请尝试将搜索到的结果用中文进行总结。
        你需要：
        1. 对搜索结果进行分类和标记
        2. 生成结构化摘要
        3. 提取关键点
        4. 避免重复之前已经讨论过的内容"""
        
        # 获取最新的搜索结果
        latest_search = state['search_results'][-1]
        search_content = self.search_tools.format_search_results(latest_search)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请总结以下搜索结果：\n{search_content}")
        ]
        
        workflow_logger.log_llm_request("总结搜索结果", self.config.get("model"))
        
        try:
            response = self.llm.invoke(messages)
            workflow_logger.log_llm_response(response.content, self.config.get("model"))
            
            # 提取关键点
            key_points_prompt = f"从以下内容中提取3-5个关键点：\n{response.content}"
            key_points_response = self.llm.invoke([
                SystemMessage(content="你是一个关键点提取专家，从文本中提取最重要的关键点。"),
                HumanMessage(content=key_points_prompt)
            ])
            
            # 更新状态
            if 'summaries' not in state:
                state['summaries'] = []
            if 'key_points' not in state:
                state['key_points'] = []
            
            state['summaries'].append(response.content)
            state['key_points'].append(key_points_response.content)
            
            summary_message = AIMessage(content=f"内容总结完成：\n{response.content}\n\n关键点：\n{key_points_response.content}")
            
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(summary_message)
            
            workflow_logger.log_conversation("assistant", f"内容总结完成，提取了关键点", "content_recorder")
            workflow_logger.log_node_end("content_recorder", {"summary_added": True, "key_points_added": True})
            
        except Exception as e:
            workflow_logger.log_error(f"内容记录失败: {str(e)}", "content_recorder")
            error_message = AIMessage(content=f"内容记录失败: {str(e)}")
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(error_message)
        
        return state
    
    def _quality_checker_node(self, state: SearchState) -> SearchState:
        """质量检查节点"""
        workflow_logger.log_node_start("quality_checker", state)
        
        # 初始化计数器
        if 'iteration_count' not in state:
            state['iteration_count'] = 0
        if 'max_iterations' not in state:
            state['max_iterations'] = 20
        
        state['iteration_count'] += 1
        
        workflow_logger.log_debug(f"质量检查 - 迭代次数: {state['iteration_count']}/{state['max_iterations']}")
        
        # 检查是否达到最大迭代次数
        if state['iteration_count'] >= state['max_iterations']:
            state['status'] = "completed"
            state['termination_reason'] = "max_iterations"
            workflow_logger.log_warning(f"达到最大迭代次数: {state['max_iterations']}", "quality_checker")
            workflow_logger.log_node_end("quality_checker", {"termination_reason": "max_iterations"})
            return state
        
        # 检查是否有足够的搜索结果
        if len(state.get('search_results', [])) >= 3:
            state['status'] = "completed"
            state['termination_reason'] = "sufficient_results"
            workflow_logger.log_info(f"获得足够搜索结果: {len(state.get('search_results', []))}条", "quality_checker")
            workflow_logger.log_node_end("quality_checker", {"termination_reason": "sufficient_results"})
            return state
        
        # 检查对话质量（简单的重复检测）
        if len(state.get('messages', [])) >= 10:
            recent_messages = state['messages'][-5:]
            if self._check_message_repetition(recent_messages):
                state['status'] = "completed"
                state['termination_reason'] = "repetition_detected"
                workflow_logger.log_warning("检测到消息重复", "quality_checker")
                workflow_logger.log_node_end("quality_checker", {"termination_reason": "repetition_detected"})
                return state
        
        # 重置查询以进行下一轮搜索
        state['current_query'] = None
        workflow_logger.log_state_transition("quality_checker", "topic_analyzer", "继续下一轮搜索")
        workflow_logger.log_node_end("quality_checker", {"continue": True})
        
        return state
    
    def _check_message_repetition(self, messages: List) -> bool:
        """检查消息重复"""
        if len(messages) < 2:
            return False
        
        # 简单的重复检测：检查最近两条消息是否相似
        last_two = messages[-2:]
        if len(last_two) == 2:
            content1 = last_two[0].content if hasattr(last_two[0], 'content') else str(last_two[0])
            content2 = last_two[1].content if hasattr(last_two[1], 'content') else str(last_two[1])
            # 如果两条消息内容相似度超过80%，认为重复
            similarity = self._calculate_similarity(content1, content2)
            workflow_logger.log_debug(f"消息相似度: {similarity:.2f}")
            return similarity > 0.8
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简单实现）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _should_continue(self, state: SearchState) -> str:
        """决定是否继续工作流"""
        if state.get('status') == "completed":
            workflow_logger.log_state_transition("quality_checker", "END", f"工作流完成: {state.get('termination_reason')}")
            return "end"
        else:
            workflow_logger.log_state_transition("quality_checker", "topic_analyzer", "继续工作流")
            return "continue"
    
    def process_topic(self, topic: str) -> Dict[str, Any]:
        """处理主题的完整工作流"""
        workflow_logger.log_workflow_start("SearchWorkflow", topic)
        
        try:
            # 初始化状态
            initial_state: SearchState = {
                "topic": topic,
                "current_query": None,
                "search_results": [],
                "summaries": [],
                "key_points": [],
                "messages": [],
                "status": "running",
                "termination_reason": None,
                "iteration_count": 0,
                "max_iterations": 20
            }
            
            workflow_logger.log_debug("初始化状态完成", initial_state)
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            workflow_logger.log_debug("工作流执行完成", final_state)
            
            # 构建最终结果 - 将BaseMessage转换为ChatMessage
            chat_history = []
            for msg in final_state.get('messages', []):
                if hasattr(msg, 'content'):
                    role = "assistant" if hasattr(msg, '__class__') and "AI" in msg.__class__.__name__ else "user"
                    chat_history.append(ChatMessage(
                        role=role,
                        content=msg.content,
                        timestamp=datetime.now()
                    ))
            
            final_result = FinalResult(
                status=final_state.get('status', 'unknown'),
                termination_reason=final_state.get('termination_reason'),
                search_results=final_state.get('search_results', []),
                summaries=final_state.get('summaries', []),
                key_points=final_state.get('key_points', []),
                chat_history=chat_history
            )
            
            # 保存结果
            self.storage.save_final_result(final_result)
            
            result_dict = final_result.dict()
            workflow_logger.log_workflow_end("SearchWorkflow", final_state.get('status', 'unknown'), result_dict)
            
            return result_dict
            
        except Exception as e:
            # 错误处理
            workflow_logger.log_error(f"工作流执行失败: {str(e)}", "process_topic")
            
            error_log = ErrorLog(
                error=str(e),
                topic=topic
            )
            self.storage.save_error_log(error_log)
            
            error_result = error_log.dict()
            workflow_logger.log_workflow_end("SearchWorkflow", "error", error_result)
            
            return error_result