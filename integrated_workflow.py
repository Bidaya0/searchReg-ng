"""
集成问题生成与搜索总结工作流
基于现有的QuestionWorkflow和SearchWorkflow实现端到端的主题分析流程
"""

from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
import traceback

from storage_models import QuestionState, QuestionDirection, QuestionItem, QuestionsResult
from storage_models import SearchState, SearchResult, ChatMessage, FinalResult, ErrorLog
from search_tools import SearchTools
from storage_utils import StorageUtils
from memory_manager import MemoryManager
from config import get_config
from logger import workflow_logger

# 导入现有的工作流
from question_workflow import QuestionWorkflow
from search_workflow import SearchWorkflow


class IntegratedWorkflowState(TypedDict):
    """集成工作流状态类型定义"""
    # 基础信息
    topic: str
    status: str
    error: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    
    # 问题生成阶段
    questions: List[QuestionItem]
    question_directions: List[QuestionDirection]
    question_generation_completed: bool
    question_generation_error: Optional[str]
    
    # 搜索阶段
    search_tasks: List[Dict[str, Any]]
    search_results: List[SearchResult]
    search_progress: Dict[str, Any]
    search_completed: bool
    search_errors: List[str]
    
    # 结果处理阶段
    processed_results: Optional[Dict[str, Any]]
    result_processing_completed: bool
    result_processing_error: Optional[str]
    
    # 汇总阶段
    integrated_summary: Optional[Dict[str, Any]]
    summary_completed: bool
    summary_error: Optional[str]
    
    # 最终结果
    final_report: Optional[Dict[str, Any]]
    report_generated: bool


class IntegratedWorkflowController:
    """集成工作流控制器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage = StorageUtils()
        
        # 初始化现有工作流
        self.question_workflow = QuestionWorkflow(config)
        self.search_workflow = SearchWorkflow(config)
        
        # 初始化LLM（用于汇总）
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 2000)
        )
        
        # 并发配置
        self.max_workers = config.get('max_concurrent_searches', 5)
        self.search_timeout = config.get('search_timeout', 30)
        self.retry_count = config.get('search_retry_count', 3)
        
        # 创建状态图
        try:
            self.workflow = self._create_workflow()
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"创建集成工作流失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
    
    def _create_workflow(self) -> StateGraph:
        """创建集成工作流"""
        try:
            workflow_logger.log_info("开始创建集成工作流状态图")
            workflow = StateGraph(IntegratedWorkflowState)
            workflow_logger.log_info("状态图创建成功")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"创建状态图失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
        
        # 添加节点
        try:
            workflow_logger.log_info("开始添加节点")
            workflow.add_node("question_generation", self._question_generation_node)
            workflow.add_node("parallel_search", self._parallel_search_node)
            workflow.add_node("result_processing", self._result_processing_node)
            workflow.add_node("summary_generator", self._integrated_summary_node)
            workflow.add_node("report_generation", self._report_generation_node)
            workflow_logger.log_info("节点添加完成")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"添加节点失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
        
        # 设置入口点
        workflow.set_entry_point("question_generation")
        
        # 添加边
        try:
            workflow_logger.log_info("开始添加边")
            workflow.add_edge("question_generation", "parallel_search")
            workflow.add_edge("parallel_search", "result_processing")
            workflow.add_edge("result_processing", "summary_generator")
            workflow.add_edge("summary_generator", "report_generation")
            workflow_logger.log_info("边添加完成")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"添加边失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
        
        # 条件边
        try:
            workflow_logger.log_info("开始添加条件边")
            workflow.add_conditional_edges(
                "question_generation",
                self._should_continue_after_questions,
                {
                    "continue": "parallel_search",
                    "error": END
                }
            )
            workflow_logger.log_info("条件边添加完成")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"添加条件边失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
        
        try:
            workflow.add_conditional_edges(
                "parallel_search",
                self._should_continue_after_search,
                {
                    "continue": "result_processing",
                    "error": END
                }
            )
            
            workflow.add_conditional_edges(
                "result_processing",
                self._should_continue_after_processing,
                {
                    "continue": "summary_generator",
                    "error": END
                }
            )
            
            workflow.add_conditional_edges(
                "summary_generator",
                self._should_continue_after_summary,
                {
                    "continue": "report_generation",
                    "error": END
                }
            )
            workflow_logger.log_info("所有条件边添加完成")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"添加剩余条件边失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
        
        try:
            workflow_logger.log_info("开始编译工作流")
            compiled_workflow = workflow.compile()
            workflow_logger.log_info("工作流编译完成")
            return compiled_workflow
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"编译工作流失败: {str(e)}")
            workflow_logger.log_error(f"调用栈:\n{traceback.format_exc()}")
            raise
    
    def _question_generation_node(self, state: IntegratedWorkflowState) -> IntegratedWorkflowState:
        """问题生成节点"""
        workflow_logger.log_node_start("question_generation", state)
        
        try:
            # 调用现有的问题生成工作流
            result = self.question_workflow.generate_questions(state['topic'])
            
            if result.get("status") == "completed":
                # 提取问题数据
                questions = []
                question_directions = []
                
                for direction_data in result.get('directions', []):
                    direction = QuestionDirection(
                        direction=direction_data['direction'],
                        rationale=direction_data.get('rationale', ''),
                        questions=[]
                    )
                    
                    for question_data in direction_data.get('questions', []):
                        question = QuestionItem(question=question_data['question'])
                        questions.append(question)
                        direction.questions.append(question)
                    
                    question_directions.append(direction)
                
                state['questions'] = questions
                state['question_directions'] = question_directions
                state['question_generation_completed'] = True
                state['question_generation_error'] = None
                
                workflow_logger.log_info(f"问题生成完成: {len(questions)}个问题", "question_generation")
            else:
                state['question_generation_completed'] = False
                state['question_generation_error'] = result.get('error', '问题生成失败')
                workflow_logger.log_error(f"问题生成失败: {state['question_generation_error']}", "question_generation")
            
            workflow_logger.log_node_end("question_generation", {"completed": state['question_generation_completed']})
            
        except Exception as e:
            state['question_generation_completed'] = False
            state['question_generation_error'] = str(e)
            workflow_logger.log_error(f"问题生成异常: {str(e)}", "question_generation")
            workflow_logger.log_node_end("question_generation", {"error": str(e)})
        
        return state
    
    def _parallel_search_node(self, state: IntegratedWorkflowState) -> IntegratedWorkflowState:
        """并行搜索节点"""
        workflow_logger.log_node_start("parallel_search", state)
        
        if not state.get('question_generation_completed', False):
            state['search_completed'] = False
            state['search_errors'] = ["问题生成未完成"]
            workflow_logger.log_error("问题生成未完成，跳过搜索", "parallel_search")
            return state
        
        try:
            questions = state.get('questions', [])
            workflow_logger.log_info(f"开始并行搜索 {len(questions)} 个问题")
            
            # 创建搜索任务
            search_tasks = []
            for i, question in enumerate(questions):
                task = {
                    "question_id": f"q_{i+1}",
                    "question": question.question,
                    "direction": getattr(question, 'direction', 'unknown'),
                    "priority": i,
                    "status": "pending",
                    "created_at": datetime.now(),
                    "completed_at": None,
                    "search_result": None,
                    "error": None
                }
                search_tasks.append(task)
            
            state['search_tasks'] = search_tasks
            state['search_results'] = []
            state['search_errors'] = []
            
            # 使用线程池执行并发搜索
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有搜索任务
                future_to_task = {
                    executor.submit(self._execute_single_search, task): task
                    for task in search_tasks
                }
                
                # 收集结果
                completed_count = 0
                for future in as_completed(future_to_task, timeout=self.search_timeout * len(questions)):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        if result:
                            state['search_results'].append(result)
                            task['status'] = "completed"
                            task['completed_at'] = datetime.now()
                            task['search_result'] = result
                        else:
                            task['status'] = "failed"
                            task['error'] = "搜索返回空结果"
                            state['search_errors'].append(f"任务 {task['question_id']}: 搜索返回空结果")
                    except Exception as e:
                        task['status'] = "failed"
                        task['error'] = str(e)
                        state['search_errors'].append(f"任务 {task['question_id']}: {str(e)}")
                        workflow_logger.log_error(f"搜索任务失败: {task['question_id']} - {str(e)}")
                    
                    completed_count += 1
                    state['search_progress'] = {
                        "completed": completed_count,
                        "total": len(search_tasks),
                        "success_rate": len(state['search_results']) / completed_count if completed_count > 0 else 0
                    }
            
            state['search_completed'] = True
            workflow_logger.log_info(f"并行搜索完成，成功 {len(state['search_results'])} 个，失败 {len(questions) - len(state['search_results'])} 个", "parallel_search")
            workflow_logger.log_node_end("parallel_search", {"completed": True, "results_count": len(state['search_results'])})
            
        except Exception as e:
            state['search_completed'] = False
            state['search_errors'].append(str(e))
            workflow_logger.log_error(f"并行搜索异常: {str(e)}", "parallel_search")
            workflow_logger.log_node_end("parallel_search", {"error": str(e)})
        
        return state
    
    def _execute_single_search(self, task: Dict[str, Any]) -> Optional[SearchResult]:
        """执行单个搜索任务"""
        try:
            # 调用现有的SearchWorkflow
            result = self.search_workflow.process_topic(task['question'])
            
            if result.get("status") == "completed":
                # 转换结果格式
                search_result = SearchResult(
                    query=task['question'],
                    results=result.get("search_results", []),
                    summaries=result.get("summaries", []),
                    key_points=result.get("key_points", [])
                )
                return search_result
            else:
                workflow_logger.log_warning(f"搜索任务失败: {task['question_id']} - {result.get('error', '未知错误')}")
                return None
                
        except Exception as e:
            workflow_logger.log_error(f"搜索任务执行异常: {task['question_id']} - {str(e)}")
            return None
    
    def _result_processing_node(self, state: IntegratedWorkflowState) -> IntegratedWorkflowState:
        """结果处理节点"""
        workflow_logger.log_node_start("result_processing", state)
        
        if not state.get('search_completed', False):
            state['result_processing_completed'] = False
            state['result_processing_error'] = "搜索未完成"
            workflow_logger.log_error("搜索未完成，跳过结果处理", "result_processing")
            return state
        
        try:
            search_results = state.get('search_results', [])
            workflow_logger.log_info(f"开始处理 {len(search_results)} 个搜索结果")
            
            # 简单的结果处理
            processed_results = {
                "total_results": len(search_results),
                "unique_results": len(search_results),  # 简化处理，暂不去重
                "quality_scores": {},
                "categorized_results": {},
                "processing_time": 0.0
            }
            
            # 按方向分类结果
            for result in search_results:
                direction = "unknown"
                for task in state.get('search_tasks', []):
                    if task.get('question') == result.query:
                        direction = task.get('direction', 'unknown')
                        break
                
                if direction not in processed_results['categorized_results']:
                    processed_results['categorized_results'][direction] = []
                processed_results['categorized_results'][direction].append(result)
            
            state['processed_results'] = processed_results
            state['result_processing_completed'] = True
            state['result_processing_error'] = None
            
            workflow_logger.log_info(f"结果处理完成，分类到 {len(processed_results['categorized_results'])} 个方向", "result_processing")
            workflow_logger.log_node_end("result_processing", {"completed": True})
            
        except Exception as e:
            state['result_processing_completed'] = False
            state['result_processing_error'] = str(e)
            workflow_logger.log_error(f"结果处理异常: {str(e)}", "result_processing")
            workflow_logger.log_node_end("result_processing", {"error": str(e)})
        
        return state
    
    def _integrated_summary_node(self, state: IntegratedWorkflowState) -> IntegratedWorkflowState:
        """综合总结节点"""
        workflow_logger.log_node_start("summary_generator", state)
        
        if not state.get('result_processing_completed', False):
            state['summary_completed'] = False
            state['summary_error'] = "结果处理未完成"
            workflow_logger.log_error("结果处理未完成，跳过总结", "summary_generator")
            return state
        
        try:
            processed_results = state.get('processed_results', {})
            workflow_logger.log_info("开始生成综合总结")
            
            # 构建汇总提示词
            summary_prompt = self._build_summary_prompt(processed_results, state.get('topic', ''))
            
            # 调用LLM生成总结
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=summary_prompt)
            ]
            
            response = self.llm.invoke(messages)
            summary_content = response.content
            
            # 解析总结内容
            comprehensive_summary = self._parse_summary_content(summary_content, processed_results)
            
            state['integrated_summary'] = comprehensive_summary
            state['summary_completed'] = True
            state['summary_error'] = None
            
            workflow_logger.log_info("综合总结生成完成", "summary_generator")
            workflow_logger.log_node_end("summary_generator", {"completed": True})
            
        except Exception as e:
            state['summary_completed'] = False
            state['summary_error'] = str(e)
            workflow_logger.log_error(f"综合总结异常: {str(e)}", "summary_generator")
            workflow_logger.log_node_end("summary_generator", {"error": str(e)})
        
        return state
    
    def _build_summary_prompt(self, processed_results: Dict[str, Any], topic: str) -> str:
        """构建汇总提示词"""
        prompt_parts = [
            f"请对以下关于'{topic}'的搜索结果进行综合分析和总结：",
            f"",
            f"总结果数：{processed_results.get('total_results', 0)}",
            f"去重后结果数：{processed_results.get('unique_results', 0)}",
            f"",
            f"按方向分类的结果："
        ]
        
        categorized_results = processed_results.get('categorized_results', {})
        for direction, results in categorized_results.items():
            prompt_parts.append(f"\n{direction}方向：")
            for i, result in enumerate(results[:3], 1):  # 只取前3个结果
                prompt_parts.append(f"  {i}. {result.query}")
                if hasattr(result, 'summaries') and result.summaries:
                    prompt_parts.append(f"     总结：{result.summaries[0][:200]}...")
        
        prompt_parts.extend([
            f"",
            f"请按照以下格式生成综合总结：",
            f"1. 执行摘要（200-300字）",
            f"2. 按方向分类的详细分析",
            f"3. 关键洞察和发现（5-10个）",
            f"4. 跨方向关联性发现",
            f"5. 建议和后续行动"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的汇总者智能体，负责对多个问题的搜索结果进行综合总结。

你的任务：
1. 分析所有问题的搜索结果
2. 识别关键信息和洞察
3. 生成结构化的综合报告
4. 提取跨问题的关联性发现
5. 提供实用的建议和后续行动

要求：
- 总结要准确、全面、有层次
- 关键洞察要具体、可操作
- 语言要专业、简洁
- 结构要清晰、逻辑性强"""
    
    def _parse_summary_content(self, content: str, processed_results: Dict[str, Any]) -> Dict[str, Any]:
        """解析总结内容"""
        # 简单的解析实现
        lines = content.split('\n')
        executive_summary = ""
        detailed_analysis = {}
        key_insights = []
        cross_cutting_findings = []
        recommendations = []
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "执行摘要" in line or "摘要" in line:
                current_section = "executive_summary"
                current_content = []
            elif "详细分析" in line or "分析" in line:
                current_section = "detailed_analysis"
                current_content = []
            elif "关键洞察" in line or "洞察" in line:
                current_section = "key_insights"
                current_content = []
            elif "关联性" in line or "关联" in line:
                current_section = "cross_cutting"
                current_content = []
            elif "建议" in line or "后续行动" in line:
                current_section = "recommendations"
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # 处理各节内容
        if current_section == "executive_summary":
            executive_summary = "\n".join(current_content)
        elif current_section == "key_insights":
            key_insights = [item.strip() for item in current_content if item.strip()]
        elif current_section == "cross_cutting":
            cross_cutting_findings = [item.strip() for item in current_content if item.strip()]
        elif current_section == "recommendations":
            recommendations = [item.strip() for item in current_content if item.strip()]
        
        return {
            "executive_summary": executive_summary,
            "detailed_analysis": detailed_analysis,
            "key_insights": key_insights,
            "cross_cutting_findings": cross_cutting_findings,
            "recommendations": recommendations,
            "confidence_scores": {},
            "generated_at": datetime.now().isoformat()
        }
    
    def _report_generation_node(self, state: IntegratedWorkflowState) -> IntegratedWorkflowState:
        """报告生成节点"""
        workflow_logger.log_node_start("report_generation", state)
        
        try:
            # 构建最终报告
            final_report = {
                "topic": state['topic'],
                "questions": [q.question for q in state.get('questions', [])],
                "search_results": state.get('search_results', []),
                "processed_results": state.get('processed_results', {}),
                "comprehensive_summary": state.get('integrated_summary', {}),
                "execution_stats": {
                    "total_time": (datetime.now() - state['start_time']).total_seconds(),
                    "questions_generated": len(state.get('questions', [])),
                    "searches_completed": len(state.get('search_results', [])),
                    "search_errors": len(state.get('search_errors', [])),
                    "success_rate": len(state.get('search_results', [])) / max(len(state.get('questions', [])), 1)
                },
                "generated_at": datetime.now().isoformat()
            }
            
            state['final_report'] = final_report
            state['report_generated'] = True
            state['status'] = "completed"
            state['end_time'] = datetime.now()
            
            # 保存结果
            self.storage.save(final_report, "results", f"integrated_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            workflow_logger.log_info("最终报告生成完成", "report_generation")
            workflow_logger.log_node_end("report_generation", {"completed": True})
            
        except Exception as e:
            state['report_generated'] = False
            state['status'] = "error"
            state['error'] = str(e)
            workflow_logger.log_error(f"报告生成异常: {str(e)}", "report_generation")
            workflow_logger.log_node_end("report_generation", {"error": str(e)})
        
        return state
    
    def _should_continue_after_questions(self, state: IntegratedWorkflowState) -> str:
        """问题生成后是否继续"""
        if state.get('question_generation_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_search(self, state: IntegratedWorkflowState) -> str:
        """搜索后是否继续"""
        if state.get('search_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_processing(self, state: IntegratedWorkflowState) -> str:
        """结果处理后是否继续"""
        if state.get('result_processing_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_summary(self, state: IntegratedWorkflowState) -> str:
        """总结后是否继续"""
        if state.get('summary_completed', False):
            return "continue"
        else:
            return "error"
    
    def process_topic(self, topic: str) -> Dict[str, Any]:
        """处理主题的完整工作流"""
        workflow_logger.log_workflow_start("IntegratedWorkflow", topic)
        
        try:
            # 初始化状态
            initial_state: IntegratedWorkflowState = {
                "topic": topic,
                "status": "running",
                "error": None,
                "start_time": datetime.now(),
                "end_time": None,
                "questions": [],
                "question_directions": [],
                "question_generation_completed": False,
                "question_generation_error": None,
                "search_tasks": [],
                "search_results": [],
                "search_progress": {},
                "search_completed": False,
                "search_errors": [],
                "processed_results": None,
                "result_processing_completed": False,
                "result_processing_error": None,
                "integrated_summary": None,
                "summary_completed": False,
                "summary_error": None,
                "final_report": None,
                "report_generated": False
            }
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            # 构建最终结果
            result_dict = final_state.get('final_report', {})
            result_dict['status'] = final_state.get('status', 'unknown')
            result_dict['error'] = final_state.get('error')
            
            workflow_logger.log_workflow_end("IntegratedWorkflow", final_state.get('status', 'unknown'), result_dict)
            
            return result_dict
            
        except Exception as e:
            error_result = {
                "topic": topic,
                "status": "error",
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
            workflow_logger.log_error(f"集成工作流执行失败: {str(e)}", "process_topic")
            return error_result
