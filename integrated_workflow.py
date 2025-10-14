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
from storage_models import SearchRoundRecord, IntegratedWorkflowRecord, DirectionScore, OptimizedReport, OptimizedWorkflowState
from email_formatter import EmailFormatter
from email_sender import EmailSender
from search_tools import SearchTools
from storage_utils import StorageUtils
from memory_manager import MemoryManager
from config import get_config
from logger import workflow_logger
from direction_evaluator import DirectionEvaluator
from report_optimizer import ReportOptimizer

# 导入现有的工作流
from question_workflow import QuestionWorkflow
from search_workflow import SearchWorkflow


# 使用新的优化工作流状态
# IntegratedWorkflowState 已移动到 storage_models.py 中作为 OptimizedWorkflowState


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
        
        # 记录相关
        self.workflow_records = []
        self.email_formatter = EmailFormatter()
        self.email_sender = EmailSender(config)
        
        # 新增组件
        self.direction_evaluator = DirectionEvaluator(config)
        self.report_optimizer = ReportOptimizer(config)
        
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
            workflow_logger.log_info("开始创建优化工作流状态图")
            workflow = StateGraph(OptimizedWorkflowState)
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
            workflow.add_node("direction_scoring", self._direction_scoring_node)
            workflow.add_node("report_optimization", self._report_optimization_node)
            workflow.add_node("email_generation", self._email_generation_node)
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
            workflow.add_edge("parallel_search", "direction_scoring")
            workflow.add_edge("direction_scoring", "report_optimization")
            workflow.add_edge("report_optimization", "email_generation")
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
            
            workflow.add_conditional_edges(
                "parallel_search",
                self._should_continue_after_search,
                {
                    "continue": "direction_scoring",
                    "error": END
                }
            )
            
            workflow.add_conditional_edges(
                "direction_scoring",
                self._should_continue_after_scoring,
                {
                    "continue": "report_optimization",
                    "error": END
                }
            )
            
            workflow.add_conditional_edges(
                "report_optimization",
                self._should_continue_after_optimization,
                {
                    "continue": "email_generation",
                    "error": END
                }
            )
            
            workflow_logger.log_info("所有条件边添加完成")
        except Exception as e:
            import traceback
            workflow_logger.log_error(f"添加条件边失败: {str(e)}")
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
    
    def _question_generation_node(self, state: OptimizedWorkflowState) -> OptimizedWorkflowState:
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
    
    def _parallel_search_node(self, state: OptimizedWorkflowState) -> OptimizedWorkflowState:
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
            original_topic = state.get('topic', '')
            question_directions = state.get('question_directions', [])
            
            # 创建问题到方向的映射
            question_to_direction = {}
            for direction in question_directions:
                for question in direction.questions:
                    question_to_direction[question.question] = direction.direction
            
            for i, question in enumerate(questions):
                direction = question_to_direction.get(question.question, 'unknown')
                task = {
                    "question_id": f"q_{i+1}",
                    "question": question.question,
                    "original_topic": original_topic,
                    "direction": direction,
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
                all_search_rounds = []
                
                for future in as_completed(future_to_task, timeout=self.search_timeout * len(questions)):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        if result:
                            state['search_results'].append(result)
                            task['status'] = "completed"
                            task['completed_at'] = datetime.now()
                            task['search_result'] = result
                            
                            # 收集搜索轮次记录
                            if 'search_rounds' in task:
                                all_search_rounds.extend(task['search_rounds'])
                        else:
                            task['status'] = "failed"
                            task['error'] = "搜索返回空结果"
                            state['search_errors'].append(f"任务 {task['question_id']}: 搜索返回空结果")
                            
                            # 收集失败的搜索轮次记录
                            if 'search_rounds' in task:
                                all_search_rounds.extend(task['search_rounds'])
                    except Exception as e:
                        task['status'] = "failed"
                        task['error'] = str(e)
                        state['search_errors'].append(f"任务 {task['question_id']}: {str(e)}")
                        workflow_logger.log_error(f"搜索任务失败: {task['question_id']} - {str(e)}")
                        
                        # 收集异常的搜索轮次记录
                        if 'search_rounds' in task:
                            all_search_rounds.extend(task['search_rounds'])
                    
                    completed_count += 1
                    state['search_progress'] = {
                        "completed": completed_count,
                        "total": len(search_tasks),
                        "success_rate": len(state['search_results']) / completed_count if completed_count > 0 else 0
                    }
                
                # 将所有搜索轮次记录添加到状态中
                state['search_rounds'] = all_search_rounds
            
            state['search_completed'] = True
            
            # 记录详细的搜索统计
            successful_rounds = [r for r in all_search_rounds if r.success]
            failed_rounds = [r for r in all_search_rounds if not r.success]
            
            workflow_logger.log_info(f"并行搜索完成，成功 {len(successful_rounds)} 个，失败 {len(failed_rounds)} 个", "parallel_search")
            
            # 如果有失败的搜索，记录详细错误信息
            if failed_rounds:
                workflow_logger.log_warning(f"失败的搜索轮次：{len(failed_rounds)}个")
                for failed_round in failed_rounds[:5]:  # 只记录前5个失败的原因
                    workflow_logger.log_warning(f"失败原因 - 问题：{failed_round.question}, 错误：{failed_round.error_message}")
            
            workflow_logger.log_node_end("parallel_search", {
                "completed": True, 
                "results_count": len(state['search_results']),
                "successful_rounds": len(successful_rounds),
                "failed_rounds": len(failed_rounds)
            })
            
        except Exception as e:
            state['search_completed'] = False
            state['search_errors'].append(str(e))
            workflow_logger.log_error(f"并行搜索异常: {str(e)}", "parallel_search")
            workflow_logger.log_node_end("parallel_search", {"error": str(e)})
        
        return state
    
    def _execute_single_search(self, task: Dict[str, Any]) -> Optional[SearchResult]:
        """执行单个搜索任务"""
        start_time = time.time()
        try:
            # 构建包含原问题和子问题的搜索上下文
            original_topic = task.get('original_topic', '')
            sub_question = task['question']
            
            # 如果原问题存在，将其与子问题结合
            if original_topic and original_topic != sub_question:
                search_context = f"原问题：{original_topic}\n子问题：{sub_question}\n\n请基于原问题和子问题生成搜索查询，确保搜索内容与原问题高度相关。"
            else:
                search_context = sub_question
            
            # 调用现有的SearchWorkflow，传入完整的搜索上下文
            result = self.search_workflow.process_topic(search_context)
            processing_time = time.time() - start_time
            
            if result.get("status") == "completed":
                # 获取搜索结果（SearchResult对象列表）
                search_results_list = result.get("search_results", [])
                
                # 提取所有SearchItem对象
                all_search_items = []
                for search_result in search_results_list:
                    if hasattr(search_result, 'results'):
                        all_search_items.extend(search_result.results)
                    elif isinstance(search_result, dict) and 'results' in search_result:
                        # 如果是字典格式，需要转换为SearchItem对象
                        for item_data in search_result['results']:
                            if isinstance(item_data, dict):
                                from storage_models import SearchItem
                                search_item = SearchItem(
                                    title=item_data.get('title', ''),
                                    snippet=item_data.get('snippet', ''),
                                    link=item_data.get('link', '')
                                )
                                all_search_items.append(search_item)
                
                # 提取摘要和关键点
                summaries = result.get("summaries", [])
                key_points = result.get("key_points", [])
                
                # 记录搜索轮次
                search_round = SearchRoundRecord(
                    round_number=task.get('priority', 0) + 1,
                    question=task['question'],
                    direction=task.get('direction', 'unknown'),
                    search_query=task['question'],
                    search_results=all_search_items,
                    summary=summaries[0] if summaries else "",
                    key_points=key_points,
                    success=True,
                    processing_time=processing_time
                )
                
                # 将记录添加到状态中
                if 'search_rounds' not in task:
                    task['search_rounds'] = []
                task['search_rounds'].append(search_round)
                
                # 创建SearchResult对象返回
                search_result = SearchResult(
                    query=task['question'],
                    results=all_search_items,
                    summaries=summaries,
                    key_points=key_points
                )
                
                return search_result
            else:
                # 记录失败的搜索
                search_round = SearchRoundRecord(
                    round_number=task.get('priority', 0) + 1,
                    question=task['question'],
                    direction=task.get('direction', 'unknown'),
                    search_query=task['question'],
                    success=False,
                    error_message=result.get('error', '未知错误'),
                    processing_time=processing_time
                )
                
                if 'search_rounds' not in task:
                    task['search_rounds'] = []
                task['search_rounds'].append(search_round)
                
                workflow_logger.log_warning(f"搜索任务失败: {task['question_id']} - {result.get('error', '未知错误')}")
                return None
                
        except Exception as e:
            processing_time = time.time() - start_time
            # 记录异常搜索
            search_round = SearchRoundRecord(
                round_number=task.get('priority', 0) + 1,
                question=task['question'],
                direction=task.get('direction', 'unknown'),
                search_query=task['question'],
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
            
            if 'search_rounds' not in task:
                task['search_rounds'] = []
            task['search_rounds'].append(search_round)
            
            workflow_logger.log_error(f"搜索任务执行异常: {task['question_id']} - {str(e)}")
            return None
    
    
    def _direction_scoring_node(self, state: OptimizedWorkflowState) -> OptimizedWorkflowState:
        """方向评分节点"""
        workflow_logger.log_node_start("direction_scoring", state)
        
        if not state.get('search_completed', False):
            state['scoring_completed'] = False
            state['scoring_error'] = "搜索未完成"
            workflow_logger.log_error("搜索未完成，跳过评分", "direction_scoring")
            return state
        
        try:
            question_directions = state.get('question_directions', [])
            search_rounds = state.get('search_rounds', [])
            
            workflow_logger.log_info(f"开始对{len(question_directions)}个方向进行评分")
            
            # 使用方向评分器进行评分
            direction_scores = self.direction_evaluator.evaluate_directions(question_directions, search_rounds)
            
            # 选择最佳方向
            best_direction = self.direction_evaluator.select_best_direction(direction_scores)
            
            state['direction_scores'] = direction_scores
            state['best_direction'] = best_direction
            state['scoring_completed'] = True
            state['scoring_error'] = None
            
            workflow_logger.log_info(f"方向评分完成，最佳方向：{best_direction}", "direction_scoring")
            workflow_logger.log_node_end("direction_scoring", {
                "completed": True,
                "best_direction": best_direction,
                "scores_count": len(direction_scores)
            })
            
        except Exception as e:
            state['scoring_completed'] = False
            state['scoring_error'] = str(e)
            workflow_logger.log_error(f"方向评分异常: {str(e)}", "direction_scoring")
            workflow_logger.log_node_end("direction_scoring", {"error": str(e)})
        
        return state
    
    def _report_optimization_node(self, state: OptimizedWorkflowState) -> OptimizedWorkflowState:
        """报告优化节点"""
        workflow_logger.log_node_start("report_optimization", state)
        
        if not state.get('scoring_completed', False):
            state['report_optimization_completed'] = False
            state['report_optimization_error'] = "评分未完成"
            workflow_logger.log_error("评分未完成，跳过报告优化", "report_optimization")
            return state
        
        try:
            topic = state.get('topic', '')
            direction_scores = state.get('direction_scores', [])
            question_directions = state.get('question_directions', [])
            search_rounds = state.get('search_rounds', [])
            
            workflow_logger.log_info("开始生成优化报告")
            
            # 使用报告优化器生成优化报告
            optimized_report = self.report_optimizer.generate_optimized_report(
                topic, direction_scores, question_directions, search_rounds
            )
            
            state['optimized_report'] = optimized_report
            state['report_optimization_completed'] = True
            state['report_optimization_error'] = None
            
            workflow_logger.log_info(f"报告优化完成，最佳方向：{optimized_report.best_direction}", "report_optimization")
            workflow_logger.log_node_end("report_optimization", {
                "completed": True,
                "best_direction": optimized_report.best_direction,
                "best_score": optimized_report.best_direction_score
            })
            
        except Exception as e:
            state['report_optimization_completed'] = False
            state['report_optimization_error'] = str(e)
            workflow_logger.log_error(f"报告优化异常: {str(e)}", "report_optimization")
            workflow_logger.log_node_end("report_optimization", {"error": str(e)})
        
        return state
    
    def _email_generation_node(self, state: OptimizedWorkflowState) -> OptimizedWorkflowState:
        """邮件生成节点"""
        workflow_logger.log_node_start("email_generation", state)
        
        try:
            optimized_report = state.get('optimized_report')
            if not optimized_report:
                state['email_sent'] = False
                state['final_email'] = "报告优化未完成，无法生成邮件"
                workflow_logger.log_error("报告优化未完成，无法生成邮件", "email_generation")
                return state
            
            # 生成优化邮件内容
            email_content = self.email_formatter.format_optimized_report(optimized_report)
            
            # 保存邮件到文件
            email_filepath = self.email_formatter.save_email_to_file(
                email_content, 
                f"optimized_email_{state.get('workflow_id', 'unknown')}.txt"
            )
            
            # 发送邮件
            workflow_logger.log_info("开始发送优化邮件...", "email_generation")
            email_result = self.email_sender.send_workflow_report({
                'topic': optimized_report.topic,
                'email_content': email_content,
                'optimized_report': optimized_report.dict()
            })
            
            if email_result.get("status") == "success":
                workflow_logger.log_info(f"邮件发送成功：{email_result.get('message_id', 'unknown')}", "email_generation")
                state['email_sent'] = True
            elif email_result.get("status") == "skipped":
                workflow_logger.log_warning("邮件发送跳过：配置不完整", "email_generation")
                state['email_sent'] = False
            else:
                workflow_logger.log_error(f"邮件发送失败：{email_result.get('error', 'unknown')}", "email_generation")
                state['email_sent'] = False
            
            state['final_email'] = email_content
            state['status'] = "completed"
            state['end_time'] = datetime.now()
            
            workflow_logger.log_info(f"邮件生成完成：{email_filepath}", "email_generation")
            workflow_logger.log_node_end("email_generation", {
                "completed": True,
                "email_file": email_filepath,
                "email_sent": state['email_sent']
            })
            
        except Exception as e:
            state['email_sent'] = False
            state['status'] = "error"
            state['error'] = str(e)
            workflow_logger.log_error(f"邮件生成异常: {str(e)}", "email_generation")
            workflow_logger.log_node_end("email_generation", {"error": str(e)})
        
        return state
    
    def _should_continue_after_questions(self, state: OptimizedWorkflowState) -> str:
        """问题生成后是否继续"""
        if state.get('question_generation_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_search(self, state: OptimizedWorkflowState) -> str:
        """搜索后是否继续"""
        if state.get('search_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_scoring(self, state: OptimizedWorkflowState) -> str:
        """评分后是否继续"""
        if state.get('scoring_completed', False):
            return "continue"
        else:
            return "error"
    
    def _should_continue_after_optimization(self, state: OptimizedWorkflowState) -> str:
        """优化后是否继续"""
        if state.get('report_optimization_completed', False):
            return "continue"
        else:
            return "error"
    
    def process_topic(self, topic: str) -> Dict[str, Any]:
        """处理主题的完整工作流"""
        workflow_logger.log_workflow_start("IntegratedWorkflow", topic)
        
        try:
            # 生成工作流ID
            workflow_id = f"integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 初始化状态
            initial_state: OptimizedWorkflowState = {
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
                "search_rounds": [],
                "search_completed": False,
                "search_errors": [],
                "direction_scores": [],
                "best_direction": None,
                "scoring_completed": False,
                "scoring_error": None,
                "optimized_report": None,
                "report_optimization_completed": False,
                "report_optimization_error": None,
                "final_email": None,
                "email_sent": False,
                "workflow_id": workflow_id
            }
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            # 构建最终结果
            result_dict = {
                "topic": final_state.get('topic', topic),
                "status": final_state.get('status', 'unknown'),
                "error": final_state.get('error'),
                "workflow_id": final_state.get('workflow_id', workflow_id),
                "optimized_report": final_state.get('optimized_report'),
                "direction_scores": final_state.get('direction_scores', []),
                "best_direction": final_state.get('best_direction'),
                "final_email": final_state.get('final_email'),
                "email_sent": final_state.get('email_sent', False),
                "execution_stats": {
                    "total_time": self._calculate_total_time(final_state),
                    "questions_generated": len(final_state.get('questions', [])),
                    "searches_completed": len(final_state.get('search_results', [])),
                    "search_errors": len(final_state.get('search_errors', [])),
                    "directions_scored": len(final_state.get('direction_scores', [])),
                    "success_rate": len(final_state.get('search_results', [])) / max(len(final_state.get('questions', [])), 1)
                },
                "generated_at": datetime.now().isoformat()
            }
            
            workflow_logger.log_workflow_end("OptimizedIntegratedWorkflow", final_state.get('status', 'unknown'), result_dict)
            
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
    
    def _calculate_total_time(self, final_state: OptimizedWorkflowState) -> float:
        """计算总执行时间"""
        try:
            start_time = final_state.get('start_time')
            end_time = final_state.get('end_time')
            
            if start_time and end_time:
                return (end_time - start_time).total_seconds()
            elif start_time:
                return (datetime.now() - start_time).total_seconds()
            else:
                return 0.0
        except Exception:
            return 0.0
