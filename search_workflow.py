from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import SearchState, SearchResult, ChatMessage, FinalResult, ErrorLog
from search_tools import SearchTools
from storage_utils import StorageUtils
from memory_manager import MemoryManager
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
        self.memory_manager = MemoryManager(self.storage)
        
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
        workflow.add_node("memory_loader", self._memory_loader_node)
        workflow.add_node("topic_analyzer", self._topic_analyzer_node)
        workflow.add_node("search_executor", self._search_executor_node)
        workflow.add_node("content_recorder", self._content_recorder_node)
        workflow.add_node("memory_updater", self._memory_updater_node)
        workflow.add_node("quality_checker", self._quality_checker_node)
        
        # 设置入口点
        workflow.set_entry_point("memory_loader")
        
        # 添加边
        workflow.add_edge("memory_loader", "topic_analyzer")
        workflow.add_edge("topic_analyzer", "search_executor")
        workflow.add_edge("search_executor", "content_recorder")
        workflow.add_edge("content_recorder", "memory_updater")
        workflow.add_edge("memory_updater", "quality_checker")
        
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
    
    def _memory_loader_node(self, state: SearchState) -> SearchState:
        """记忆加载节点"""
        workflow_logger.log_node_start("memory_loader", state)
        
        try:
            # 加载记忆数据
            memory_data = self.memory_manager.load_memory()
            
            # 初始化记忆相关字段
            state['historical_topics'] = memory_data.get('historical_topics', [])
            state['learning_mode'] = memory_data.get('user_preferences', {}).get('learning_mode', True)
            state['knowledge_graph'] = memory_data.get('knowledge_graph', {})
            state['related_concepts'] = self.memory_manager.get_related_concepts(state['topic'], memory_data)
            state['user_preferences'] = memory_data.get('user_preferences', {})
            state['session_memory'] = {}
            state['context_memory'] = self.memory_manager.get_context_memory(state['topic'], memory_data)
            state['search_patterns'] = memory_data.get('search_patterns', [])
            
            # 添加主题到历史记录
            memory_data = self.memory_manager.add_topic_to_history(state['topic'], memory_data)
            self.memory_manager.save_memory(memory_data)
            
            # 生成记忆上下文消息
            context_info = self._generate_memory_context_message(state)
            if context_info:
                context_message = AIMessage(content=context_info)
                if 'messages' not in state:
                    state['messages'] = []
                state['messages'].append(context_message)
            
            workflow_logger.log_info(f"加载记忆完成: 历史主题{len(state['historical_topics'])}个, 相关概念{len(state['related_concepts'])}个", "memory_loader")
            workflow_logger.log_node_end("memory_loader", {"memory_loaded": True})
            
        except Exception as e:
            workflow_logger.log_error(f"记忆加载失败: {str(e)}", "memory_loader")
            # 初始化默认值
            state['historical_topics'] = []
            state['learning_mode'] = True
            state['knowledge_graph'] = {}
            state['related_concepts'] = []
            state['user_preferences'] = {}
            state['session_memory'] = {}
            state['context_memory'] = []
            state['search_patterns'] = []
        
        return state
    
    def _generate_memory_context_message(self, state: SearchState) -> str:
        """生成记忆上下文消息"""
        context_parts = []
        
        # 历史主题信息
        if state.get('historical_topics'):
            recent_topics = state['historical_topics'][-3:]  # 最近3个主题
            context_parts.append(f"相关历史主题: {', '.join(recent_topics)}")
        
        # 相关概念信息
        if state.get('related_concepts'):
            concepts = state['related_concepts'][:5]  # 前5个概念
            context_parts.append(f"相关概念: {', '.join(concepts)}")
        
        # 学习模式信息
        if state.get('learning_mode'):
            context_parts.append("学习模式已启用，将记录和关联新知识")
        
        # 上下文记忆信息
        if state.get('context_memory'):
            context_parts.append(f"发现 {len(state['context_memory'])} 个相关上下文")
        
        if context_parts:
            return f"记忆上下文:\n" + "\n".join(f"- {part}" for part in context_parts)
        
        return ""
    
    def _topic_analyzer_node(self, state: SearchState) -> SearchState:
        """主题分析节点"""
        workflow_logger.log_node_start("topic_analyzer", state)
        
        system_prompt = """你是一个主题分析专家，负责分析用户输入的主题，提取关键词和生成搜索建议。
        你需要：
        1. 分析主题的核心概念，并进行扩展性陈述。
        2. 评估主题的搜索难度。
        3. 根据已有搜索结果，生成新的搜索建议。
        4. 给搜索执行器提供具体的搜索查询建议，确保搜索内容与原问题高度相关。
        5. 利用历史记忆和知识图谱，发现主题间的关联。
        6. 在学习模式下，特别关注新概念的学习和关联。
        7. 如果输入包含原问题和子问题，要确保分析结果与原问题保持一致，避免偏离主题。"""
        
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
            # 基于主题生成搜索查询，同时考虑原问题和子问题
            query_prompt = f"""原问题：{state['topic']}

请基于原问题生成一个具体的搜索查询词，确保搜索内容与原问题高度相关，避免偏离主题。"""
            query_response = self.llm.invoke([
                SystemMessage(content="你是一个搜索查询生成专家，根据原问题生成具体的搜索查询词。请确保搜索查询与原问题高度相关，避免偏离主题。"),
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
        2. 生成结构化摘要，确保内容与原问题高度相关
        3. 提取关键点，重点关注与原问题相关的信息
        4. 避免重复之前已经讨论过的内容
        5. 如果搜索结果偏离了原问题，要在总结中明确指出并重新聚焦到原问题"""
        
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
    
    def _memory_updater_node(self, state: SearchState) -> SearchState:
        """记忆更新节点"""
        workflow_logger.log_node_start("memory_updater", state)
        
        try:
            # 加载当前记忆数据
            memory_data = self.memory_manager.load_memory()
            
            # 更新知识图谱
            if state.get('search_results'):
                memory_data = self.memory_manager.update_knowledge_graph(
                    state['topic'], 
                    state['search_results'], 
                    memory_data
                )
            
            # 更新搜索模式
            if state.get('current_query'):
                success = len(state.get('search_results', [])) > 0
                memory_data = self.memory_manager.update_search_patterns(
                    state['topic'],
                    state['current_query'],
                    success,
                    memory_data
                )
            
            # 更新会话记忆
            session_data = {
                'topic': state['topic'],
                'search_count': len(state.get('search_results', [])),
                'summary_count': len(state.get('summaries', [])),
                'key_points_count': len(state.get('key_points', [])),
                'iteration_count': state.get('iteration_count', 0)
            }
            memory_data = self.memory_manager.update_session_memory(session_data, memory_data)
            
            # 保存更新后的记忆
            self.memory_manager.save_memory(memory_data)
            
            # 更新状态中的记忆字段
            state['knowledge_graph'] = memory_data.get('knowledge_graph', {})
            state['search_patterns'] = memory_data.get('search_patterns', [])
            
            # 生成学习洞察消息
            insights = self.memory_manager.get_learning_insights(memory_data)
            if insights and state.get('learning_mode'):
                insight_message = AIMessage(content=f"学习洞察:\n" + "\n".join(f"- {insight}" for insight in insights))
                if 'messages' not in state:
                    state['messages'] = []
                state['messages'].append(insight_message)
            
            workflow_logger.log_info(f"记忆更新完成: 知识图谱{len(memory_data.get('knowledge_graph', {}))}个主题", "memory_updater")
            workflow_logger.log_node_end("memory_updater", {"memory_updated": True})
            
        except Exception as e:
            workflow_logger.log_error(f"记忆更新失败: {str(e)}", "memory_updater")
        
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
        
        # 基于记忆的智能终止条件
        search_results_count = len(state.get('search_results', []))
        
        # 检查是否有足够的搜索结果（基于历史模式调整阈值）
        min_results = self._get_adaptive_min_results(state)
        if search_results_count >= min_results:
            state['status'] = "completed"
            state['termination_reason'] = "sufficient_results"
            workflow_logger.log_info(f"获得足够搜索结果: {search_results_count}条 (阈值: {min_results})", "quality_checker")
            workflow_logger.log_node_end("quality_checker", {"termination_reason": "sufficient_results"})
            return state
        
        # 检查知识图谱覆盖度
        if self._check_knowledge_coverage(state):
            state['status'] = "completed"
            state['termination_reason'] = "knowledge_coverage"
            workflow_logger.log_info("知识图谱覆盖度达到要求", "quality_checker")
            workflow_logger.log_node_end("quality_checker", {"termination_reason": "knowledge_coverage"})
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
    
    def _get_adaptive_min_results(self, state: SearchState) -> int:
        """基于历史模式获取自适应最小结果数"""
        base_min = 3
        
        # 基于历史搜索模式调整
        patterns = state.get('search_patterns', [])
        if patterns:
            # 计算历史成功率
            success_count = sum(1 for p in patterns if p.get('success', False))
            success_rate = success_count / len(patterns)
            
            # 根据成功率调整最小结果数
            if success_rate > 0.8:
                return max(base_min, 2)  # 高成功率，降低要求
            elif success_rate < 0.5:
                return max(base_min, 5)  # 低成功率，提高要求
        
        # 基于学习模式调整
        if state.get('learning_mode', False):
            return max(base_min, 4)  # 学习模式需要更多结果
        
        return base_min
    
    def _check_knowledge_coverage(self, state: SearchState) -> bool:
        """检查知识图谱覆盖度"""
        topic = state['topic']
        knowledge_graph = state.get('knowledge_graph', {})
        
        if topic not in knowledge_graph:
            return False
        
        topic_data = knowledge_graph[topic]
        concepts = topic_data.get('concepts', [])
        relationships = topic_data.get('relationships', [])
        
        # 检查概念数量
        if len(concepts) < 5:
            return False
        
        # 检查关系数量
        if len(relationships) < 3:
            return False
        
        # 检查搜索次数（需要多次搜索才能建立好的知识图谱）
        search_count = topic_data.get('search_count', 0)
        if search_count < 2:
            return False
        
        return True
    
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
                "max_iterations": 20,
                # 记忆相关字段将在memory_loader节点中初始化
                "historical_topics": [],
                "learning_mode": True,
                "knowledge_graph": {},
                "related_concepts": [],
                "user_preferences": {},
                "session_memory": {},
                "context_memory": [],
                "search_patterns": []
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