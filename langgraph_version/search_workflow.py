from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import SearchState, SearchResult, ChatMessage, FinalResult, ErrorLog
from search_tools import SearchTools
from storage_utils import StorageUtils
from config import get_config
import json

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
        system_prompt = """你是一个主题分析专家，负责分析用户输入的主题，提取关键词和生成搜索建议。
        你需要：
        1. 分析主题的核心概念，并进行扩展性陈述。
        2. 评估主题的搜索难度。
        3. 根据已有搜索结果，生成新的搜索建议。
        4. 给搜索执行器提供具体的搜索查询建议。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析主题：{state.topic}")
        ]
        
        # 如果有历史消息，添加到上下文中
        for msg in state.messages[-5:]:  # 只取最近5条消息
            if msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            else:
                messages.append(HumanMessage(content=msg.content))
        
        response = self.llm.invoke(messages)
        
        # 更新状态
        state.messages.append(ChatMessage(
            role="assistant",
            content=response.content
        ))
        
        return state
    
    def _search_executor_node(self, state: SearchState) -> SearchState:
        """搜索执行节点"""
        system_prompt = """你是一个搜索执行专家，负责执行搜索请求并管理搜索结果。
        你必须：
        1. 在每次对话中至少执行一次搜索工具调用
        2. 根据主题分析结果构建搜索查询
        3. 执行搜索并评估结果
        4. 如果搜索失败，明确说明原因并建议解决方案"""
        
        # 构建搜索查询
        if not state.current_query:
            # 基于主题生成搜索查询
            query_prompt = f"基于主题 '{state.topic}' 生成一个具体的搜索查询词"
            query_response = self.llm.invoke([
                SystemMessage(content="你是一个搜索查询生成专家，根据主题生成具体的搜索查询词。"),
                HumanMessage(content=query_prompt)
            ])
            state.current_query = query_response.content.strip()
        
        try:
            # 执行搜索
            search_result = self.search_tools.search_query(
                state.current_query,
                self.config.get("max_results", 20)
            )
            
            state.search_results.append(search_result)
            
            # 生成搜索总结
            search_summary = f"搜索查询：{state.current_query}\n搜索结果：{len(search_result.results)}条\n"
            search_summary += self.search_tools.format_search_results(search_result)
            
            state.messages.append(ChatMessage(
                role="assistant",
                content=f"搜索完成：\n{search_summary}"
            ))
            
        except Exception as e:
            error_msg = f"搜索失败：{str(e)}"
            state.messages.append(ChatMessage(
                role="assistant",
                content=error_msg
            ))
        
        return state
    
    def _content_recorder_node(self, state: SearchState) -> SearchState:
        """内容记录节点"""
        system_prompt = """你是一个内容记录专家，负责记录和总结搜索结果。
        搜索结果可能会有多语言场景，请尝试将搜索到的结果用中文进行总结。
        你需要：
        1. 对搜索结果进行分类和标记
        2. 生成结构化摘要
        3. 提取关键点
        4. 避免重复之前已经讨论过的内容"""
        
        if not state.search_results:
            return state
        
        # 获取最新的搜索结果
        latest_search = state.search_results[-1]
        search_content = self.search_tools.format_search_results(latest_search)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请总结以下搜索结果：\n{search_content}")
        ]
        
        response = self.llm.invoke(messages)
        
        # 提取关键点
        key_points_prompt = f"从以下内容中提取3-5个关键点：\n{response.content}"
        key_points_response = self.llm.invoke([
            SystemMessage(content="你是一个关键点提取专家，从文本中提取最重要的关键点。"),
            HumanMessage(content=key_points_prompt)
        ])
        
        # 更新状态
        state.summaries.append(response.content)
        state.key_points.append(key_points_response.content)
        
        state.messages.append(ChatMessage(
            role="assistant",
            content=f"内容总结完成：\n{response.content}\n\n关键点：\n{key_points_response.content}"
        ))
        
        return state
    
    def _quality_checker_node(self, state: SearchState) -> SearchState:
        """质量检查节点"""
        state.iteration_count += 1
        
        # 检查是否达到最大迭代次数
        if state.iteration_count >= state.max_iterations:
            state.status = "completed"
            state.termination_reason = "max_iterations"
            return state
        
        # 检查是否有足够的搜索结果
        if len(state.search_results) >= 3:
            state.status = "completed"
            state.termination_reason = "sufficient_results"
            return state
        
        # 检查对话质量（简单的重复检测）
        if len(state.messages) >= 10:
            recent_messages = state.messages[-5:]
            if self._check_message_repetition(recent_messages):
                state.status = "completed"
                state.termination_reason = "repetition_detected"
                return state
        
        # 重置查询以进行下一轮搜索
        state.current_query = None
        
        return state
    
    def _check_message_repetition(self, messages: List[ChatMessage]) -> bool:
        """检查消息重复"""
        if len(messages) < 2:
            return False
        
        # 简单的重复检测：检查最近两条消息是否相似
        last_two = messages[-2:]
        if len(last_two) == 2:
            content1 = last_two[0].content
            content2 = last_two[1].content
            # 如果两条消息内容相似度超过80%，认为重复
            similarity = self._calculate_similarity(content1, content2)
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
        if state.status == "completed":
            return "end"
        else:
            return "continue"
    
    def process_topic(self, topic: str) -> Dict[str, Any]:
        """处理主题的完整工作流"""
        try:
            # 初始化状态
            initial_state = SearchState(topic=topic)
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            # 构建最终结果
            final_result = FinalResult(
                status=final_state.status,
                termination_reason=final_state.termination_reason,
                search_results=final_state.search_results,
                summaries=final_state.summaries,
                key_points=final_state.key_points,
                chat_history=final_state.messages
            )
            
            # 保存结果
            self.storage.save_final_result(final_result)
            
            return final_result.dict()
            
        except Exception as e:
            # 错误处理
            error_log = ErrorLog(
                error=str(e),
                topic=topic
            )
            self.storage.save_error_log(error_log)
            
            return error_log.dict()
